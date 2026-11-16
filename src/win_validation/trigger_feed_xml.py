"""Render and validate the Spanish XML output contract.

This module formats decisions and does not fetch network data or activate advertising.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .creative_trigger import MAX_SIGNAL_AGE, run_demo

ROOT = Path.cwd()
DEFAULT_OUTPUT = ROOT / "trigger_feed_simulated.xml"
SCHEMA_VERSION = "1.0"

OPERATORS = {"movistar", "claro", "entel", "bitel"}
SERVICE_TYPES = {"fixed", "mobile", "unknown"}
INCIDENT_TYPES = {"outage", "degradation", "unknown"}
STATES = {"candidate", "active", "recovering", "closed"}
GEO_PRECISIONS = {"country", "department", "province", "district", "unknown"}
SYSTEM_STATUSES = {"ok", "degraded", "down"}
REQUIRED_FEED_ATTRS = ("schemaVersion", "systemStatus", "generatedAt", "validUntil")
REQUIRED_EVENT_CHILDREN = (
    "operator",
    "serviceType",
    "incidentType",
    "state",
    "trigger",
    "zone",
    "geoPrecision",
    "startedAt",
    "expiresAt",
)

TAGS_ES = {
    "triggerFeed": "feedActivador", "event": "evento", "operator": "operador",
    "serviceType": "tipoServicio", "incidentType": "tipoIncidente", "state": "estado",
    "trigger": "activador", "zone": "zona", "district": "distrito", "ubigeo": "ubigeo",
    "geoPrecision": "precisionGeo", "startedAt": "iniciadoEn", "expiresAt": "expiraEn",
    "creativeUrl": "urlCreativo", "confidence": "confianza", "severity": "severidad",
}
ATTRS_ES = {"schemaVersion": "versionEsquema", "systemStatus": "estadoSistema", "generatedAt": "generadoEn", "validUntil": "validoHasta", "simulationOnly": "simulacion"}
VALUES_ES = {
    "serviceType": {"fixed": "fijo", "mobile": "movil", "unknown": "desconocido"},
    "incidentType": {"outage": "corte", "degradation": "degradacion", "unknown": "desconocido"},
    "state": {"candidate": "candidato", "active": "activo", "recovering": "recuperando", "closed": "cerrado"},
    "geoPrecision": {"country": "pais", "department": "departamento", "province": "provincia", "district": "distrito", "unknown": "desconocido"},
    "systemStatus": {"ok": "ok", "degraded": "degradado", "down": "caido"},
}


def _translate_tree(root: ET.Element, *, to_spanish: bool) -> ET.Element:
    tags = TAGS_ES if to_spanish else {value: key for key, value in TAGS_ES.items()}
    attrs = ATTRS_ES if to_spanish else {value: key for key, value in ATTRS_ES.items()}
    values = VALUES_ES if to_spanish else {key: {value: name for name, value in mapping.items()} for key, mapping in VALUES_ES.items()}
    for node in root.iter():
        original = node.tag if to_spanish else tags.get(node.tag, node.tag)
        if original in values and node.text:
            node.text = values[original].get(node.text.strip(), node.text)
        translated_attrs = {}
        for key, value in node.attrib.items():
            original_attr = key if to_spanish else attrs.get(key, key)
            if original_attr in values:
                value = values[original_attr].get(value, value)
            translated_attrs[attrs.get(key, key)] = value
        node.attrib.clear()
        node.attrib.update(translated_attrs)
        node.tag = tags.get(node.tag, node.tag)
    return root


def _geo_names(code: str, level: str) -> tuple[str, str | None]:
    path = ROOT / "data" / "ubigeo_hibrido.csv"
    if not path.exists():
        return code, None
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("UBIGEO", "").startswith(code) and code:
                return row.get("DEPARTAMENTO") or code, row.get("DISTRITO") if level == "district" and row.get("UBIGEO") == code else None
    return code, None


def _normalise_geo(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char) and char.isalnum())


def _validate_geography(event: ET.Element, values: dict[str, str], prefix: str, errors: list[str]) -> None:
    level = values.get("geoPrecision", "")
    lengths = {"department": 2, "province": 4, "district": 6}
    if level not in lengths:
        return
    node = event.find("ubigeo")
    code = (node.text or "").strip() if node is not None else ""
    if not code.isascii() or not code.isdigit() or len(code) != lengths[level]:
        errors.append(f"{prefix}: ubigeo must have {lengths[level]} digits for {level}")
        return
    path = ROOT / "data" / "ubigeo_hibrido.csv"
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = [row for row in csv.DictReader(handle) if row.get("UBIGEO", "").startswith(code)]
    except OSError:
        errors.append(f"{prefix}: UBIGEO catalogue unavailable")
        return
    if not rows or (level == "district" and not any(row.get("UBIGEO") == code for row in rows)):
        errors.append(f"{prefix}: unknown ubigeo {code}")
        return
    if _normalise_geo(values.get("zone", "")) != _normalise_geo(rows[0].get("DEPARTAMENTO", "")):
        errors.append(f"{prefix}: zona does not match ubigeo")
    if level == "district":
        district = event.find("district")
        label = (district.text or "").strip() if district is not None else ""
        if not label or _normalise_geo(label) != _normalise_geo(rows[0].get("DISTRITO", "")):
            errors.append(f"{prefix}: distrito does not match ubigeo")


def build_empty_feed(now: datetime, *, system_status: str = "ok") -> ET.Element:
    if system_status not in SYSTEM_STATUSES:
        raise ValueError(f"invalid system status: {system_status}")
    root = ET.Element("triggerFeed", {
        "schemaVersion": SCHEMA_VERSION, "systemStatus": system_status,
        "generatedAt": _format_utc(now), "validUntil": _format_utc(now + timedelta(minutes=5)),
    })
    return _translate_tree(root, to_spanish=True)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp without timezone: {value}")
    return parsed.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _service_type(technology: str) -> str:
    return technology if technology in {"fixed", "mobile"} else "unknown"


def _incident_type(kind: str) -> str:
    return kind if kind in {"outage", "degradation"} else "unknown"


def _incident_id(operator: str, code: str, level: str, service: str) -> str:
    return f"pe-{operator}-{level}-{code}-{service}"


def select_demo_decision(result: dict[str, Any]) -> dict[str, Any]:
    for item in result.get("scenarios", []):
        if item.get("scenario") == "direct_plus_independent_same_zone":
            return item["decision"]
    raise ValueError("demo result has no direct_plus_independent_same_zone scenario")


def build_feed(
    decision: dict[str, Any],
    *,
    state: str,
    incident_type: str = "degradation",
    system_status: str = "ok",
    simulation_only: bool = True,
    district_name: str | None = None,
    creative_url: str | None = None,
) -> ET.Element:
    if decision.get("status") != "QUALIFIED_FOR_SIMULATED_CREATIVE":
        raise ValueError("only QUALIFIED_FOR_SIMULATED_CREATIVE decisions can produce an event")
    if state not in STATES:
        raise ValueError(f"invalid event state: {state}")
    if simulation_only and state == "active":
        raise ValueError("a simulation cannot produce an active trigger")
    if system_status not in SYSTEM_STATUSES:
        raise ValueError(f"invalid system status: {system_status}")
    scope = decision.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("qualified decision has no object scope")

    generated = _parse_utc(str(decision["decision_at"]))
    valid_until = _parse_utc(str(decision["expires_at"]))
    if valid_until < generated:
        raise ValueError("validUntil cannot precede generatedAt")
    if state == "active" and system_status != "ok":
        raise ValueError("an active trigger requires systemStatus=ok")

    geography = scope.get("geography") or {}
    operator = str(scope["operator"]).casefold()
    code = str(geography.get("code", "")).strip()
    level = str(geography.get("level", "")).casefold()
    started = _parse_utc(str(scope["first_observed_at"]))
    last_observed = _parse_utc(str(scope["last_observed_at"]))
    event_expires = min(last_observed + MAX_SIGNAL_AGE, valid_until)

    trigger = state == "active" and system_status == "ok"

    root = ET.Element(
        "triggerFeed",
        {
            "schemaVersion": SCHEMA_VERSION,
            "systemStatus": system_status,
            "generatedAt": _format_utc(generated),
            "validUntil": _format_utc(valid_until),
        },
    )
    if simulation_only:
        root.set("simulationOnly", "true")
    service = _service_type(str(scope.get("technology", "")))
    event = ET.SubElement(root, "event", {"id": _incident_id(operator, code, level, service)})
    ET.SubElement(event, "operator").text = operator
    ET.SubElement(event, "serviceType").text = service
    ET.SubElement(event, "incidentType").text = _incident_type(incident_type)
    ET.SubElement(event, "state").text = state
    ET.SubElement(event, "trigger").text = "true" if trigger else "false"
    zone_name, resolved_district = _geo_names(code, level)
    ET.SubElement(event, "zone").text = zone_name
    district_name = district_name or resolved_district
    if district_name:
        ET.SubElement(event, "district").text = district_name.strip()
    if level in {"district", "province", "department"} and code.isdigit():
        ET.SubElement(event, "ubigeo").text = code
    ET.SubElement(event, "geoPrecision").text = level if level in GEO_PRECISIONS else "unknown"
    ET.SubElement(event, "startedAt").text = _format_utc(started)
    ET.SubElement(event, "expiresAt").text = _format_utc(event_expires)
    creative_url = (creative_url or f"https://example.com/creativos/{operator}/{code}.html").strip()
    parsed_url = urllib.parse.urlparse(creative_url)
    if parsed_url.scheme != "https" or parsed_url.hostname not in {"example.com", "example.org", "example.net"}:
        raise ValueError("creative_url must use an HTTPS example.com, example.org or example.net URL")
    ET.SubElement(event, "creativeUrl").text = creative_url
    return _translate_tree(root, to_spanish=True)


def write_feed(root: ET.Element, path: Path) -> None:
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, prefix=".feed-", suffix=".tmp", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write('<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        validation = validate_feed(temp_path)
        if not validation["valid"]:
            raise ValueError("XML validation failed: " + "; ".join(validation["errors"]))
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def validate_feed(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except (OSError, ET.ParseError) as exc:
        return {
            "valid": False,
            "errors": [f"xml_not_well_formed: {exc}"],
            "warnings": [],
            "events": 0,
            "trigger_active": False,
            "expired_now": None,
        }

    try:
        import xmlschema

        schema = xmlschema.XMLSchema(str(ROOT / "config" / "trigger_feed.xsd"))
        errors.extend(f"xsd: {error.reason}" for error in schema.iter_errors(root))
    except Exception as exc:
        errors.append(f"xsd_validation_unavailable: {exc}")

    if root.tag != "feedActivador":
        errors.append(f"root element must be feedActivador, got {root.tag}")
    else:
        _translate_tree(root, to_spanish=False)

    for attr in REQUIRED_FEED_ATTRS:
        if not root.get(attr):
            errors.append(f"missing required attribute: {attr}")

    if root.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("schemaVersion must be 1.0")

    system_status = root.get("systemStatus", "")
    if system_status not in SYSTEM_STATUSES:
        errors.append(f"invalid systemStatus: {system_status}")

    simulation_only = root.get("simulationOnly")
    if simulation_only is not None and simulation_only not in {"true", "false"}:
        errors.append(f"invalid simulationOnly: {simulation_only}")

    generated: datetime | None = None
    valid_until: datetime | None = None
    for attr in ("generatedAt", "validUntil"):
        raw = root.get(attr)
        if not raw:
            continue
        try:
            parsed = _parse_utc(raw)
        except ValueError as exc:
            errors.append(f"{attr}: {exc}")
            continue
        if attr == "generatedAt":
            generated = parsed
        else:
            valid_until = parsed

    if generated is not None and valid_until is not None and valid_until <= generated:
        errors.append("validUntil must be after generatedAt")
    if generated is not None and generated > datetime.now(timezone.utc) + timedelta(minutes=2):
        errors.append("generatedAt is too far in the future")

    events = root.findall("event")
    seen_ids: set[str] = set()
    trigger_active = False
    for index, event in enumerate(events, start=1):
        prefix = f"event[{index}]"
        event_id = event.get("id", "").strip()
        if not event_id:
            errors.append(f"{prefix}: missing id")
        elif event_id in seen_ids:
            errors.append(f"{prefix}: duplicate id {event_id}")
        seen_ids.add(event_id)

        values: dict[str, str] = {}
        for child in REQUIRED_EVENT_CHILDREN:
            node = event.find(child)
            if node is None or node.text is None or not node.text.strip():
                errors.append(f"{prefix}: missing {child}")
            else:
                values[child] = node.text.strip()

        if "operator" in values and values["operator"] not in OPERATORS:
            errors.append(f"{prefix}: invalid operator {values['operator']}")
        if "serviceType" in values and values["serviceType"] not in SERVICE_TYPES:
            errors.append(f"{prefix}: invalid serviceType {values['serviceType']}")
        if "incidentType" in values and values["incidentType"] not in INCIDENT_TYPES:
            errors.append(f"{prefix}: invalid incidentType {values['incidentType']}")
        if "state" in values and values["state"] not in STATES:
            errors.append(f"{prefix}: invalid state {values['state']}")
        if "geoPrecision" in values and values["geoPrecision"] not in GEO_PRECISIONS:
            errors.append(f"{prefix}: invalid geoPrecision {values['geoPrecision']}")
        if "trigger" in values:
            if values["trigger"] not in {"true", "false"}:
                errors.append(f"{prefix}: trigger must be true or false")
            elif values["trigger"] == "true":
                trigger_active = True
                if values.get("state") != "active":
                    errors.append(f"{prefix}: trigger=true requires state=active")
                if system_status != "ok":
                    errors.append(f"{prefix}: trigger=true requires systemStatus=ok")
                if simulation_only == "true":
                    errors.append(f"{prefix}: simulation cannot activate")

        _validate_geography(event, values, prefix, errors)

        district = event.find("district")
        if district is not None and (district.text is None or not district.text.strip()):
            errors.append(f"{prefix}: district must not be empty")

        creative_url = event.find("creativeUrl")
        if creative_url is not None:
            value = (creative_url.text or "").strip()
            if not value:
                errors.append(f"{prefix}: creativeUrl must not be empty")
            elif not value.startswith("https://"):
                errors.append(f"{prefix}: creativeUrl must start with https://")

        confidence = event.find("confidence")
        if confidence is not None and confidence.text is not None:
            try:
                number = float(confidence.text)
                if not 0.0 <= number <= 1.0:
                    errors.append(f"{prefix}: confidence must be within [0,1]")
            except ValueError:
                errors.append(f"{prefix}: confidence is not numeric")

        started: datetime | None = None
        expires: datetime | None = None
        for child in ("startedAt", "expiresAt"):
            if child not in values:
                continue
            try:
                parsed = _parse_utc(values[child])
            except ValueError as exc:
                errors.append(f"{prefix}: {child}: {exc}")
                continue
            if child == "startedAt":
                started = parsed
            else:
                expires = parsed
        if started is not None and expires is not None and expires <= started:
            errors.append(f"{prefix}: expiresAt must be after startedAt")
        if expires is not None and valid_until is not None and expires > valid_until:
            errors.append(f"{prefix}: expiresAt must not exceed validUntil")
        if started is not None and generated is not None and started > generated + timedelta(minutes=2):
            errors.append(f"{prefix}: startedAt is after generatedAt")
        if expires is not None and values.get("trigger") == "true" and expires <= datetime.now(timezone.utc):
            errors.append(f"{prefix}: active event has expired")

    if system_status != "ok" and trigger_active:
        errors.append("trigger=true is not allowed when systemStatus is not ok")

    now = datetime.now(timezone.utc)
    expired_now = valid_until <= now if valid_until is not None else None
    if expired_now:
        warnings.append("document_expired_relative_to_now")
        if trigger_active:
            errors.append("active feed has expired")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "events": len(events),
        "trigger_active": trigger_active,
        "expired_now": expired_now,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render/validate the local creative-trigger simulation using the XML output contract"
    )
    parser.add_argument("--demo", action="store_true", help="run the synthetic simulator and write the XML feed")
    parser.add_argument("--validate", metavar="PATH", help="validate an existing XML feed")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="XML output path for --demo")
    args = parser.parse_args()

    if args.validate:
        output = Path(args.validate)
        result = validate_feed(output)
        result["path"] = str(output)
    elif args.demo:
        simulation = run_demo()
        decision = select_demo_decision(simulation)
        now = datetime.now(timezone.utc)
        decision["decision_at"] = _format_utc(now)
        decision["expires_at"] = _format_utc(now + timedelta(minutes=10))
        decision["scope"]["first_observed_at"] = _format_utc(now - timedelta(minutes=2))
        decision["scope"]["last_observed_at"] = _format_utc(now - timedelta(minutes=1))
        root = build_feed(decision, state="candidate", incident_type="degradation", simulation_only=True)
        output = Path(args.output)
        write_feed(root, output)
        result = validate_feed(output)
        result["path"] = str(output)
        result["simulation"] = {
            "status": decision["status"],
            "hysteresis": simulation["hysteresis"],
            "real_source_data_used": simulation["real_source_data_used"],
        }
    else:
        parser.error("Use --demo or --validate PATH")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
