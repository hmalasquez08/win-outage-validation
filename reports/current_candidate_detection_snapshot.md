# Snapshot prospectivo de señales candidatas

Consulta UTC: 2026-10-25T08:00:00+00:00
Ventana medida: 2026-10-18T08:00:00Z a 2026-10-25T08:00:00Z; comparador: 2026-10-11T08:00:00Z a 2026-10-18T08:00:00Z.

Este snapshot prueba acceso y señales actuales de NetFlows, eventos IODA y anotaciones Radar para cuatro ASNs. No es una alerta de corte: no hay etiqueta independiente de estado normal/falla para la ventana actual, y NetFlows no localiza distritos ni distingue internet fijo de móvil.

| Operador | NetFlows (puntos actual/comparador; delta mediana) | IODA (eventos; inicios) | Radar (anotaciones; inicio ASN/PE) |
|---|---|---:|---:|
| movistar | 667/667; 0.010929000000000078 | 0; 0 | 0; 0 |
| claro | 667/667; -0.04504399999999997 | 1; 1 | 0; 0 |
| entel | 667/667; -0.014700999999999964 | 0; 0 | 0; 0 |
| bitel | 667/667; -0.0011209999999999276 | 0; 0 | 0; 0 |

Las comparaciones son exploratorias y no se traducen a porcentaje de usuarios sin internet ni permiten activar una zona. Los resultados por endpoint, estados HTTP y rutas de evidencia están en `current_candidate_detection_snapshot.csv/.json` y `evidencias/manifest.jsonl`.

IODA devolvió un evento para Claro con inicio dentro del rango, pero su respuesta incluyó overlaps_window=false; se trata como una señal ambigua y no como detección positiva. El cotejo puntual por hora está en candidate_claro_event_corroboration.md.
