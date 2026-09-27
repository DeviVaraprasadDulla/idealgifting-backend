from django.conf import settings
from django.core.mail import send_mail

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework import status

from .serializers import ContactEnquirySerializer, CorporateEnquirySerializer


class ContactEnquiryAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "enquiries"

    def post(self, request):
        serializer = ContactEnquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        subject = f"New contact enquiry from idealgifting.in - {data['name']}"
        message = (
            f"Name: {data['name']}\n"
            f"Contact: {data['contact']}\n"
            f"Topic: {data.get('topic') or 'General enquiry'}\n\n"
            f"Message:\n{data['message']}"
        )

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            fail_silently=False,
        )

        return Response(
            {"message": "Enquiry received"}, status=status.HTTP_201_CREATED
        )


class CorporateEnquiryAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "enquiries"

    def post(self, request):
        serializer = CorporateEnquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        subject = f"New corporate gifting enquiry - {data['company']}"
        message = (
            f"Name: {data['name']}\n"
            f"Company: {data['company']}\n"
            f"Contact: {data['contact']}\n"
            f"Quantity: {data.get('quantity') or 'Not specified'}\n"
            f"Occasion: {data.get('occasion') or 'Not specified'}\n"
            f"Budget per gift: {data.get('budget') or 'Not specified'}\n"
            f"Needed by: {data.get('need_by') or 'Not specified'}\n\n"
            f"Idea:\n{data['message']}"
        )

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            fail_silently=False,
        )

        return Response(
            {"message": "Enquiry received"}, status=status.HTTP_201_CREATED
        )
