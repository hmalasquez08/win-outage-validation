# Informe de validación técnica

**Alcance del proyecto:** detectar afectaciones de conectividad a internet de operadores peruanos (internet fijo o móvil cuando la afectación sea de internet) para el negocio de Win, que vende internet. No se evalúan cortes aislados de voz/SMS como señal de internet, y una cobertura declarada no equivale a disponibilidad actual.

Se archivaron y auditaron las respuestas de cierre. UBIGEO: SISCONCODE 2026 contiene 1,893 códigos únicos (incluye 120307 Sangani); la capa distrital INEI 2023 contiene 1,890 geometrías, faltan 120307, 130112 y 160405. geoBoundaries ADM1/ADM2 se cotejó solo por nombres. Los feeds de cinco medios respondieron en siete endpoints, sin coincidencias con la regla estricta en las capturas. Las nueve identidades oficiales se verificaron y consultaron. Radar y TwexAPI autenticaron y respondieron.

Se documentaron 9 casos; 8 tienen inicio horario utilizable y forman 15 pares positivos por operador. IODA registró un inicio en 1/15 pares: AS6147, dos minutos después de la hora de detección OSIPTEL para una caída de internet fijo Movistar. Radar anotaciones: 0/15 coincidencias. NetFlows fue menor que el comparador semanal en 9/15 medianas normalizadas, y en 6/8 pares OSIPTEL que incluyen internet fijo. Es un replay retrospectivo, el comparador no está verificado como normal y las series no identifican producto ni distrito; no representa latencia operacional. Sin negativos etiquetados ni umbral fijo no se estiman falsos positivos, precisión/recall general ni valor incremental. No hay fuentes `APPROVED`; las señales auxiliares de voz/SMS se clasifican como corroboración, nunca evidencia suficiente por sí sola de caída de internet; cobertura declarada es solo contexto.

Consultar `final_decisions.md`, `incident_validation.md`, `inei_ubigeo_validation.md`, `peru_news_relevance.csv`, `x_peru_signal_quality.md`, `operator_fixed_mobile_coverage.csv`, `architecture_compliance.md` y `evidencias/manifest.jsonl`.


## Cierre complementario: respuestas, prensa y límites oficiales

Se consultaron respuestas dirigidas a Movistar, Claro, Entel, Bitel y OSIPTEL, además de respuestas publicadas por OSIPTEL: seis solicitudes, todas HTTP 200; hubo tres respuestas con contexto de interrupción y ninguna con los tres componentes operador, distrito y servicio. Ocho feeds nacionales adicionales fueron consultados directamente; tres endpoints devolvieron XML, pero solo corresponden a dos feeds distintos (Perú21 duplicado y Gestión Tecnología), sin coincidencias estrictas. No se descargaron páginas de artículos.

El WFS oficial distrital del INEI permitió cotejar topología para las 1.890 geometrías disponibles: 0 inválidas, 0 solapes positivos, 5.326 pares de bordes compartidos y ningún par de hueco candidato en tolerancia 1e-8 grados. Quedan dos polígonos sin vecino y los códigos 120307, 130112 y 160405 sin geometría en esa capa; seis nombres distritales difieren del catálogo. El WFS refleja la cobertura/vintage disponible, no una geometría distrital 2026 completa. Reportes: `official_boundary_continuity_validation.md/.json`, `x_reply_search_summary.md/.csv` y `peru_major_newspaper_feeds.md/.csv`.

## Corrección de validación de conversaciones en X

La consulta a la pestaña Respuestas de las cuatro cuentas respondió HTTP 200. El primer parser no interpretó la lista `data[]` del endpoint de mensajes padre; la relectura corregida obtuvo 177/183 posts padre. En contextos de soporte de Claro, 2 autores distintos de 46 reportaron explícitamente problemas de internet, en horas diferentes y sin distrito. En una modalidad separada, tres hilos oficiales de Claro contuvieron 8 publicaciones de queja entre 43 respuestas de clientes y dos menciones distritales, una ambigua. No se suman ambas muestras. X queda como candidata a corroboración agregada por operador × zona × tiempo, no como detector ni targeting individual; el aporte incremental todavía no está medido. Ver `x_operator_replies_parent_context.md`, `x_operator_replies_tab_validation.md` y `x_thread_replies_validation.md`.

## Replay retrospectivo del detector

Se ejecutó el replay por fuente sobre los 15 pares positivos de 8 casos. NetFlows generó un candidato direccional en 9/15; IODA detectó un inicio en 1/15 y anotaciones Radar, 0/15. X se buscó en 15 positivos y 17 controles: dos autores con queja explícita en positivos y cero controles, pero ningún cluster con ≥2 autores del mismo distrito en 15 minutos. OR de todas las señales con regla geográfica X: 9/15; exigir dos familias: 1/15. En dos pares explícitamente móviles, NetFlows marca 0; en dos pares solo fijo marca 1; no se puede separar producto en los 11 pares mixtos. No hay ventanas normales independientes, por lo que no se estiman falsas alarmas generales, precisión o frescura operacional. RSS y voz/SMS no tienen capturas históricas alineadas. Ver `historical_detector_replay.md/.csv/.json` y `x_historical_incident_replay.md`.


## Diagnóstico final de incidencias y geografía

En las referencias comparables, IODA registró 1/15 inicios positivos. Un evento distinto se solapó con Áncash pero había empezado aproximadamente seis días antes. No se estima FPR general. Los 9 casos cubren cuatro operadores; el impacto fijo es explícito en 7 y móvil en 7. La coincidencia de dos minutos es una diferencia entre marcas retrospectivas, no latencia del detector.

Los dos polígonos sin vecino corresponden a los distritos insulares Anapia y Amantaní. Para Alto Trujillo se creó un parche candidato a partir de cuatro tramos PCM; conserva cobertura y no genera solapes. Sangani y Santa Rosa de Loreto siguen sin vector completo en los servicios oficiales consultados. Ver `ioda_diagnostic_metrics.json`, `incident_attribution_coverage.md` y `official_boundary_continuity_validation.md`.
