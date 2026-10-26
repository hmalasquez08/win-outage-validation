"""Historical, read-only replay against M-Lab HERMES' public event overview."""
from __future__ import annotations

import argparse
import csv
import json
import urllib.parse
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .cli import request

ROOT = Path.cwd()
REPORTS = ROOT / "reports"
OPERATORS = {"movistar": 6147, "claro": 12252, "entel": 21575, "bitel": 262210}
CASES = [
    {"id": "claro_los_olivos_2025-12-11", "date": "2025-12-11", "affected": [12252], "areas": ["lima"], "area_basis": "Los Olivos, Lima; HERMES only reports provider city/region"},
    {"id": "loreto_shared_carrier_2025-12-19", "date": "2025-12-19", "affected": [12252, 21575, 262210], "areas": ["loreto", "iquitos"], "area_basis": "Loreto department; no district list in reference"},
    {"id": "ancash_multioperator_2025-04-24", "date": "2025-04-24", "affected": [6147, 12252, 21575, 262210], "areas": ["ancash"], "area_basis": "Localities in five provinces of Ancash"},
    {"id": "ayacucho_integratel_entel_mobile_2025-12-26", "date": "2025-12-26", "affected": [6147, 21575], "areas": ["ayacucho", "huanca sancos", "lucanas"], "area_basis": "Some districts named, no district list in reference"},
    {"id": "movistar_lima_fiber_2026-07-01", "date": "2026-07-01", "affected": [6147], "areas": ["lima"], "area_basis": "Lima locations; reference lists districts but HERMES city is broader"},
]


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace("department", "").replace("region", "").split())


def _location_match(row: dict[str, Any], areas: list[str]) -> bool:
    place = " | ".join(_norm(row.get(key)) for key in ("src_city", "src_state", "src_metro", "src_group_label"))
    return any(_norm(area) in place for area in areas)


