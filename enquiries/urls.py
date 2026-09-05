from django.urls import path
from .views import ContactEnquiryAPIView, CorporateEnquiryAPIView

urlpatterns = [
    path("contact/", ContactEnquiryAPIView.as_view()),
    path("corporate/", CorporateEnquiryAPIView.as_view()),
]
