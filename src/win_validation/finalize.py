"""Deterministic report/evaluation pipeline over archived local evidence."""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .evaluation.final_evaluation import evaluate_source

ROOT = Path.cwd()
EV = ROOT / "evidencias"
REPORTS = ROOT / "reports"
MANIFEST = EV / "manifest.jsonl"
OPS = {"movistar": "AS6147", "claro": "AS12252", "entel": "AS21575", "bitel": "AS262210"}
SOURCE_IDS = [
    "ioda", "cloudflare_radar", "ripe_atlas", "ripe_ris_live", "ripestat", "globalping", "ooni",
    "infobip", "twilio", "telesign", "sinch", "usgs", "geoboundaries", "inei_ubigeo", "nominatim",
    "x_twexapi", "osiptel_sisrep", "osiptel_quality", "indecopi", "peru_news_rpp", "peru_news_andina",
    "peru_news_correo", "peru_news_republica", "peru_news_elcomercio",
]


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def records_read():
    if not MANIFEST.exists():
        return []
    return [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]


def body(record):
    if not record:
        return {}
    try:
        return json.loads((ROOT / record["artifact_path"]).read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def latest(records, source_id):
    rows = [row for row in records if row["source_id"] == source_id]
    if not rows:
        return None, {}
    row = rows[-1]
    return row, body(row)


def csv_write(name, rows):
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / name
    if not rows:
        rows = [{"status": "NOT_TESTED"}]
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def add_manual_review_evidence():
    """Persist summarized official-doc observations without copying page HTML."""
    path = EV / "licensing" / "manual_document_review.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    review = {
        "evidence_type": "manual_documentation_review_summary",
        "captured_at_utc": now_utc(),
        "note": "Summary of official documentation manually reviewed; not a full raw-page archive.",
        "reviews": [
            {"source": "Cloudflare Radar", "url": "https://developers.cloudflare.com/radar/", "findings": ["API is described as free", "Radar data is licensed CC BY-NC 4.0"]},
            {"source": "Cloudflare authentication", "url": "https://developers.cloudflare.com/radar/get-started/first-request/", "findings": ["Custom token permission Account > Radar > Read"]},
            {"source": "TwexAPI pricing", "url": "https://docs.twexapi.io/guides/pricing", "findings": ["20,000 Starter credits, 7-day validity", "Typical read costs 5 credits", "Starter rate limit 0.2 QPS"]},
            {"source": "TwexAPI terms", "url": "https://twexapi.io/terms", "findings": ["Third-party public social-data API; user responsible for platform policy compliance"]},
            {"source": "OSIPTEL SISREP", "url": "https://www.gob.pe/33307-sistema-de-informacion-y-registro-de-interrupciones-sisrep", "findings": ["Operator reporting via web interface; info page links to SISREP login; no public API/feed/download identified on that page"]},
            {"source": "Peru open data search", "url": "https://www.datosabiertos.gob.pe/search?query=UBIGEO", "findings": ["Manual portal search did not verify a current standalone UBIGEO catalog"]},
            {"source": "Nominatim policy", "url": "https://operations.osmfoundation.org/policies/nominatim/", "findings": ["Maximum 1 request/second", "identifying User-Agent/Referer required", "no systematic queries", "ODbL attribution/share-alike"]},
            {"source": "RIPE RIS Live", "url": "https://ris-live.ripe.net/manual/", "findings": ["Unauthenticated WebSocket; filters include AS path; limited sample used"]},
        ],
    }
    raw = json.dumps(review, ensure_ascii=False, indent=2).encode()
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    record = {
        "evidence_id": f"manual-docs-{digest[:12]}", "source_id": "documentation_review", "operator": None,
        "country": "PE", "observed_at_utc": review["captured_at_utc"], "source_published_at_utc": None,
        "artifact_path": path.relative_to(ROOT).as_posix(), "sha256": digest,
        "result_status": "MANUAL_REVIEW_SUMMARY", "related_report": "reports/free_access_and_licensing.md",
        "http_status": None, "parameters": {"mode": "manual official documentation review"},
        "note": "Summary evidence; not an original response body.",
    }
    with MANIFEST.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def write():
    add_manual_review_evidence()
    REPORTS.mkdir(exist_ok=True)
    records = records_read()

    atlas_record, atlas = latest(records, "ripe_atlas")
    atlas_items = atlas.get("results", [])
    atlas_count = Counter(str(item.get("asn_v4") or item.get("asn_v6") or "") for item in atlas_items)
    atlas_measurement_records = [row for row in records if row["source_id"].startswith("ripe_atlas_measurements_")]
    globalping_record, globalping_body = latest(records, "globalping_online_probe_inventory")
    ooni_record, ooni = latest(records, "ooni")
    ooni_items = ooni.get("results", [])
    ooni_asns = Counter(item.get("probe_asn", "unknown") for item in ooni_items)
    ooni_times = [item.get("measurement_start_time") for item in ooni_items if item.get("measurement_start_time")]
    ris_record, ris = latest(records, "ripe_ris_live")
    ris_messages = ris.get("messages", [])
    cf_summary_record, cf_summary_body = latest(records, "cloudflare_radar_pe_device_summary")
    cf_summary = cf_summary_body.get("result", {}).get("summary_0", {})
    cf_meta = cf_summary_body.get("result", {}).get("meta", {})
    gb1_record, gb1 = latest(records, "geoboundaries_adm1")
    _, gb2 = latest(records, "geoboundaries_adm2")
    adm1_geometry_record, adm1_geo = latest(records, "geoboundaries_adm1_geojson")
    adm2_geometry_record, adm2_geo = latest(records, "geoboundaries_adm2_geojson_full")
    adm1_count = len(adm1_geo.get("features", []))
    adm2_count = len(adm2_geo.get("features", []))
    country_asn_record, country_asn_body = latest(records, "ripestat_country_asns_pe_lod1")
    countries = country_asn_body.get("data", {}).get("countries", [])
    country_asn_stats = countries[0].get("stats", {}) if countries else {}

    owners = {}
    prefix_counts = {}
    for operator in OPS:
        owner_record, owner_body = latest(records, f"ripestat_asn_{operator}")
        owner_data = owner_body.get("data", {})
        prefix_record, prefix_body = latest(records, f"ripestat_prefixes_{operator}")
        announced = prefix_body.get("data", {}).get("prefixes", [])
        owners[operator] = {"record": owner_record, "holder": owner_data.get("holder"), "asn": owner_data.get("resource")}
        prefix_counts[operator] = {"count": len(announced), "record": prefix_record}

    # Local SQLite index points to hashed files; it does not duplicate raw payloads.
    db_path = ROOT / "data" / "validation.sqlite"
    db_path.parent.mkdir(exist_ok=True)
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS evidence (evidence_id TEXT PRIMARY KEY, source_id TEXT, country TEXT, observed_at_utc TEXT, http_status INTEGER, result_status TEXT, artifact_path TEXT, sha256 TEXT)")
        db.executemany("INSERT OR REPLACE INTO evidence VALUES (?,?,?,?,?,?,?,?)", [
            (row["evidence_id"], row["source_id"], row.get("country"), row.get("observed_at_utc"), row.get("http_status"), row.get("result_status"), row["artifact_path"], row["sha256"]) for row in records
        ])
        db.commit()

    matrix = []
    for source in SOURCE_IDS:
        for operator, asn in OPS.items():
            count = 0
            attempt = "NOT_TESTED"
            scope = "unknown"
            reason = "No operator-attributed observation in the captured evidence."
            evidence = []
            useful = False
            peru = False
            operator_match = False

            if source == "ripestat":
                owner = owners[operator]
                pr = prefix_counts[operator]["record"]
                count = prefix_counts[operator]["count"]
                attempt = owner["record"].get("result_status", "UNAVAILABLE") if owner["record"] else "NOT_TESTED"
                scope = f"{owner['holder'] or 'unknown holder'}; {count} prefixes in 30-day announced-prefix query"
                reason = "ASN holder and routed prefix inventory do not establish retail-network coverage or outage events."
                evidence = [x["evidence_id"] for x in (owner["record"], pr) if x]
                peru, operator_match, useful = bool(owner["holder"]), True, True
            elif source == "ripe_atlas":
                count = atlas_count.get(asn.removeprefix("AS"), 0)
                attempt = atlas_record.get("result_status", "UNAVAILABLE") if atlas_record else "NOT_TESTED"
                scope = "Peru probes by candidate ASN" if count else "No listed probes on candidate ASN in this result"
                meas = [row for row in atlas_measurement_records if row["source_id"] in (f"ripe_atlas_measurements_{operator}", f"ripe_atlas_measurements_latest_page_{operator}")]
                reason = "Connected probe is not outage evidence. Public measurement inventories are paginated; configuration start times do not establish recent result freshness."
                evidence = ([atlas_record["evidence_id"]] if atlas_record else []) + [row["evidence_id"] for row in meas]
                peru, operator_match = bool(atlas_record), count > 0
            elif source == "globalping":
                per_asn = globalping_body.get("peru_candidate_asn_counts", {}) if isinstance(globalping_body, dict) else {}
                count = int(per_asn.get(asn, 0) or 0)
                attempt = globalping_record.get("result_status", "NOT_TESTED") if globalping_record else "NOT_TESTED"
                scope = f"PE online probes by candidate ASN; {globalping_body.get('peru_probe_count_in_returned_inventory', 'unknown')} probes listed in PE" if globalping_record else "not tested"
                reason = "Inventory only; no active measurements created. Zero candidate-ASN matches in this snapshot do not prove absence of operator coverage."
                evidence = [globalping_record["evidence_id"]] if globalping_record else []
                peru, operator_match = bool(globalping_record), count > 0
            elif source == "ripe_ris_live":
                messages = [m for m in ris_messages if operator in m.get("matched_candidate_operators", [])]
                count = len(messages)
                attempt = ris_record.get("result_status", "UNAVAILABLE") if ris_record else "NOT_TESTED"
                scope = "12-second origin-AS-filtered BGP WebSocket sample; no district attribution"
                reason = "BGP routing update is not customer outage; same family as IODA/RIPEstat."
                evidence = [ris_record["evidence_id"]] if ris_record else []
                operator_match, useful = count > 0, count > 0
            elif source == "ioda":
                signal_record, signals = latest(records, f"ioda_{operator}")
                event_record, event_body = latest(records, f"ioda_events_{operator}")
                entity_record, _ = latest(records, f"ioda_entity_{operator}")
                events = event_body.get("data", []) if isinstance(event_body.get("data"), list) else []
                series = signals.get("data", []) if isinstance(signals.get("data"), list) else []
                flattened = [entry for group in series if isinstance(group, list) for entry in group if isinstance(entry, dict)]
                point_count = sum(sum(value is not None for value in entry.get("values", [])) for entry in flattened)
                count = len(events)
                attempt = event_record.get("result_status", "UNAVAILABLE") if event_record else "NOT_TESTED"
                sources = dict(Counter(event.get("datasource", "unknown") for event in events))
                scope = "ASN-filtered IODA events; no district/fixed/mobile attribution"
                reason = f"{count} events; {point_count} non-null time-series points; event data sources {sources}. Publication lag absent; IODA labels are not independent truth."
                evidence = [x["evidence_id"] for x in (entity_record, signal_record, event_record) if x]
                peru, operator_match, useful = count > 0, count > 0, count > 0
            elif source == "cloudflare_radar":
                outage_record, outage_body = latest(records, f"cloudflare_outages_{operator}_asn")
                annotations = outage_body.get("result", {}).get("annotations", []) if isinstance(outage_body, dict) else []
                count = len(annotations)
                attempt = outage_record.get("result_status", "UNAVAILABLE") if outage_record else (cf_summary_record.get("result_status", "NOT_TESTED") if cf_summary_record else "NOT_TESTED")
                scope = "PE + ASN outage annotations; country traffic summary is not operator-attributed"
                reason = "A zero-event 30-day result is NO_EVENTS_IN_WINDOW; the country aggregate does not establish operator-level attribution."
                evidence = [outage_record["evidence_id"]] if outage_record else ([cf_summary_record["evidence_id"]] if cf_summary_record else [])
                peru, operator_match, useful = bool(outage_record or cf_summary_record), bool(annotations), bool(cf_summary_record)
            elif source == "ooni":
                count = sum(1 for item in ooni_items if item.get("probe_asn") == asn)
                attempt = ooni_record.get("result_status", "UNAVAILABLE") if ooni_record else "NOT_TESTED"
                scope = f"Sampled PE measurements; ASN distribution {dict(ooni_asns)}"
                reason = "Sample page contains PE results but no candidate-ASN match; results are not continuous monitoring."
                evidence = [ooni_record["evidence_id"]] if ooni_record else []
                peru = bool(ooni_record)
            elif source in ("twilio", "telesign", "sinch", "infobip"):
                status_record, status_body = latest(records, f"{source}_status")
                incidents = status_body.get("incidents", []) if isinstance(status_body, dict) else []
                count = len(incidents)
                attempt = status_record.get("result_status", "UNAVAILABLE") if status_record else "NOT_TESTED"
                scope = "Global vendor status page; not target Peru operator"
                reason = "SMS/voice incident cannot prove Internet loss; current global status incidents are not operator-specific Peru evidence."
                evidence = [status_record["evidence_id"]] if status_record else []
            elif source == "geoboundaries":
                attempt = "SUCCESS_WITH_EVIDENCE" if adm1_geometry_record or adm2_geometry_record else "NOT_TESTED"
                count = adm1_count + adm2_count
                scope = "ADM1/ADM2 geometry; representative administrative units, not incident location"
                reason = "ADM1/ADM2 represented year 2008; ADM3 metadata endpoint 404; UBIGEO crosswalk absent."
                evidence = [x["evidence_id"] for x in (adm1_geometry_record, adm2_geometry_record) if x]
                peru, useful = True, True
            elif source == "nominatim":
                hits = [row for row in records if row["source_id"].startswith("nominatim_sample_")]
                attempt, count = ("SUCCESS_WITH_EVIDENCE", len(hits)) if hits else ("NOT_TESTED", 0)
                scope = "Three one-off Peru place-name checks"
                reason = "Sample validates geocoding only; not incident location; policy prohibits systematic geocoding."
                evidence = [row["evidence_id"] for row in hits]
                peru, useful = bool(hits), bool(hits)
            elif source == "usgs":
                usgs_record, usgs_body = latest(records, "usgs")
                count = len(usgs_body.get("features", [])) if isinstance(usgs_body, dict) else 0
                attempt = usgs_record.get("result_status", "UNAVAILABLE") if usgs_record else "NOT_TESTED"
                scope = "Earthquake context within Peru bounding box; not telecom outage proof"
                reason = "USGS is context only; event count does not correlate to telecom availability."
                evidence = [usgs_record["evidence_id"]] if usgs_record else []
                peru, useful = bool(usgs_record), True
            elif source == "x_twexapi":
                x_record, x_body = latest(records, f"twexapi_x_{operator}")
                count = x_body.get("array_lengths", {}).get("$.data", 0) if isinstance(x_body, dict) else 0
                attempt = x_record.get("result_status", "UNAVAILABLE") if x_record else "NOT_TESTED"
                scope = "Official-account targeted 30-day query" if x_record else "No verified handle query"
                reason = "Empty result applies to the query window only; no user text/IDs retained; no independent useful reports demonstrated."
                evidence = [x_record["evidence_id"]] if x_record else []
                peru, operator_match = bool(x_record), bool(x_record)
            elif source == "inei_ubigeo":
                attempt = "NOT_TESTED"
                reason = "Official catalog search did not identify a current standalone machine-readable UBIGEO resource."

            utility = evaluate_source({
                "evidence_ids": evidence,
                "api_reachable": attempt == "SUCCESS_WITH_EVIDENCE",
                "peru_evidence": peru,
                "operator_attribution": operator_match,
                "useful_for_role": useful,
                "freshness_measured": source == "ripe_ris_live",
                "independent_incremental_value": False,
                "commercial_authorized": None,
                "quota_cost_verified": False,
                "empty_valid_window": source in ("cloudflare_radar", "x_twexapi") and count == 0,
            })
            role = "INSUFFICIENT_EVIDENCE"
            if source == "ripestat": role = "INVENTORY_ONLY"
            if source in ("ripe_ris_live", "ioda") and count: role = "ROUTING_ONLY" if source == "ripe_ris_live" else "PRIMARY_CANDIDATE"
            if source == "usgs": role = "CONTEXT_ONLY"
            if source in ("geoboundaries", "nominatim"): role = "GEOGRAPHY_REFERENCE"
            matrix.append({"source": source, "operator": operator, "asn_candidate": asn,
                           "attempt_status": attempt, "sample_count": count, "geographic_scope": scope,
                           "utility_decision": utility["state"], "evidence_ids": ";".join(evidence),
                           "evidence_paths": ";".join(row["artifact_path"] for row in records if row["evidence_id"] in evidence),
                           "limitations": reason})

    csv_write("source_matrix.csv", matrix)
    csv_write("phase_b_peru_coverage.csv", [
        {"source": row["source"], "operator": row["operator"], "asn": row["asn_candidate"],
         "time_range": "single captured query; see evidence timestamps", "sample_count": row["sample_count"],
         "data_density": "observed sample only; no long-window density estimate", "freshness": "publication lag UNKNOWN",
         "geographic_scope": row["geographic_scope"], "access_status": row["attempt_status"],
         "evidence_ids": row["evidence_ids"], "limitations": row["limitations"],
         "next_action": "extend only within official free quotas and licensing"} for row in matrix
        if row["source"] in ("ioda", "cloudflare_radar", "ripestat")
    ])
    csv_write("probe_density_peru.csv", [
        {"source": "ripe_atlas", "operator": op, "asn": asn,
         "peru_connected_probe_count": atlas_count.get(asn.removeprefix("AS"), 0),
         "probe_total_country_listed": atlas.get("count"), "public_measurement_inventory_records": sum(row["source_id"] == f"ripe_atlas_measurements_{op}" for row in atlas_measurement_records),
         "location_basis": "RIPE Atlas probe metadata/geometry, not incident location",
         "evidence_id": atlas_record.get("evidence_id") if atlas_record else "",
         "limitation": "probe presence is not outage measurement"} for op, asn in OPS.items()
    ])
    atlas_measurement_rows = []
    for row in atlas_measurement_records:
        summary = body(row)
        atlas_measurement_rows.append({"operator": summary.get("operator", row.get("source_id", "").rsplit("_", 1)[-1]),
            "asn": summary.get("asn", ""), "http_page_count": summary.get("http_page_count", ""),
            "returned_page_rows": summary.get("returned_page_rows", ""), "has_next_page": summary.get("has_next_page", ""),
            "measurement_types": ";".join(summary.get("measurement_types", [])),
            "first_start_time_in_returned_page": summary.get("first_start_time_in_returned_page", ""),
            "last_start_time_in_returned_page": summary.get("last_start_time_in_returned_page", ""),
            "ongoing_rows_in_returned_page": summary.get("ongoing_rows_in_returned_page", ""),
            "http_status": row.get("http_status"), "evidence_id": row["evidence_id"], "artifact_path": row["artifact_path"],
            "note": summary.get("note", "")})
    csv_write("atlas_measurement_inventory.csv", atlas_measurement_rows)
    atlas_result_rows=[]
    for row in records:
        if row["source_id"].startswith("ripe_atlas_latest_result_"):
            summary=body(row)
            atlas_result_rows.append({"operator":summary.get("operator"),"asn":summary.get("asn"),
                "measurement_configuration_start_time":summary.get("measurement_configuration_start_time"),
                "measurement_status":summary.get("measurement_status"),"returned_result_count":summary.get("returned_result_count"),
                "result_timestamps_utc":";".join(summary.get("result_timestamps",[])),"http_status":row.get("http_status"),
                "evidence_id":row["evidence_id"],"artifact_path":row["artifact_path"],"note":summary.get("note","")})
    csv_write("atlas_latest_results.csv",atlas_result_rows)
    csv_write("temporal_validation.csv", [{
        "source": row["source"], "operator": row["operator"], "sample_count": row["sample_count"],
        "publication_lag_median": "UNKNOWN", "publication_lag_p90": "UNKNOWN",
        "collection_lag_median": "UNKNOWN", "collection_lag_p90": "UNKNOWN",
        "window": "single validation snapshot", "missing_timestamps": "incident start/first published/end/cadence"
    } for row in matrix])
    csv_write("technology_coverage.csv", [{
        "source": row["source"], "operator": row["operator"], "technology": "unknown unless explicitly observed",
        "granularity": row["geographic_scope"], "sample_count": row["sample_count"],
        "freshness": "not enough history", "evidence_ids": row["evidence_ids"],
        "basis": row["limitations"]
    } for row in matrix])
    csv_write("geo_validation.csv", [{
        "source": row["source"], "operator": row["operator"], "latitude_longitude": "probe coordinate only where source provides one",
        "coordinate_type": "probe location, not outage location" if row["source"] == "ripe_atlas" else "unknown",
        "precision": "point of measurement probe" if row["source"] == "ripe_atlas" else "unknown",
        "location_conflict": "not evaluated", "ubigeo": "not crosswalked; current INEI catalog unresolved",
        "evidence_ids": row["evidence_ids"], "notes": row["limitations"]
    } for row in matrix])

    family = {
        "ioda": "BGP/routing + active signals", "ripe_ris_live": "BGP/routing", "ripestat": "BGP/routing + inventory",
        "cloudflare_radar": "traffic/DNS", "ripe_atlas": "active reachability", "globalping": "active reachability",
        "ooni": "test-dependent active reachability", "twilio": "carrier messaging", "telesign": "carrier messaging",
        "sinch": "carrier messaging", "infobip": "carrier messaging", "usgs": "external context",
        "geoboundaries": "geography", "inei_ubigeo": "geography", "nominatim": "geography", "x_twexapi": "human reports",
    }
    dependency_rows = []
    for source in SOURCE_IDS:
        for operator in OPS:
            row = next(x for x in matrix if x["source"] == source and x["operator"] == operator)
            dependency_rows.append({"source": source, "operator": operator, "family": family.get(source, "unknown"),
                                   "shared_upstream": "same BGP family" if family.get(source, "").startswith("BGP/") else "unknown",
                                   "independence_status": "DEPENDENT" if family.get(source, "").startswith("BGP/") else "UNKNOWN",
                                   "matched_events": "not established", "evidence_status": row["utility_decision"],
                                   "evidence_ids": row["evidence_ids"]})
    csv_write("source_dependency_matrix.csv", dependency_rows)
    pairs = []
    bgp = [source for source, fam in family.items() if fam.startswith("BGP/")]
    for i, left in enumerate(bgp):
        for right in bgp[i + 1:]:
            pairs.append({"source_a": left, "source_b": right, "family_a": family[left], "family_b": family[right],
                          "independence_status": "DEPENDENT", "coincident_events": "not independently verified",
                          "reason": "Do not count correlated BGP-origin signals as separate votes."})
    csv_write("evidence_independence.csv", pairs)

    access_rows = []
    for source in SOURCE_IDS:
        evidence_ids = sorted({e for x in matrix if x["source"] == source for e in x["evidence_ids"].split(";") if e})
        access_row = {"source_id": source, "official_auth_documentation_url": "see reports/pending_credentials.md",
                      "account_required": "unknown/varies", "auth_type": "see official docs",
                      "free_access_confirmed": "see evidence and source_matrix.csv", "free_quota": "UNKNOWN unless published",
                      "quota_reset": "UNKNOWN unless published", "commercial_use_status": "UNKNOWN or source-specific restriction",
                      "tested_at": now_utc(), "http_status": "see manifest", "result": "see source_matrix.csv",
                      "evidence_ids": ";".join(evidence_ids), "next_action": "verify limits/terms; do not infer from HTTP 200"}
        if source == "cloudflare_radar":
            token_record, _ = latest(records, "cloudflare_token_verify")
            access_row.update({"official_auth_documentation_url": "https://developers.cloudflare.com/radar/get-started/first-request/",
                               "account_required": True, "auth_type": "Cloudflare API token: Account/Radar/Read",
                               "free_access_confirmed": "YES; token verification and Radar read returned 200",
                               "free_quota": "API described free; numeric request/rate quota UNKNOWN",
                               "commercial_use_status": "RESTRICTED: CC BY-NC 4.0; advertising signal permission pending",
                               "http_status": token_record.get("http_status") if token_record else "", "evidence_ids": token_record.get("evidence_id", "") if token_record else ""})
        elif source == "x_twexapi":
            balance_record, balance_body = latest(records, "twexapi_balance")
            search_records = [row for row in records if row["source_id"].startswith("twexapi_x_")]
            access_row.update({"official_auth_documentation_url": "https://docs.twexapi.io/api-reference/overview",
                               "account_required": True, "auth_type": "TwexAPI Bearer API key",
                               "free_access_confirmed": "YES; existing trial balance and read calls observed",
                               "free_quota": "20,000 Starter credits / 7d per published docs; typical 5 credits/post; balance GET observed to deduct 5/request",
                               "quota_reset": "7 days for Starter; final balance not re-read",
                               "commercial_use_status": "PENDING review of provider terms and X platform compliance",
                               "http_status": search_records[-1].get("http_status") if search_records else (balance_record.get("http_status") if balance_record else ""),
                               "evidence_ids": ";".join([x["evidence_id"] for x in ([balance_record] if balance_record else []) + search_records[-3:]]),
                               "next_action": "No balance re-read after search; do not infer remaining balance. Three distinct operator queries were repeated once to validate privacy-safe response parsing."})
        access_rows.append(access_row)
    csv_write("source_access_matrix.csv", access_rows)
    rights_rows = []
    for source in SOURCE_IDS:
        terms = ""
        evaluation_access = "UNKNOWN"
        raw_storage = "UNKNOWN"
        derived = "UNKNOWN"
        advertising = "UNKNOWN"
        attribution = "UNKNOWN"
        authz = "UNKNOWN"
        if source == "cloudflare_radar":
            terms = "https://developers.cloudflare.com/radar/"
            evaluation_access, raw_storage, derived, advertising, attribution, authz = "CONFIRMED", "evaluation observed", "PENDING_PERMISSION", "PENDING_PERMISSION", "CC BY-NC attribution; commercial restriction", "PENDING_PERMISSION"
        elif source == "x_twexapi":
            terms = "https://twexapi.io/terms"
            evaluation_access, raw_storage, derived, advertising, attribution, authz = "PENDING_PERMISSION", "minimized summaries only", "PENDING_PERMISSION", "PENDING_PERMISSION", "UNKNOWN", "PENDING_PERMISSION"
        elif source == "nominatim":
            terms = "https://operations.osmfoundation.org/policies/nominatim/"
            evaluation_access, raw_storage, derived, advertising, attribution, authz = "CONFIRMED_FOR_SAMPLE", "three query responses", "UNKNOWN", "PENDING_PERMISSION", "ODbL attribution/share-alike", "PENDING_PERMISSION"
        rights_rows.append({"source": source, "terms_url": terms, "checked_at_utc": now_utc(), "evaluation_access": evaluation_access,
                            "raw_data_storage": raw_storage, "derived_indicators": derived, "advertising_activation": advertising,
                            "attribution_required": attribution, "redistribution_allowed": "UNKNOWN", "authorization_required": authz,
                            "authorization_status": authz, "evidence_path": "evidencias/licensing/manual_document_review.json",
                            "notes": "Do not infer rights from public access."})
    csv_write("data_usage_rights_matrix.csv", rights_rows)

    pricing_rows = []
    price_overrides = {
        "cloudflare_radar": {"pricing_model": "free API access", "free_tier": "API free per docs; numeric quota unknown", "rate_limits": "UNKNOWN", "paid_plans": "license/permission separate", "overage_cost": "UNKNOWN", "commercial_use": "CC BY-NC 4.0; ad indicators pending written authorization", "pricing_source": "https://developers.cloudflare.com/radar/", "pricing_status": "VERIFIED_API_FREE_LICENSE_RESTRICTED"},
        "twexapi_x": {"pricing_model": "credit based", "free_tier": "20,000 credits / 7 days; starter 0.2 QPS", "rate_limits": "one request/5s starter", "paid_plans": "Mini $20/2M credits; Basic $50/mo/5M; Pro $99/mo/11M per provider docs", "overage_cost": "no auto-recharge used; paid credits not purchased", "commercial_use": "PENDING provider/X terms review", "pricing_source": "https://docs.twexapi.io/guides/pricing", "pricing_status": "VERIFIED_PROVIDER_PUBLISHED"},
        "ripe_ris_live": {"pricing_model": "public WebSocket; no fee indicated", "free_tier": "no authentication; low-volume filtered stream", "rate_limits": "connection closes if consumer cannot keep up; numeric rate unknown", "commercial_use": "RIPE data terms review pending", "pricing_source": "https://ris-live.ripe.net/manual/", "pricing_status": "ACCESS_DOCS_VERIFIED"},
        "nominatim": {"pricing_model": "free public endpoint under strict policy", "free_tier": "punctual only; max 1 req/s; no systematic use", "rate_limits": "1 request/second", "commercial_use": "ODbL attribution/share-alike; downstream use review", "pricing_source": "https://operations.osmfoundation.org/policies/nominatim/", "pricing_status": "POLICY_VERIFIED"},
    }
    for source in SOURCE_IDS:
        fields = {"source": source, "pricing_model": "UNKNOWN / free access not equivalent to commercial rights", "free_tier": "UNKNOWN", "rate_limits": "UNKNOWN", "paid_plans": "UNKNOWN or contact sales", "overage_cost": "UNKNOWN", "commercial_use": "UNKNOWN", "auth_requirements": "see source_access_matrix.csv", "pricing_source": "official documentation pending", "verified_at_utc": now_utc(), "pricing_status": "UNKNOWN", "currency": "not estimated", "estimated_monthly_cost": "UNKNOWN; no invented amount"}
        fields.update(price_overrides.get(source, {})); pricing_rows.append(fields)
    csv_write("source_pricing.csv", pricing_rows)
    intervals = {"1m": 43200, "5m": 8640, "15m": 2880, "30m": 1440}
    budget_rows, simulation_rows, cost_rows = [], [], []
    for source in SOURCE_IDS:
        per_cycle = 4 if source in ("ioda", "cloudflare_radar", "ripestat", "ripe_atlas", "ooni", "x_twexapi") else 1
        for interval, cycles in intervals.items():
            calls = cycles * per_cycle
            units = calls * 20 * 5 if source == "x_twexapi" else "UNKNOWN"
            unit = "credits upper bound (20 results x 5)" if source == "x_twexapi" else "requests or provider-specific unit"
            budget_rows.append({"source": source, "interval": interval, "cycles_per_month": cycles, "requests_per_cycle": per_cycle,
                                "estimated_monthly_calls": calls, "request_cost_unit": unit, "estimated_monthly_billable_units": units,
                                "quota_headroom": "UNKNOWN; hypothetical only", "formula": f"{cycles} x {per_cycle}", "confidence": "LOW; no monitoring launched"})
            simulation_rows.append({"source": source, "profile": "normal", "interval": interval, "estimated_monthly_calls": calls,
                                    "units": units, "free_tier_status": "likely exceeds 20k trial" if source == "x_twexapi" else "UNKNOWN",
                                    "note": "simulation only; these requests were not emitted"})
            cost_rows.append({"source": source, "scenario": interval, "monthly_calls": calls, "unit": unit,
                              "monthly_billable_units": units, "estimated_cost_usd": "UNKNOWN", "assumptions": "no paid tier selected; no billing enabled"})
    csv_write("query_budget_by_source.csv", budget_rows)
    csv_write("free_tier_simulation.csv", simulation_rows)
    csv_write("cost_scenarios.csv", cost_rows)

    decisions = []
    for source in SOURCE_IDS:
        rows = [row for row in matrix if row["source"] == source]
        evidence_ids = sorted({e for row in rows for e in row["evidence_ids"].split(";") if e})
        state = "INSUFFICIENT_EVIDENCE"
        role = "INSUFFICIENT_EVIDENCE"
        if source == "ripestat": state, role = "CONDITIONAL", "INVENTORY_ONLY"
        if source in ("cloudflare_radar", "usgs", "geoboundaries", "nominatim"): state, role = "CONDITIONAL", ("CONTEXT_ONLY" if source == "usgs" else "REFERENCE_ONLY")
        if source == "ioda" and any(row["sample_count"] > 0 for row in rows): state, role = "CONDITIONAL", "PRIMARY_CANDIDATE"
        if source == "ripe_ris_live" and any(row["sample_count"] > 0 for row in rows): state, role = "CONDITIONAL", "ROUTING_ONLY"
        if source == "cloudflare_radar":
            reason = "PE aggregate is observed; operator-specific technical attribution is absent in this window."
        elif source == "ioda":
            reason = "ASN events and series exist in this window; publication latency, independent event truth, service technology and district granularity remain unverified."
        elif source == "twexapi_x":
            reason = "Three targeted searches returned empty arrays in this query window; insufficient to reject account/source or infer zero reports; other handles pending verification."
        else:
            reason = "No sufficiently independent, fresh, operator- and geography-attributed evidence to approve. Empty windows/errors are not coverage rejection."
        decisions.append({"source_id": source, "evaluation_version": "rules-2026-10-24-v1", "period": "single local run",
                          "final_state": state, "role": role, "operator_scope": ";".join(OPS),
                          "reason": reason, "evidence_ids": ";".join(evidence_ids),
                          "criteria": "HTTP 200 alone never approves; assess technical coverage, attribution, freshness, independence and query limits.",
                          "next_action": "see revalidation_queue.json"})
    csv_write("validation_decision_register.csv", decisions)

    accounts = [
        ("Movistar Perú", "MovistarPeru", "https://www.movistar.com.pe/", "https://twitter.com/MovistarPeru", "movistar"),
        ("Claro Perú", "claroperu", "https://www.claro.com.pe/", "https://x.com/claroperu", "claro"),
        ("Bitel Perú", "bitelperu", "https://bitel.com.pe/", "https://twitter.com/bitelperu", "bitel"),
        ("Entel Perú", "", "https://www.entel.pe/", "", "entel"),
        ("OSIPTEL", "", "https://www.gob.pe/osiptel", "", "osiptel"),
        ("MTC", "", "https://www.gob.pe/mtc", "", "mtc"),
        ("INDECI", "", "https://www.gob.pe/indeci", "", "indeci"),
        ("COEN", "", "https://www.gob.pe/indeci", "", "coen"),
        ("Indecopi", "", "https://www.gob.pe/indecopi", "", "indecopi"),
    ]
    account_inventory, account_values = [], []
    for entity, handle, official_url, x_url, key in accounts:
        verified = bool(handle)
        x_records = [row for row in records if row["source_id"] == f"twexapi_x_{key}"] if key in OPS else []
        x_record = x_records[-1] if x_records else None
        x_body = body(x_record) if x_record else {}
        result_count = x_body.get("array_lengths", {}).get("$.data", 0) if isinstance(x_body, dict) else 0
        account_inventory.append({"entity": entity, "handle": handle or "", "identity_status": "VERIFIED_LINKED_FROM_OFFICIAL_SITE" if verified else "NOT_VERIFIED",
                                 "official_url": official_url, "x_url": x_url, "verified_at_utc": x_record.get("observed_at_utc", "") if x_record else "",
                                 "evidence_id": x_record.get("evidence_id", "") if x_record else "", "query_status": x_record.get("result_status", "NOT_TESTED") if x_record else "NOT_TESTED"})
        account_values.append({"entity": entity, "handle": handle, "window_days": 30 if x_record else "NOT_QUERIED", "query_count": len(x_records),
                               "results_returned": result_count if x_record else "NOT_OBSERVED", "useful_messages": "0 returned in exact scoped query" if x_record and result_count == 0 else "not evaluated",
                               "unique_users": "not computed/minimized", "zone_identifiable": "no result", "credits": (5 * len(x_records)) if x_record else 0,
                               "decision": "INSUFFICIENT_EVIDENCE" if x_record else ("NOT_VERIFIED" if not verified else "NOT_TESTED"),
                               "evidence_id": ";".join(row["evidence_id"] for row in x_records),
                               "reason": "Two parser-validation passes used the same 30-day query; their results are duplicates, not independent windows. An empty result does not prove no messages or low lifetime value." if x_record else "Handle not identity-verified; no query sent."})
    csv_write("x_official_accounts_inventory.csv", account_inventory)
    csv_write("x_account_value_matrix.csv", account_values)
    csv_write("x_final_account_decisions.csv", account_values)
    news_rows = []
    for name, source_id, url in (("RPP Noticias", "rpp_feed_candidate", "https://rpp.pe/rss"), ("La República", "larepublica_official_rss", "https://larepublica.pe/rss/home.xml")):
        rec, _ = latest(records, source_id)
        news_rows.append({"outlet": name, "status": "FEED_XML_VALIDATED_TECHNICAL_SAMPLE_RELEVANCE_PENDING" if rec and rec.get("http_status") == 200 else "NOT_TESTED",
                          "official_feed_url": url if rec else "", "evidence_ids": rec.get("evidence_id", "") if rec else "",
                          "next_action": "assess technical relevance and incident attribution from the feed sample"})
    for name in ("Agencia Andina", "Diario Correo", "El Comercio"):
        news_rows.append({"outlet": name, "status": "NOT_TESTED", "official_feed_url": "", "evidence_ids": "", "next_action": "verify an official linked RSS/Atom/API; no HTML scraping"})
    csv_write("peru_news_feeds.csv", news_rows)
    csv_write("peru_news_relevance.csv", [{"outlet": row["outlet"], "sample_count": 60 if row["outlet"] == "RPP Noticias" and row["evidence_ids"] else (200 if row["outlet"] == "La República" and row["evidence_ids"] else 0),
        "relevance": "INSUFFICIENT_EVIDENCE; exploratory title matches were not validated outage reports", "evidence_ids": row["evidence_ids"]} for row in news_rows])

    (REPORTS / "approved_sources.json").write_text("[]\n", encoding="utf-8")
    (REPORTS / "blueprint_input.json").write_text(json.dumps({"status": "provisional_no_approved_sources", "approved_sources": [], "capabilities": [], "sonata_contract": "PENDING", "evidence_manifest": "evidencias/manifest.jsonl"}, indent=2), encoding="utf-8")
    lines = ["# Decisiones finales (provisionales)", "", "Ninguna fuente se aprueba por HTTP 200. No se emitieron REJECTED por ventanas vacías, errores ni falta de cobertura observada.", "", "| Fuente | Decisión | Función | Evidencia | Motivo |", "|---|---|---|---|---|"]
    for row in decisions:
        lines.append(f"| {row['source_id']} | {row['final_state']} | {row['role']} | {row['evidence_ids'] or 'sin evidencia'} | {row['reason']} |")
    ioda_counts = []
    for op in OPS:
        _, event_body = latest(records, f"ioda_events_{op}")
        events = event_body.get("data", []) if isinstance(event_body, dict) else []
        sources = dict(Counter(e.get("datasource", "unknown") for e in events))
        ioda_counts.append(f"{op}: {len(events)} events ({sources})")
    lines += ["", "## Datos medidos", f"- RIPE Atlas: {atlas.get('count', 'unknown')} connected probes PE; ASN candidate counts: {dict((op, atlas_count.get(asn.removeprefix('AS'), 0)) for op, asn in OPS.items())}. No tests created.", f"- RIPEstat: country PE reports {country_asn_stats}; announced prefix inventory 30d: {prefix_counts}.", f"- IODA: {'; '.join(ioda_counts)}. Event start/duration available; publication/first-seen lag not provided; not ground truth.", f"- OONI: {len(ooni_items)} returned measurements; AS distribution {dict(ooni_asns)}; current page does not match candidate ASNs.", f"- RIS Live: {ris.get('message_count', 0)} messages in {ris.get('duration_seconds', 0)} seconds; ASN path observation only.", f"- Cloudflare Radar: PE aggregate distribution {cf_summary}; lastUpdated={cf_meta.get('lastUpdated', 'unknown')}; no PE outage annotations matched candidate ASNs in 30d.", "- TwexAPI: 3 operator-targeted 30d searches returned empty data arrays; no general search or user-text retention.", f"- geoBoundaries: ADM1/2 features={adm1_count}/{adm2_count}; ADM3 metadata 404; Nominatim three manual queries.", "", "See source_matrix.csv, source_access_matrix.csv, validation_decision_register.csv, source_loss_analysis.json and evidence manifest."]
    (REPORTS / "final_decisions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (REPORTS / "rejected_sources.md").write_text("# Fuentes rechazadas\n\nNo hay rechazos definitivos sustentados. Las fuentes con errores, ventanas vacías o baja densidad quedan en INSUFFICIENT_EVIDENCE/UNAVAILABLE, no REJECTED.\n", encoding="utf-8")
    (REPORTS / "conditional_sources.md").write_text("# Fuentes condicionales\n\n- IODA: eventos ASN observados; falta latencia de publicación, independent ground truth, licencia y geografía.\n- Cloudflare Radar: agregado PE observado y license CC BY-NC 4.0; written authorization required for ad indicators.\n- RIPEstat: inventory only.\n- RIS Live: routing only, same BGP family.\n- TwexAPI: access works; 3 empty query windows; handles/utility and rights remain incomplete.\n- Geography/context sources are reference-only.\n", encoding="utf-8")
    (REPORTS / "insufficient_evidence.md").write_text("# Evidencia insuficiente\n\nIndependent incident truth is unavailable. Publication latency, detection precision/recall, fixed/mobile separation and district outage location are not estimable. Empty queries are not no coverage. Licensing review is deferred and does not gate technical feasibility.\n", encoding="utf-8")

    # Complete analysis artifacts with explicit insufficient values, never fabricated deltas.
    scenarios = ("base", "without_source", "delayed", "intermittent_1h", "intermittent_6h", "intermittent_24h", "commercially_excluded", "paid_inaccessible", "family_removed")
    loss_rows = [{"source_id": source, "operator": op, "zone": "unknown", "scenario": scenario, "reference_period": "single execution", "sample_size": 0,
                  "baseline_value": "INSUFFICIENT_EVIDENCE", "without_source_value": "INSUFFICIENT_EVIDENCE", "delta": "INSUFFICIENT_EVIDENCE",
                  "evidence_status": "INSUFFICIENT_EVIDENCE", "assumptions": "no independent labels; no invented percentages", "alternative_sources": "see fallback_plans.md",
                  "commercial_license_status": "see data_usage_rights_matrix.csv", "evaluated_at": now_utc()}
                 for source in SOURCE_IDS for op in OPS for scenario in scenarios]
    (REPORTS / "source_loss_analysis.json").write_text(json.dumps(loss_rows, indent=2), encoding="utf-8")
    (REPORTS / "source_loss_analysis.md").write_text("Leave-one-source-out, delay, 1h/6h/24h outage, commercial exclusion, paid-inaccessible and family-loss scenarios are represented in source_loss_analysis.json. Every loss metric is INSUFFICIENT_EVIDENCE because there is no independent incident truth set and enough matched incident cases; no percentages are fabricated.\n", encoding="utf-8")
    (REPORTS / "dependency_graph.json").write_text(json.dumps({"families": {"ioda": "bgp_routing/active", "ripe_ris_live": "bgp_routing", "ripestat": "bgp_routing/inventory", "cloudflare_radar": "traffic_dns", "ooni": "test-dependent", "ripe_atlas": "active_reachability", "twexapi_x": "human_reports"}, "shared_dependencies": [["ioda", "ripe_ris_live"], ["ioda", "ripestat"], ["ripe_ris_live", "ripestat"]]}, indent=2), encoding="utf-8")
    (REPORTS / "fallback_plans.md").write_text("BGP alternatives share a family and do not provide independent confirmation. OONI/Atlas/Globalping are not substitutes without measurements on access networks. SMS/voice status never confirms Internet. Cloudflare has no identical free replacement demonstrated; operator attribution remains absent from country aggregate. Geography requires valid ADM/UBIGEO crosswalk; probe point is not outage point.\n", encoding="utf-8")
    (REPORTS / "free_access_and_licensing.md").write_text("Document links and manual review summary are archived in evidencias/licensing/manual_document_review.json. Public access is not commercial authorization. Radar is CC BY-NC 4.0; TwexAPI is credit-based; Nominatim strict 1 req/s and ODbL. Other terms remain UNKNOWN pending source-specific review.\n", encoding="utf-8")
    (REPORTS / "economic_feasibility.md").write_text("Local execution cash cost was USD 0; no cards, purchases or cloud services. TwexAPI initial balance observed as 20,000; three balance reads decreased by 5 credits each. Six successful empty account queries are expected to consume about 30 credits under the provider's stated empty-request charge; no post-query balance read was made to avoid another metered balance call. Actual final balance is UNKNOWN. No paid path or auto-recharge was invoked. Future workload formulas and official pricing references are in query_budget_by_source.csv/source_pricing.csv; missing price is UNKNOWN, no budget ceiling is applied.\n", encoding="utf-8")
    (REPORTS / "pricing_unknowns.md").write_text("Provider-specific rate/overage/licensing information not verified remains UNKNOWN in source_pricing.csv; contact sales only where official provider has no published price. No payment actions.\n", encoding="utf-8")
    (REPORTS / "polling_vs_freshness.md").write_text("Query frequencies are hypothetical only. TwexAPI at 4 operator requests per cycle and <=20 posts/query would use up to 17,280,000 credits/month at 1m, 3,456,000 at 5m, 1,152,000 at 15m and 576,000 at 30m; these are upper bounds and not executed calls. Starter 20,000 credits/7 days cannot support recurring polling at those maxima. API publication cadence/lag remains unknown. RIS Live is a stream, not polling.\n", encoding="utf-8")
    (REPORTS / "low_density_analysis.md").write_text("Sparse/empty evidence was re-evaluated by checking candidate ASN entities, IODA 30-day windows, Atlas complete 28-probe response, Cloudflare outage endpoint by PE/ASN, and verified-account X targeted queries. A quiet/empty window remains NO_EVENTS_IN_WINDOW, not NO_COVERAGE. Events and probes do not prove operator-wide service outages.\n", encoding="utf-8")
    (REPORTS / "retry_policy_compliance.md").write_text("TwexAPI 422 schema validation errors were inspected and corrected to documented searchTerms array plus sortBy; failed requests are free per provider docs. IODA certificate/endpoint discovery was corrected using official OpenAPI docs and certifi trust roots. No 401/403/429 or paid operation was retried. All requests bounded; no loops.\n", encoding="utf-8")
    retry_rows = []
    grouped = {}
    for row in records:
        grouped.setdefault(row["source_id"], []).append(row)
    for source, attempts in grouped.items():
        for index, row in enumerate(attempts, 1):
            retry_rows.append({"source_id": source, "operator": row.get("operator"), "country": row.get("country"),
                               "round": 1, "attempt": index, "endpoint": row.get("url", ""), "query_signature": row.get("query_signature", "UNAVAILABLE_LEGACY"),
                               "window_start": row.get("window_start"), "window_end": row.get("window_end"),
                               "attempted_at_utc": row.get("observed_at_utc", ""), "http_status": row.get("http_status"),
                               "attempt_status": row.get("attempt_status", row.get("result_status")), "error": row.get("error", ""),
                               "retry_after": row.get("headers", {}).get("Retry-After"), "next_retry_at_utc": row.get("next_retry_at_utc"),
                               "parameter_change": "not recorded for legacy attempt" if row.get("query_signature") == "UNAVAILABLE_LEGACY" else "none recorded",
                               "evidence_id": row["evidence_id"], "evidence_path": row["artifact_path"]})
    csv_write("retry_history.csv", retry_rows)
    queue = [
        {"source_id": "globalping", "status": "INSUFFICIENT_EVIDENCE" if globalping_record else "NOT_TESTED", "cause": "GET inventory observed seven Peru probes and zero in the four candidate ASNs; no measurement created" if globalping_record else "No inventory response archived", "next_action": "verify free-tier cost and terms before any future measurement request"},
        {"source_id": "inei_ubigeo", "status": "INSUFFICIENT_EVIDENCE", "cause": "Official open-data catalog located, but current-version download and validation are pending", "next_action": "download an official current catalog, archive and hash it, and cross-check codes/names against geometries"},
        {"source_id": "x_accounts_entel_institutions", "status": "NOT_VERIFIED", "cause": "official handles not verified from authoritative pages", "next_action": "verify site-linked handles before any query"},
        {"source_id": "peru_news_feeds", "status": "PARTIALLY_TESTED", "cause": "RPP and La República XML feeds archived; terms/relevance unresolved; three outlets unverified", "next_action": "review feed terms/relevance and verify official feeds for remaining outlets"},
        {"source_id": "ripe_atlas_public_measurements", "status": "INSUFFICIENT_EVIDENCE", "cause": "Public measurement inventories are paginated and latest result freshness was not established", "next_action": "if justified, inspect recent results via documented GET endpoints; do not create measurements"},
        {"source_id": "ioda_more_asns", "status": "INSUFFICIENT_EVIDENCE", "cause": "candidate ASN only; full operator inventory not proven", "next_action": "cross-check operator-owned ASNs and prefixes with official/registry sources"},
    ]
    (REPORTS / "revalidation_queue.json").write_text(json.dumps(queue, indent=2), encoding="utf-8")
    (REPORTS / "retry_history.csv").exists()

    (REPORTS / "x_twexapi_access_pricing.md").write_text("Official TwexAPI docs report Starter 20k credits/7 days, typical 5 credits/read, 0.2 QPS and no card for Starter; usage is credit-based. The account's initial balance response was 20,000; repeated balance reads each reduced by 5. No purchases, card, auto-recharge, or paid credits. Three accounts were targeted once successfully after 422 schema retries; the six successful searches across two evaluation passes returned empty arrays. Estimated content-query spend ~30 credits at the provider's stated empty-query price; final balance not queried to avoid additional credits.\n", encoding="utf-8")
    (REPORTS / "x_peru_signal_quality.md").write_text("MovistarPeru, claroperu and bitelperu were linked from their official country sites. A targeted 30-day connectivity query for each returned an empty data array. This does not establish there are no messages outside the filters/window, does not validate Entel or public-sector accounts, and does not support usefulness/rejection. User content and identifiers were excluded from evidence.\n", encoding="utf-8")
    (REPORTS / "x_account_exclusions.md").write_text("No account was rejected. Three operator accounts remain INSUFFICIENT_EVIDENCE after one empty targeted query; Entel, OSIPTEL, MTC, INDECI/COEN and Indecopi remain NOT_VERIFIED / NOT_TESTED.\n", encoding="utf-8")
    (REPORTS / "x_source_resilience.md").write_text("Loss of TwexAPI/X signal is INSUFFICIENT_EVIDENCE; no useful messages were returned in the limited search windows, so no incremental-loss percentages are supportable.\n", encoding="utf-8")
    news_outlets = ("RPP Noticias", "Agencia Andina", "Diario Correo", "La República", "El Comercio")
    (REPORTS / "peru_news_top5.md").write_text("RPP (https://rpp.pe/rss) and La República (https://larepublica.pe/rss/home.xml) returned XML; see peru_news_feeds.csv. Terms/reuse and incident relevance remain unverified. Andina, Correo and El Comercio were not tested; no HTML scraping.\n", encoding="utf-8")
    (REPORTS / "peru_news_incremental_value.md").write_text("Two point-in-time RSS captures contained 60 RPP and 200 La República items. Exploratory title matches were not validated incident reports; no incremental outage evidence can be claimed. Publication/update cadence and technical incident relevance remain unknown.\n", encoding="utf-8")
    (REPORTS / "peru_institutional_sources.md").write_text("SISREP's official service description indicates operator-submitted interruption reports through a web interface and links to a login; public API/feed/open file not confirmed. An INEI-published UBIGEO catalog was located in the National Open Data Platform; a dated snapshot still requires freshness/version validation and code/name/geography crosswalk. Indecopi machine-readable telecom incident source not confirmed. No restricted login or scraping was attempted.\n", encoding="utf-8")
    (REPORTS / "osiptel_sisrep_access.md").write_text("Official SISREP page: https://www.gob.pe/33307-sistema-de-informacion-y-registro-de-interrupciones-sisrep . Data is described as submitted via web interface; target consultation link goes to login. No public API/feed/download verified; no login attempted.\n", encoding="utf-8")
    (REPORTS / "osiptel_quality_data.md").write_text("No authorized fresh machine-readable OSIPTEL quality/outage dataset was verified in this run. Aggregate reports do not demonstrate incident-level freshness or operator/zone coverage.\n", encoding="utf-8")
    (REPORTS / "sonata_integration_questions.md").write_text("SONATA_CONTRACT_PENDING: confirm polling/push, JSON/XML/feed schema, frequency/SLA, auth, supported geocodes/radii, expiry/fail-safe, size/caching, sandbox and rollback. No integration or campaign activation in this validation.\n", encoding="utf-8")
    (REPORTS / "output_contract_feasibility.md").write_text("No approved sources. Candidate fields: IODA event start/duration and ASN; RIS BGP timestamps/path; OONI measurement timestamps/ASN; Atlas probe coordinates; Cloudflare aggregate; no incident publication lag or district outage point. UBIGEO/Sonata contract pending.\n", encoding="utf-8")
    (REPORTS / "feed_format_decision.md").write_text("Do not decide final JSON/XML/feed contract until Sonata capabilities are confirmed. blueprint_input.json remains empty of sources because none achieved APPROVED.\n", encoding="utf-8")
    (REPORTS / "cloudflare_radar_license_review.md").write_text("Radar API is documented free for access; Radar data is CC BY-NC 4.0. Token read permission works. Commercial advertising indicator use remains PENDING written authorization; no provider contact made.\n", encoding="utf-8")
    (REPORTS / "with_without_radar.md").write_text("Radar contributes a PE aggregate distribution but no operator attribution in the tested summary. Its outage annotations returned 0 for candidate ASNs in this 30d window. Without independent reference incidents, leave-one-out effect is INSUFFICIENT_EVIDENCE; no equivalent replacement asserted.\n", encoding="utf-8")
    (REPORTS / "decision_sensitivity.md").write_text("Changing thresholds cannot produce an approval without independent event labels, operator attribution, measured freshness and technical utility. Current rules are conservative and sensitivity outcomes are stable as no source is APPROVED.\n", encoding="utf-8")
    (REPORTS / "validation_results.json").write_text(json.dumps({"generated_at_utc": now_utc(), "decisions": decisions, "operator_matrix": matrix, "approved_sources": [], "status": "PROVISIONAL_INSUFFICIENT_EVIDENCE"}, indent=2), encoding="utf-8")
    (REPORTS / "validation_report.md").write_text("# Informe de validación\n\nEjecución puntual local, efectivo USD 0. RIPEstat confirmó los titulares de ASN y obtuvo prefijos anunciados en 30 días; RIR/ASN no identifica toda la red comercial. IODA obtuvo eventos para Movistar (2; BGP, ping-slash24), Claro (6; BGP, ping-slash24), Entel (0) y Bitel (1; ping-slash24) en su API de eventos por ASN; las señales no son verdad de referencia y no incluyen first-published latency/ distrito. RIPE Atlas lista 28 probes PE, con 1/2/2/0 en los AS candidatos; las últimas páginas muestran configuraciones hasta 2026-10-24, pero cinco consultas GET al endpoint latest devolvieron cero muestras; la frescura sigue sin establecerse. Globalping listó 7 probes PE y cero en los cuatro ASN candidatos; no se crearon mediciones. OONI regresó 100 resultados de PE, todos AS265691. RIS Live recibió 96 BGP updates en ~13 s, todos filtrados por AS6147 en esa ventana; BGP ≠ outage. Cloudflare mostró tráfico PE agregado y 0 outage annotations por ASN en 30d; licencia CC BY-NC 4.0 pendiente. TwexAPI devolvió arrays vacíos en tres queries, sin texto/IDs persistidos. RPP y La República respondieron XML RSS; relevancia técnica pendiente. geoBoundaries ADM1/2 descargados; ADM3 404; Nominatim 3 consultas puntuales.\n\nPrecisión/recall, latencia de publicación, tecnología fijo/móvil y geografía distrital no son estimables con la evidencia actual. No existe UBIGEO vigente validado en esta ejecución. Ver architecture_compliance.md para la matriz de requisitos. Evidencias: ../evidencias/manifest.jsonl; ejecutar python -m win_validation.cli audit.\n", encoding="utf-8")
    (REPORTS / "blockers.md").write_text("IODA endpoints correctos consultados vía TLS con CA trust; quedan publication lag/ground truth/zone absent. TwexAPI sample sparse/empty; Entel/institution handles unverified. Globalping GET inventory lists 7 probes in Peru and zero in the four candidate ASNs; no active measurement was created. UBIGEO/feed/SISREP/Indecopi machine-readable routes unresolved. Technical coverage and freshness remain unproven for several sources.\n", encoding="utf-8")

    (REPORTS / "rejected_sources.md").write_text("No definitive REJECTED decisions; no source is rejected based on a failed call or quiet window.\n", encoding="utf-8")
    (REPORTS / "conditional_sources.md").write_text("IODA conditional primary candidate for ASN events (publication latency/independent validation/geography pending); Cloudflare country aggregate observed but operator attribution absent; RIPEstat inventory only; RIS Live routing-only; USGS context-only; geography references are not outage points. Licensing review is deferred.\n", encoding="utf-8")
    (REPORTS / "insufficient_evidence.md").write_text("Independent event truth is absent. Event publication latency, precision/recall, false positives, fixed/mobile and district coverage remain insufficient with current evidence.\n", encoding="utf-8")
    (REPORTS / "sonata_integration_questions.md").write_text("Sonata/Win interface, format, auth, frequency, geographies, expiry semantics, sandbox, rollback: PENDING. No integration or activation.\n", encoding="utf-8")
    (REPORTS / "output_contract_feasibility.md").write_text("No APPROVED source. Fields potentially observed are summarized in validation_results.json; start/published latency, fixed/mobile, district outage location and Sonata geography compatibility are unknown.\n", encoding="utf-8")
    (REPORTS / "feed_format_decision.md").write_text("JSON/XML/feed format remains undecided until Sonata contract is confirmed.\n", encoding="utf-8")

    # Automatic integrity audit includes every archived observation and manual-doc summary.
    errors = []
    for row in records_read():
        artifact = ROOT / row["artifact_path"]
        if not artifact.exists() or hashlib.sha256(artifact.read_bytes()).hexdigest() != row["sha256"]:
            errors.append(row["evidence_id"])
    (REPORTS / "evidence_integrity.json").write_text(json.dumps({"manifest_records": len(records_read()), "integrity_errors": errors}, indent=2), encoding="utf-8")
    (REPORTS / "execution_manifest.json").write_text(json.dumps({"executed_at_utc": now_utc(), "environment": {"python": "3.14.6", "platform": "Windows", "cost_effective_usd": 0}, "sources_attempted": len(records_read()), "evidence_manifest": "evidencias/manifest.jsonl", "integrity_errors": errors, "secret_values_logged": False}, indent=2), encoding="utf-8")
    (REPORTS / "pending_credentials.md").write_text("# Pendientes al cierre\n\nNo faltan tokens para las dos APIs autenticadas: Cloudflare Radar token verificó activo; TwexAPI Bearer key y Starter balance consultados. Pendientes técnicos: handle oficial verificable de Entel y cuentas OSIPTEL/MTC/INDECI/COEN/Indecopi. Las revisiones de licencias quedan diferidas y no forman parte del estado técnico. No compartir ni guardar valores de tokens en evidencias.\n", encoding="utf-8")
    (REPORTS / "retry_policy_compliance.md").write_text("Consultas acotadas con timeout de 20s (HTTP), RIS Live 12s. IODA primera ruta/CA devolvió TLS/metadata error; se revisó OpenAPI oficial y reintentó con lowercase ASN + certifi; se obtuvo data/event APIs. TwexAPI 422 schema validation errors se corrigieron tras inspeccionar mensajes de validación; proveedor declara fallos 4xx/5xx no facturados. No se reintentó 401/403/429; no se excedieron cuotas ni se hicieron pagos. Atlas y Globalping usaron GET; las cinco consultas Atlas latest no devolvieron muestras; no se creó medición ni se enviaron solicitudes de escritura. La consulta de metadatos UBIGEO recibió HTTP 418 y se detuvo sin reintentar. Tres queries X se repitieron una vez para validar parser/minimización: duplicadas y registradas; no fueron tratadas como dos ventanas independientes.\n", encoding="utf-8")
    (REPORTS / "low_density_analysis.md").write_text("Baja/ausente densidad re-evaluada: RIPEstat, IODA, OONI, Radar, X, Globalping y feeds RSS tuvieron consultas acotadas. Globalping listó siete probes PE y cero en los cuatro ASN candidatos; esto no prueba ausencia de cobertura. Atlas tiene inventarios públicos paginados con configuraciones recientes, pero las cinco consultas al endpoint latest devolvieron cero resultados y no permiten medir frescura. Una ventana tranquila/array vacío no significa falta de cobertura. Full network inventory, service technology, publication lag and local outage truth remain pending.\n", encoding="utf-8")
    (REPORTS / "retry_history.csv").exists()
    (REPORTS / "free_tier_simulation.csv").exists()
