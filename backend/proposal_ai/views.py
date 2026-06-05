import sys
import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
import json
import queue
import threading
from pathlib import Path

from django.http import FileResponse, Http404, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rag.crew import ProgressCallbackScope
from .models import ChatMessage, Conversation
from .serializers import (
    ChatMessageSerializer,
    ConversationDetailSerializer,
    ConversationSerializer,
    ProposalRequestSerializer,
)
from .services import generate_proposal

_SAFE_FILENAME_RE = re.compile(r'^[\w\s\-\.]+$')
_ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc'}


def _make_title(query: str) -> str:
    words = query.split()
    return " ".join(words[:8])[:200]


class GenerateProposalView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ProposalRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data["query"]
        use_web_search = serializer.validated_data.get("use_web_search", False)
        conversation_id = serializer.validated_data.get("conversation_id", None)
        tone = serializer.validated_data.get("tone", "balanced")
        person_name = serializer.validated_data.get("person_name", "")
        company_name = serializer.validated_data.get("company_name", "")
        output_format = serializer.validated_data.get("output_format", "proposal")

        try:
            result = generate_proposal(
                query,
                use_web_search=use_web_search,
                tone=tone,
                person_name=person_name,
                company_name=company_name,
                output_format=output_format,
                conversation_id=conversation_id,
                user=request.user if request.user.is_authenticated else None,
            )
        except RuntimeError as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception:
            return Response(
                {"error": "Failed to generate a response. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if request.user.is_authenticated:
            if conversation_id:
                conv = get_object_or_404(Conversation, pk=conversation_id, user=request.user)
            else:
                conv = Conversation.objects.create(user=request.user, title=_make_title(query))

            ChatMessage.objects.create(conversation=conv, role=ChatMessage.ROLE_USER, text=query)
            ChatMessage.objects.create(conversation=conv, role=ChatMessage.ROLE_ASSISTANT, proposal_data=result)

            result = {**result, "conversation_id": conv.id, "conversation_title": conv.title}

        return Response(result, status=status.HTTP_200_OK)


class StreamingProposalView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ProposalRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data["query"]
        use_web_search = serializer.validated_data.get("use_web_search", False)
        conversation_id = serializer.validated_data.get("conversation_id", None)
        tone = serializer.validated_data.get("tone", "balanced")
        person_name = serializer.validated_data.get("person_name", "")
        company_name = serializer.validated_data.get("company_name", "")
        output_format = serializer.validated_data.get("output_format", "proposal")
        user = request.user

        event_queue = queue.Queue()

        def worker():
            from django import db
            try:
                def on_progress(stage, message):
                    event_queue.put({"type": "progress", "stage": stage, "message": message})

                with ProgressCallbackScope(on_progress):
                    res = generate_proposal(
                        query,
                        use_web_search=use_web_search,
                        tone=tone,
                        person_name=person_name,
                        company_name=company_name,
                        output_format=output_format,
                        conversation_id=conversation_id,
                        user=user,
                    )
                event_queue.put({"type": "complete", "data": res})
            except Exception as e:
                event_queue.put({"type": "error", "error": str(e)})
            finally:
                db.connections.close_all()

        t = threading.Thread(target=worker)
        t.start()

        def event_generator():
            yield f"data: {json.dumps({'stage': 'planning', 'message': '🔍 Analyzing your query...'})}\n\n"
            while True:
                try:
                    item = event_queue.get(timeout=300) # 5-minute limit per step
                except queue.Empty:
                    yield f"data: {json.dumps({'stage': 'error', 'message': 'Pipeline execution timed out.'})}\n\n"
                    break

                if item["type"] == "progress":
                    yield f"data: {json.dumps({'stage': item['stage'], 'message': item['message']})}\n\n"
                elif item["type"] == "error":
                    yield f"data: {json.dumps({'stage': 'error', 'message': item['error']})}\n\n"
                    break
                elif item["type"] == "complete":
                    res = item["data"]
                    if user and user.is_authenticated:
                        if conversation_id:
                            conv = get_object_or_404(Conversation, pk=conversation_id, user=user)
                        else:
                            conv = Conversation.objects.create(user=user, title=_make_title(query))

                        ChatMessage.objects.create(conversation=conv, role=ChatMessage.ROLE_USER, text=query)
                        ChatMessage.objects.create(conversation=conv, role=ChatMessage.ROLE_ASSISTANT, proposal_data=res)

                        res = {**res, "conversation_id": conv.id, "conversation_title": conv.title}

                    yield f"data: {json.dumps({'stage': 'complete', 'data': res})}\n\n"
                    break

        response = StreamingHttpResponse(event_generator(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no" # Disable buffering in Nginx if applicable
        return response


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        convs = Conversation.objects.filter(user=request.user)
        return Response(ConversationSerializer(convs, many=True).data)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        conv = get_object_or_404(Conversation, pk=pk, user=request.user)
        return Response(ConversationDetailSerializer(conv).data)

    def delete(self, request, pk):
        conv = get_object_or_404(Conversation, pk=pk, user=request.user)
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocView(View):
    """Serve source PDFs so users can open the original document from citation links."""

    def get(self, request, filename):
        if not _SAFE_FILENAME_RE.match(filename) or ".." in filename:
            raise Http404

        if Path(filename).suffix.lower() not in _ALLOWED_EXTENSIONS:
            raise Http404

        docs_dir = os.getenv("DOCS_DIR") or str(
            Path(__file__).parent.parent.parent / "docs"
        )
        filepath = Path(docs_dir) / filename

        if not filepath.exists() or not filepath.is_file():
            raise Http404

        content_type = (
            "application/pdf"
            if filepath.suffix.lower() == ".pdf"
            else "application/octet-stream"
        )
        response = FileResponse(open(filepath, "rb"), content_type=content_type)
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
