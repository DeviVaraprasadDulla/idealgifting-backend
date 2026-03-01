from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import SiteAnnouncement

class ActiveAnnouncementAPIView(APIView):
    permission_classes = [AllowAny]   # 👈 IMPORTANT

    def get(self, request):
        announcement = SiteAnnouncement.objects.filter(
            is_active=True
        ).order_by("-created_at").first()

        if not announcement:
            return Response({})

        return Response({
            "message": announcement.message
        })
