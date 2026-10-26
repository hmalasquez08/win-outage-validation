"""Local acceptance checks for the evidence and report bundle."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


REQUIRED_REPORTS = (
    "final_decisions.md", "approved_sources.json", "rejected_sources.md",
    "conditional_sources.md", "insufficient_evidence.md", "x_final_account_decisions.csv",
    "decision_sensitivity.md", "blueprint_input.json", "retry_history.csv",
    "revalidation_queue.json", "low_density_analysis.md", "retry_policy_compliance.md",
    "architecture_compliance.md", "globalping_probe_attribution.md", "atlas_public_measurement_review.md",
    "atlas_measurement_inventory_detailed.csv", "atlas_latest_results.csv", "inei_ubigeo_validation.md",
    "geography_geometry_check.md",
)

def _validate_schema(instance, schema: dict, location: str="$") -> list[str]:
    errors=[]; expected=schema.get("type")
    type_map={"object":dict,"array":list,"string":str,"integer":int,"number":(int,float),"boolean":bool,"null":type(None)}
    if expected in type_map and (not isinstance(instance,type_map[expected]) or (expected=="integer" and isinstance(instance,bool))):
        return [f"{location}:expected_{expected}"]
    if isinstance(instance,dict):
        for key in schema.get("required",[]):
            if key not in instance: errors.append(f"{location}:missing_{key}")
        properties=schema.get("properties",{})
        for key,value in instance.items():
            if key in properties: errors.extend(_validate_schema(value,properties[key],f"{location}.{key}"))
            elif schema.get("additionalProperties") is False: errors.append(f"{location}:unexpected_{key}")
    if isinstance(instance,list) and "items" in schema:
        for index,value in enumerate(instance): errors.extend(_validate_schema(value,schema["items"],f"{location}[{index}]"))
    if isinstance(instance,str) and len(instance)<schema.get("minLength",0): errors.append(f"{location}:min_length")
    if "enum" in schema and instance not in schema["enum"]: errors.append(f"{location}:not_in_enum")
    return errors


def audit(root: Path) -> dict:
    evidence_root = root / "evidencias"
    report_root = root / "reports"
    manifest_path = evidence_root / "manifest.jsonl"
    records, errors = [], []
    if not manifest_path.is_file():
        errors.append("missing_manifest")
    else:
        for line_number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                artifact = (root / row["artifact_path"]).resolve()
                if root.resolve() not in artifact.parents:
                    errors.append(f"manifest_path_outside_root:{line_number}")
                    continue
                if not artifact.is_file():
                    errors.append(f"missing_artifact:{line_number}:{row.get('evidence_id','unknown')}")
                    continue
                digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
                if digest != row.get("sha256"):
                    errors.append(f"hash_mismatch:{line_number}:{row.get('evidence_id','unknown')}")
                records.append(row)
            except Exception as exc:
                errors.append(f"invalid_manifest_line:{line_number}:{type(exc).__name__}")

    missing_reports = [name for name in REQUIRED_REPORTS if not (report_root / name).is_file()]
    if missing_reports:
        errors.extend(f"missing_report:{name}" for name in missing_reports)
    json_checks = {}
    for name in ("approved_sources.json", "blueprint_input.json", "revalidation_queue.json"):
        try:
            json_checks[name] = json.loads((report_root / name).read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid_json_report:{name}:{type(exc).__name__}")
    approved = json_checks.get("approved_sources.json")
    if isinstance(approved, list) and approved:
        errors.append("approved_sources_not_empty_requires_manual_review")
    blueprint = json_checks.get("blueprint_input.json", {})
    if isinstance(blueprint, dict) and blueprint.get("approved_sources"):
        errors.append("blueprint_contains_unapproved_sources")
    schema_errors=[]
    for filename,instance in (("approved_sources.schema.json",approved),("blueprint_input.schema.json",blueprint)):
        try:
            schema=json.loads((root/"config"/filename).read_text(encoding="utf-8"))
            schema_errors.extend(_validate_schema(instance,schema,f"{filename}:instance"))
        except Exception as exc:
            schema_errors.append(f"{filename}:schema_load_error:{type(exc).__name__}")
    errors.extend(f"schema_validation:{item}" for item in schema_errors)
    manifest_ids={row.get("evidence_id") for row in records}
    for source in approved if isinstance(approved,list) else []:
        for evidence_id in source.get("evidence_ids",[]):
            if evidence_id not in manifest_ids: errors.append(f"approved_source_missing_evidence:{source.get('source_id')}:{evidence_id}")
        for artifact_path in source.get("artifact_paths",[]):
            target=(root/artifact_path).resolve()
            if root.resolve() not in target.parents or not target.is_file():
                errors.append(f"approved_source_missing_artifact:{source.get('source_id')}:{artifact_path}")
    if isinstance(blueprint,dict) and isinstance(approved,list):
        approved_ids={row.get("source_id") for row in approved if isinstance(row,dict)}
        if any(source_id not in approved_ids for source_id in blueprint.get("approved_sources",[])):
            errors.append("blueprint_references_source_not_in_approved_sources")
    report_reference_errors=[]
    evidence_id_pattern=re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*-[0-9a-f]{12}(?![A-Za-z0-9_-])")
    uuid_pattern=re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$",re.I)
    evidence_path_pattern=re.compile(r"(?:\.\./)?evidencias/[^\s`\"'),;]+")
    for report in report_root.rglob("*"):
        if not report.is_file() or report.name == "evidence_integrity.json": continue
        content=report.read_text(encoding="utf-8",errors="ignore")
        for evidence_id in set(evidence_id_pattern.findall(content)):
            if uuid_pattern.fullmatch(evidence_id): continue
            if evidence_id not in manifest_ids:
                report_reference_errors.append(f"{report.relative_to(root).as_posix()}:unknown_evidence_id:{evidence_id}")
        for value in set(evidence_path_pattern.findall(content)):
            candidate=(report.parent/value).resolve() if value.startswith("../") else (root/value).resolve()
            if root.resolve() not in candidate.parents and candidate != root.resolve():
                report_reference_errors.append(f"{report.relative_to(root).as_posix()}:evidence_path_outside_root:{value}")
            elif not candidate.exists():
                report_reference_errors.append(f"{report.relative_to(root).as_posix()}:missing_evidence_path:{value}")
    errors.extend(f"report_reference:{item}" for item in report_reference_errors)

    # Scan only generated evidence/reports, never .env or other credential stores.
    secret_patterns = [re.compile(p, re.I) for p in (
        r"(?:CLOUDFLARE_API_TOKEN|TWEXAPI_API_KEY)\s*[=:]\s*[^\s\"']+",
        r"Bearer\s+[A-Za-z0-9._~-]{20,}",
        r"(?:api[_-]?key|access[_-]?token)\s*[=:]\s*[A-Za-z0-9._~-]{20,}",
    )]
    secret_hits = []
    for folder in (evidence_root, report_root):
        for path in folder.rglob("*"):
            if path.is_file() and path.name != "manifest.jsonl":
                try:
                    value = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                # Claro's official public site embeds a UUID-shaped frontend API
                # identifier in its HTML. It is not one of this project's secrets;
                # allow only that exact public-site field/location while scanning
                # all other content with the normal credential patterns.
                relative = path.relative_to(root).as_posix().casefold()
                if relative.startswith("evidencias/api_responses/official_link_claro_per"):
                    value = re.sub(r"(?i)apikey=[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "apikey=[PUBLIC_SITE_UUID]", value)
                if any(pattern.search(value) for pattern in secret_patterns):
                    secret_hits.append(path.relative_to(root).as_posix())
    if secret_hits:
        errors.extend(f"possible_secret_in_output:{name}" for name in sorted(set(secret_hits)))
    return {
        "manifest_records": len(records), "integrity_errors": errors,
        "missing_reports": missing_reports, "secret_scan_files": "evidencias/ and reports/ only; .env was not read",
        "secret_scan_hits": sorted(set(secret_hits)),
        "schema_validation_errors": schema_errors,
        "report_reference_errors": report_reference_errors,
        "approved_sources_count": len(approved) if isinstance(approved, list) else None,
        "blueprint_approved_sources_count": len(blueprint.get("approved_sources", [])) if isinstance(blueprint, dict) else None,
    }
