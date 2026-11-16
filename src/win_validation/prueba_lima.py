"""One manual, real-data snapshot for all monitored operators in Lima."""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .live_runner import ASNS, ROOT, run
from .news import collect_news_snapshot
from .social import ApifyBudget, NEWS_ACCOUNTS, collect_social_evidence
from .trigger_feed_xml import build_empty_feed, validate_feed, write_feed


def _log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


def _utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp without timezone")
    return result.astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Consulta manual real de los cuatro operadores para el departamento de Lima")
    parser.add_argument("--presupuesto-apify-usd", default="5.00", help="Límite total conservador de cargos de actores (por defecto: 5 USD)")
    parser.add_argument("--max-posts", type=int, default=3, help="Publicaciones por cuenta y plataforma (por defecto: 3)")
    parser.add_argument("--max-comments", type=int, default=10, help="Comentarios o respuestas por publicación (por defecto: 10)")
    parser.add_argument("--confirmar", action="store_true", help="Permite activador=true en eventos calificados; por defecto solo candidatos")
    parser.add_argument("--output", default=str(ROOT / "xml" / "trigger_feed_live.xml"), help="Ruta del XML consolidado (por defecto: xml/trigger_feed_live.xml)")
    args = parser.parse_args()
    try:
        budget = ApifyBudget(args.presupuesto_apify_usd)
    except ValueError as exc:
        parser.error(str(exc))
    if args.max_posts < 1 or args.max_comments < 1:
        parser.error("--max-posts y --max-comments deben ser positivos")
    output = Path(args.output)
    _log("Inicio de consulta REAL y manual: Lima; Movistar, Claro, Entel y Bitel")
    _log(f"Tope reservado para cargos de actores Apify: US$ {budget.limit}")
    try:
        write_feed(build_empty_feed(datetime.now(timezone.utc), system_status="degraded"), output)
    except Exception as exc:
        _log(f"No se pudo preparar el XML de salida: {exc}")
        raise SystemExit(1) from exc

    operators = list(ASNS)
    accounts = [*operators, "osiptel", *sorted(NEWS_ACCOUNTS)]
    _log("Consultando redes sociales reales: X mediante TWEXAPI y las demás mediante Apify")
    try:
        social = collect_social_evidence(
            operators=accounts, max_posts=args.max_posts, max_comments=args.max_comments, timeout=90,
            budget=budget, progress=_log,
        )
    except Exception as exc:
        social = {"status": "ERROR", "error": str(exc), "candidates_report": None}
        _log(f"Consulta social incompleta: {exc}")
    _log(f"Redes sociales: {social.get('status')}; presupuesto reservado US$ {budget.reserved}")

    partial = social.get("status") != "COMPLETE"
    news_snapshot = None
    try:
        _log("Consultando noticias RSS una sola vez para los cuatro operadores")
        news_snapshot = collect_news_snapshot()
        news_summary = news_snapshot["summary"]
        _log(f"RSS: {news_summary.get('status')}; feeds OK {news_summary.get('feeds_http_200_xml')}/{news_summary.get('configured_feeds')}")
    except Exception as exc:
        partial = True
        _log(f"Consulta RSS incompleta: {exc}")

    results: dict[str, Any] = {}
    events: list[ET.Element] = []
    for index, operator in enumerate(operators, start=1):
        _log(f"[{index}/{len(operators)}] {operator.upper()}: iniciando consultas")
        try:
            result = run(
                operator, "Lima", use_news=True, use_social=True, use_osiptel_news=True,
                social_summary=social, news_snapshot=news_snapshot, confirm=args.confirmar, write_feed=False,
                progress=lambda message, name=operator: _log(f"{name}: {message}"),
            )
            feed_root = result.pop("feed_root", None)
            results[operator] = result
            if result.get("status") in {"ERROR", "FEED_INVALID", "AUTH_BLOCKED_NO_CREDENTIAL", "GEOGRAPHY_NOT_RESOLVED"}:
                partial = True
            if result.get("feed_system_status") != "ok":
                partial = True
            news = result.get("news") or {}
            if (news.get("summary") or {}).get("status") != "COMPLETE":
                partial = True
            osiptel = result.get("osiptel_news") or {}
            if osiptel.get("status") != "PARSED":
                partial = True
            if feed_root is not None:
                events.extend(feed_root.findall("evento"))
            _log(f"{operator}: resultado {result.get('status')}; decisión {(result.get('decision') or {}).get('status', 'sin decisión')}")
        except Exception as exc:
            partial = True
            results[operator] = {"status": "ERROR", "error": str(exc)}
            _log(f"{operator}: error {exc}")

    now = datetime.now(timezone.utc)
    current = []
    for event in events:
        try:
            if _utc(event.findtext("expiraEn", "")) > now:
                current.append(event)
            else:
                partial = True
                _log(f"Evento {event.get('id')} venció durante la consulta y fue omitido")
        except ValueError:
            partial = True
            _log(f"Evento {event.get('id')} sin vencimiento válido; omitido")

    root = build_empty_feed(now, system_status="degraded" if partial else "ok")
    if current:
        cutoff = min(_utc(event.findtext("expiraEn", "")) for event in current)
        valid_events = []
        for event in current:
            if _utc(event.findtext("iniciadoEn", "")) >= cutoff:
                partial = True
                _log(f"Evento {event.get('id')} fuera de la ventana consolidada; omitido")
            else:
                valid_events.append(event)
        if partial:
            root.set("estadoSistema", "degradado")
        root.set("validoHasta", cutoff.isoformat().replace("+00:00", "Z"))
        for event in valid_events:
            event.find("expiraEn").text = cutoff.isoformat().replace("+00:00", "Z")
            if partial:
                event.find("estado").text = "candidato"
                event.find("activador").text = "false"
            root.append(event)
    try:
        write_feed(root, output)
        validation = validate_feed(output)
    except Exception as exc:
        _log(f"No se pudo publicar el XML consolidado: {exc}")
        raise SystemExit(1) from exc

    report_dir = ROOT / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "prueba_lima_latest.json"
    report_path.write_text(json.dumps({
        "tipo": "consulta_real_manual", "departamento": "Lima", "parcial": partial,
        "presupuesto_apify_usd": str(budget.limit), "reservado_apify_usd": str(budget.reserved),
        "social": social, "operadores": results, "xml": str(output), "xml_validation": validation,
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    _log(f"XML: {output}; eventos vigentes: {len(root.findall('evento'))}; estado: {'PARCIAL' if partial else 'COMPLETO'}")
    _log(f"Detalle: {report_path}")
    print(output.read_text(encoding="utf-8"))
    if not validation.get("valid"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
