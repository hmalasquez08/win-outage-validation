# Replay histórico de respuestas en X por operador, zona y tiempo

Consulta observada 2026-10-25T07:51:24.336476+00:00. Incluye los cuatro operadores en ocho casos con ventana horaria y etiquetas positivas/NO_CONTROL; máximo tres páginas por operador-caso; ninguna consulta agotó el límite, y las que continuaron terminaron con página vacía.

## Regla social probada

Se marcó candidato geo-temporal si había ≥2 autores distintos con queja explícita de internet para el mismo operador, distrito inequívoco y bloque UTC de 15 minutos. También se midió sensibilidad a ≥3 autores. Quejas de voz/SMS se clasificaron aparte.

| Grupo | Pares | Pares con queja explícita | Autores quejándose | Pares con cluster distrito×15m ≥2 | ≥3 | Paginación limitada |
|---|---:|---:|---:|---:|---:|---:|
| Positivos | 15 | 2 | 2 | 0 | 0 | 0 |
| Controles declarados | 17 | 0 | 0 | 0 | 0 | 0 |

## Resultados por par

| Incidente | Operador | Etiqueta | Autores internet | Datos móviles | Voz/SMS solo | Pico autores mismo distrito×15m | ≥2 | ≥3 | No |
|---|---|---|---:|---:|---:|---:|---|---|---|
| movistar_entel_south_2022-10-25 | bitel | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| movistar_entel_south_2022-10-25 | claro | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| movistar_entel_south_2022-10-25 | entel | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |
| movistar_entel_south_2022-10-25 | movistar | POSITIVE | 1 | 0 | 0 | 1 | No | No | No |
| movistar_national_2024-11-18 | bitel | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| movistar_national_2024-11-18 | claro | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| movistar_national_2024-11-18 | entel | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| movistar_national_2024-11-18 | movistar | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |
| movistar_lima_fixed_2024-11-26 | bitel | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| movistar_lima_fixed_2024-11-26 | claro | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| movistar_lima_fixed_2024-11-26 | entel | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| movistar_lima_fixed_2024-11-26 | movistar | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |
| ancash_multioperator_2025-04-24 | bitel | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |
| ancash_multioperator_2025-04-24 | claro | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |
| ancash_multioperator_2025-04-24 | entel | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |
| ancash_multioperator_2025-04-24 | movistar | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |
| claro_los_olivos_2025-12-11 | bitel | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| claro_los_olivos_2025-12-11 | claro | POSITIVE | 1 | 0 | 0 | 0 | No | No | No |
| claro_los_olivos_2025-12-11 | entel | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| claro_los_olivos_2025-12-11 | movistar | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| loreto_shared_carrier_2025-12-19 | bitel | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |
| loreto_shared_carrier_2025-12-19 | claro | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |
| loreto_shared_carrier_2025-12-19 | entel | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |
| loreto_shared_carrier_2025-12-19 | movistar | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| ayacucho_integratel_entel_mobile_2025-12-26 | bitel | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| ayacucho_integratel_entel_mobile_2025-12-26 | claro | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| ayacucho_integratel_entel_mobile_2025-12-26 | entel | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |
| ayacucho_integratel_entel_mobile_2025-12-26 | movistar | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |
| movistar_lima_fiber_2026-07-01 | bitel | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| movistar_lima_fiber_2026-07-01 | claro | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| movistar_lima_fiber_2026-07-01 | entel | NO_CONTROL | 0 | 0 | 0 | 0 | No | No | No |
| movistar_lima_fiber_2026-07-01 | movistar | POSITIVE | 0 | 0 | 0 | 0 | No | No | No |

## Lectura

Una publicación individual no cumple la regla. Los conteos provienen solo de respuestas dirigidas a las cuentas oficiales y recuperadas en la ventana exacta. Los mensajes en controles no son automáticamente falsos positivos: pueden reflejar reclamos no confirmados o incidentes no etiquetados. Una coincidencia en un positivo es corroboración social, no verificación técnica de una caída.

Consultas: 40; errores HTTP/parseo: 0; pares que agotaron el límite de páginas: 0/32. Todas las búsquedas que devolvieron una continuación alcanzaron después una página vacía. Se guardaron solo metadatos de API y conteos agregados.

Entradas: `incident_reference_ioda_comparison.csv`; datos de salida: `x_historical_incident_replay.csv/.json` y `historical_detector_replay.csv`.
