from django.urls import path

from apps.routing.views import GeocodingSearchView, RouteAlternativesView

urlpatterns = [
    path("routes/", RouteAlternativesView.as_view(), name="route-alternatives"),
    path("geocoding/search/", GeocodingSearchView.as_view(), name="geocoding-search"),
]
