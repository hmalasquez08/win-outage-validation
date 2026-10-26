# Replay retrospectivo de detecciones por fuente y combinación

## Resultado ejecutivo

En **15 pares positivos** de **8 casos temporizados**, NetFlows genera un candidato direccional en **9/15 (60%)** y al menos un operador en 6/8 casos. IODA marca 1/15; Radar outage, 0/15. En la búsqueda histórica de X, dos autores aislados reportaron problemas explícitos en dos pares positivos; no apareció ningún cluster de ≥2 autores en el mismo distrito y bloque de 15 minutos, que es la unidad social que sí podría respaldar un segmento. La combinación OR de las cuatro señales marca 9/15, la misma cobertura que NetFlows; exigir dos fuentes mantiene 1/15.

Este es un replay exploratorio sobre positivos seleccionados y controles operador-caso; no mide rendimiento operativo ni habilita activación publicitaria.

## Reglas probadas

- **NetFlows:** mediana normalizada en el incidente < comparador del mismo día/hora de la semana anterior. No fue umbral preregistrado ni validado: el comparador no tiene etiqueta de normal y no representa porcentaje de tráfico perdido.
- **IODA:** al menos un inicio de evento dentro de la ventana del caso; solapamiento de duración sin inicio dentro no cuenta.
- **Cloudflare Radar outage:** anotación coincidente por ASN/Perú en la ventana.
- **X social:** ≥2 autores distintos con queja explícita de internet, mismo distrito no ambiguo y mismo intervalo UTC de 15 minutos. También se evaluó ≥3. No se infiere distrito del perfil ni se usa un reclamo individual.
- **OR / dos familias:** combinación booleana de las cuatro señales disponibles. OSIPTEL se usa para etiquetas, e INEI/UBIGEO para geografía, no como detectores. Voz/SMS y RSS no tenían series históricas por operador-zona-tiempo, así que no se les asignaron aciertos o fallos.

## Detecciones observadas

| Fuente/regla | Pares positivos con candidato | Resultado de control / limitación |
|---|---:|---|
| NetFlows: mediana normalizada inferior | 9/15 | Comparador semanal no etiquetado como normal. |
| IODA: inicio en ventana | 1/15 | Coincide con uno ya marcado por NetFlows; no añade par nuevo. |
| Radar outage: anotación coincidente | 0/15 | Sin coincidencia en las consultas realizadas. |
| X: queja explícita en cualquier zona | 2/15 pares, 2 autores | Dos quejas aisladas; no bastan para un segmento. |
| X: cluster ≥2 autores, mismo distrito×15m | 0/15 | 0/17 controles en este replay; resultado acotado, no tasa general de falsos positivos. |
| OR técnico (NetFlows/IODA/Radar) | 9/15 | No supera NetFlows solo. |
| OR incluyendo cluster X | 9/15 | No suma pares nuevos sobre NetFlows. |
| Dos o más fuentes en el mismo par | 1/15 | Consenso severo: reduce candidatos; no se valida por esta muestra. |

### X: prueba histórica en los controles y positivos

Se consultaron 32 ventanas operador-caso (15 positivas, 17 `NO_CONTROL`), con 40 llamadas de búsqueda y cero errores HTTP. Hubo quejas explícitas solo en 2/15 pares positivos y 0/17 controles. Ninguna positiva produjo dos autores distintos en un mismo distrito y bloque de 15 minutos; por tanto, la regla que habilitaría corroboración geográfica no detectó un evento. Las 2 publicaciones aisladas siguen siendo contexto, no un trigger. El muestreo abarcó las respuestas dirigidas a cada operador, no todas las respuestas debajo de cada publicación oficial.

### Sensibilidad al corte de NetFlows

Los valores `MIN0_MAX` son unidades normalizadas. La tabla no selecciona el corte óptimo; muestra el costo de exigir una caída más grande.

