"""Software-only, evidence-linked outage detector prototype and historical replay."""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import time
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
REPORTS = ROOT / "reports"
ASNS = {"movistar": "6147", "claro": "12252", "entel": "21575", "bitel": "262210"}
THRESHOLDS = (0.0, -0.005, -0.01, -0.02, -0.05, -0.10, -0.15, -0.20)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _truth(value: Any) -> bool:
    return str(value).strip().casefold() in {"true", "1", "yes", "si", "sí"}


def _number(value: Any) -> float | None:
    try:
        if value in (None, "", "NOT_COMPARABLE"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _hermes_signal_qualifies(item: dict[str, Any]) -> bool:
    """Conservative experimental HERMES gate, independent of event label."""
    return (
        _truth(item.get("expected_area_text_match"))
        and _truth(item.get("exact_date_match"))
        and (_number(item.get("throughput_drop_pct_vs_baseline")) or 0) >= 40
        and (_number(item.get("anomalous_throughput_sample_fraction")) or 0) >= 0.80
        and (_number(item.get("sample_unique_clients")) or 0) >= 5
    )


def _load_aligned_news() -> dict[tuple[str, str], dict[str, str]]:
    """Accept only human-reviewed news rows aligned to operator, area and time.

    A row is independent only when its review explicitly says INDEPENDENT and
    it is not marked as derived from social complaints. The current RSS scan
    does not create historical labels; it only writes candidates for review.
    """
    path = REPORTS / "news_historical_incident_replay.csv"
    if not path.exists():
        return {}
    accepted: dict[tuple[str, str], dict[str, str]] = {}
    for row in read_csv(path):
        aligned = _truth(row.get("operator_area_time_aligned"))
        candidate = _truth(row.get("news_candidate"))
        independent = str(row.get("independence_status", "")).strip().upper() == "INDEPENDENT"
        social_derived = _truth(row.get("possibly_socially_derived"))
        if aligned and candidate and independent and not social_derived:
            accepted[(row.get("incident_id", ""), row.get("operator", "").casefold())] = row
    return accepted


def _negative_bin_fraction(artifact_path: str | None) -> tuple[float | None, int]:
    """Share of paired 15-minute bins below the matched prior-week value."""
    if not artifact_path:
        return None, 0
    try:
        obj = json.loads((ROOT / artifact_path).read_text(encoding="utf-8"))
        result = obj.get("result", {})
        incident = [float(v) for v in result.get("incident", {}).get("values", []) if v not in (None, "")]
        control = [float(v) for v in result.get("weekday_control", {}).get("values", []) if v not in (None, "")]
        pairs = list(zip(incident, control))
        if not pairs:
            return None, 0
        return sum(a < b for a, b in pairs) / len(pairs), len(pairs)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None, 0


def fetch_matched_controls() -> dict[str, Any]:
    """Fetch the 17 non-affected operator controls for the existing timed cases."""
    from .cli import load_env, request

    token = load_env().get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        return {"status": "AUTH_BLOCKED_NO_CREDENTIAL"}

    positives = read_csv(REPORTS / "cloudflare_netflows_incident_replay.csv")
    x_rows = read_csv(REPORTS / "x_historical_incident_replay.csv")
    positive_by_case: dict[str, dict[str, str]] = {}
    for row in positives:
        positive_by_case.setdefault(row["incident_id"], row)

    controls = [row for row in x_rows if row.get("reference_label") == "NO_CONTROL"]
    output: list[dict[str, Any]] = []
    for control in controls:
        case, operator = control["incident_id"], control["operator"]
        reference = positive_by_case.get(case)
        if not reference or operator not in ASNS:
            continue
        start = reference["incident_window_start_utc"].replace("+00:00", "Z")
        end = reference["incident_window_end_utc"].replace("+00:00", "Z")
        compare_start = reference["comparison_window_start_utc"].replace("+00:00", "Z")
        compare_end = reference["comparison_window_end_utc"].replace("+00:00", "Z")
        netflow_params = [
            ("name", "incident"), ("dateStart", start), ("dateEnd", end),
            ("location", "PE"), ("asn", ASNS[operator]), ("product", "ALL"),
            ("name", "weekday_control"), ("dateStart", compare_start), ("dateEnd", compare_end),
            ("location", "PE"), ("asn", ASNS[operator]), ("product", "ALL"),
            ("aggInterval", "15m"), ("normalization", "MIN0_MAX"), ("format", "JSON"),
        ]
        netflow_url = "https://api.cloudflare.com/client/v4/radar/netflows/timeseries?" + urllib.parse.urlencode(netflow_params)
        nrec, nbody = request(f"cloudflare_netflows_control_{case}_{operator}", netflow_url, "historical_signal", token)
        incident_values: list[float] = []
        control_values: list[float] = []
        delta = None
        negative_bins = 0
        negative_bin_fraction = None
        try:
            result = json.loads(nbody).get("result", {})
            incident_values = [float(v) for v in result.get("incident", {}).get("values", []) if v not in (None, "")]
            control_values = [float(v) for v in result.get("weekday_control", {}).get("values", []) if v not in (None, "")]
            paired = [a - b for a, b in zip(incident_values, control_values)]
            delta = statistics.median(paired) if paired else None
            negative_bins = sum(value < 0 for value in paired)
            negative_bin_fraction = negative_bins / len(paired) if paired else None
        except (ValueError, TypeError, json.JSONDecodeError):
            pass

        radar_params = {"dateStart": start, "dateEnd": end, "asn": ASNS[operator], "location": "PE", "limit": 100, "format": "JSON"}
        radar_url = "https://api.cloudflare.com/client/v4/radar/annotations/outages?" + urllib.parse.urlencode(radar_params)
        rrec, rbody = request(f"cloudflare_radar_control_{case}_{operator}", radar_url, "historical_event", token)
        matching_annotations = 0
        try:
            obj = json.loads(rbody)
            for annotation in obj.get("result", {}).get("annotations", []) if obj.get("success") else []:
                annotation_asns = {str(value) for value in annotation.get("asns", [])}
                annotation_locations = {str(value).upper() for value in annotation.get("locations", [])}
                if ASNS[operator] in annotation_asns and "PE" in annotation_locations:
                    matching_annotations += 1
        except (ValueError, TypeError, json.JSONDecodeError):
            pass

        output.append({
            "incident_id": case, "operator": operator, "reference_label": "NO_CONTROL",
            "reference_independence": control.get("reference_independence", ""),
            "netflows_http_status": nrec.get("http_status"), "netflows_points": len(incident_values),
            "weekday_control_points": len(control_values), "netflows_normalized_delta": delta,
            "negative_difference_bins": negative_bins, "negative_bin_fraction": negative_bin_fraction,
            "radar_http_status": rrec.get("http_status"), "radar_matching_annotations": matching_annotations,
            "x_explicit_internet_complaint_authors": control.get("authors_with_explicit_internet_complaint", "0"),
            "x_geo_cluster_candidate": control.get("district_cluster_ge2", "False"),
            "netflows_evidence_id": nrec.get("evidence_id"), "netflows_artifact_path": nrec.get("artifact_path"),
            "radar_evidence_id": rrec.get("evidence_id"), "radar_artifact_path": rrec.get("artifact_path"),
            "window_start_utc": start, "window_end_utc": end,
        })
        time.sleep(0.2)

    write_csv(REPORTS / "detector_historical_controls.csv", output)
    return {
        "status": "COMPLETE", "controls": len(output),
        "netflows_http_200": sum(row["netflows_http_status"] == 200 for row in output),
        "radar_http_200": sum(row["radar_http_status"] == 200 for row in output),
        "report": "reports/detector_historical_controls.csv",
    }


def _cluster_bootstrap(rows: list[dict[str, Any]], flag: str, replicates: int = 5000) -> dict[str, list[float] | None]:
    """Bootstrap whole incident clusters, not correlated operator rows."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["incident_id"])].append(row)
    keys = sorted(groups)
    if len(keys) < 2:
        return {"precision": None, "sensitivity": None, "specificity": None, "matched_control_false_trigger_rate": None}
    rng = random.Random(20261025)
    samples: dict[str, list[float]] = {"precision": [], "sensitivity": [], "specificity": [], "matched_control_false_trigger_rate": []}
    for _ in range(replicates):
        picked = [rng.choice(keys) for _ in keys]
        batch = [row for key in picked for row in groups[key]]
        pos = [row for row in batch if row["reference_label"] == "POSITIVE"]
        neg = [row for row in batch if row["reference_label"] == "NO_CONTROL"]
        tp = sum(bool(row[flag]) for row in pos)
        fp = sum(bool(row[flag]) for row in neg)
        fn, tn = len(pos) - tp, len(neg) - fp
        values = {
            "precision": tp / (tp + fp) if tp + fp else None,
            "sensitivity": tp / len(pos) if pos else None,
            "specificity": tn / len(neg) if neg else None,
            "matched_control_false_trigger_rate": fp / len(neg) if neg else None,
        }
        for name, value in values.items():
            if value is not None:
                samples[name].append(value)
    result: dict[str, list[float] | None] = {}
    for name, values in samples.items():
        if not values or len(set(values)) == 1:
            result[name] = None
            continue
        values.sort()
        low = values[int(0.025 * (len(values) - 1))]
        high = values[int(0.975 * (len(values) - 1))]
        result[name] = [round(low, 4), round(high, 4)]
    return result


def _metrics(rows: list[dict[str, Any]], flag: str) -> dict[str, Any]:
    positives = [row for row in rows if row["reference_label"] == "POSITIVE"]
    controls = [row for row in rows if row["reference_label"] == "NO_CONTROL"]
    tp = sum(bool(row[flag]) for row in positives)
    fp = sum(bool(row[flag]) for row in controls)
    fn, tn = len(positives) - tp, len(controls) - fp
    precision = tp / (tp + fp) if tp + fp else None
    sensitivity = tp / len(positives) if positives else None
    specificity = tn / len(controls) if controls else None
    return {
        "true_candidate_pairs": tp, "missed_positive_pairs": fn,
        "control_candidate_pairs": fp, "quiet_control_pairs": tn,
        "precision_in_selected_matched_sample": precision,
        "sensitivity_in_selected_positive_sample": sensitivity,
        "specificity_in_matched_operator_controls": specificity,
        "matched_control_false_trigger_rate": fp / len(controls) if controls else None,
        "incident_cluster_bootstrap_95pct_ci": _cluster_bootstrap(rows, flag),
        "positive_pairs": len(positives), "matched_controls": len(controls),
    }


def _candidate_at(row: dict[str, Any], threshold: float, minimum_share: float) -> bool:
    persistent_netflow = (
        _number(row.get("netflows_http_status")) == 200
        and row.get("netflows_normalized_delta") is not None
        and row["netflows_normalized_delta"] < threshold
        and row.get("netflows_negative_bin_fraction") is not None
        and row["netflows_negative_bin_fraction"] >= minimum_share
        and row.get("netflows_paired_points", 0) >= 8
    )
    return bool(persistent_netflow or row.get("ioda_candidate") or row.get("x_geo_cluster_candidate") or row.get("hermes_candidate") or row.get("news_candidate"))


def _leave_one_incident_out(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Tune only on other incidents, then score every pair in the held-out incident."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["incident_id"])].append(row)
    grid = [(threshold, share) for threshold in (-0.01, -0.02, -0.05) for share in (0.70, 0.80, 0.90, 1.0)]
    folds = []
    for held_case in sorted(grouped):
        train = [row for case, group in grouped.items() if case != held_case for row in group]
        held = grouped[held_case]
        scored = []
        for threshold, share in grid:
            positives = [row for row in train if row["reference_label"] == "POSITIVE"]
            controls = [row for row in train if row["reference_label"] == "NO_CONTROL"]
            tp = sum(_candidate_at(row, threshold, share) for row in positives)
            fp = sum(_candidate_at(row, threshold, share) for row in controls)
            sensitivity = tp / len(positives) if positives else 0.0
            specificity = (len(controls) - fp) / len(controls) if controls else 0.0
            scored.append((sensitivity + specificity - 1, sensitivity, specificity, threshold, share))
        # Maximize training-set balanced accuracy (Youden's J); ties prefer
        # sensitivity, then specificity, then a less restrictive delta cutoff.
        best = max(scored, key=lambda item: (item[0], item[1], item[2], item[3], item[4]))
        held_pos = [row for row in held if row["reference_label"] == "POSITIVE"]
        held_neg = [row for row in held if row["reference_label"] == "NO_CONTROL"]
        for row in held:
            row["loo_delta_threshold"] = best[3]
            row["loo_minimum_bin_share"] = best[4]
            row["loo_candidate"] = _candidate_at(row, best[3], best[4])
        folds.append({
            "held_out_incident": held_case,
            "training_selected_delta_threshold": best[3],
            "training_selected_minimum_bin_share": best[4],
            "held_positive_candidates": sum(_candidate_at(row, best[3], best[4]) for row in held_pos),
            "held_positive_pairs": len(held_pos),
            "held_control_candidates": sum(_candidate_at(row, best[3], best[4]) for row in held_neg),
            "held_control_pairs": len(held_neg),
        })
    return _metrics(rows, "loo_candidate"), folds


def assemble_dataset() -> list[dict[str, Any]]:
    positives = read_csv(REPORTS / "historical_detector_replay.csv")
    netflows_positive = {(row["incident_id"], row["operator"]): row for row in read_csv(REPORTS / "cloudflare_netflows_incident_replay.csv")}
    controls = read_csv(REPORTS / "detector_historical_controls.csv")
    aligned_news = _load_aligned_news()
    ioda = {(row["incident_id"], row["operator"]): row for row in read_csv(REPORTS / "incident_reference_ioda_comparison.csv")}
    x_rows = {(row["incident_id"], row["operator"]): row for row in read_csv(REPORTS / "x_historical_incident_replay.csv")}
    # HERMES is a daily, user-initiated throughput anomaly feed. Treat it as an
    # experimental independent family only when operator, area and date match;
    # never infer a match from `reference_match` (which includes the label).
    hermes_rows = read_csv(REPORTS / "mlab_hermes_historical_replay.csv")
    hermes_by_pair: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for item in hermes_rows:
        hermes_by_pair[(item["incident_id"], item["operator"].casefold())].append(item)

    def hermes_signal(case: str, operator: str) -> tuple[bool, dict[str, Any]]:
        matched = [item for item in hermes_by_pair.get((case, operator.casefold()), []) if _hermes_signal_qualifies(item)]
        return bool(matched), {
            "rows": len(matched),
            "max_throughput_drop_pct": max((_number(x.get("throughput_drop_pct_vs_baseline")) or 0 for x in matched), default=None),
            "max_unique_clients": max((_number(x.get("sample_unique_clients")) or 0 for x in matched), default=0),
        }
    combined: list[dict[str, Any]] = []
    for source in positives:
        netflow_row = netflows_positive.get((source["incident_id"], source["operator"]), {})
        negative_fraction, paired_points = _negative_bin_fraction(netflow_row.get("artifact_path"))
        hermes_candidate, hermes_detail = hermes_signal(source["incident_id"], source["operator"])
        news_item = aligned_news.get((source["incident_id"], source["operator"].casefold()), {})
        combined.append({
            "incident_id": source["incident_id"], "operator": source["operator"],
            "reference_label": "POSITIVE", "reference_independence": source.get("reference_independence", ""),
            "netflows_normalized_delta": _number(source.get("netflows_normalized_delta")),
            "netflows_negative_bin_fraction": negative_fraction,
            "netflows_paired_points": paired_points,
            "netflows_http_status": 200,
            "ioda_candidate": _truth(source.get("ioda_onset_candidate")),
            "radar_candidate": _truth(source.get("radar_outage_annotation_candidate")),
            "x_complaint_authors": int(source.get("x_complaint_authors_unclustered") or 0),
            "x_geo_cluster_candidate": _truth(source.get("x_geo_cluster_ge2_authors_same_district_15m")),
            "hermes_candidate": hermes_candidate, "hermes_detail": hermes_detail,
            "news_candidate": bool(news_item), "news_alignment_status": "VERIFIED" if news_item else "NOT_AVAILABLE",
            "service_scope": source.get("service_scope", "unknown"),
            "source_reference": "reports/historical_detector_replay.csv",
        })
    for source in controls:
        key = (source["incident_id"], source["operator"])
        ioda_row = ioda.get(key, {})
        x_row = x_rows.get(key, {})
        negative_fraction, paired_points = _negative_bin_fraction(source.get("netflows_artifact_path"))
        hermes_candidate, hermes_detail = hermes_signal(source["incident_id"], source["operator"])
        news_item = aligned_news.get((source["incident_id"], source["operator"].casefold()), {})
        combined.append({
            "incident_id": source["incident_id"], "operator": source["operator"],
            "reference_label": "NO_CONTROL", "reference_independence": source.get("reference_independence", ""),
            "netflows_normalized_delta": _number(source.get("netflows_normalized_delta")),
            "netflows_negative_bin_fraction": negative_fraction,
            "netflows_paired_points": paired_points,
            "netflows_http_status": _number(source.get("netflows_http_status")),
            "ioda_candidate": int(ioda_row.get("ioda_event_onset_count_window") or 0) > 0,
            "radar_candidate": int(source.get("radar_matching_annotations") or 0) > 0,
            "x_complaint_authors": int(x_row.get("authors_with_explicit_internet_complaint") or 0),
            "x_geo_cluster_candidate": _truth(x_row.get("district_cluster_ge2")),
            "hermes_candidate": hermes_candidate, "hermes_detail": hermes_detail,
            "news_candidate": bool(news_item), "news_alignment_status": "VERIFIED" if news_item else "NOT_AVAILABLE",
            "service_scope": "matched_operator_control",
            "source_reference": "reports/detector_historical_controls.csv + existing IODA/X controls",
        })
    return combined


def evaluate(output_dir: Path = REPORTS) -> dict[str, Any]:
    rows = assemble_dataset()
    for row in rows:
        row["netflows_candidate"] = (
            _number(row["netflows_http_status"]) == 200
            and row["netflows_normalized_delta"] is not None
            and row["netflows_normalized_delta"] < 0
        )
        row["persistent_netflows_candidate"] = (
            _number(row["netflows_http_status"]) == 200
            and row["netflows_normalized_delta"] is not None
            and row["netflows_normalized_delta"] < -0.02
            and row["netflows_negative_bin_fraction"] is not None
            and row["netflows_negative_bin_fraction"] >= 0.90
            and row["netflows_paired_points"] >= 8
        )
        row["cloudflare_family_candidate"] = bool(row["netflows_candidate"] or row["radar_candidate"])
        row["available_source_families"] = sum((row["cloudflare_family_candidate"], row["ioda_candidate"], row["x_geo_cluster_candidate"], row["hermes_candidate"], row["news_candidate"]))
        row["sensitive_candidate"] = row["available_source_families"] >= 1
        row["corroborated_candidate"] = row["available_source_families"] >= 2
        row["strict_candidate"] = bool(row["persistent_netflows_candidate"] or row["ioda_candidate"] or row["x_geo_cluster_candidate"] or row["hermes_candidate"] or row["news_candidate"])
        row["event_reference_scope"] = "pair-level OSIPTEL/operator/media historical label; mixed precision and independence"

    thresholds = []
    for threshold in THRESHOLDS:
        for row in rows:
            row[f"netflows_below_{threshold:g}"] = (
                _number(row["netflows_http_status"]) == 200
                and row["netflows_normalized_delta"] is not None
                and row["netflows_normalized_delta"] < threshold
            )
        thresholds.append({"delta_threshold": threshold, **_metrics(rows, f"netflows_below_{threshold:g}")})

    persistence_sensitivity = []
    persistence_grid = [(-0.01, 0.90), (-0.02, 0.70), (-0.02, 0.80), (-0.02, 0.90), (-0.02, 1.00), (-0.05, 0.90)]
    for threshold, minimum_share in persistence_grid:
        key = f"persistent_{threshold:g}_{minimum_share:g}"
        for row in rows:
            row[key] = (
                _number(row["netflows_http_status"]) == 200
                and row["netflows_normalized_delta"] is not None
                and row["netflows_normalized_delta"] < threshold
                and row["netflows_negative_bin_fraction"] is not None
                and row["netflows_negative_bin_fraction"] >= minimum_share
                and row["netflows_paired_points"] >= 8
            )
        persistence_sensitivity.append({"delta_threshold": threshold, "minimum_lower_bins_share": minimum_share, **_metrics(rows, key)})

    aligned_news_count = sum(bool(row.get("news_candidate")) for row in rows)
    rule_metrics = {
        "netflows_only_delta_lt_0": _metrics(rows, "netflows_candidate"),
        "persistent_netflows_delta_lt_minus_0_02_and_90pct_bins": _metrics(rows, "persistent_netflows_candidate"),
        "any_family_sensitive_candidate": _metrics(rows, "sensitive_candidate"),
        "two_independent_families_corroborated": _metrics(rows, "corroborated_candidate"),
        "strict_candidate_union": _metrics(rows, "strict_candidate"),
        "ioda_only": _metrics(rows, "ioda_candidate"),
        "radar_only": _metrics(rows, "radar_candidate"),
        "x_geographic_cluster_only": _metrics(rows, "x_geo_cluster_candidate"),
        "mlab_hermes_experimental_only": _metrics(rows, "hermes_candidate"),
        "strict_candidate_with_hermes_and_aligned_news": _metrics(rows, "strict_candidate"),
    }
    if aligned_news_count:
        rule_metrics["news_only_independent_aligned"] = _metrics(rows, "news_candidate")
    # Leave-one-family-out is descriptive on this selected replay. It answers
    # whether a source changes candidate counts here; it is not population value.
    ablations = []
    source_flags = {"cloudflare_netflows_radar": "persistent_netflows_candidate", "ioda": "ioda_candidate", "x": "x_geo_cluster_candidate", "mlab_hermes": "hermes_candidate"}
    if aligned_news_count:
        source_flags["news"] = "news_candidate"
    for removed, flag in source_flags.items():
        remaining = []
        for row in rows:
            families = [row[k] for name, k in source_flags.items() if name != removed]
            remaining.append({**row, "candidate": any(families)})
        metric = _metrics(remaining, "candidate")
        ablations.append({"removed_family": removed, **metric,
                          "delta_positive_pairs_vs_all": sum(r["strict_candidate"] for r in rows) - metric["true_candidate_pairs"],
                          "delta_matched_control_pairs_vs_all": sum(r["strict_candidate"] for r in rows if r["reference_label"] == "NO_CONTROL") - metric["control_candidate_pairs"]})

    positives = [row for row in rows if row["reference_label"] == "POSITIVE"]
    controls = [row for row in rows if row["reference_label"] == "NO_CONTROL"]
    technology_coverage: dict[str, dict[str, int]] = {}
    for operator in sorted({row["operator"] for row in rows}):
        op_rows = [row for row in positives if row["operator"] == operator]
        scopes = [str(row.get("service_scope", "unknown")).casefold() for row in op_rows]
        technology_coverage[operator] = {
            "positive_pairs": len(op_rows),
            "fixed_only_pairs": sum("fixed" in scope and "mobile" not in scope for scope in scopes),
            "mobile_only_pairs": sum("mobile" in scope and "fixed" not in scope for scope in scopes),
            "mixed_fixed_mobile_pairs": sum("fixed" in scope and "mobile" in scope for scope in scopes),
            "unspecified_pairs": sum(not any(x in scope for x in ("fixed", "mobile")) for scope in scopes),
        }
    live_latency = {"status": "NOT_MEASURABLE_FROM_REPLAY", "pairs_with_first_valid_detector_alert_timestamp": 0,
                    "pairs_with_independent_incident_start_timestamp": 0,
                    "reason": "Historical signal snapshots contain window aggregates, not timestamped first-valid alerts and independently timed incident onset pairs."}
    negative_windows = {"status": "MISSING_INDEPENDENT_NORMAL_WINDOWS", "count": 0,
                       "available_controls": len(controls),
                       "control_definition": "operator not named in an incident window; not independently confirmed normal time"}
    positives = [row for row in rows if row["reference_label"] == "POSITIVE"]
    controls = [row for row in rows if row["reference_label"] == "NO_CONTROL"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["incident_id"]].append(row)
    group_events = []
    for case, group in grouped.items():
        pos = [row for row in group if row["reference_label"] == "POSITIVE"]
        neg = [row for row in group if row["reference_label"] == "NO_CONTROL"]
        group_events.append({
            "incident_id": case,
            "positive_operator_pairs": len(pos),
            "positive_pairs_flagged": sum(row["sensitive_candidate"] for row in pos),
            "positive_event_has_candidate": any(row["sensitive_candidate"] for row in pos),
            "unaffected_operator_pairs_flagged": sum(row["sensitive_candidate"] for row in neg),
            "unaffected_operators_flagged": ";".join(row["operator"] for row in neg if row["sensitive_candidate"]),
            "positive_pairs_strict_candidate": sum(row["strict_candidate"] for row in pos),
            "strict_positive_event_has_candidate": any(row["strict_candidate"] for row in pos),
            "unaffected_operator_pairs_strict_flagged": sum(row["strict_candidate"] for row in neg),
            "strict_unaffected_operators_flagged": ";".join(row["operator"] for row in neg if row["strict_candidate"]),
        })
    loo_metrics, loo_folds = _leave_one_incident_out(rows)
    rule_metrics["leave_one_incident_out"] = loo_metrics

    summary = {
        "algorithm_version": "rule-detector-2026-10-25-v4-hermes-ablation-audit",
        "approach": "Deterministic multi-source rules. No machine learning: 8 incidents are too few to fit and validate a generalizable model.",
        "data_scope": "15 positive operator-event pairs and 17 matched operator-not-affected controls across 8 historical incident windows.",
        "labels": "Controls mean the operator was not named as affected in that incident reference; they are matched operator controls, not a broad independent sample of outage-free time.",
        "main_candidate_rule": "Experimental candidate if persistent Cloudflare NetFlows, IODA onset, X explicit complaint cluster, M-Lab HERMES throughput anomaly, OR a human-reviewed news item aligned to incident operator/area/time and independently sourced. HERMES is counted only for exact incident date + area + operator, >=40% throughput drop, >=80% anomalous sample fraction and >=5 clients; news RSS extraction alone cannot authorize activation.",
        "corroboration_rule": "At least two distinct reviewed families among Cloudflare (NetFlows/Radar), IODA, X, M-Lab HERMES and news. News is eligible only with explicit operator-area-time alignment and source-independence review; a story derived from social complaints does not count independently from X. Live creative simulator still requires fresh direct internet signal, aligned independent corroboration and verified geography.",
        "news_integration": {"collector": "python -m win_validation.detector --fetch-news", "historical_alignment_file": "reports/news_historical_incident_replay.csv", "accepted_rows": len(_load_aligned_news()), "historical_aligned_rows_in_replay": aligned_news_count, "status": "INTEGRATED_NO_ALIGNED_HISTORICAL_CANDIDATES" if aligned_news_count == 0 else "INTEGRATED_WITH_REVIEWED_HISTORICAL_CANDIDATES", "current_feed_candidates_are_not_automatically_independent": True},
        "rule_metrics": rule_metrics,
        "source_ablation": {"status": "DESCRIPTIVE_SELECTED_REPLAY", "results": ablations,
                            "caveat": "Ablations compare candidate counts on the same selected positive and matched-operator-control replay; they do not estimate independent incremental value."},
        "validation_gaps": {"independent_negative_windows": negative_windows, "live_detection_latency": live_latency,
                            "fixed_mobile_attribution_by_operator": technology_coverage,
                            "geographic_completeness": {"missing_ubigeo": ["120307", "130112", "160405"], "district_geometry_activation_safe": False,
                                                         "note": "The official boundary crosswalk is incomplete for two codes; the available 130112 geometry is a candidate patch, not a complete authoritative boundary."},
                            "aligned_corroboration": {"current_live_candidate_has_same_operator_zone_time_independent_confirmation": False,
                                                      "policy": "No aggregation across operator, zone, technology or non-overlapping time windows."}},
        "hermes_evaluation_rule": {"exact_operator_area_date": True, "minimum_throughput_drop_pct": 40,
                                   "minimum_anomalous_sample_fraction": 0.8, "minimum_unique_clients": 5,
                                   "role": "experimental direct performance signal; daily, user-initiated; not an outage proof"},
        "leave_one_incident_out_folds": loo_folds,
        "netflows_threshold_sensitivity": thresholds,
        "netflows_persistence_sensitivity": persistence_sensitivity,
        "positive_pairs": len(positives), "matched_control_pairs": len(controls),
        "incidents_with_any_positive_candidate": sum(e["positive_event_has_candidate"] for e in group_events),
        "incidents_with_any_unaffected_operator_flagged": sum(e["unaffected_operator_pairs_flagged"] > 0 for e in group_events),
        "incidents_with_strict_positive_candidate": sum(e["strict_positive_event_has_candidate"] for e in group_events),
        "incidents_with_strict_unaffected_operator_flagged": sum(e["unaffected_operator_pairs_strict_flagged"] > 0 for e in group_events),
        "events": group_events,
        "confidence_and_usage": "These are development-set descriptive metrics on a selected matched sample. Uncertainty intervals resample whole incident clusters because operator pairs within an incident are not independent. Do not interpret as population precision/recall or launch criteria; thresholds were explored on positive cases before matched control signals were fetched.",
        "critical_limits": [
            "The 17 controls are operator-not-affected pairs during real incident windows, not independent normal windows; the observed control-trigger rate is a matched-control false-trigger rate only.",
            "Positive labels mix OSIPTEL, operator and media references with different time precision and independence.",
            "NetFlows is a normalized partial Cloudflare view, not total operator traffic. Its prior-week comparator is not independently verified normal.",
            "Lima GeoID NetFlows returned only zero-valued data; geographic targeting below Peru is not demonstrated by that source.",
            "No first-alert timestamps exist in this historical replay, so alert lead time/freshness is not measured.",
            "Fixed and mobile attribution is unresolved for most pairs; a broad ASN signal can flag an unaffected operator during a shared-area event.",
            "Human complaints are corroborative context; the evaluated district/time X cluster rule did not activate in these cases.",
        ],
        "control_query_completeness": {
            "netflows_controls_http_200": sum(_number(row.get("netflows_http_status")) == 200 and _number(row.get("netflows_normalized_delta")) is not None for row in read_csv(REPORTS / "detector_historical_controls.csv")),
            "radar_controls_http_200": sum(_number(row.get("radar_http_status")) == 200 for row in read_csv(REPORTS / "detector_historical_controls.csv")),
            "ioda_controls_http_200": sum(_number(row.get("http_status")) == 200 for row in read_csv(REPORTS / "incident_reference_ioda_comparison.csv") if row.get("reference_case_operator") == "NO_CONTROL"),
            "expected_matched_controls": len(controls),
            "x_controls_complete": sum(not row.get("http_or_parse_errors") and not _truth(row.get("pagination_capped")) for row in read_csv(REPORTS / "x_historical_incident_replay.csv") if row.get("reference_label") == "NO_CONTROL"),
        },
        "outputs": {
            "csv": "reports/robust_detector_replay.csv",
            "summary": "reports/robust_detector_replay.json",
            "report": "reports/robust_detector_replay.md",
            "controls": "reports/detector_historical_controls.csv",
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "robust_detector_replay.csv", rows)
    write_csv(output_dir / "robust_detector_event_summary.csv", group_events)
    (output_dir / "robust_detector_replay.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    def pct(value: Any) -> str:
        return "n/a" if value is None else f"{value * 100:.1f}%"

    def ci_pct(interval: Any) -> str:
        return "n/a" if not interval else f"{interval[0] * 100:.1f}–{interval[1] * 100:.1f}%"

    metric_rows = []
    for label, key in [
        ("NetFlows básico, delta < 0", "netflows_only_delta_lt_0"),
        ("NetFlows persistente, delta < −0.02 y ≥90% de bins", "persistent_netflows_delta_lt_minus_0_02_and_90pct_bins"),
        ("Regla sensible: cualquier familia", "any_family_sensitive_candidate"),
        ("Regla corroborada: dos familias", "two_independent_families_corroborated"),
        ("Candidato estricto: persistencia o señal independiente", "strict_candidate_union"),
        ("Ajuste por incidente excluido (LOIO)", "leave_one_incident_out"),
        ("IODA", "ioda_only"), ("Radar", "radar_only"), ("X: grupo geográfico", "x_geographic_cluster_only"),
        ("M-Lab HERMES experimental", "mlab_hermes_experimental_only"),
    ]:
        m = rule_metrics[key]
        ci = m["incident_cluster_bootstrap_95pct_ci"]
        metric_rows.append(f"| {label} | {m['true_candidate_pairs']}/{m['positive_pairs']} | {m['control_candidate_pairs']}/{m['matched_controls']} | {pct(m['sensitivity_in_selected_positive_sample'])} ({ci_pct(ci['sensitivity'])}) | {pct(m['matched_control_false_trigger_rate'])} ({ci_pct(ci['matched_control_false_trigger_rate'])}) | {pct(m['precision_in_selected_matched_sample'])} |")
    if aligned_news_count:
        m = rule_metrics["news_only_independent_aligned"]
        ci = m["incident_cluster_bootstrap_95pct_ci"]
        metric_rows.append(f"| Noticias: alineación revisada e independiente | {m['true_candidate_pairs']}/{m['positive_pairs']} | {m['control_candidate_pairs']}/{m['matched_controls']} | {pct(m['sensitivity_in_selected_positive_sample'])} ({ci_pct(ci['sensitivity'])}) | {pct(m['matched_control_false_trigger_rate'])} ({ci_pct(ci['matched_control_false_trigger_rate'])}) | {pct(m['precision_in_selected_matched_sample'])} |")
    threshold_rows = [f"| {m['delta_threshold']:g} | {m['true_candidate_pairs']}/{m['positive_pairs']} | {m['control_candidate_pairs']}/{m['matched_controls']} | {pct(m['sensitivity_in_selected_positive_sample'])} | {pct(m['specificity_in_matched_operator_controls'])} |" for m in thresholds]
    persistence_rows = [f"| {m['delta_threshold']:g} | {m['minimum_lower_bins_share']:.0%} | {m['true_candidate_pairs']}/{m['positive_pairs']} | {m['control_candidate_pairs']}/{m['matched_controls']} |" for m in persistence_sensitivity]
    event_rows = [f"| {e['incident_id']} | {e['positive_pairs_strict_candidate']}/{e['positive_operator_pairs']} | {e['unaffected_operator_pairs_strict_flagged']} | {e['strict_unaffected_operators_flagged'] or '—'} |" for e in group_events]
    report = [
        "# Detector de interrupciones: replay retrospectivo robustecido (solo software)", "",
        "## Qué se construyó", "",
        "Un detector determinístico y reproducible con Cloudflare NetFlows/Radar, IODA, quejas agregadas de X y M-Lab HERMES como señal experimental de rendimiento. No se entrenó un modelo estadístico porque ocho incidentes no permiten entrenar y validar uno generalizable. NetFlows y Radar se agrupan como una sola familia Cloudflare.", "",
        "El colector RSS/XML de siete medios también está conectado mediante `python -m win_validation.detector --fetch-news`; revisa únicamente el contenido incluido en cada feed y no abre artículos. La última consulta registrada y el número de ítems por medio se muestran en `reports/current_news_feed_status.csv`; no generó candidatos. No hay casos periodísticos históricos alineados por operador, zona y hora en este replay, así que las noticias todavía no forman parte de sus métricas ni tienen aporte incremental medido. Ver también `reports/current_news_candidates.csv`.", "",
        "## Resultado en positivos y controles emparejados", "",
        f"La muestra contiene **{len(positives)} pares positivos** y **{len(controls)} pares control** en **{len(grouped)} incidentes**. NetFlows básico marcó 9/15 positivos y 9/17 controles. La regla estricta v4, con HERMES experimental, marcó {rule_metrics['strict_candidate_union']['true_candidate_pairs']}/{len(positives)} positivos y {rule_metrics['strict_candidate_union']['control_candidate_pairs']}/{len(controls)} controles; a nivel de incidente encontró afectados en {summary['incidents_with_strict_positive_candidate']}/{len(grouped)} y señaló controles en {summary['incidents_with_strict_unaffected_operator_flagged']}/{len(grouped)} incidentes. En la evaluación dejando fuera cada incidente completo y ajustando con los demás, marcó {loo_metrics['true_candidate_pairs']}/{len(positives)} positivos y {loo_metrics['control_candidate_pairs']}/{len(controls)} controles.", "",
        "| Regla | Positivos con señal | Controles con señal | Sensibilidad (IC 95% por incidente) | Activación en controles (IC 95% por incidente) | Precisión en esta muestra balanceada |", "|---|---:|---:|---:|---:|---:|", *metric_rows, "",
        "Las métricas describen esta muestra seleccionada y no son estimaciones poblacionales. Los controles son pares de operadores no reportados como afectados dentro de incidentes reales. La regla v4 agrega persistencia NetFlows y HERMES experimental, pero no equivale a una política de activación.", "",
        "## Sensibilidad del umbral NetFlows", "",
        "El umbral 0 reproduce la regla exploratoria previa. Los demás cortes muestran el intercambio entre casos positivos marcados y operadores control señalados. El barrido conjunto delta/persistencia permite ver qué se pierde al exigir una caída más consistente. La tabla de reglas incluye una evaluación agrupada que deja fuera un incidente completo para cada pliegue; sus umbrales se eligen solo en los otros incidentes.", "",
        "| Delta normalizado < | Positivos detectados | Controles marcados | Sensibilidad | Especificidad en controles emparejados |", "|---:|---:|---:|---:|---:|", *threshold_rows, "",
        "### Persistencia por intervalos de 15 minutos", "",
        "| Delta < | Proporción mínima de intervalos bajo comparador | Positivos marcados | Controles marcados |", "|---:|---:|---:|---:|", *persistence_rows, "",
        "## Dónde hubo candidatos", "",
        "| Incidente | Pares afectados con candidato | Pares control marcados | Operadores control marcados |", "|---|---:|---:|---|", *event_rows, "",
        "## Cómo decide", "",
        "1. Calcula señales por operador e intervalo; NetFlows y Radar cuentan como una sola familia Cloudflare.\n2. NetFlows activa la ruta estricta si su diferencia normalizada es menor que −0.02, al menos 90% de los intervalos están debajo del comparador semanal y hay al menos ocho pares de intervalos.\n3. IODA puede generar candidato por inicio de evento; X requiere dos autores distintos en un distrito inequívoco y bloque UTC de 15 minutos.\n4. `CORROBORADO` exige dos familias distintas. La regla estricta genera candidatos, no confirma una pérdida de internet.", "",
        "## Qué demuestra y qué no", "",
        "Demuestra que el código reproduce las reglas sobre señales históricas y revela el problema de falsos disparos hacia operadores no incluidos en los reportes de afectación. **No demuestra** rendimiento en tiempo real, frescura, precisión poblacional, ni capacidad para localizar el disparo por distrito. Los controles son los otros operadores dentro de ventanas de incidentes reales, no ventanas normales independientes; algunas afectaciones pueden no haber sido reportadas. Las referencias positivas también mezclan reportes regulatorios, de operadores y de prensa.", "",
        "El NetFlows de Lima filtrado por GeoID devolvió 668 valores en cero para cada operador, así que la evaluación usa únicamente las consultas históricas por país y ASN y no acredita cobertura distrital. La atribución fijo/móvil permanece débil. No se usó ni se requiere hardware.", "",
        "## Auditoría de brechas incorporada en v4", "",
        f"- **Negativos independientes:** {negative_windows['count']} ventanas normales etiquetadas; los {negative_windows['available_controls']} controles existentes solo indican operadores no nombrados dentro de incidentes.",
        f"- **Latencia en vivo:** {live_latency['pairs_with_first_valid_detector_alert_timestamp']} pares con primer alerta válida y hora de inicio independiente; no se puede calcular frescura de detección con este replay.",
        "- **Operador/tecnología:** la tabla siguiente cuenta solo etiquetas explícitas en las referencias; lo mixto no se redistribuye a fijo o móvil.",
        "- **Geografía:** quedan sin geometría oficial completa 120307 y 160405; 130112 usa un parche candidato, por lo que ninguno debe habilitarse como límite oficial final sin completar cotejo.",
        "- **Corroboración:** el candidato vivo de Ica no tiene confirmación independiente alineada por operador, zona y tiempo; se mantiene suprimido.",
        "- **Ablación:** se calculó el cambio de candidatos al retirar cada familia en el replay seleccionado. Es una comparación descriptiva, no valor incremental validado, porque faltan ventanas normales independientes.", "",
        "| Operador | Pares positivos | Solo fijo | Solo móvil | Fijo+móvil | Sin atribución |", "|---|---:|---:|---:|---:|---:|",
        *[f"| {op} | {v['positive_pairs']} | {v['fixed_only_pairs']} | {v['mobile_only_pairs']} | {v['mixed_fixed_mobile_pairs']} | {v['unspecified_pairs']} |" for op, v in technology_coverage.items()], "",
        "### Ablación de familias", "",
        "| Familia retirada | Positivos que aún generan candidato | Controles emparejados que aún generan candidato |", "|---|---:|---:|",
        *[f"| {item['removed_family']} | {item['true_candidate_pairs']}/{item['positive_pairs']} | {item['control_candidate_pairs']}/{item['matched_controls']} |" for item in ablations], "",
        "HERMES se añadió como señal experimental de rendimiento. Para este replay se aplicó una puerta exploratoria: operador, área y fecha exactos; caída de throughput ≥40%; fracción anómala ≥80%; y al menos cinco clientes. Los umbrales se definieron con la muestra disponible y no están validados prospectivamente. HERMES es diario y no prueba por sí solo una interrupción de internet.", "",
        f"**Conclusión:** el replay v4, incluyendo HERMES, marca {rule_metrics['strict_candidate_union']['true_candidate_pairs']}/{len(positives)} pares positivos y {rule_metrics['strict_candidate_union']['control_candidate_pairs']}/{len(controls)} controles emparejados. Al retirar HERMES, queda en {next(x for x in ablations if x['removed_family'] == 'mlab_hermes')['true_candidate_pairs']}/{len(positives)} positivos y {next(x for x in ablations if x['removed_family'] == 'mlab_hermes')['control_candidate_pairs']}/{len(controls)} controles. LOIO (con umbral ajustado por pliegue) marca {loo_metrics['true_candidate_pairs']}/{len(positives)} positivos y {loo_metrics['control_candidate_pairs']}/{len(controls)} controles. La muestra no prueba métricas poblacionales ni latencia operacional.", "",
        "Código: `src/win_validation/detector.py`. Datos reproducibles: `robust_detector_replay.csv`, `robust_detector_event_summary.csv`, `robust_detector_replay.json` y `detector_historical_controls.csv`. Ejecutar `python -m win_validation.detector`; añadir `--fetch-controls` para volver a consultar los controles Cloudflare y guardar evidencia.",
    ]
    (output_dir / "robust_detector_replay.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a software-only historical replay of the outage detector")
    parser.add_argument("--fetch-controls", action="store_true", help="Fetch historical Cloudflare data for matched non-affected operator controls")
    parser.add_argument("--fetch-news", action="store_true", help="Fetch tested top-10 Peru RSS/XML feeds and emit news corroboration candidates; never fetch article pages")
    args = parser.parse_args()
    news = None
    if args.fetch_controls:
        fetched = fetch_matched_controls()
        print(json.dumps({"control_fetch": fetched}, ensure_ascii=False, indent=2))
        if fetched.get("status") != "COMPLETE":
            return
    if args.fetch_news:
        from .news import collect_current_news
        news = collect_current_news()
    summary = evaluate()
    output = {"replay": summary}
    if news is not None:
        output["news_ingestion"] = news
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
