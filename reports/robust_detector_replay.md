# Detector de interrupciones: replay retrospectivo robustecido (solo software)

## Qué se construyó

Un detector determinístico y reproducible con Cloudflare NetFlows/Radar, IODA, quejas agregadas de X y M-Lab HERMES como señal experimental de rendimiento. No se entrenó un modelo estadístico porque ocho incidentes no permiten entrenar y validar uno generalizable. NetFlows y Radar se agrupan como una sola familia Cloudflare.

El colector RSS/XML de siete medios también está conectado mediante `python -m win_validation.detector --fetch-news`; revisa únicamente el contenido incluido en cada feed y no abre artículos. La última consulta registrada y el número de ítems por medio se muestran en `reports/current_news_feed_status.csv`; no generó candidatos. No hay casos periodísticos históricos alineados por operador, zona y hora en este replay, así que las noticias todavía no forman parte de sus métricas ni tienen aporte incremental medido. Ver también `reports/current_news_candidates.csv`.

## Resultado en positivos y controles emparejados

La muestra contiene **15 pares positivos** y **17 pares control** en **8 incidentes**. NetFlows básico marcó 9/15 positivos y 9/17 controles. La regla estricta v4, con HERMES experimental, marcó 8/15 positivos y 2/17 controles; a nivel de incidente encontró afectados en 7/8 y señaló controles en 2/8 incidentes. En la evaluación dejando fuera cada incidente completo y ajustando con los demás, marcó 7/15 positivos y 2/17 controles.

| Regla | Positivos con señal | Controles con señal | Sensibilidad (IC 95% por incidente) | Activación en controles (IC 95% por incidente) | Precisión en esta muestra balanceada |
|---|---:|---:|---:|---:|---:|
| NetFlows básico, delta < 0 | 9/15 | 9/17 | 60.0% (36.4–84.6%) | 52.9% (15.4–100.0%) | 50.0% |
| NetFlows persistente, delta < −0.02 y ≥90% de bins | 6/15 | 1/17 | 40.0% (20.0–60.0%) | 5.9% (0.0–17.6%) | 85.7% |
| Regla sensible: cualquier familia | 10/15 | 9/17 | 66.7% (44.4–92.3%) | 52.9% (15.4–100.0%) | 52.6% |
| Regla corroborada: dos familias | 2/15 | 1/17 | 13.3% (0.0–40.0%) | 5.9% (0.0–17.6%) | 66.7% |
| Candidato estricto: persistencia o señal independiente | 8/15 | 2/17 | 53.3% (35.3–80.0%) | 11.8% (0.0–23.8%) | 80.0% |
| Ajuste por incidente excluido (LOIO) | 7/15 | 2/17 | 46.7% (25.0–77.8%) | 11.8% (0.0–23.8%) | 77.8% |
| IODA | 1/15 | 0/17 | 6.7% (0.0–27.3%) | 0.0% (n/a) | 100.0% |
| Radar | 0/15 | 0/17 | 0.0% (n/a) | 0.0% (n/a) | n/a |
| X: grupo geográfico | 0/15 | 0/17 | 0.0% (n/a) | 0.0% (n/a) | n/a |
| M-Lab HERMES experimental | 2/15 | 1/17 | 13.3% (0.0–40.0%) | 5.9% (0.0–17.6%) | 66.7% |

Las métricas describen esta muestra seleccionada y no son estimaciones poblacionales. Los controles son pares de operadores no reportados como afectados dentro de incidentes reales. La regla v4 agrega persistencia NetFlows y HERMES experimental, pero no equivale a una política de activación.

## Sensibilidad del umbral NetFlows

El umbral 0 reproduce la regla exploratoria previa. Los demás cortes muestran el intercambio entre casos positivos marcados y operadores control señalados. El barrido conjunto delta/persistencia permite ver qué se pierde al exigir una caída más consistente. La tabla de reglas incluye una evaluación agrupada que deja fuera un incidente completo para cada pliegue; sus umbrales se eligen solo en los otros incidentes.

| Delta normalizado < | Positivos detectados | Controles marcados | Sensibilidad | Especificidad en controles emparejados |
|---:|---:|---:|---:|---:|
| 0 | 9/15 | 9/17 | 60.0% | 47.1% |
| -0.005 | 9/15 | 7/17 | 60.0% | 58.8% |
| -0.01 | 9/15 | 6/17 | 60.0% | 64.7% |
| -0.02 | 8/15 | 5/17 | 53.3% | 70.6% |
| -0.05 | 5/15 | 1/17 | 33.3% | 94.1% |
| -0.1 | 2/15 | 1/17 | 13.3% | 94.1% |
| -0.15 | 1/15 | 0/17 | 6.7% | 100.0% |
| -0.2 | 1/15 | 0/17 | 6.7% | 100.0% |

### Persistencia por intervalos de 15 minutos

| Delta < | Proporción mínima de intervalos bajo comparador | Positivos marcados | Controles marcados |
|---:|---:|---:|---:|
| -0.01 | 90% | 6/15 | 1/17 |
| -0.02 | 70% | 8/15 | 3/17 |
| -0.02 | 80% | 6/15 | 2/17 |
| -0.02 | 90% | 6/15 | 1/17 |
| -0.02 | 100% | 4/15 | 1/17 |
| -0.05 | 90% | 5/15 | 1/17 |

