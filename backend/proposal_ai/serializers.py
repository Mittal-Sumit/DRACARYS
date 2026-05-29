from rest_framework import serializers


class ProposalRequestSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=2, max_length=1000)
    use_web_search = serializers.BooleanField(default=False, required=False)


class SectionSerializer(serializers.Serializer):
    heading = serializers.CharField(allow_null=True, allow_blank=True, default=None)
    content = serializers.CharField()
