"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.conf import settings
from django.conf.urls.static import static


def deploy_info(request):
    """Plain-text proof of exactly what commit this running process is
    executing - served by Django/Gunicorn directly (not a static file
    Nginx might route differently), written by the deploy script right
    after `git pull`. No auth, no secrets - just a commit hash, so a
    deploy can be verified with a single HTTP request instead of
    assuming the Actions job succeeding means the right code is live."""
    marker_path = settings.BASE_DIR / "DEPLOYED_COMMIT.txt"
    try:
        content = marker_path.read_text()
    except FileNotFoundError:
        content = "no deploy marker found (local/dev environment, or not deployed via the standard script yet)\n"
    return HttpResponse(content, content_type="text/plain")


urlpatterns = [
    path("deploy-info/", deploy_info),
    path("admin/", admin.site.urls),
    path("api/", include("products.urls")),
    path("api/cart/", include("cart.urls")),
    path("api/orders/", include("orders.urls")),
    path("api/", include("banners.urls")),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/payments/", include("payments.urls")),
    path("api/users/", include("users.urls")),
    path("api/settings/", include("settings_app.urls")),
    path("api/wishlist/", include("wishlist.urls")),
    path("api/personalization/", include("personalization.urls")),
    path("api/enquiries/", include("enquiries.urls")),

]

# ✅ Only once, and inside DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
