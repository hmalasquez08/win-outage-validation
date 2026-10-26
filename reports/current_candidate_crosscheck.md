# Cotejo de candidato actual: Claro en Ica

## Decisión

**UNCONFIRMED_CANDIDATE — sin activación.** Este registro no se etiqueta como caída confirmada ni se convierte en una orden de creatividad.

## Evidencia observada

M-Lab HERMES registró el 2026-10-23 una anomalía diaria para Claro (AS12252) en Ica: descarga mediana 5.26 Mbps frente a 17.04 Mbps de base (−69.2%), fracción anómala 0.914, 20 clientes únicos. La geolocalización proviene de ipinfo y la etiqueta de atribución de ruta fue `weak`. La respuesta se capturó el 2026-10-25T10:02:56.083184+00:00; HERMES publica datos diarios, por lo que esto no es una señal de estado en vivo.

Cloudflare confirmó que Ica tiene GeoID departamental `3938526` y devolvió en una sola respuesta series comparables para el mismo ASN y departamento: 97 pares de intervalos de 15 minutos con normalización compartida. La mediana del índice normalizado fue 0.577480 frente a 0.614150 el viernes anterior (-5.97% relativo en el índice; no equivale a volumen de tráfico). La mediana de las diferencias emparejadas fue -0.008302; 57.7% de los intervalos quedaron por debajo del comparador.

La regla NetFlows ya definida exige diferencia emparejada < −0.02 y al menos 90% de intervalos bajo el comparador, con ocho o más pares. **No pasó**: el valor emparejado fue -0.008302 y solo 57.7% quedó por debajo. La variación relativa de medianas no equivale a usuarios desconectados ni a tráfico perdido.

## Interpretación

El cotejo es útil porque alinea operador, fecha y nivel administrativo departamental entre dos familias de medición. Aun así, HERMES no verifica la ubicación física de los participantes ni separa internet fijo y móvil; Cloudflare ofrece una serie agregada, sin barrio/distrito. El comparador semanal tampoco está etiquetado como normal. No se encontró una referencia externa independiente que confirme que este registro concreto fuera una interrupción real.

Por tanto, **hay una anomalía de rendimiento observada y corroboración departamental débil, pero no una caída confirmada ni evidencia accionable vigente**. El motor debe mantener el caso en candidato/suprimido, nunca activar por este registro histórico.

## Evidencias

| Artefacto | Evidence ID | Ruta | SHA-256 | HTTP |
|---|---|---|---|---:|
| hermes | `mlab_hermes_recent_scan_20261022_25-fd15735a611b` | `evidencias/api_responses/mlab_hermes_recent_scan_20261022_25/20261025T100256.083184+0000.json` | `fd15735a611b15dbc995c8f652170c839688ea2ca83acf493891b760828f8051` | 200 |
| cloudflare_ica_geography | `cloudflare_geolocations_peru-7bf048ced142` | `evidencias/api_responses/cloudflare_geolocations_peru/20261025T100410.176653+0000.json` | `7bf048ced142ba4f567f4249f66e65b5e0a5df5baaee61bc934e2b3841a3f302` | 200 |
| cloudflare_paired | `cloudflare_netflows_ica_paired_claro_20261023-c25cfb06a100` | `evidencias/api_responses/cloudflare_netflows_ica_paired_claro_20261023/20261025T100730.385427+0000.json` | `c25cfb06a10087b04bf1db0e26a5cfba1506c80fed792753d000ae373a4f1638` | 200 |

## Reproducibilidad

Desde la raíz del proyecto: `python -m win_validation.candidate_crosscheck`. El módulo solo lee las respuestas archivadas y vuelve a generar este informe y el JSON; no consulta servicios ni altera las evidencias originales.
