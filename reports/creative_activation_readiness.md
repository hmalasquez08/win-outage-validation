# Estado técnico para activar creatividades

**Estado observado: STALE_SINGLE_FAMILY_CANDIDATE. Activación permitida: no.** Se consultó NetFlows por operador y GeoID departamental de Ica para el 25 de octubre de 2026 (03:00–08:45 UTC), comparándolo con el mismo bloque del 18 de octubre. Las ocho series se pidieron en una sola consulta para compartir la normalización.

## Resultado por operador

| Operador | Intervalos emparejados | Diferencia mediana normalizada | Intervalos bajo comparador | Pasa regla estricta |
|---|---:|---:|---:|---|
| Movistar | 24 | -0.101499 | 100.0% | Sí |
| Claro | 24 | +0.023946 | 41.7% | No |
| Entel | 24 | +0.025710 | 25.0% | No |
| Bitel | 24 | +0.000004 | 37.5% | No |

Movistar muestra un **candidato técnico departamental**: diferencia mediana normalizada -0.101499 y 100.0% de intervalos por debajo del comparador en 24 pares. Cloudflare informó actualización hasta 2026-10-25T08:45:00Z y la captura se hizo a las 2026-10-25T10:10:50.372208+00:00 (85.8 minutos de desfase). Pasa la regla de persistencia para candidato, pero no demuestra que usuarios estuvieran desconectados ni que existiera una caída de servicio.

## Corroboración buscada

- IODA: HTTP 200, 0 eventos en la consulta acotada. Las series crudas de AS6147 muestran BGP estable (5.933 prefijos /24 visibles, sin cambio) y sondeos activos con mediana de 952 bloques /24 accesibles frente a 959 en el comparador semanal (−7; 65.7% de intervalos más bajos). Es una variación pequeña y de ASN completo, no corroboración localizada en Ica; un endpoint vacío no prueba que la red esté sana.
- Respuestas a la cuenta oficial de Movistar: HTTP 200; el resultado redactado tuvo 0 campos de texto y ningún elemento clasificable. La búsqueda es inconclusa, no prueba ausencia de quejas.
- HERMES: la anomalía más reciente consultada fue para Claro en Ica el 23 de octubre; es otro operador y otra fecha, así que no corrobora el candidato actual de Movistar.

## Por qué no se activa

1. Solo Cloudflare cumple la regla de candidato a nivel departamental. IODA aporta una señal independiente débil a nivel de ASN, sin resolver Ica.
2. No hay una segunda señal independiente que coincida en Movistar, Ica y la misma ventana con magnitud suficiente para corroborar una degradación.
3. El dato departamental no resuelve qué distritos están afectados ni diferencia fijo de móvil.
4. La actualización consultada llega con 85.8 minutos de desfase; supera el límite de frescura de 30 minutos que usa el simulador local.
5. Una activación programática necesita una impresión y una solicitud de anuncio procedentes de un sitio o aplicación. Por inferencia del flujo OpenRTB documentado, un dispositivo totalmente desconectado no puede pedir un anuncio nuevo por esa misma conexión. La activación puede orientar inventario que sí esté conectado en la zona; garantizar un anuncio dinámico al dispositivo sin ninguna conexión requeriría una vía prealmacenada/local, que no forma parte de esta validación.
6. Al pasar el dato real por el simulador local, el resultado fue `SUPPRESSED`: missing_fresh_direct_internet_signal.

## Qué está resuelto y qué queda

Resuelto en esta iteración: ya se ejecuta una señal regional de Cloudflare para los cuatro operadores y se aplica una regla persistente sobre datos comparables; se capturó HERMES como fuente nueva y se buscó corroboración IODA/X para el candidato actual; el evaluador produce un estado reproducible sin tocar un destino publicitario.

Para que el motor pueda emitir un evento apto para creatividad todavía se necesita una fuente independiente, fresca y alineada en operador, zona y tiempo; señal directa que permita distinguir interrupción/degradación de una caída de tráfico; granularidad geográfica suficiente para una zona segmentable; y un caso confirmado de extremo a extremo con salida local de prueba. La negociación de integración queda para después de que esa evidencia pase la regla.

## Evidencias

| Fuente | Evidence ID | Ruta | SHA-256 | HTTP |
|---|---|---|---|---:|
| cloudflare_ica_geography | `cloudflare_geolocations_peru-7bf048ced142` | `evidencias/api_responses/cloudflare_geolocations_peru/20261025T100410.176653+0000.json` | `7bf048ced142ba4f567f4249f66e65b5e0a5df5baaee61bc934e2b3841a3f302` | 200 |
| current_ica_netflows | `cloudflare_netflows_ica_recent_all_operators-ac7e230ca4c9` | `evidencias/api_responses/cloudflare_netflows_ica_recent_all_operators/20261025T101050.372208+0000.json` | `ac7e230ca4c968f690a52b3580ef4faa3ad9fab2994777363bdba3d1a86571c4` | 200 |
| current_ioda | `ioda_movistar_ica_candidate_20261025-242282f2c412` | `evidencias/api_responses/ioda_movistar_ica_candidate_20261025/20261025T101221.336931+0000.json` | `242282f2c412a8a8f9c4b27d4a19855465d12976ffaae33129a9477d65ab0e88` | 200 |
| current_ioda_raw | `ioda_movistar_ica_candidate_raw_signals_20261025-85723c22fce9` | `evidencias/api_responses/ioda_movistar_ica_candidate_raw_signals_20261025/20261025T102827.270885+0000.json` | `85723c22fce9e1ff38b6fb5b136b565ce01a7936ee8d07259167ae7f7c1afba7` | 200 |
| control_ioda_raw | `ioda_movistar_ica_candidate_raw_control_20261018-af2630a262f0` | `evidencias/api_responses/ioda_movistar_ica_candidate_raw_control_20261018/20261025T102900.261744+0000.json` | `af2630a262f0d9a6096c44231e7c32e0b7a2803bc775ed9db7c280b4043df15e` | 200 |
| current_x | `twexapi_replies_movistar_ica_candidate_20261025-74bd04629a7a` | `evidencias/api_responses/twexapi_replies_movistar_ica_candidate_20261025/20261025T101205.094978+0000.json` | `74bd04629a7ac6ef3aa60183a4c367b0d6bfa07875b316233f956d4f56c016b4` | 200 |

## Documentación primaria consultada

- [M-Lab HERMES: actualización diaria y cobertura](https://www.measurementlab.net/tests/hermes/quickstart/).
- [Cloudflare Radar NetFlows](https://developers.cloudflare.com/radar/investigate/netflows/) y [geografías GeoID](https://developers.cloudflare.com/api/resources/radar/subresources/geolocations/methods/list/).
- [IAB OpenRTB 2.6: flujo de puja por impresión](https://github.com/InteractiveAdvertisingBureau/openrtb2.x/blob/main/2.6.md). La imposibilidad de una solicitud nueva desde un dispositivo desconectado es una inferencia del flujo descrito.

Reproducir desde la raíz: `python -m win_validation.candidate_crosscheck`.
