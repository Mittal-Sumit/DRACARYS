import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

class ProposalIntegrationTests(APITestCase):

    @patch('proposal_ai.views.generate_proposal')
    def test_generate_proposal_view_success(self, mock_generate):
        mock_generate.return_value = {
            "sections": [{"heading": "Executive Summary", "content": "Test proposal contents"}],
            "sources": [],
            "web_sources": []
        }
        
        url = reverse('generate-proposal')
        payload = {
            "query": "retail store data pipeline",
            "use_web_search": False,
            "tone": "balanced",
            "output_format": "proposal"
        }
        
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("sections", response.data)
        self.assertEqual(response.data["sections"][0]["heading"], "Executive Summary")
        mock_generate.assert_called_once()

    @patch('proposal_ai.views.generate_proposal')
    def test_streaming_proposal_view_success(self, mock_generate):
        mock_generate.return_value = {
            "sections": [{"heading": "Executive Summary", "content": "Test streaming proposal contents"}],
            "sources": [],
            "web_sources": []
        }
        
        url = reverse('generate-proposal-stream')
        payload = {
            "query": "retail store data pipeline",
            "use_web_search": False,
            "tone": "balanced",
            "output_format": "proposal"
        }
        
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        
        # Read the streamed response content
        content = b"".join(response.streaming_content).decode('utf-8')
        lines = content.split('\n\n')
        
        # We expect a planning message, then a complete message with mock data
        self.assertTrue(any("planning" in line for line in lines))
        self.assertTrue(any("complete" in line for line in lines))
        mock_generate.assert_called_once()
