from django.urls import path
from .views import GenerateProposalView

urlpatterns = [
    path("generate-proposal/", GenerateProposalView.as_view(), name="generate-proposal"),
]
