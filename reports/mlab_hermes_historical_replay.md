# Replay histórico de M-Lab HERMES en incidentes peruanos

Consulta pública de solo lectura ejecutada el 2026-10-25T09:51:06.466580+00:00. Se cotejaron cinco referencias con ventanas UTC de tres días y umbral de consulta de 25 mediciones tanto para el día analizado como para la base. HERMES encontró coincidencia de operador y área en **2/5** casos; coincidencia en la fecha exacta en **2/5**. Se observaron 5 eventos de otros operadores objetivo en las áreas descritas por los casos; son señales sin correspondencia con la etiqueta disponible, no falsos positivos confirmados.

| Caso de referencia | Operadores objetivo | Filas HERMES en ASN objetivo | Coincidencias operador + área ±1 día | En fecha exacta | Eventos de otro operador en área |
|---|---|---:|---:|---:|---:|
| claro_los_olivos_2025-12-11 | claro | 5 | 1 | 1 | 2 |
| loreto_shared_carrier_2025-12-19 | claro, entel, bitel | 1 | 0 | 0 | 0 |
| ancash_multioperator_2025-04-24 | movistar, claro, entel, bitel | 0 | 0 | 0 | 0 |
| ayacucho_integratel_entel_mobile_2025-12-26 | movistar, entel | 19 | 0 | 0 | 0 |
| movistar_lima_fiber_2026-07-01 | movistar | 15 | 2 | 1 | 3 |

## Señales que sí coincidieron

| Referencia | Fecha HERMES | Operador | Área HERMES | Descenso mediano de descarga vs. base | Fracción de muestras anómalas | Clientes únicos | Nivel geográfico informado |
|---|---|---|---|---:|---:|---:|---|
| claro_los_olivos_2025-12-11 | 2025-12-11 | claro (AS12252) | Lima, Lima | 74.0% | 1.000 | 5 | maxmind_city / maxmind |
| movistar_lima_fiber_2026-07-01 | 2026-07-01 | movistar (AS6147) | Lima, Lima | 77.8% | 1.000 | 7 | maxmind_city / maxmind |
| movistar_lima_fiber_2026-07-01 | 2026-06-30 | movistar (AS6147) | Lima, Lima | 88.9% | 1.000 | 1 | maxmind_city / maxmind |

## Interpretación técnica

HERMES es un avance sustantivo frente al detector previo: usa pruebas NDT iniciadas por usuarios, agrupa por ASN y ciudad/metro y compara rendimiento contra la propia base del grupo. La documentación del servicio describe tests estadísticos sobre RTT y throughput y publicación diaria normalmente el día siguiente. En el incidente de Movistar Lima del 1 de julio de 2026, la vista pública devolvió una señal en Lima, AS6147, con descarga mediana 11.11 Mbps frente a 50.16 Mbps de base (−77.8%), fracción anómala 1.0 y siete clientes únicos. En el caso Claro de Los Olivos del 11 de diciembre de 2025, devolvió una fila Claro-Lima con caída de descarga y cinco clientes únicos; el nivel HERMES de esa fila no venía informado como `strong`.

La misma ventana del caso Claro mostró además una fila Movistar-Lima que no coincide con el operador afectado anunciado. Esto es una advertencia concreta de que el rendimiento observado en una muestra diaria puede activar otro operador; no prueba que el evento Movistar sea falso porque la referencia no es un registro completo de incidentes. HERMES tampoco detectó en esta consulta las referencias de Loreto, Áncash o Ayacucho bajo las áreas y ventanas usadas.

HERMES puede añadirse como **entrada técnica experimental de rendimiento** y completar a Cloudflare, no como detector aprobado. No demuestra cobertura homogénea, causalidad de operador, distrito, tecnología fija/móvil ni actualidad suficiente para alertar durante caídas de minutos. El nivel de área es la ciudad/metro estimada por IP, no UBIGEO. El conjunto evaluado es muy pequeño y escogido; sus proporciones no son métricas poblacionales.

## Cobertura, latencia y acceso observados

Las cinco respuestas JSON públicas del overview están indexadas en `evidencias/manifest.jsonl`; el detalle filtrado de las cuatro ASN está en `mlab_hermes_historical_replay.csv`. El overview se consultó sin credenciales. La documentación indica procesamiento diario y datos normalmente disponibles al día siguiente; la vista de detalle ejecuta consultas de BigQuery como la persona usuaria y requiere pertenencia al grupo M-Lab. El endpoint del dashboard no se presenta como contrato productivo estable.

| Referencia | HTTP | Evidence ID | Artefacto |
|---|---:|---|---|
| claro_los_olivos_2025-12-11 | 200 | `mlab_hermes_claro_los_olivos_2025-12-11-a0f6d9050318` | `evidencias/api_responses/mlab_hermes_claro_los_olivos_2025-12-11/20261025T095059.474515+0000.json` |
| loreto_shared_carrier_2025-12-19 | 200 | `mlab_hermes_loreto_shared_carrier_2025-12-19-a11227550249` | `evidencias/api_responses/mlab_hermes_loreto_shared_carrier_2025-12-19/20261025T095100.984805+0000.json` |
| ancash_multioperator_2025-04-24 | 200 | `mlab_hermes_ancash_multioperator_2025-04-24-41ceff4a03a7` | `evidencias/api_responses/mlab_hermes_ancash_multioperator_2025-04-24/20261025T095102.184547+0000.json` |
| ayacucho_integratel_entel_mobile_2025-12-26 | 200 | `mlab_hermes_ayacucho_integratel_entel_mobile_2025-12-26-059596143ef9` | `evidencias/api_responses/mlab_hermes_ayacucho_integratel_entel_mobile_2025-12-26/20261025T095103.359031+0000.json` |
| movistar_lima_fiber_2026-07-01 | 200 | `mlab_hermes_movistar_lima_fiber_2026-07-01-258acf4fbee9` | `evidencias/api_responses/mlab_hermes_movistar_lima_fiber_2026-07-01/20261025T095104.751613+0000.json` |

## Límites para el evento creativo

- This is a selected five-case retrospective replay, not an unbiased estimate of sensitivity, precision, or false-positive rate.
- A missing HERMES event can mean insufficient tests or coverage, not a healthy network; a query returns only detected groups.
- HERMES uses user-initiated speed tests. Its users are not a representative sample and its events are daily, so short outages can be missed.
- Geography is provider IP geolocation at city/metro scale, not an official district boundary; fixed versus mobile access is not identified.
- The public overview is available without sign-in, but event drill-down requires an M-Lab/Google account with BigQuery access. The dashboard endpoint is not documented as a production integration contract.
- Three-day date windows help with UTC/local date boundary differences. A match within this window is not proof the measured performance change was the same outage.

Fuentes técnicas: [M-Lab HERMES](https://www.measurementlab.net/tests/hermes/), [acceso y actualización](https://www.measurementlab.net/tests/hermes/quickstart/), [esquema y método](https://www.measurementlab.net/tests/hermes/schema/).
