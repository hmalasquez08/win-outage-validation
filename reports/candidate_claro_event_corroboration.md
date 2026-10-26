# Cotejo del evento candidato de Claro

Consulta realizada: 2026-10-25T08:09:00.309938+00:00.

IODA devolvió un evento BGP de 15 minutos para AS12252 con inicio 2026-10-19 19:20 UTC. La propia respuesta marca `overlaps_window=false`, aunque el inicio cae dentro de la ventana consultada; por esa inconsistencia se trata como evento candidato devuelto por el endpoint, no como evento confirmado. Se cotejó la hora 19:00–20:00 UTC con NetFlows por los cuatro ASN y contra la misma hora de la semana anterior; además se consultaron respuestas públicas dirigidas a Claro.

| Operador | NetFlows evento / semana anterior | Medianas y diferencia |
|---|---:|---|
| movistar | 5/5 puntos | 0.956707 / 0.890558 / 0.06614900000000001 |
| claro | 5/5 puntos | 0.896601 / 0.819421 / 0.07718000000000003 |
| entel | 5/5 puntos | 0.942868 / 0.882731 / 0.060136999999999996 |
| bitel | 5/5 puntos | 0.979316 / 0.919022 / 0.06029399999999996 |

La consulta de X por hora devolvió páginas vacías y mantuvo `has_next_page=true`; la consulta por día también devolvió 0 publicaciones con ese indicador activo. Por la inconsistencia de paginación, X queda inconcluso para esta ventana; esos ceros no demuestran que nadie reclamara.

Este cotejo es diagnóstico. NetFlows compara unidades normalizadas y la semana anterior no es un período normal verificado; el evento BGP puede representar una anomalía de enrutamiento sin caída de acceso del usuario. No se considera una detección confirmada ni permite seleccionar una zona para creatividad. Evidencia y límites en `candidate_claro_event_corroboration.json/.csv`.
