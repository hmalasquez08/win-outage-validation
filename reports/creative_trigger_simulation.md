# Simulador local de decisión para creatividades

Este artefacto demuestra la lógica de decisión y el formato de salida con escenarios sintéticos. No ingiere datos reales, no detecta cortes, no llama servicios externos y no activa publicidad.

## Reglas de admisión

- Exige una señal directa de degradación o interrupción de internet; quejas, voz/SMS, ruteo o cobertura declarada no bastan por sí solos.
- Exige corroboración de una familia independiente para elevar el caso a listo para simulación.
- Solo agrupa evidencia del mismo operador y la misma zona administrativa peruana verificada. No convierte ASN o país en distrito.
- Descarta señales con error, más antiguas de 30 minutos o con reloj adelantado por más de dos minutos.
- Conserva la tecnología como `internet_unspecified` cuando la fuente no distingue fijo/móvil.
- Requiere dos snapshots consecutivos para entrar y dos snapshots válidos que confirmen ausencia de incidente para recuperarse. Si faltan datos o vencen las señales, caduca inmediatamente; cada señal tiene vencimiento propio.

## Resultados de escenarios sintéticos

| Escenario | Decisión | Motivo |
|---|---|---|
| direct_plus_independent_same_zone | QUALIFIED_FOR_SIMULATED_CREATIVE | — |
| complaints_without_internet_signal | SUPPRESSED | missing_fresh_direct_internet_signal |
| direct_only | CANDIDATE_ONLY | no_independent_same_operator_zone_time_corroboration |
| same_provider_products_do_not_corroborate | CANDIDATE_ONLY | no_independent_same_operator_zone_time_corroboration |
| other_operator_complaints_do_not_corroborate | CANDIDATE_ONLY | no_independent_same_operator_zone_time_corroboration |
| unverified_geography | SUPPRESSED | direct_signal_has_no_verified_actionable_geography |
| stale_evidence | SUPPRESSED | missing_fresh_direct_internet_signal |
| source_error | SUPPRESSED | missing_fresh_direct_internet_signal |

**Histéresis:** activación ['PENDING_ACTIVATION', 'ACTIVE']; el mismo snapshot repetido ['PENDING_ACTIVATION', 'PENDING_ACTIVATION']; recuperación ['PENDING_RECOVERY', 'RECOVERED'].

## Límite de la demostración

El simulador demuestra que la tubería de decisión puede producir un payload gobernado por reglas y fail-closed. No demuestra que las fuentes actuales produzcan evidencia suficientemente local, fresca o precisa. El replay histórico v4 sigue siendo experimental: 8/15 pares positivos y 2/17 controles emparejados con HERMES; al retirar HERMES, 7/15 y 1/17. LOIO se informa por separado en el replay. Por eso el simulador no declara eventos reales listos para activación.
La evaluación con evidencia real del candidato regional más reciente está separada en `reports/creative_activation_readiness.md/.json`: Movistar-Ica pasó la regla de persistencia de NetFlows, pero el motor lo suprimió por desfase y geografía no verificada; no se produjo activación.

## Contrato lógico de salida

El JSON incluye estado, operador, tecnología, geografía verificada, familias/IDs de evidencia, hora de decisión y expiración. El mapeo a identificadores y campos aceptados por el destino se define en la fase de conexión, que se mantiene para el final.

Reproducir: `python -m win_validation.creative_trigger --demo`. Salida: `reports/creative_trigger_simulation.json`.
