from django.urls import path
from .views import DocView, GenerateProposalView

urlpatterns = [
    path("generate-proposal/", GenerateProposalView.as_view(), name="generate-proposal"),
    path("docs/<str:filename>", DocView.as_view(), name="serve-doc"),
]
