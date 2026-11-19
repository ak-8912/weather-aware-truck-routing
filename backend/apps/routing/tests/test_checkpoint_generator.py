import math
from datetime import datetime, timedelta, timezone
from unittest import TestCase

from apps.routing.services.checkpoint_generator import (
    EARTH_RADIUS_METERS,
    METERS_PER_MILE,
    CheckpointGenerationError,
    generate_weather_checkpoints,
)


def equator_route(distance_miles, duration_seconds=3600, route_id="route-test"):
    distance_meters = distance_miles * METERS_PER_MILE
    longitude = math.degrees(distance_meters / EARTH_RADIUS_METERS)
    return {
        "route_id": route_id,
        "geometry": [[-1.0, 0.0], [longitude - 1.0, 0.0]],
        "distance_meters": distance_meters,
        "duration_seconds": duration_seconds,
    }


class CheckpointGeneratorTests(TestCase):
    def setUp(self):
        self.departure = datetime(2026, 11, 20, 8, 0, tzinfo=timezone(timedelta(hours=-5)))

    def test_generates_supported_intervals_and_always_includes_both_endpoints(self):
        route = equator_route(62)

        for interval in (10, 25, 50):
            with self.subTest(interval=interval):
                points = generate_weather_checkpoints(route, self.departure, interval)
                distances = [point["distance_from_origin_miles"] for point in points]
                self.assertAlmostEqual(distances[0], 0)
                self.assertAlmostEqual(distances[-1], 62)
                self.assertEqual(points[0]["longitude"], -1.0)
                self.assertAlmostEqual(points[-1]["longitude"], route["geometry"][-1][0])
                self.assertEqual(len(distances), math.ceil(62 / interval) + 1)
                for left, right in zip(distances, distances[1:]):
                    self.assertGreater(right, left)

    def test_short_route_has_origin_and_destination_without_extra_checkpoints(self):
        points = generate_weather_checkpoints(equator_route(8), self.departure, 25)

        self.assertEqual(len(points), 2)
        self.assertEqual([point["distance_from_origin_miles"] for point in points], [0, 8])

    def test_exact_interval_multiple_includes_destination_once(self):
        points = generate_weather_checkpoints(equator_route(50), self.departure, 25)

        self.assertEqual(len(points), 3)
        self.assertEqual([point["distance_from_origin_miles"] for point in points], [0, 25, 50])

    def test_checkpoint_is_interpolated_on_cumulative_geometry_segments(self):
        half_distance = 50 * METERS_PER_MILE
        half_longitude = math.degrees(half_distance / EARTH_RADIUS_METERS)
        route = {
            "route_id": "bent",
            "geometry": [[0, 0], [half_longitude, 0], [half_longitude * 2, 0]],
            "distance_meters": half_distance * 2,
            "duration_seconds": 7200,
        }

        points = generate_weather_checkpoints(route, self.departure, 50)

        self.assertAlmostEqual(points[1]["longitude"], half_longitude, places=8)
        self.assertAlmostEqual(points[1]["latitude"], 0, places=8)

    def test_eta_uses_checkpoint_distance_fraction_and_preserves_timezone(self):
        route = equator_route(100, duration_seconds=7200)

        points = generate_weather_checkpoints(route, self.departure, 25)

        self.assertEqual(points[1]["estimated_arrival_time"], self.departure + timedelta(minutes=30))
        self.assertEqual(points[1]["estimated_arrival_time"].utcoffset(), timedelta(hours=-5))
        self.assertEqual(points[-1]["estimated_arrival_time"], self.departure + timedelta(hours=2))

    def test_checkpoint_ids_are_scoped_to_route_and_ordered(self):
        points = generate_weather_checkpoints(equator_route(30, route_id="route-7"), self.departure, 10)

        self.assertEqual([point["checkpoint_id"] for point in points], [
            "route-7:checkpoint:1", "route-7:checkpoint:2", "route-7:checkpoint:3", "route-7:checkpoint:4",
        ])

    def test_rejects_unsupported_intervals_naive_times_and_invalid_routes(self):
        route = equator_route(30)
        with self.assertRaises(CheckpointGenerationError):
            generate_weather_checkpoints(route, self.departure, 15)
        with self.assertRaises(CheckpointGenerationError):
            generate_weather_checkpoints(route, datetime(2026, 11, 20, 8, 0), 25)
        with self.assertRaises(CheckpointGenerationError):
            generate_weather_checkpoints({**route, "geometry": [[0, 0]]}, self.departure, 25)
        with self.assertRaises(CheckpointGenerationError):
            generate_weather_checkpoints({**route, "distance_meters": 0}, self.departure, 25)

    def test_rejects_zero_length_geometry(self):
        route = {"route_id": "flat", "geometry": [[1, 2], [1, 2]], "distance_meters": 100, "duration_seconds": 100}

        with self.assertRaises(CheckpointGenerationError):
            generate_weather_checkpoints(route, self.departure, 25)