| Delta normalizado (incidente − comparador) | Pares candidatos |
|---|---:|
| < 0.000 | 9/15 |
| < -0.005 | 9/15 |
| < -0.010 | 9/15 |
| < -0.020 | 8/15 |
| < -0.050 | 5/15 |
| < -0.100 | 2/15 |
| < -0.150 | 1/15 |
| < -0.200 | 1/15 |

### Resultado por operador

| Operador | Pares | NetFlows | IODA | Radar | X clusters geográficos | OR de todas |
|---|---:|---:|---:|---:|---:|---:|
| Bitel | 2 | 1 | 0 | 0 | 0 | 1 |
| Claro | 3 | 2 | 0 | 0 | 0 | 2 |
| Entel | 4 | 2 | 0 | 0 | 0 | 2 |
| Movistar | 6 | 4 | 1 | 0 | 0 | 4 |

### Resultado por caso

| Incidente | Pares | NetFlows | IODA | X clusters | Al menos un candidato |
|---|---:|---:|---:|---:|---|
| ancash_multioperator_2025-04-24 | 4 | 2 | 0 | 0 | Sí |
| ayacucho_integratel_entel_mobile_2025-12-26 | 2 | 0 | 0 | 0 | No |
| claro_los_olivos_2025-12-11 | 1 | 1 | 0 | 0 | Sí |
| loreto_shared_carrier_2025-12-19 | 3 | 2 | 0 | 0 | Sí |
| movistar_entel_south_2022-10-25 | 2 | 2 | 0 | 0 | Sí |
| movistar_lima_fiber_2026-07-01 | 1 | 0 | 0 | 0 | No |
| movistar_lima_fixed_2024-11-26 | 1 | 1 | 1 | 0 | Sí |
| movistar_national_2024-11-18 | 1 | 1 | 0 | 0 | Sí |

### Desglose del tipo de servicio en la referencia

| Alcance | Pares | NetFlows candidatos | IODA | OR |
|---|---:|---:|---:|---:|
| fixed and mobile | 4 | 3 | 0 | 3 |
| fixed and mobile internet | 7 | 5 | 0 | 5 |
| fixed internet | 2 | 1 | 1 | 1 |
| mobile internet and mobile service | 2 | 0 | 0 | 0 |

En los dos pares explícitamente solo móviles, NetFlows no marcó candidato; en dos de solo fijo marcó uno; 11 pares incluyen fijo y móvil. NetFlows por ASN no separa producto minorista.

## Fuentes no puntuables como detector histórico

- **Voz/SMS, feeds de prensa y fuentes institucionales distintas de OSIPTEL:** las capturas disponibles no cubren estas ventanas con operador, zona y hora; no cuentan como cero detecciones.
- **UBIGEO/INEI:** habilita una geografía verificable cuando la señal incluye lugar; no detecta fallas.
- **OSIPTEL:** aporta referencias/etiquetas de positivo y controles, no se cuenta como predictor.

## Conclusión de validación

Hay una señal técnica que merece continuar experimentándose: NetFlows produce 9/15 flags direccionales, pero faltó en 6/15 pares positivos y no tiene controles normales independientes. IODA y Radar no aumentan cobertura positiva; X no produjo clusters geotemporales aunque aportó dos quejas aisladas. El resultado **no demuestra que el detector final funcione**. Falsos positivos globales, precisión, recall general, frescura de primera detección y desempeño fijo/móvil independiente no son calculables con estas etiquetas y estas capturas. No activar campañas a partir de este replay.

## Artefactos

- `historical_detector_replay.csv`: marcas por señal para cada par positivo.
- `historical_detector_replay.json`: reglas, resultados, cortes y limitaciones.
- `x_historical_incident_replay.csv/.json/.md`: búsqueda X alineada a ventanas positivas y `NO_CONTROL`.
- Entradas técnicas: `cloudflare_netflows_incident_replay.csv`, `incident_reference_ioda_comparison.csv`, `incident_reference_cloudflare_comparison.csv`.
