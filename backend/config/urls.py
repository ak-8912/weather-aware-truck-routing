import os
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path

def health(_request):
    return JsonResponse({"status":"ok","version":"0.1.0","providers":{"routing_configured":bool(os.getenv("OPENROUTESERVICE_API_KEY"))}})

urlpatterns = [path("admin/",admin.site.urls),path("api/health/",health,name="health")]
