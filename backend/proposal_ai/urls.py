from django.urls import path

from .views import ConversationDetailView, ConversationListView, DocView, GenerateProposalView

urlpatterns = [
    path("generate-proposal/", GenerateProposalView.as_view(), name="generate-proposal"),
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path("conversations/<int:pk>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("docs/<str:filename>", DocView.as_view(), name="serve-doc"),
]
