import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from win_validation.ioda_geoasn import _series_summary, collect_geoasn
from win_validation.live_runner import ROOT, run
from win_validation.radar_context import _fetch, collect_radar_context


class IodaContextTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc)
        self.end = int(self.now.timestamp())
        self.row = {
            "entityType": "geoasn", "entityCode": "6147-3128", "datasource": "bgp",
            "from": self.end - 600, "until": self.end + 300,
            "step": 300, "nativeStep": 300, "values": [100, None, 0],
        }

    def test_missing_and_future_samples_do_not_count_as_measurements(self):
        row = _series_summary([[self.row]], "bgp", "6147-3128", self.now)[0]
        self.assertEqual(row["latest_value"], 100)
        self.assertEqual(row["age_seconds"], 300)
        self.assertEqual(row["null_samples"], 1)

    def test_zero_is_a_valid_value(self):
        self.row["values"] = [100, 0, None]
        self.assertEqual(_series_summary([[self.row]], "bgp", "6147-3128", self.now)[0]["latest_value"], 0)

    def test_wrong_entity_or_buckets_rejected(self):
        with self.assertRaises(ValueError):
            _series_summary([[self.row]], "bgp", "12252-3128", self.now)
        self.row["until"] += 1
        with self.assertRaises(ValueError):
            _series_summary([[self.row]], "bgp", "6147-3128", self.now)

    def test_coarse_buckets_have_unknown_coverage(self):
        self.row["nativeStep"] = 60
        self.assertEqual(_series_summary([[self.row]], "bgp", "6147-3128", self.now)[0]["coverage"], "unknown")

    def test_ambiguous_region_is_not_guessed(self):
        regions = [{"type": "region", "code": code, "name": "Callao", "attrs": {"country_code": "PE"}} for code in ("3103", "3111")]
        with patch("win_validation.ioda_geoasn._fetch", return_value={"status": "OK", "data": regions}):
            result = collect_geoasn("6147", {"code": "07", "name": "Callao"}, self.now)
        self.assertEqual(result["status"], "REGION_AMBIGUOUS")
        self.assertNotIn("geoasn", result)

    def test_unknown_region_fails_closed(self):
        with patch("win_validation.ioda_geoasn._fetch", return_value={"status": "OK", "data": []}):
            result = collect_geoasn("6147", {"code": "21", "name": "Puno"}, self.now)
        self.assertEqual(result["status"], "REGION_NOT_RESOLVED")


class RadarContextTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc)

    def test_no_operator_or_geography_inference(self):
        anomaly = {"type": "AS", "status": "UNVERIFIED", "startDate": "2026-01-01T00:00:00Z"}
        annotation = {"asns": [], "geoIds": [], "startDate": "2026-01-01T00:00:00Z", "endDate": "2026-01-01T00:05:00Z"}
        with patch("win_validation.radar_context._fetch", side_effect=[{"status": "OK", "items": [anomaly]}, {"status": "OK", "items": [annotation]}]):
            result = collect_radar_context("6147", "3936452", "token", self.now)
        self.assertFalse(result["traffic_anomalies"]["items"][0]["requested_asn_match"])
        self.assertEqual(result["traffic_anomalies"]["items"][0]["department_attribution"], "NOT_ESTABLISHED")
        self.assertFalse(result["outage_annotations"]["items"][0]["requested_geoid_match"])
        self.assertEqual(annotation["event_time_status"], "ENDED")

    def test_http_200_with_api_failure_is_not_success(self):
        record = {"result_status": "SUCCESS_WITH_EVIDENCE", "http_status": 200}
        with patch("win_validation.radar_context.request", return_value=(record, json.dumps({"success": False, "result": {"annotations": []}}).encode())):
            self.assertEqual(_fetch("annotations", "annotations", {}, "token")["status"], "INVALID_RESPONSE")

    def test_rate_limit_does_not_become_empty_success(self):
        with patch("win_validation.radar_context.request", return_value=({"result_status": "RATE_LIMITED", "http_status": 429}, b"{}")):
            self.assertEqual(_fetch("annotations", "annotations", {}, "token")["status"], "RATE_LIMITED")


class RunnerIntegrationTests(unittest.TestCase):
    def test_context_outages_cannot_create_signals(self):
        with patch("win_validation.http.load_env", return_value={"CLOUDFLARE_API_TOKEN": "test"}), \
             patch("win_validation.live_runner.resolve_department", return_value={"code": "15", "name": "Lima"}), \
             patch("win_validation.live_runner.resolve_cloudflare_geography", return_value={"status": "RESOLVED", "geo_id": "3936452"}), \
             patch("win_validation.live_runner.fetch_netflows", return_value={"candidate": False}), \
             patch("win_validation.live_runner.fetch_ioda", return_value={"event_count": 0}), \
             patch("win_validation.ioda_geoasn.collect_geoasn", return_value={"status": "OK", "events": {"data": [{"start": 1}]}}), \
             patch("win_validation.radar_context.collect_radar_context", return_value={"status": "OK", "outage_annotations": {"items": [{"asns": [6147]}]}}), \
             patch("win_validation.live_runner._empty_output", return_value=(ROOT / "trigger_feed_live.xml", {"valid": True})), \
             patch("win_validation.live_runner._write_report", return_value=ROOT / "reports" / "test.json"):
            result = run("movistar", "Lima")
        self.assertEqual(result["status"], "SUPPRESSED")
        self.assertEqual(result["signals"], [])
        self.assertEqual(result["feed_path"], str(ROOT / "trigger_feed_live.xml"))


if __name__ == "__main__":
    unittest.main()