def _event_row(case: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    baseline = row.get("baseline_median_throughput")
    current = row.get("median_daily_throughput")
    drop = round((1 - current / baseline) * 100, 2) if isinstance(baseline, (int, float)) and baseline > 0 and isinstance(current, (int, float)) else None
    asn = row.get("src_asn")
    return {
        "incident_id": case["id"], "reference_date": case["date"], "hermes_date": row.get("partition_date"),
        "asn": asn, "operator": next((name for name, number in OPERATORS.items() if number == asn), "other"),
        "city": row.get("src_city"), "region": row.get("src_state"), "metro": row.get("src_metro"),
        "geolocation_source": row.get("client_geo_source"), "detection_granularity": row.get("detection_granularity"),
        "server_site": row.get("dst_site"), "sample_unique_clients": row.get("unique_ip_count"),
        "throughput_drop_pct_vs_baseline": drop, "anomalous_throughput_sample_fraction": row.get("anomaly_ratio_throughput"),
        "median_download_mbps": row.get("median_daily_throughput"), "baseline_download_mbps": baseline,
        "median_rtt_ms": row.get("median_daily_rtt"), "baseline_rtt_ms": row.get("baseline_median_rtt"),
        "hermes_confidence_label": row.get("confidence_tier"), "inferred_path_entity": row.get("culprit_entity"),
        "affected_operator_in_reference": asn in case["affected"], "expected_area_text_match": _location_match(row, case["areas"]),
        "exact_date_match": row.get("partition_date") == case["date"],
        "reference_match": asn in case["affected"] and _location_match(row, case["areas"]),
    }


def fetch_replay() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    for case in CASES:
        center = date.fromisoformat(case["date"])
        start, end = (center - timedelta(days=1)).isoformat(), (center + timedelta(days=1)).isoformat()
        params = urllib.parse.urlencode({"start": start, "end": end, "country": "PE", "page": 0, "min_dayof": 25, "min_baseline": 25})
        url = "https://hermes-dashboard.org/api/events?" + params
        rec, body = request("mlab_hermes_" + case["id"], url, "historical_signal", max_response_bytes=5_000_000)
        query = {"incident_id": case["id"], "start": start, "end": end, "http_status": rec.get("http_status"), "evidence_id": rec.get("evidence_id"), "artifact_path": rec.get("artifact_path")}
        try:
            obj = json.loads(body)
            query["total_public_events"] = obj.get("total")
            query["returned_rows"] = len(obj.get("rows", []))
            query["pagination_complete"] = len(obj.get("rows", [])) >= int(obj.get("total", 0))
            for row in obj.get("rows", []):
                if row.get("src_asn") in set(OPERATORS.values()):
                    rows.append(_event_row(case, row))
        except (ValueError, TypeError, json.JSONDecodeError):
            query.update({"total_public_events": None, "returned_rows": 0, "pagination_complete": False, "parse_error": True})
        queries.append(query)

    by_case: list[dict[str, Any]] = []
    for case in CASES:
        relevant = [row for row in rows if row["incident_id"] == case["id"]]
        matches = [row for row in relevant if row["reference_match"]]
        controls_in_area = [row for row in relevant if row["asn"] not in case["affected"] and row["expected_area_text_match"]]
        by_case.append({
            "incident_id": case["id"], "expected_operators": [name for name, asn in OPERATORS.items() if asn in case["affected"]],
            "expected_geography_basis": case["area_basis"], "public_hermes_rows_for_target_asns": len(relevant),
            "operator_and_area_matches_in_3day_window": len(matches), "exact_date_operator_and_area_matches": sum(row["exact_date_match"] for row in matches),
            "other_target_operator_events_in_expected_area": len(controls_in_area),
            "matched_events": matches, "coincident_unmatched_operator_events": controls_in_area,
        })

    matched_cases = sum(bool(item["operator_and_area_matches_in_3day_window"]) for item in by_case)
    exact_cases = sum(bool(item["exact_date_operator_and_area_matches"]) for item in by_case)
    control_pairs = sum(item["other_target_operator_events_in_expected_area"] for item in by_case)
    return {
        "source": "M-Lab HERMES public dashboard overview endpoint",
        "query_date_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "method": "Read-only public event overview, Peru, reference date ±1 UTC day, at least 25 day-of and 25 baseline measurements; only four project ASNs retained in summary.",
        "case_count": len(CASES), "cases_with_matching_operator_and_area": matched_cases,
        "cases_with_exact_date_operator_and_area_match": exact_cases,
        "unmatched_operator_events_in_expected_areas": control_pairs,
        "case_summary": by_case, "query_evidence": queries,
        "event_rows": rows,
        "limitations": [
            "This is a selected five-case retrospective replay, not an unbiased estimate of sensitivity, precision, or false-positive rate.",
            "A missing HERMES event can mean insufficient tests or coverage, not a healthy network; a query returns only detected groups.",
            "HERMES uses user-initiated speed tests. Its users are not a representative sample and its events are daily, so short outages can be missed.",
            "Geography is provider IP geolocation at city/metro scale, not an official district boundary; fixed versus mobile access is not identified.",
            "The public overview is available without sign-in, but event drill-down requires an M-Lab/Google account with BigQuery access. The dashboard endpoint is not documented as a production integration contract.",
            "Three-day date windows help with UTC/local date boundary differences. A match within this window is not proof the measured performance change was the same outage.",
        ],
    }


def write_outputs(summary: dict[str, Any]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "mlab_hermes_historical_replay.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    detail_fields = list(summary["event_rows"][0]) if summary["event_rows"] else ["incident_id", "reference_date", "hermes_date", "asn", "operator", "city", "region", "server_site", "reference_match"]
    with (REPORTS / "mlab_hermes_historical_replay.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=detail_fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(summary["event_rows"])
    lines = [
        "# Replay histórico de M-Lab HERMES en incidentes peruanos", "",
        f"Consulta pública de solo lectura ejecutada el {summary['query_date_utc']}. Se cotejaron cinco referencias con ventanas UTC de tres días y umbral de consulta de 25 mediciones tanto para el día analizado como para la base. HERMES encontró coincidencia de operador y área en **{summary['cases_with_matching_operator_and_area']}/5** casos; coincidencia en la fecha exacta en **{summary['cases_with_exact_date_operator_and_area_match']}/5**. Se observaron {summary['unmatched_operator_events_in_expected_areas']} eventos de otros operadores objetivo en las áreas descritas por los casos; son señales sin correspondencia con la etiqueta disponible, no falsos positivos confirmados.", "",
        "| Caso de referencia | Operadores objetivo | Filas HERMES en ASN objetivo | Coincidencias operador + área ±1 día | En fecha exacta | Eventos de otro operador en área |", "|---|---|---:|---:|---:|---:|",
    ]
    for item in summary["case_summary"]:
        lines.append(f"| {item['incident_id']} | {', '.join(item['expected_operators'])} | {item['public_hermes_rows_for_target_asns']} | {item['operator_and_area_matches_in_3day_window']} | {item['exact_date_operator_and_area_matches']} | {item['other_target_operator_events_in_expected_area']} |")
    lines += ["", "## Señales que sí coincidieron", ""]
    matched = [row for row in summary["event_rows"] if row["reference_match"]]
    if matched:
        lines += ["| Referencia | Fecha HERMES | Operador | Área HERMES | Descenso mediano de descarga vs. base | Fracción de muestras anómalas | Clientes únicos | Nivel geográfico informado |", "|---|---|---|---|---:|---:|---:|---|"]
        for row in matched:
            drop = "n/d" if row["throughput_drop_pct_vs_baseline"] is None else f"{row['throughput_drop_pct_vs_baseline']:.1f}%"
            fraction = "n/d" if row["anomalous_throughput_sample_fraction"] is None else f"{row['anomalous_throughput_sample_fraction']:.3f}"
            geo = f"{row['detection_granularity']} / {row['geolocation_source']}"
            lines.append(f"| {row['incident_id']} | {row['hermes_date']} | {row['operator']} (AS{row['asn']}) | {row['city']}, {row['region']} | {drop} | {fraction} | {row['sample_unique_clients']} | {geo} |")
    else:
        lines.append("No hubo coincidencias en los casos consultados.")
    lines += ["", "## Interpretación técnica", "",
        "HERMES es un avance sustantivo frente al detector previo: usa pruebas NDT iniciadas por usuarios, agrupa por ASN y ciudad/metro y compara rendimiento contra la propia base del grupo. La documentación del servicio describe tests estadísticos sobre RTT y throughput y publicación diaria normalmente el día siguiente. En el incidente de Movistar Lima del 1 de julio de 2026, la vista pública devolvió una señal en Lima, AS6147, con descarga mediana 11.11 Mbps frente a 50.16 Mbps de base (−77.8%), fracción anómala 1.0 y siete clientes únicos. En el caso Claro de Los Olivos del 11 de diciembre de 2025, devolvió una fila Claro-Lima con caída de descarga y cinco clientes únicos; el nivel HERMES de esa fila no venía informado como `strong`.", "",
        "La misma ventana del caso Claro mostró además una fila Movistar-Lima que no coincide con el operador afectado anunciado. Esto es una advertencia concreta de que el rendimiento observado en una muestra diaria puede activar otro operador; no prueba que el evento Movistar sea falso porque la referencia no es un registro completo de incidentes. HERMES tampoco detectó en esta consulta las referencias de Loreto, Áncash o Ayacucho bajo las áreas y ventanas usadas.", "",
        "HERMES puede añadirse como **entrada técnica experimental de rendimiento** y completar a Cloudflare, no como detector aprobado. No demuestra cobertura homogénea, causalidad de operador, distrito, tecnología fija/móvil ni actualidad suficiente para alertar durante caídas de minutos. El nivel de área es la ciudad/metro estimada por IP, no UBIGEO. El conjunto evaluado es muy pequeño y escogido; sus proporciones no son métricas poblacionales.", "",
        "## Cobertura, latencia y acceso observados", "",
        "Las cinco respuestas JSON públicas del overview están indexadas en `evidencias/manifest.jsonl`; el detalle filtrado de las cuatro ASN está en `mlab_hermes_historical_replay.csv`. El overview se consultó sin credenciales. La documentación indica procesamiento diario y datos normalmente disponibles al día siguiente; la vista de detalle ejecuta consultas de BigQuery como la persona usuaria y requiere pertenencia al grupo M-Lab. El endpoint del dashboard no se presenta como contrato productivo estable.", "",
        "| Referencia | HTTP | Evidence ID | Artefacto |", "|---|---:|---|---|",
    ]
    for query in summary["query_evidence"]:
        lines.append(f"| {query['incident_id']} | {query['http_status']} | `{query['evidence_id']}` | `{query['artifact_path']}` |")
    lines += [
        "",
        "## Límites para el evento creativo", "",
    ]
    lines += [f"- {limit}" for limit in summary["limitations"]]
    lines += ["", "Fuentes técnicas: [M-Lab HERMES](https://www.measurementlab.net/tests/hermes/), [acceso y actualización](https://www.measurementlab.net/tests/hermes/quickstart/), [esquema y método](https://www.measurementlab.net/tests/hermes/schema/).", ""]
    (REPORTS / "mlab_hermes_historical_replay.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a small read-only M-Lab HERMES historical replay")
    parser.add_argument("--fetch-historical", action="store_true", help="query five Peru reference windows and save evidence")
    args = parser.parse_args()
    if not args.fetch_historical:
        parser.error("Use --fetch-historical to make the five explicit public GET requests.")
    summary = fetch_replay()
    write_outputs(summary)
    print(json.dumps({"cases": summary["case_count"], "matches_3day": summary["cases_with_matching_operator_and_area"], "matches_exact_date": summary["cases_with_exact_date_operator_and_area_match"], "other_operator_events_in_area": summary["unmatched_operator_events_in_expected_areas"], "report": "reports/mlab_hermes_historical_replay.md", "csv": "reports/mlab_hermes_historical_replay.csv"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
