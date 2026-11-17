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


if __name__ == "__main__":
    unittest.main()
