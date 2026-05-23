from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import ProposalRequestSerializer
from .services import generate_proposal


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
