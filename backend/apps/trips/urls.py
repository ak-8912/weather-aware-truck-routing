from django.urls import path

from apps.trips.views import HealthView

urlpatterns = [path("health/", HealthView.as_view(), name="health")]
