import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import dda  # noqa: E402


class TestDda(unittest.TestCase):
    def test_mask_keeps_prefix(self):
        self.assertEqual(dda.mask("abcdefgh", 4), "abcd****")

    def test_fetch_records_concatenates_pages_until_short(self):
        pages = {1: [{"i": n} for n in range(1000)], 2: [{"i": 1000}]}
        calls = []

        def fake(path, params):
            calls.append(params)
            return {"results": pages.get(params["page"], [])}

        out = dda.fetch_records(fake, "rta/x", total=5000)
        self.assertEqual(len(out), 1001)
        self.assertEqual(calls[0]["pageSize"], 1000)
        self.assertEqual(len(calls), 2)

    def test_fetch_records_stops_on_empty_first_page(self):
        self.assertEqual(
            dda.fetch_records(lambda p, q: {"results": []}, "rta/x", total=10), []
        )


if __name__ == "__main__":
    unittest.main()
