from rest_framework import serializers


class ProposalRequestSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=5, max_length=1000)


class ProposalResponseSerializer(serializers.Serializer):
    executive_summary = serializers.CharField()
    proposed_solution = serializers.CharField()
    relevant_experience = serializers.CharField()
    why_us = serializers.CharField()
    sources = serializers.ListField(child=serializers.CharField())
