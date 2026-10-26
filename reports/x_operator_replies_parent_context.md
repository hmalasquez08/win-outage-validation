# Contexto padre de respuestas oficiales de operadores en X

Consulta observada: 2026-10-25T07:20:10.917120+00:00. Ventana consultada: 2026-07-27 a 2026-10-26 UTC. Hasta cinco páginas por cuenta, paginadas con el cursor del proveedor. Se obtuvieron los mensajes padre mediante el endpoint de detalle (respuesta `data` en formato de lista); los IDs, textos y autores se procesaron solo en memoria. Evidencia conservada: metadatos de respuesta sin publicaciones, identidades ni texto.

| Operador | Respuestas oficiales | Mensajes padre recuperados | Autores ciudadanos | Autores con queja explícita de internet | Pico de autores por hora UTC | Distritos con mención | Distritos con ≥3 autores |
|---|---:|---:|---:|---:|---:|---:|---:|
| Movistar | 11 | 10 | 10 | 0 | 0 | 0 | 0 |
| Claro | 77 | 72 | 46 | 2 | 1 | 0 | 0 |
| Entel | 84 | 84 | 54 | 0 | 0 | 0 | 0 |
| Bitel | 15 | 15 | 13 | 0 | 0 | 0 | 0 |

Posts padre solicitados: 183; devueltos: 177; llamadas API: 39; errores HTTP: 0.

## Interpretación

La queja de una persona no es una caída. La hipótesis comprobable es que varias personas distintas reportando problemas de internet para el mismo operador en el mismo ámbito y ventana puedan elevar la confianza de un incidente técnico. Los conteos son de actividad pública recuperada, no del universo de abonados. La activación prevista es por segmento/zona; nunca por autor de una publicación. No se asignó peso ni umbral, y esta muestra por sí sola no confirma outages ni permite calcular aporte incremental.

Los resultados horarios UTC y menciones distritales se entregan en archivos agregados; los lugares se suprimen cuando tienen menos de tres autores distintos.
