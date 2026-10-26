import unittest

from win_validation.detector import _hermes_signal_qualifies


class DetectorSourceQualificationTests(unittest.TestCase):
    def setUp(self):
        self.signal = {
            "expected_area_text_match": "True",
            "exact_date_match": "True",
            "throughput_drop_pct_vs_baseline": "74.0",
            "anomalous_throughput_sample_fraction": "1.0",
            "sample_unique_clients": "5",
            # The qualifying rule must not read the reference label.
            "reference_match": "False",
        }

    def test_hermes_candidate_uses_signal_fields_not_reference_label(self):
        self.assertTrue(_hermes_signal_qualifies(self.signal))

    def test_hermes_requires_area_and_exact_date_match(self):
        for field in ("expected_area_text_match", "exact_date_match"):
            item = dict(self.signal, **{field: "False"})
            self.assertFalse(_hermes_signal_qualifies(item))

    def test_hermes_rejects_weak_or_low_sample_anomaly(self):
        for field, value in (
            ("throughput_drop_pct_vs_baseline", "39.9"),
            ("anomalous_throughput_sample_fraction", "0.79"),
            ("sample_unique_clients", "4"),
        ):
            item = dict(self.signal, **{field: value})
            self.assertFalse(_hermes_signal_qualifies(item))


if __name__ == "__main__":
    unittest.main()
