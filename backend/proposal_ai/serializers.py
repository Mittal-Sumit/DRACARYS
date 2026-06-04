from rest_framework import serializers

from .models import ChatMessage, Conversation


class ProposalRequestSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=2, max_length=1000)
    use_web_search = serializers.BooleanField(default=False, required=False)
    conversation_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class SectionSerializer(serializers.Serializer):
    heading = serializers.CharField(allow_null=True, allow_blank=True, default=None)
    content = serializers.CharField()


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "text", "proposal_data", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at"]


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "messages"]
