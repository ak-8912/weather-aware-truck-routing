from django.urls import path

from apps.trips.views import HealthView, TripAnalysisView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("trips/analyze/", TripAnalysisView.as_view(), name="trip-analysis"),
]