## Dónde hubo candidatos

| Incidente | Pares afectados con candidato | Pares control marcados | Operadores control marcados |
|---|---:|---:|---|
| claro_los_olivos_2025-12-11 | 1/1 | 1 | movistar |
| loreto_shared_carrier_2025-12-19 | 1/3 | 0 | — |
| movistar_lima_fiber_2026-07-01 | 1/1 | 0 | — |
| movistar_national_2024-11-18 | 1/1 | 1 | claro |
| movistar_lima_fixed_2024-11-26 | 1/1 | 0 | — |
| movistar_entel_south_2022-10-25 | 1/2 | 0 | — |
| ancash_multioperator_2025-04-24 | 2/4 | 0 | — |
| ayacucho_integratel_entel_mobile_2025-12-26 | 0/2 | 0 | — |

## Cómo decide

1. Calcula señales por operador e intervalo; NetFlows y Radar cuentan como una sola familia Cloudflare.
2. NetFlows activa la ruta estricta si su diferencia normalizada es menor que −0.02, al menos 90% de los intervalos están debajo del comparador semanal y hay al menos ocho pares de intervalos.
3. IODA puede generar candidato por inicio de evento; X requiere dos autores distintos en un distrito inequívoco y bloque UTC de 15 minutos.
4. `CORROBORADO` exige dos familias distintas. La regla estricta genera candidatos, no confirma una pérdida de internet.

## Qué demuestra y qué no

Demuestra que el código reproduce las reglas sobre señales históricas y revela el problema de falsos disparos hacia operadores no incluidos en los reportes de afectación. **No demuestra** rendimiento en tiempo real, frescura, precisión poblacional, ni capacidad para localizar el disparo por distrito. Los controles son los otros operadores dentro de ventanas de incidentes reales, no ventanas normales independientes; algunas afectaciones pueden no haber sido reportadas. Las referencias positivas también mezclan reportes regulatorios, de operadores y de prensa.

El NetFlows de Lima filtrado por GeoID devolvió 668 valores en cero para cada operador, así que la evaluación usa únicamente las consultas históricas por país y ASN y no acredita cobertura distrital. La atribución fijo/móvil permanece débil. No se usó ni se requiere hardware.

## Auditoría de brechas incorporada en v4

- **Negativos independientes:** 0 ventanas normales etiquetadas; los 17 controles existentes solo indican operadores no nombrados dentro de incidentes.
- **Latencia en vivo:** 0 pares con primer alerta válida y hora de inicio independiente; no se puede calcular frescura de detección con este replay.
- **Operador/tecnología:** la tabla siguiente cuenta solo etiquetas explícitas en las referencias; lo mixto no se redistribuye a fijo o móvil.
- **Geografía:** quedan sin geometría oficial completa 120307 y 160405; 130112 usa un parche candidato, por lo que ninguno debe habilitarse como límite oficial final sin completar cotejo.
- **Corroboración:** el candidato vivo de Ica no tiene confirmación independiente alineada por operador, zona y tiempo; se mantiene suprimido.
- **Ablación:** se calculó el cambio de candidatos al retirar cada familia en el replay seleccionado. Es una comparación descriptiva, no valor incremental validado, porque faltan ventanas normales independientes.

| Operador | Pares positivos | Solo fijo | Solo móvil | Fijo+móvil | Sin atribución |
|---|---:|---:|---:|---:|---:|
| bitel | 2 | 0 | 0 | 2 | 0 |
| claro | 3 | 0 | 0 | 3 | 0 |
| entel | 4 | 0 | 1 | 3 | 0 |
| movistar | 6 | 2 | 1 | 3 | 0 |

### Ablación de familias

| Familia retirada | Positivos que aún generan candidato | Controles emparejados que aún generan candidato |
|---|---:|---:|
| cloudflare_netflows_radar | 3/15 | 1/17 |
| ioda | 7/15 | 2/17 |
| x | 8/15 | 2/17 |
| mlab_hermes | 7/15 | 1/17 |

HERMES se añadió como señal experimental de rendimiento. Para este replay se aplicó una puerta exploratoria: operador, área y fecha exactos; caída de throughput ≥40%; fracción anómala ≥80%; y al menos cinco clientes. Los umbrales se definieron con la muestra disponible y no están validados prospectivamente. HERMES es diario y no prueba por sí solo una interrupción de internet.

**Conclusión:** el replay v4, incluyendo HERMES, marca 8/15 pares positivos y 2/17 controles emparejados. Al retirar HERMES, queda en 7/15 positivos y 1/17 controles. LOIO (con umbral ajustado por pliegue) marca 7/15 positivos y 2/17 controles. La muestra no prueba métricas poblacionales ni latencia operacional.

Código: `src/win_validation/detector.py`. Datos reproducibles: `robust_detector_replay.csv`, `robust_detector_event_summary.csv`, `robust_detector_replay.json` y `detector_historical_controls.csv`. Ejecutar `python -m win_validation.detector`; añadir `--fetch-controls` para volver a consultar los controles Cloudflare y guardar evidencia.
