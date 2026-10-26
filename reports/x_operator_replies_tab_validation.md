# Validación de la pestaña Respuestas de las cuentas oficiales

Se consultó el endpoint documentado de TwexAPI para obtener publicaciones y respuestas escritas por cada cuenta, separado de la cronología normal y de las búsquedas `to:HANDLE`. Se recorrieron hasta cinco páginas por operador; la API devuelve hasta 20 elementos por página. Se clasificó en memoria el texto de la respuesta oficial y el contexto original anidado cuando estuvo presente. Se archivaron solo conteos: no se guardaron textos ni identidades de usuarios.

| Operador | Páginas | Elementos | Respuestas oficiales revisadas | Posts padre recuperados | Autores distintos en contexto | Autores con queja explícita de internet | Pico de autores por hora UTC |
|---|---:|---:|---:|---:|---:|---:|---:|
| Movistar | 5 | 207 | 11 | 10 | 10 | 0 | 0 |
| Claro | 5 | 180 | 77 | 72 | 46 | 2 | 1 |
| Entel | 5 | 199 | 84 | 84 | 54 | 0 | 0 |
| Bitel | 5 | 194 | 15 | 15 | 13 | 0 | 0 |

La primera pasada no enlazó los posts padre porque el parser esperaba una forma distinta de la respuesta. La relectura usó el formato documentado `data` como lista y resolvió 177 de 183 padres solicitados (39 llamadas, todas HTTP 200). El resultado corregido está en `x_operator_replies_parent_context.md/.csv/.json`; la primera tabla de cero contextos queda reemplazada por esta relectura. Los resultados son una muestra paginada, no un censo de cuentas.

## Lectura para Win

La pestaña de respuestas es una vía distinta y útil para recuperar casos donde soporte contestó a una queja. La señal buscada no es una queja individual: es la concentración de usuarios distintos que describen falta o degradación de internet para un operador, con coincidencia temporal y geográfica. La respuesta del operador puede respaldar que recibió el reclamo, pero no confirma por sí sola una avería de red.

La muestra de hasta cinco páginas todavía no representa todo el historial de la cuenta. En este muestreo solo aparecieron dos autores con queja explícita en el contexto de Claro, en horas diferentes; no hubo concentración horaria ni mención distrital explícita en esas quejas. En una modalidad distinta, tres hilos de publicaciones de Claro acumularon 8 quejas explícitas entre 43 respuestas de clientes y dos menciones distritales (una ambigua). No se suman ambas modalidades porque pueden solaparse y su deduplicación conjunta no está demostrada. La señal debe evaluarse como volumen agregado por operador, zona y tiempo, no como targeting de una persona.
