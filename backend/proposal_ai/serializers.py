from rest_framework import serializers


class ProposalRequestSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=5, max_length=1000)


class ProposalResponseSerializer(serializers.Serializer):
    proposal = serializers.CharField()
    sources = serializers.ListField(child=serializers.CharField())
