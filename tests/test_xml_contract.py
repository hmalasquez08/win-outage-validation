import tempfile
import os
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from win_validation.live_runner import ROOT, run
from win_validation.trigger_feed_xml import build_empty_feed, build_feed, validate_feed, write_feed


class XmlContractTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.decision = {
            "status": "QUALIFIED_FOR_SIMULATED_CREATIVE",
            "decision_at": self.now.isoformat(),
            "expires_at": (self.now + timedelta(minutes=10)).isoformat(),
            "scope": {
                "operator": "movistar", "technology": "fixed",
                "geography": {"code": "150122", "level": "district"},
                "first_observed_at": (self.now - timedelta(minutes=2)).isoformat(),
                "last_observed_at": (self.now - timedelta(minutes=1)).isoformat(),
            },
        }

    def _validate_element(self, root):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.xml"
            ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
            return validate_feed(path)

    def test_qualified_event_uses_spanish_contract_and_example_url(self):
        root = build_feed(self.decision, state="active", incident_type="outage", simulation_only=False)
        event = root.find("evento")
        self.assertEqual(root.tag, "feedActivador")
        self.assertEqual(event.findtext("operador"), "movistar")
        self.assertEqual(event.findtext("tipoServicio"), "fijo")
        self.assertEqual(event.findtext("tipoIncidente"), "corte")
        self.assertEqual(event.findtext("activador"), "true")
        self.assertEqual(event.findtext("zona"), "Lima")
        self.assertEqual(event.findtext("distrito"), "Miraflores")
        self.assertEqual(event.findtext("precisionGeo"), "distrito")
        self.assertTrue(event.findtext("urlCreativo").startswith("https://example.com/"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.xml"
            write_feed(root, path)
            self.assertTrue(validate_feed(path)["valid"])

    def test_empty_feed_is_valid_and_has_no_event(self):
        root = build_empty_feed(self.now)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.xml"
            write_feed(root, path)
            result = validate_feed(path)
            self.assertTrue(result["valid"])
            self.assertEqual(result["events"], 0)
            self.assertFalse(result["trigger_active"])

    def test_real_creative_url_is_rejected(self):
        with self.assertRaises(ValueError):
            build_feed(self.decision, state="active", simulation_only=False, creative_url="https://real.example.com/creative")

    def test_simulation_cannot_activate(self):
        with self.assertRaises(ValueError):
            build_feed(self.decision, state="active", simulation_only=True)
        root = build_feed(self.decision, state="active", simulation_only=False)
        root.set("simulacion", "true")
        self.assertFalse(self._validate_element(root)["valid"])

    def test_simulation_is_marked_and_inactive(self):
        root = build_feed(self.decision, state="candidate", simulation_only=True)
        self.assertEqual(root.get("simulacion"), "true")
        self.assertEqual(root.findtext("evento/activador"), "false")
        self.assertTrue(self._validate_element(root)["valid"])

    def test_xsd_rejects_extra_and_duplicate_elements(self):
        for extra in ("noPermitido", "operador"):
            root = build_feed(self.decision, state="active", simulation_only=False)
            ET.SubElement(root.find("evento"), extra).text = "test"
            self.assertFalse(self._validate_element(root)["valid"])

    def test_missing_and_mismatched_ubigeo_are_rejected(self):
        root = build_feed(self.decision, state="active", simulation_only=False)
        event = root.find("evento")
        event.remove(event.find("ubigeo"))
        self.assertFalse(self._validate_element(root)["valid"])
        root = build_feed(self.decision, state="active", simulation_only=False)
        root.find("evento/ubigeo").text = "150101"
        self.assertFalse(self._validate_element(root)["valid"])

    def test_active_expired_event_rejected_even_if_feed_is_fresh(self):
        root = build_feed(self.decision, state="active", simulation_only=False)
        root.find("evento/iniciadoEn").text = (self.now - timedelta(hours=2)).isoformat()
        root.find("evento/expiraEn").text = (self.now - timedelta(minutes=1)).isoformat()
        self.assertFalse(self._validate_element(root)["valid"])

    def test_expired_active_feed_is_rejected(self):
        root = build_feed(self.decision, state="active", simulation_only=False)
        root.set("generadoEn", (self.now - timedelta(hours=1)).isoformat())
        root.set("validoHasta", (self.now - timedelta(minutes=1)).isoformat())
        root.find("evento/iniciadoEn").text = (self.now - timedelta(hours=1)).isoformat()
        root.find("evento/expiraEn").text = (self.now - timedelta(minutes=2)).isoformat()
        self.assertFalse(self._validate_element(root)["valid"])

    def test_future_generated_timestamp_is_rejected(self):
        root = build_empty_feed(self.now + timedelta(hours=1))
        self.assertFalse(self._validate_element(root)["valid"])

    def test_invalid_candidate_never_replaces_existing_feed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.xml"
            write_feed(build_empty_feed(self.now), path)
            original = path.read_bytes()
            invalid = build_empty_feed(self.now)
            ET.SubElement(invalid, "inesperado")
            with self.assertRaises(ValueError):
                write_feed(invalid, path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(sorted(p.name for p in path.parent.iterdir()), ["feed.xml"])

    def test_failed_run_replaces_old_active_file_with_degraded_feed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.xml"
            write_feed(build_feed(self.decision, state="active", simulation_only=False), path)
            with patch("win_validation.http.load_env", return_value={"CLOUDFLARE_API_TOKEN": "test"}), \
                 patch("win_validation.live_runner.resolve_department", side_effect=ValueError("unknown department")), \
                 patch("win_validation.live_runner._write_report", return_value=ROOT / "reports" / "test.json"):
                result = run("movistar", "invalid", output=path)
            self.assertEqual(result["status"], "ERROR")
            root = ET.parse(path).getroot()
            self.assertEqual(root.get("estadoSistema"), "degradado")
            self.assertEqual(root.findall("evento"), [])
            self.assertTrue(validate_feed(path)["valid"])

    def test_cli_argument_error_replaces_old_active_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.xml"
            write_feed(build_feed(self.decision, state="active", simulation_only=False), path)
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
            completed = subprocess.run(
                [sys.executable, "-m", "win_validation.live_runner", "--operator", "invalido", "--department", "Lima", "--output", str(path)],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(completed.returncode, 0)
            root = ET.parse(path).getroot()
            self.assertEqual(root.get("estadoSistema"), "degradado")
            self.assertEqual(root.findall("evento"), [])
            self.assertEqual(ET.fromstring(completed.stdout).tag, "feedActivador")

    def test_id_is_stable_for_same_scope(self):
        first = build_feed(self.decision, state="active", simulation_only=False).find("evento").get("id")
        self.decision["scope"]["first_observed_at"] = (self.now - timedelta(minutes=1)).isoformat()
        second = build_feed(self.decision, state="active", simulation_only=False).find("evento").get("id")
        self.assertEqual(first, second)

    def test_xsd_is_well_formed(self):
        self.assertEqual(ET.parse("config/trigger_feed.xsd").getroot().tag, "{http://www.w3.org/2001/XMLSchema}schema")


if __name__ == "__main__":
    unittest.main()
