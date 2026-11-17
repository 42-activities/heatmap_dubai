import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import unittest
import export_web_data


class TestExport(unittest.TestCase):
    def test_dedupe_drops_invalid_coords(self):
        rows = [{"stop_id": 1, "stop_name": "A", "stop_location_latitude": "",
                 "stop_location_longitude": "55.1", "valid_from": "2020-01-01"}]
        self.assertEqual(export_web_data.dedupe_stops(rows), [])

    def test_dedupe_keeps_latest_valid_from_per_stop_id(self):
        rows = [
            {"stop_id": 5, "stop_name": "Old", "stop_location_latitude": 25.0,
             "stop_location_longitude": 55.0, "valid_from": "2017-01-01"},
            {"stop_id": 5, "stop_name": "New", "stop_location_latitude": 25.1,
             "stop_location_longitude": 55.1, "valid_from": "2020-01-01"}]
        out = export_web_data.dedupe_stops(rows)
        self.assertTrue(len(out) == 1 and out[0]["stop_name"] == "New")
        self.assertEqual(set(out[0]), {"stop_id", "stop_name", "lat", "lon"})

    def test_dedupe_coerces_float_stop_id_to_int(self):
        rows = [{"stop_id": 2032.0, "stop_name": "F", "stop_location_latitude": 25.2,
                 "stop_location_longitude": 55.3, "valid_from": "2020-01-01"}]
        out = export_web_data.dedupe_stops(rows)
        self.assertEqual(out[0]["stop_id"], 2032)
        self.assertIsInstance(out[0]["stop_id"], int)

    def test_dedupe_drops_non_numeric_stop_id(self):
        rows = [{"stop_id": "abc", "stop_name": "F", "stop_location_latitude": 25.2,
                 "stop_location_longitude": 55.3, "valid_from": "2020-01-01"}]
        self.assertEqual(export_web_data.dedupe_stops(rows), [])

    def test_dedupe_drops_sentinel_coords_keeps_nearby(self):
        rows = [{"stop_id": 1, "stop_name": "S", "stop_location_latitude": 25.0,
                 "stop_location_longitude": 55.0, "valid_from": "2020-01-01"},
                {"stop_id": 2, "stop_name": "R", "stop_location_latitude": 25.2,
                 "stop_location_longitude": 55.3, "valid_from": "2020-01-01"}]
        out = export_web_data.dedupe_stops(rows)
        self.assertEqual([o["stop_id"] for o in out], [2])

    def test_placeholder_is_deterministic_and_monthly_2026(self):
        stops = [{"stop_id": 1, "stop_name": "A", "lat": 25.0, "lon": 55.0}]
        a = export_web_data.build_placeholder_passengers(stops)
        b = export_web_data.build_placeholder_passengers(stops)
        self.assertEqual(a, b)
        months = [m["month"] for m in a["stations"]["1"]]
        self.assertTrue(len(months) == 12 and months[0] == "2026-01" and months[-1] == "2026-12")
        self.assertIs(a["placeholder"], True)

    def test_summarize_coverage_coerces_blank_population_to_zero(self):
        rows = [{"community_num": 9, "community_name": "X", "population": "",
                 "accessible_population": 10, "geographic_coverage": 80}]
        self.assertEqual(export_web_data.summarize_coverage(rows)[0]["population"], 0)

    def test_summarize_routes_dedupes_and_counts(self):
        rows = [
            {"route_name": "F22", "route_type": "EK", "stop_number": 1},
            {"route_name": "F22", "route_type": "EK", "stop_number": 2},
            {"route_name": "GE95B", "route_type": "EK", "stop_number": 1}]
        out = {r["route_name"]: r for r in export_web_data.summarize_routes(rows)}
        self.assertEqual(set(out), {"F22", "GE95B"})
        self.assertEqual(out["F22"]["stop_count"], 2)
        self.assertEqual(out["F22"]["route_type"], "EK")

    # ---- real ridership aggregation ----
    def _rides(self):
        # 'in' at start_location (CKA), 'out' at end_location (CKO).
        return [
            {"txn_type": "CKA", "txn_date": "2026-01-05", "start_location": "Alpha", "end_location": "Beta"},
            {"txn_type": "CKA", "txn_date": "2026-01-20", "start_location": "Alpha", "end_location": "Gamma"},
            {"txn_type": "CKO", "txn_date": "2026-01-22", "start_location": "Gamma", "end_location": "Beta"},
            {"txn_type": "CKA", "txn_date": "2026-02-01", "start_location": "Alpha", "end_location": "Beta"},
            {"txn_type": "CKA", "txn_date": "2025-12-31", "start_location": "Alpha", "end_location": "Beta"},  # not 2026
            {"txn_type": "ZZZ", "txn_date": "2026-01-09", "start_location": "Alpha", "end_location": "Beta"},  # unmapped
        ]

    def test_aggregate_filters_year_maps_direction_and_station(self):
        agg, report = export_web_data.aggregate_ridership(self._rides(), year=2026)
        # 'in' (CKA) counts at start_location: Alpha has 2 in Jan, 1 in Feb
        self.assertEqual(agg["Alpha"]["2026-01"]["in"], 2)
        self.assertEqual(agg["Alpha"]["2026-02"]["in"], 1)
        # 'out' (CKO) counts at end_location: Beta gets 1 out in Jan
        self.assertEqual(agg["Beta"]["2026-01"]["out"], 1)
        self.assertEqual(report["year_rows"], 5)                     # the lone 2025 row excluded
        self.assertEqual(report["unmapped_types"], {"ZZZ": 1})

    def test_aggregate_accepts_generator(self):
        agg, _ = export_web_data.aggregate_ridership(iter(self._rides()))
        self.assertIn("Alpha", agg)

    def test_passengers_from_agg_matches_by_stop_name_and_12_months(self):
        agg, _ = export_web_data.aggregate_ridership(self._rides())
        stops = [{"stop_id": 10, "stop_name": "Alpha"}]   # Beta intentionally has no stop
        payload, report = export_web_data.passengers_from_agg(agg, stops)
        self.assertFalse(payload["placeholder"])
        self.assertEqual(len(payload["stations"]["10"]), 12)          # all 12 months present
        jan = next(m for m in payload["stations"]["10"] if m["month"] == "2026-01")
        self.assertEqual(jan["in"], 2)
        self.assertEqual(report["matched_locations"], 1)
        self.assertEqual(report["unmatched_locations"], 1)           # 'Beta' has no stop


if __name__ == "__main__":
    unittest.main()
