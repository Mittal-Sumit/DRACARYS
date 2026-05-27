import os
import re
from pathlib import Path

from django.http import FileResponse, Http404
from django.views import View
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ProposalRequestSerializer
from .services import generate_proposal

_SAFE_FILENAME_RE = re.compile(r'^[\w\s\-\.]+$')
_ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc'}


class GenerateProposalView(APIView):

    def post(self, request):
        serializer = ProposalRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data["query"]

        try:
            result = generate_proposal(query)
        except RuntimeError as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception:
            return Response(
                {"error": "Failed to generate a response. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=status.HTTP_200_OK)


class DocView(View):
    """Serve source PDFs so users can open the original document from citation links."""

    def get(self, request, filename):
        # Reject anything with path separators or unexpected characters
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
