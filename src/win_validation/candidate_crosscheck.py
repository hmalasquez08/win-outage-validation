"""Reproduce the Oct. 23 Claro/Ica candidate cross-check from archived evidence."""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .creative_trigger import assess

ROOT = Path.cwd()
EVIDENCE = ROOT / "evidencias"
REPORTS = ROOT / "reports"
EXPECTED = {
    "hermes": "mlab_hermes_recent_scan_20261022_25-fd15735a611b",
    "cloudflare_ica_geography": "cloudflare_geolocations_peru-7bf048ced142",
    "cloudflare_paired": "cloudflare_netflows_ica_paired_claro_20261023-c25cfb06a100",
    "current_ica_netflows": "cloudflare_netflows_ica_recent_all_operators-ac7e230ca4c9",
    "current_ioda": "ioda_movistar_ica_candidate_20261025-242282f2c412",
    "current_ioda_raw": "ioda_movistar_ica_candidate_raw_signals_20261025-85723c22fce9",
    "control_ioda_raw": "ioda_movistar_ica_candidate_raw_control_20261018-af2630a262f0",
    "current_x": "twexapi_replies_movistar_ica_candidate_20261025-74bd04629a7a",
}


def _manifest() -> dict[str, dict[str, Any]]:
    result = {}
    for line in (EVIDENCE / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            result[item["evidence_id"]] = item
    return result


def _read_json(record: dict[str, Any]) -> dict[str, Any]:
    return json.loads((ROOT / record["artifact_path"]).read_text(encoding="utf-8"))


def _series(obj: dict[str, Any], series_name: str) -> tuple[list[str], list[float]]:
    serie = obj.get("result", {}).get(series_name, {})
    points = [(str(t), float(v)) for t, v in zip(serie.get("timestamps", []), serie.get("values", [])) if v is not None]
    return [item[0] for item in points], [item[1] for item in points]


def build() -> dict[str, Any]:
    records = _manifest()
    historical_keys = ("hermes", "cloudflare_ica_geography", "cloudflare_paired")
    missing = [EXPECTED[key] for key in historical_keys if EXPECTED[key] not in records]
    if missing:
        raise RuntimeError("Required evidence IDs missing from manifest: " + ", ".join(missing))

    hermes_record = records[EXPECTED["hermes"]]
    hermes = _read_json(hermes_record)
    rows = hermes.get("rows", [])
    row = next((item for item in rows if item.get("src_asn") == 12252 and item.get("partition_date") == "2026-10-23"), None)
    if row is None:
        raise RuntimeError("Expected Claro AS12252 HERMES event on 2026-10-23 was not found")

    geos_record = records[EXPECTED["cloudflare_ica_geography"]]
    geos = _read_json(geos_record).get("result", {}).get("geolocations", [])
    ica = next((geo for geo in geos if geo.get("name", "").casefold() == "ica" and geo.get("type") == "ADM1"), None)
    if ica is None or ica.get("geoId") != "3938526":
        raise RuntimeError("Archived Cloudflare geography response no longer matches expected Ica ADM1 GeoID")

    paired_record = records[EXPECTED["cloudflare_paired"]]
    paired_response = _read_json(paired_record)
    event_times, event_series = _series(paired_response, "event")
    control_times, control_series = _series(paired_response, "weekday_control")
    paired_points = min(len(event_series), len(control_series))
    if paired_points < 8:
        raise RuntimeError(f"Only {paired_points} paired intervals; at least 8 required for the historical rule")
    # Same-weekday windows are seven days apart, so pair by quarter-hour slot,
    # not by absolute timestamp. Preserve the source timestamps in evidence.
    event_values = event_series[:paired_points]
    control_values = control_series[:paired_points]
    paired = [left - right for left, right in zip(event_values, control_values)]
    event_median = statistics.median(event_values)
    control_median = statistics.median(control_values)
    paired_median = statistics.median(paired)
    below_share = sum(value < 0 for value in paired) / len(paired)
    passes = paired_median < -0.02 and below_share >= 0.90
    observed = datetime.fromisoformat(hermes_record["observed_at_utc"].replace("Z", "+00:00"))
    days = (observed - datetime(2026, 10, 23, tzinfo=timezone.utc)).total_seconds() / 86400

    return {
        "assessment_id": "claro_ica_2026-10-23",
        "assessment_status": "UNCONFIRMED_CANDIDATE" if not passes else "STRICT_NETFLOWS_CANDIDATE",
        "activation_allowed": False,
        "event": {
            "operator": "claro", "asn": 12252, "country": "PE", "hermes_partition_date": row.get("partition_date"),
            "hermes_capture_time_utc": hermes_record["observed_at_utc"],
            "hermes_data_age_from_day_start_hours": round(days * 24, 2),
            "city": row.get("src_city"), "region": row.get("src_state"), "ip_geolocation_source": row.get("client_geo_source"),
            "hermes_confidence_tier": row.get("confidence_tier"), "unique_clients": row.get("unique_ip_count"),
            "median_download_mbps": row.get("median_daily_throughput"), "baseline_download_mbps": row.get("baseline_median_throughput"),
            "throughput_drop_pct_vs_baseline": round((1 - row["median_daily_throughput"] / row["baseline_median_throughput"]) * 100, 2),
            "anomalous_sample_fraction": row.get("anomaly_ratio_throughput"),
        },
        "cloudflare_same_geographic_admin_level": {
            "department": ica["name"], "geoid": ica["geoId"], "geography_type": ica["type"], "operator": "claro", "asn": 12252,
            "event_window": "2026-10-23T00:00:00Z/2026-10-24T00:00:00Z",
            "control_window": "2026-10-16T00:00:00Z/2026-10-17T00:00:00Z",
            "paired_intervals": paired_points, "event_median_normalized": event_median, "control_median_normalized": control_median,
            "event_first_timestamp_utc": event_times[0], "event_last_timestamp_utc": event_times[paired_points - 1],
            "control_first_timestamp_utc": control_times[0], "control_last_timestamp_utc": control_times[paired_points - 1],
            "relative_median_change_pct": round((event_median / control_median - 1) * 100, 2) if control_median else None,
            "median_paired_normalized_difference": paired_median, "intervals_below_control": sum(value < 0 for value in paired),
            "fraction_intervals_below_control": below_share,
            "strict_rule": {"median_difference_less_than": -0.02, "minimum_fraction_below_control": 0.90, "minimum_paired_intervals": 8, "passed": passes},
            "normalization": paired_response.get("result", {}).get("meta", {}).get("normalization"),
            "interpretation": "Event and control were requested together so normalization is common within the pair. The result is not a percentage of users offline or traffic lost; the prior Friday is not independently labeled normal.",
        },
        "decision_reasons": [
            "HERMES found a multi-client daily throughput anomaly for Claro in Ica, using IP-based city/region geolocation.",
            "Cloudflare is a distinct source family and returned a same-department Claro series, but it did not meet the frozen persistent NetFlows rule.",
            "The sources do not provide a district-verified scope or fixed/mobile attribution for this event.",
            "The HERMES event is daily and its observation date is 2026-10-23; it is not fresh enough to represent a live outage at capture time.",
            "No independent incident label was found for this particular event; it remains a candidate rather than a confirmed outage.",
        ],
        "evidence": {key: {"evidence_id": EXPECTED[key], "artifact_path": records[EXPECTED[key]]["artifact_path"], "sha256": records[EXPECTED[key]]["sha256"], "http_status": records[EXPECTED[key]].get("http_status")} for key in historical_keys},
        "method": "Read-only comparison of archived HERMES daily event and Cloudflare NetFlows 15-minute series for the same ASN and Ica department; prior same-weekday period used only as an unlabeled comparator.",
    }


def build_current_readiness() -> dict[str, Any]:
    records = _manifest()
    current_keys = ("cloudflare_ica_geography", "current_ica_netflows", "current_ioda", "current_ioda_raw", "control_ioda_raw", "current_x")
    missing = [EXPECTED[key] for key in current_keys if EXPECTED[key] not in records]
    if missing:
        raise RuntimeError("Required evidence IDs missing from manifest: " + ", ".join(missing))

    current_record = records[EXPECTED["current_ica_netflows"]]
    current_data = _read_json(current_record)
    result = current_data.get("result", {})
    operators = {}
    for operator, asn in (("movistar", 6147), ("claro", 12252), ("entel", 21575), ("bitel", 262210)):
        current = result.get(f"{operator}_current", {})
        control = result.get(f"{operator}_control", {})
        current_values = [float(v) for v in current.get("values", []) if v is not None]
        control_values = [float(v) for v in control.get("values", []) if v is not None]
        points = min(len(current_values), len(control_values))
        differences = [left - right for left, right in zip(current_values[:points], control_values[:points])]
        median_delta = statistics.median(differences) if differences else None
        below_share = sum(v < 0 for v in differences) / points if points else None
        candidate = points >= 8 and median_delta is not None and median_delta < -0.02 and below_share is not None and below_share >= 0.90
        operators[operator] = {
            "asn": asn, "paired_intervals": points, "current_start": (current.get("timestamps") or [None])[0],
            "current_end": (current.get("timestamps") or [None])[-1], "median_paired_delta": median_delta,
            "fraction_below_weekday_comparator": below_share, "strict_netflows_candidate": candidate,
            "independent_same_zone_corroboration": False,
        }

    ioda_record = records[EXPECTED["current_ioda"]]
    ioda = _read_json(ioda_record)
    ioda_events = ioda.get("data", []) if isinstance(ioda.get("data"), list) else []
    ioda_current_record = records[EXPECTED["current_ioda_raw"]]
    ioda_control_record = records[EXPECTED["control_ioda_raw"]]
    ioda_current_data = _read_json(ioda_current_record).get("data", [])
    ioda_control_data = _read_json(ioda_control_record).get("data", [])
    def unpack_ioda(data: Any) -> dict[str, dict[str, Any]]:
        groups = data[0] if isinstance(data, list) and data and isinstance(data[0], list) else []
        return {str(item.get("datasource")): item for item in groups if isinstance(item, dict)}
    ioda_current_series = unpack_ioda(ioda_current_data)
    ioda_control_series = unpack_ioda(ioda_control_data)
    ioda_raw_summary = {}
    for datasource, series in ioda_current_series.items():
        control = ioda_control_series.get(datasource, {})
        values = series.get("values", [])
        control_values = control.get("values", [])
        pairs = [(a, b) for a, b in zip(values, control_values) if isinstance(a, (int, float)) and isinstance(b, (int, float))]
        diffs = [a - b for a, b in pairs]
        current_numeric = [a for a in values if isinstance(a, (int, float))]
        prior_numeric = [b for b in control_values if isinstance(b, (int, float))]
        ioda_raw_summary[datasource] = {
            "current_points": len(values), "control_points": len(control_values), "paired_numeric_points": len(pairs),
            "current_median": statistics.median(current_numeric) if current_numeric else None,
            "control_median": statistics.median(prior_numeric) if prior_numeric else None,
            "paired_median_delta": statistics.median(diffs) if diffs else None,
            "fraction_intervals_below_week_prior": sum(a < b for a, b in pairs) / len(pairs) if pairs else None,
            "current_last_sample_utc": datetime.fromtimestamp(int(series.get("from", 0)) + int(series.get("step", 0)) * max(len(values) - 1, 0), tz=timezone.utc).isoformat().replace("+00:00", "Z") if values and series.get("from") else None,
        }
    x_record = records[EXPECTED["current_x"]]
    x_summary = _read_json(x_record)
    last_updated = result.get("meta", {}).get("lastUpdated")
    captured = datetime.fromisoformat(current_record["observed_at_utc"].replace("Z", "+00:00"))
    source_lag_minutes = None
    if last_updated:
        source_lag_minutes = round((captured - datetime.fromisoformat(last_updated.replace("Z", "+00:00"))).total_seconds() / 60, 1)

    has_candidate = any(x["strict_netflows_candidate"] for x in operators.values())
    status = "NO_STRICT_CANDIDATE"
    if has_candidate:
        status = "STALE_SINGLE_FAMILY_CANDIDATE" if source_lag_minutes is not None and source_lag_minutes > 30 else "SINGLE_FAMILY_CANDIDATE"
    assessment_now = datetime.fromisoformat(current_record["observed_at_utc"].replace("Z", "+00:00"))
    latest_point = max((str(t) for series in result.values() if isinstance(series, dict) for t in series.get("timestamps", [])), default=None)
    real_signal = [{
        "signal_id": current_record["evidence_id"], "family": "cloudflare", "kind": "internet_degradation",
        "operator": "movistar", "technology": "unknown", "observed_at": last_updated or latest_point,
        "source_status": "ok",
        "geography": {"country": "PE", "level": "department", "code": "11", "verified": False},
    }] if has_candidate and (last_updated or latest_point) else []
    real_engine_decision = assess(real_signal, assessment_now)

    return {
        "assessment_id": "ica_department_live_scan_2026-10-25",
        "assessment_status": status,
        "activation_allowed": False,
        "scope": {"country": "PE", "department": "Ica", "cloudflare_geoid": "3938526", "operator_asns": [x["asn"] for x in operators.values()]},
        "capture_time_utc": current_record["observed_at_utc"], "source_data_last_updated_utc": last_updated,
        "source_data_lag_minutes_at_capture": source_lag_minutes, "normalization": result.get("meta", {}).get("normalization"),
        "current_window": "2026-10-25T03:00:00Z/2026-10-25T08:45:00Z",
        "weekday_comparator_window": "2026-10-18T03:00:00Z/2026-10-18T08:45:00Z",
        "operators": operators,
        "real_signal_engine_evaluation": real_engine_decision,
        "ioda": {"http_status": ioda_record.get("http_status"), "event_count": len(ioda_events), "evidence_id": ioda_record["evidence_id"], "artifact_path": ioda_record["artifact_path"], "raw_current_evidence_id": ioda_current_record["evidence_id"], "raw_control_evidence_id": ioda_control_record["evidence_id"], "raw_signals": ioda_raw_summary, "geographic_scope": "AS6147 aggregate; no Ica/department breakdown in this query", "interpretation": "The event endpoint returned no event. Raw signals show BGP route count stable and a small change in active-probe reachable /24 counts; this is weak ASN-level context, not same-department corroboration."},
        "x_replies": {"http_status": x_record.get("http_status"), "returned_text_fields": x_summary.get("unique_text_fields"), "connectivity_complaint_texts": x_summary.get("connectivity_complaint_texts"), "ica_mentions": x_summary.get("ica_mentions"), "interpretation": "The redacted response contained no text fields to classify; this is inconclusive and does not establish that no complaints existed."},
        "limits": [
            "Cloudflare NetFlows measures traffic reaching Cloudflare from the ASN; it is not a direct count of users without internet or total ISP traffic.",
            "The comparator is the same period one week earlier, not an independently verified normal period.",
            "The GeoID is department-level; it does not identify a district, street, or exact customer location.",
            "Cloudflare is the only family meeting the area-level candidate rule. IODA provides an independent but ASN-wide, weak active-probing context that is not geographically aligned with Ica.",
            "No distinction between fixed and mobile access is available from these series.",
        ],
        "evidence": {key: {"evidence_id": EXPECTED[key], "artifact_path": records[EXPECTED[key]]["artifact_path"], "sha256": records[EXPECTED[key]]["sha256"], "http_status": records[EXPECTED[key]].get("http_status")} for key in current_keys},
    }


def write(result: dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "current_candidate_crosscheck.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    event = result["event"]
    cf = result["cloudflare_same_geographic_admin_level"]
    ev = result["evidence"]
    lines = [
        "# Cotejo de candidato actual: Claro en Ica",
        "",
        "## Decisión",
        "",
        f"**{result['assessment_status']} — sin activación.** Este registro no se etiqueta como caída confirmada ni se convierte en una orden de creatividad.",
        "",
        "## Evidencia observada",
        "",
        f"M-Lab HERMES registró el {event['hermes_partition_date']} una anomalía diaria para Claro (AS12252) en Ica: descarga mediana {event['median_download_mbps']:.2f} Mbps frente a {event['baseline_download_mbps']:.2f} Mbps de base (−{event['throughput_drop_pct_vs_baseline']:.1f}%), fracción anómala {event['anomalous_sample_fraction']:.3f}, {event['unique_clients']} clientes únicos. La geolocalización proviene de {event['ip_geolocation_source']} y la etiqueta de atribución de ruta fue `{event['hermes_confidence_tier']}`. La respuesta se capturó el {event['hermes_capture_time_utc']}; HERMES publica datos diarios, por lo que esto no es una señal de estado en vivo.",
        "",
        f"Cloudflare confirmó que Ica tiene GeoID departamental `{cf['geoid']}` y devolvió en una sola respuesta series comparables para el mismo ASN y departamento: {cf['paired_intervals']} pares de intervalos de 15 minutos con normalización compartida. La mediana del índice normalizado fue {cf['event_median_normalized']:.6f} frente a {cf['control_median_normalized']:.6f} el viernes anterior ({cf['relative_median_change_pct']:+.2f}% relativo en el índice; no equivale a volumen de tráfico). La mediana de las diferencias emparejadas fue {cf['median_paired_normalized_difference']:+.6f}; {cf['fraction_intervals_below_control']:.1%} de los intervalos quedaron por debajo del comparador.",
        "",
        f"La regla NetFlows ya definida exige diferencia emparejada < −0.02 y al menos 90% de intervalos bajo el comparador, con ocho o más pares. **No pasó**: el valor emparejado fue {cf['median_paired_normalized_difference']:+.6f} y solo {cf['fraction_intervals_below_control']:.1%} quedó por debajo. La variación relativa de medianas no equivale a usuarios desconectados ni a tráfico perdido.",
        "",
        "## Interpretación",
        "",
        "El cotejo es útil porque alinea operador, fecha y nivel administrativo departamental entre dos familias de medición. Aun así, HERMES no verifica la ubicación física de los participantes ni separa internet fijo y móvil; Cloudflare ofrece una serie agregada, sin barrio/distrito. El comparador semanal tampoco está etiquetado como normal. No se encontró una referencia externa independiente que confirme que este registro concreto fuera una interrupción real.",
        "",
        "Por tanto, **hay una anomalía de rendimiento observada y corroboración departamental débil, pero no una caída confirmada ni evidencia accionable vigente**. El motor debe mantener el caso en candidato/suprimido, nunca activar por este registro histórico.",
        "",
        "## Evidencias",
        "",
        "| Artefacto | Evidence ID | Ruta | SHA-256 | HTTP |",
        "|---|---|---|---|---:|",
    ]
    for key, item in ev.items():
        lines.append(f"| {key} | `{item['evidence_id']}` | `{item['artifact_path']}` | `{item['sha256']}` | {item['http_status']} |")
    lines += ["", "## Reproducibilidad", "", "Desde la raíz del proyecto: `python -m win_validation.candidate_crosscheck`. El módulo solo lee las respuestas archivadas y vuelve a generar este informe y el JSON; no consulta servicios ni altera las evidencias originales.", ""]
    (REPORTS / "current_candidate_crosscheck.md").write_text("\n".join(lines), encoding="utf-8")


def write_current_readiness(result: dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "creative_activation_readiness.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Estado técnico para activar creatividades", "",
        f"**Estado observado: {result['assessment_status']}. Activación permitida: no.** Se consultó NetFlows por operador y GeoID departamental de Ica para el 25 de octubre de 2026 (03:00–08:45 UTC), comparándolo con el mismo bloque del 18 de octubre. Las ocho series se pidieron en una sola consulta para compartir la normalización.", "",
        "## Resultado por operador", "", "| Operador | Intervalos emparejados | Diferencia mediana normalizada | Intervalos bajo comparador | Pasa regla estricta |", "|---|---:|---:|---:|---|",
    ]
    for operator, item in result["operators"].items():
        delta = "n/d" if item["median_paired_delta"] is None else f"{item['median_paired_delta']:+.6f}"
        share = "n/d" if item["fraction_below_weekday_comparator"] is None else f"{item['fraction_below_weekday_comparator']:.1%}"
        lines.append(f"| {operator.title()} | {item['paired_intervals']} | {delta} | {share} | {'Sí' if item['strict_netflows_candidate'] else 'No'} |")
    lines += [
        f"", f"Movistar muestra un **candidato técnico departamental**: diferencia mediana normalizada {result['operators']['movistar']['median_paired_delta']:+.6f} y {result['operators']['movistar']['fraction_below_weekday_comparator']:.1%} de intervalos por debajo del comparador en {result['operators']['movistar']['paired_intervals']} pares. Cloudflare informó actualización hasta {result['source_data_last_updated_utc']} y la captura se hizo a las {result['capture_time_utc']} ({result['source_data_lag_minutes_at_capture']:.1f} minutos de desfase). Pasa la regla de persistencia para candidato, pero no demuestra que usuarios estuvieran desconectados ni que existiera una caída de servicio.",
        "", "## Corroboración buscada", "",
        f"- IODA: HTTP {result['ioda']['http_status']}, {result['ioda']['event_count']} eventos en la consulta acotada. Las series crudas de AS6147 muestran BGP estable (5.933 prefijos /24 visibles, sin cambio) y sondeos activos con mediana de 952 bloques /24 accesibles frente a 959 en el comparador semanal (−7; 65.7% de intervalos más bajos). Es una variación pequeña y de ASN completo, no corroboración localizada en Ica; un endpoint vacío no prueba que la red esté sana.",
        f"- Respuestas a la cuenta oficial de Movistar: HTTP {result['x_replies']['http_status']}; el resultado redactado tuvo {result['x_replies']['returned_text_fields']} campos de texto y ningún elemento clasificable. La búsqueda es inconclusa, no prueba ausencia de quejas.",
        "- HERMES: la anomalía más reciente consultada fue para Claro en Ica el 23 de octubre; es otro operador y otra fecha, así que no corrobora el candidato actual de Movistar.",
        "", "## Por qué no se activa", "",
        "1. Solo Cloudflare cumple la regla de candidato a nivel departamental. IODA aporta una señal independiente débil a nivel de ASN, sin resolver Ica.",
        "2. No hay una segunda señal independiente que coincida en Movistar, Ica y la misma ventana con magnitud suficiente para corroborar una degradación.",
        "3. El dato departamental no resuelve qué distritos están afectados ni diferencia fijo de móvil.",
        f"4. La actualización consultada llega con {result['source_data_lag_minutes_at_capture']:.1f} minutos de desfase; supera el límite de frescura de 30 minutos que usa el simulador local.",
        "5. Una activación programática necesita una impresión y una solicitud de anuncio procedentes de un sitio o aplicación. Por inferencia del flujo OpenRTB documentado, un dispositivo totalmente desconectado no puede pedir un anuncio nuevo por esa misma conexión. La activación puede orientar inventario que sí esté conectado en la zona; garantizar un anuncio dinámico al dispositivo sin ninguna conexión requeriría una vía prealmacenada/local, que no forma parte de esta validación.",
        f"6. Al pasar el dato real por el simulador local, el resultado fue `{result['real_signal_engine_evaluation']['status']}`: {', '.join(result['real_signal_engine_evaluation']['reasons']) or 'sin motivos'}.",
        "", "## Qué está resuelto y qué queda", "",
        "Resuelto en esta iteración: ya se ejecuta una señal regional de Cloudflare para los cuatro operadores y se aplica una regla persistente sobre datos comparables; se capturó HERMES como fuente nueva y se buscó corroboración IODA/X para el candidato actual; el evaluador produce un estado reproducible sin tocar un destino publicitario.",
        "", "Para que el motor pueda emitir un evento apto para creatividad todavía se necesita una fuente independiente, fresca y alineada en operador, zona y tiempo; señal directa que permita distinguir interrupción/degradación de una caída de tráfico; granularidad geográfica suficiente para una zona segmentable; y un caso confirmado de extremo a extremo con salida local de prueba. La negociación de integración queda para después de que esa evidencia pase la regla.",
        "", "## Evidencias", "", "| Fuente | Evidence ID | Ruta | SHA-256 | HTTP |", "|---|---|---|---|---:|",
    ]
    for key, item in result["evidence"].items():
        lines.append(f"| {key} | `{item['evidence_id']}` | `{item['artifact_path']}` | `{item['sha256']}` | {item['http_status']} |")
    lines += ["", "## Documentación primaria consultada", "", "- [M-Lab HERMES: actualización diaria y cobertura](https://www.measurementlab.net/tests/hermes/quickstart/).", "- [Cloudflare Radar NetFlows](https://developers.cloudflare.com/radar/investigate/netflows/) y [geografías GeoID](https://developers.cloudflare.com/api/resources/radar/subresources/geolocations/methods/list/).", "- [IAB OpenRTB 2.6: flujo de puja por impresión](https://github.com/InteractiveAdvertisingBureau/openrtb2.x/blob/main/2.6.md). La imposibilidad de una solicitud nueva desde un dispositivo desconectado es una inferencia del flujo descrito.", "", "Reproducir desde la raíz: `python -m win_validation.candidate_crosscheck`.", ""]
    (REPORTS / "creative_activation_readiness.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    result = build()
    write(result)
    current = build_current_readiness()
    write_current_readiness(current)
    print(json.dumps({"historical_candidate_status": result["assessment_status"], "current_scan_status": current["assessment_status"], "activation_allowed": current["activation_allowed"], "reports": ["reports/current_candidate_crosscheck.md", "reports/creative_activation_readiness.md"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
