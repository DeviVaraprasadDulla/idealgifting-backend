from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from .models import Banner
from .serializers import BannerSerializer


class BannerListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = BannerSerializer

    def get_queryset(self):
        return Banner.objects.filter(is_active=True).order_by("order")

    def get_serializer_context(self):
        return {"request": self.request}
