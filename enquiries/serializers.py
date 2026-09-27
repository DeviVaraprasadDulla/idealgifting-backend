from rest_framework import serializers


class ContactEnquirySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    contact = serializers.CharField(max_length=150)
    topic = serializers.CharField(max_length=150, required=False, allow_blank=True)
    message = serializers.CharField(max_length=2000)


class CorporateEnquirySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    company = serializers.CharField(max_length=150)
    contact = serializers.CharField(max_length=150)
    quantity = serializers.CharField(max_length=100, required=False, allow_blank=True)
    occasion = serializers.CharField(max_length=150, required=False, allow_blank=True)
    budget = serializers.CharField(max_length=100, required=False, allow_blank=True)
    need_by = serializers.CharField(max_length=100, required=False, allow_blank=True)
    message = serializers.CharField(max_length=2000)
