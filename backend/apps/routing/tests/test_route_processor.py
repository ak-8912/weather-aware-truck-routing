from django.test import SimpleTestCase
from rest_framework.exceptions import APIException

from apps.routing.services.route_processor import normalize_route_response


def feature(coordinates, distance=1200, duration=120):
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "properties": {"summary": {"distance": distance, "duration": duration}},
    }


class RouteProcessorTests(SimpleTestCase):
    def test_normalizes_coordinates_distance_duration_and_caps_routes(self):
        payload = {"features": [
            feature([[-73.9, 40.7], [-73.8, 40.8]]),
            feature([[-73.9, 40.7], [-73.7, 40.8]], 1500, 130),
            feature([[-73.9, 40.7], [-73.6, 40.8]], 1800, 150),
            feature([[-73.9, 40.7], [-73.5, 40.8]], 1900, 160),
        ]}

        routes = normalize_route_response(payload)

        self.assertEqual(len(routes), 3)
        self.assertEqual(routes[0]["route_id"], "route-1")
        self.assertEqual(routes[0]["geometry"][0], [-73.9, 40.7])
        self.assertEqual(routes[0]["distance_meters"], 1200)
        self.assertEqual(routes[0]["duration_seconds"], 120)

    def test_discards_duplicate_geometries_instead_of_presenting_fake_alternatives(self):
        payload = {"features": [
            feature([[-73.9, 40.7], [-73.8, 40.8]]),
            feature([[-73.9, 40.7], [-73.8, 40.8]], 1300, 130),
        ]}

        routes = normalize_route_response(payload)

        self.assertEqual(len(routes), 1)

    def test_empty_provider_response_is_no_routes(self):
        with self.assertRaises(APIException) as raised:
            normalize_route_response({"features": []})
        self.assertEqual(raised.exception.status_code, 422)

    def test_invalid_geometry_is_rejected(self):
        with self.assertRaises(APIException):
            normalize_route_response({"features": [feature([[181, 40], [0, 0]])]})

