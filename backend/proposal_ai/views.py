from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import ProposalRequestSerializer, ProposalResponseSerializer
from .services import generate_proposal


class GenerateProposalView(APIView):

    def post(self, request):
        request_serializer = ProposalRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = request_serializer.validated_data["query"]

        try:
            result = generate_proposal(query)
        except RuntimeError as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response({"error": "Failed to generate proposal. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response_serializer = ProposalResponseSerializer(data=result)
        response_serializer.is_valid()
        return Response(response_serializer.data, status=status.HTTP_200_OK)
