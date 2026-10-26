"""Local, fail-closed creative-trigger simulator (no external integrations).

The simulator accepts already-normalized signals. It is deliberately not a
collector and does not claim that the current historical sources are launch
ready. Its purpose is to exercise the decision/state/output path before any
connection to an advertising system is attempted.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
REPORTS = ROOT / "reports"
OPERATORS = {"movistar", "claro", "entel", "bitel"}
DIRECT_INTERNET_KINDS = {"internet_outage", "internet_degradation"}
SUPPORTING_KINDS = {"internet_complaints", "voice_sms", "routing_anomaly"}
MAX_SIGNAL_AGE = timedelta(minutes=30)
MAX_FUTURE_SKEW = timedelta(minutes=2)


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp must include a timezone: {value}")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class Signal:
    signal_id: str
    family: str
    kind: str
    operator: str
    technology: str
    observed_at: datetime
    source_status: str
    geography: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Signal":
        required = {"signal_id", "family", "kind", "operator", "technology", "observed_at", "source_status", "geography"}
        missing = required - data.keys()
        if missing:
            raise ValueError("Missing signal fields: " + ", ".join(sorted(missing)))
        return cls(
            signal_id=str(data["signal_id"]), family=str(data["family"]).strip().casefold(),
            kind=str(data["kind"]).strip().casefold(), operator=str(data["operator"]).strip().casefold(),
            technology=str(data["technology"]).strip().casefold(), observed_at=parse_time(str(data["observed_at"])),
            source_status=str(data["source_status"]).strip().casefold(), geography=dict(data["geography"]),
        )


def _zone_key(geography: dict[str, Any]) -> tuple[str, str, str] | None:
    if geography.get("verified") is not True:
        return None
    level = str(geography.get("level", "")).casefold()
    code = str(geography.get("code", "")).strip()
    country = str(geography.get("country", "")).upper()
    if country != "PE" or level not in {"district", "province", "department"} or not code:
        return None
    return country, level, code


def assess(signals_data: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    """Assess one operator-zone snapshot and return a safe, auditable decision."""
    signals = [Signal.from_dict(row) for row in signals_data]
    problems: list[str] = []
    eligible: list[Signal] = []
    for signal in signals:
        age = now - signal.observed_at
        if signal.source_status != "ok":
            continue
        if age > MAX_SIGNAL_AGE or age < -MAX_FUTURE_SKEW:
            continue
        eligible.append(signal)

    direct = [s for s in eligible if s.kind in DIRECT_INTERNET_KINDS and s.operator in OPERATORS]
    if not direct:
        problems.append("missing_fresh_direct_internet_signal")
        return _decision("SUPPRESSED", problems, [], None, now)

    # Do not combine different operators or infer a zone from an ASN, centroid,
    # country-only response, or unverified address.
    supported_direct = [(s, _zone_key(s.geography)) for s in direct]
    supported_direct = [(s, zone) for s, zone in supported_direct if zone]
    if not supported_direct:
        problems.append("direct_signal_has_no_verified_actionable_geography")
        return _decision("SUPPRESSED", problems, direct, None, now)

    # Evaluate one exact operator + technology + verified geographic segment at a time.
    groups: dict[tuple[str, str, tuple[str, str, str]], list[Signal]] = {}
    for signal, zone in supported_direct:
        key = (signal.operator, signal.technology, zone)
        groups.setdefault(key, []).append(signal)

    candidates: list[dict[str, Any]] = []
    for (operator, technology, zone), direct_group in groups.items():
        direct_families = {s.family for s in direct_group}
        matching_support = [
            s for s in eligible
            if s.operator == operator and s.kind in SUPPORTING_KINDS
            and _zone_key(s.geography) == zone
            and s.family not in direct_families
            and abs((max(x.observed_at for x in direct_group) - s.observed_at)) <= MAX_SIGNAL_AGE
        ]
        independent_families = sorted({s.family for s in matching_support})
        # Multiple products from the same provider are still one family.
        if not independent_families:
            continue
        candidates.append({
            "operator": operator,
            "technology": technology if technology in {"fixed", "mobile"} else "internet_unspecified",
            "geography": {"country": zone[0], "level": zone[1], "code": zone[2]},
            "direct_signal_ids": sorted({s.signal_id for s in direct_group}),
            "corroborating_signal_ids": sorted({s.signal_id for s in matching_support}),
            "evidence_families": sorted(direct_families | set(independent_families)),
            "first_observed_at": min(s.observed_at for s in direct_group).isoformat().replace("+00:00", "Z"),
            "last_observed_at": max([s.observed_at for s in direct_group + matching_support]).isoformat().replace("+00:00", "Z"),
        })

    if not candidates:
        problems.append("no_independent_same_operator_zone_time_corroboration")
        return _decision("CANDIDATE_ONLY", problems, eligible, None, now)
    if len(candidates) > 1:
        # One event payload must not merge distinct operator/service/geographic scopes.
        problems.append("multiple_scopes_require_separate_events")
        return _decision("CANDIDATE_ONLY", problems, eligible, candidates, now)
    return _decision("QUALIFIED_FOR_SIMULATED_CREATIVE", [], eligible, candidates[0], now)


def _decision(status: str, problems: list[str], signals: list[Signal], scope: Any, now: datetime) -> dict[str, Any]:
    observed = [s.observed_at for s in signals]
    expires = min((t + MAX_SIGNAL_AGE for t in observed), default=now)
    return {
        "schema_version": "win-creative-trigger-simulation-v1",
        "status": status,
        "simulation_only": True,
        "decision_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "scope": scope,
        "reasons": problems,
        "policy": {
            "requires_direct_internet_evidence": True,
            "requires_independent_corroboration": True,
            "requires_verified_peru_geography": True,
            "max_signal_age_minutes": int(MAX_SIGNAL_AGE.total_seconds() / 60),
            "voice_sms_or_complaints_alone_can_trigger": False,
            "declared_coverage_can_trigger": False,
        },
    }


class TriggerState:
    """Two-snapshot entry/clear hysteresis and strict expiry for local replay."""

    def __init__(self, confirmations: int = 2, clears: int = 2) -> None:
        self.confirmations = confirmations
        self.clears = clears
        self.state = "INACTIVE"
        self._positive = 0
        self._clear = 0
        self._scope_key: str | None = None
        self._last_positive_snapshot: str | None = None
        self._last_clear_snapshot: str | None = None
        self._required_families: set[str] = set()

    def step(self, decision: dict[str, Any], now: datetime, *, healthy_snapshot: dict[str, Any] | None = None) -> str:
        qualified = decision.get("status") == "QUALIFIED_FOR_SIMULATED_CREATIVE"
        scope = decision.get("scope") or {}
        scope_key = json.dumps({"operator": scope.get("operator"), "technology": scope.get("technology"), "geography": scope.get("geography")}, sort_keys=True, ensure_ascii=False)
        expires = parse_time(decision["expires_at"])
        if qualified and now < expires:
            evidence_key = json.dumps({
                "scope": decision.get("scope"),
                "direct": decision.get("scope", {}).get("direct_signal_ids", []),
                "support": decision.get("scope", {}).get("corroborating_signal_ids", []),
                "last_observed_at": decision.get("scope", {}).get("last_observed_at"),
            }, sort_keys=True, ensure_ascii=False)
            fingerprint = evidence_key
            if fingerprint == self._last_positive_snapshot:
                # Retrying the same source snapshot must not satisfy hysteresis.
                return self.state
            self._last_positive_snapshot = fingerprint
            self._last_clear_snapshot = None
            if self._scope_key not in (None, scope_key):
                self._positive = 0
                self._clear = 0
                self.state = "INACTIVE"
            self._scope_key = scope_key
            self._required_families = set(scope.get("evidence_families", []))
            self._positive += 1
            self._clear = 0
            self.state = "ACTIVE" if self._positive >= self.confirmations else "PENDING_ACTIVATION"
            return self.state

        self._positive = 0
        health_is_valid = self._valid_health_snapshot(healthy_snapshot, now)
        if self.state in {"ACTIVE", "PENDING_RECOVERY"} and health_is_valid:
            clear_fingerprint = str(healthy_snapshot["snapshot_id"])
            if clear_fingerprint == self._last_clear_snapshot:
                return self.state
            self._last_clear_snapshot = clear_fingerprint
            self._clear += 1
            if self._clear >= self.clears:
                self.state = "RECOVERED"
                self._scope_key = None
                self._clear = 0
                self._last_positive_snapshot = None
                self._last_clear_snapshot = None
                self._required_families.clear()
            else:
                self.state = "PENDING_RECOVERY"
        elif self.state in {"ACTIVE", "PENDING_RECOVERY"} and now >= expires:
            # Stale/missing data must never keep an activation alive.
            self.state = "EXPIRED"
            self._scope_key = None
            self._clear = 0
            self._last_positive_snapshot = None
            self._last_clear_snapshot = None
            self._required_families.clear()
        elif self.state in {"ACTIVE", "PENDING_RECOVERY"}:
            # Unknown source state is not evidence of recovery. Fail closed.
            self.state = "EXPIRED"
            self._scope_key = None
            self._clear = 0
            self._last_positive_snapshot = None
            self._last_clear_snapshot = None
            self._required_families.clear()
        else:
            self.state = "INACTIVE"
        return self.state

    def _valid_health_snapshot(self, snapshot: dict[str, Any] | None, now: datetime) -> bool:
        if not snapshot or not snapshot.get("snapshot_id") or not self._required_families:
            return False
        try:
            checked_at = parse_time(str(snapshot["checked_at"]))
        except (KeyError, TypeError, ValueError):
            return False
        age = now - checked_at
        if age > MAX_SIGNAL_AGE or age < -MAX_FUTURE_SKEW:
            return False
        observations = snapshot.get("observations", [])
        healthy_families = {
            str(item.get("family", "")).casefold()
            for item in observations
            if item.get("status") == "ok" and item.get("incident_active") is False
        }
        return self._required_families <= healthy_families


def _sample(now: datetime, *, direct: bool = True, corroboration: bool = True, verified_geo: bool = True, fresh: bool = True, status: str = "ok", corroboration_family: str = "community_reports", corroboration_operator: str = "movistar") -> list[dict[str, Any]]:
    observed = now - (timedelta(minutes=5) if fresh else timedelta(hours=2))
    geo = {"country": "PE", "level": "district", "code": "150101", "verified": verified_geo}
    result = []
    if direct:
        result.append({"signal_id": "demo-netflow", "family": "cloudflare", "kind": "internet_degradation", "operator": "movistar", "technology": "unknown", "observed_at": observed.isoformat(), "source_status": status, "geography": geo})
    if corroboration:
        result.append({"signal_id": "demo-independent-internet-reports", "family": corroboration_family, "kind": "internet_complaints", "operator": corroboration_operator, "technology": "unknown", "observed_at": observed.isoformat(), "source_status": status, "geography": geo})
    return result


def run_demo() -> dict[str, Any]:
    now = datetime(2026, 10, 25, 16, 0, tzinfo=timezone.utc)
    cases = [
        ("direct_plus_independent_same_zone", _sample(now)),
        ("complaints_without_internet_signal", _sample(now, direct=False, corroboration=True)),
        ("direct_only", _sample(now, corroboration=False)),
        ("same_provider_products_do_not_corroborate", _sample(now, corroboration_family="cloudflare")),
        ("other_operator_complaints_do_not_corroborate", _sample(now, corroboration_operator="claro")),
        ("unverified_geography", _sample(now, verified_geo=False)),
        ("stale_evidence", _sample(now, fresh=False)),
        ("source_error", _sample(now, status="error")),
    ]
    outputs = [{"scenario": name, "decision": assess(signals, now)} for name, signals in cases]
    state = TriggerState()
    positive = assess(_sample(now), now)
    second_positive = assess(_sample(now + timedelta(minutes=5)), now + timedelta(minutes=5))
    activation = [state.step(positive, now), state.step(second_positive, now + timedelta(minutes=5))]
    duplicate_state = TriggerState()
    duplicate_snapshot = [duplicate_state.step(positive, now), duplicate_state.step(positive, now + timedelta(minutes=1))]
    healthy = assess([], now + timedelta(minutes=10))
    def healthy_check(snapshot_id: str, checked: datetime) -> dict[str, Any]:
        return {
            "snapshot_id": snapshot_id,
            "checked_at": checked.isoformat(),
            "observations": [
                {"family": "cloudflare", "status": "ok", "incident_active": False},
                {"family": "community_reports", "status": "ok", "incident_active": False},
            ],
        }
    recovery = [
        state.step(healthy, now + timedelta(minutes=10), healthy_snapshot=healthy_check("healthy-1", now + timedelta(minutes=10))),
        state.step(healthy, now + timedelta(minutes=15), healthy_snapshot=healthy_check("healthy-2", now + timedelta(minutes=15))),
    ]
    return {"simulator": "local-only-v1", "real_source_data_used": False, "scenarios": outputs, "hysteresis": {"activation": activation, "duplicate_snapshot": duplicate_snapshot, "recovery": recovery}}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local creative-trigger simulator; no external calls are made")
    parser.add_argument("--demo", action="store_true", help="generate deterministic synthetic scenarios and reports")
    args = parser.parse_args()
    if not args.demo:
        parser.error("Use --demo. This module does not ingest live or historical data.")
    result = run_demo()
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "creative_trigger_simulation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = []
    for item in result["scenarios"]:
        decision = item["decision"]
        rows.append(f"| {item['scenario']} | {decision['status']} | {'; '.join(decision['reasons']) or '—'} |")
    report = [
        "# Simulador local de decisión para creatividades", "",
        "Este artefacto demuestra la lógica de decisión y el formato de salida con escenarios sintéticos. No ingiere datos reales, no detecta cortes, no llama servicios externos y no activa publicidad.", "",
        "## Reglas de admisión", "",
        "- Exige una señal directa de degradación o interrupción de internet; quejas, voz/SMS, ruteo o cobertura declarada no bastan por sí solos.",
        "- Exige corroboración de una familia independiente para elevar el caso a listo para simulación.",
        "- Solo agrupa evidencia del mismo operador y la misma zona administrativa peruana verificada. No convierte ASN o país en distrito.",
        "- Descarta señales con error, más antiguas de 30 minutos o con reloj adelantado por más de dos minutos.",
        "- Conserva la tecnología como `internet_unspecified` cuando la fuente no distingue fijo/móvil.",
        "- Requiere dos snapshots consecutivos para entrar y dos snapshots válidos que confirmen ausencia de incidente para recuperarse. Si faltan datos o vencen las señales, caduca inmediatamente; cada señal tiene vencimiento propio.", "",
        "## Resultados de escenarios sintéticos", "",
        "| Escenario | Decisión | Motivo |", "|---|---|---|", *rows, "",
        f"**Histéresis:** activación {result['hysteresis']['activation']}; el mismo snapshot repetido {result['hysteresis']['duplicate_snapshot']}; recuperación {result['hysteresis']['recovery']}.", "",
        "## Límite de la demostración", "",
        "El simulador demuestra que la tubería de decisión puede producir un payload gobernado por reglas y fail-closed. No demuestra que las fuentes actuales produzcan evidencia suficientemente local, fresca o precisa. El replay histórico v4 sigue siendo experimental: 8/15 pares positivos y 2/17 controles emparejados con HERMES; al retirar HERMES, 7/15 y 1/17. LOIO se informa por separado en el replay. Por eso el simulador no declara eventos reales listos para activación.",
        "La evaluación con evidencia real del candidato regional más reciente está separada en `reports/creative_activation_readiness.md/.json`: Movistar-Ica pasó la regla de persistencia de NetFlows, pero el motor lo suprimió por desfase y geografía no verificada; no se produjo activación.", "",
        "## Contrato lógico de salida", "",
        "El JSON incluye estado, operador, tecnología, geografía verificada, familias/IDs de evidencia, hora de decisión y expiración. El mapeo a identificadores y campos aceptados por el destino se define en la fase de conexión, que se mantiene para el final.", "",
        "Reproducir: `python -m win_validation.creative_trigger --demo`. Salida: `reports/creative_trigger_simulation.json`.",
    ]
    (REPORTS / "creative_trigger_simulation.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"report": "reports/creative_trigger_simulation.md", "json": "reports/creative_trigger_simulation.json", "scenarios": len(result["scenarios"]), "hysteresis": result["hysteresis"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
