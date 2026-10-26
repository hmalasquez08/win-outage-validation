# Búsqueda de respuestas públicas de X

Se consultó TwexAPI con `to:<cuenta> filter:replies` para respuestas dirigidas a Movistar, Claro, Entel, Bitel y OSIPTEL, además de `from:OSIPTEL filter:replies` para las respuestas publicadas por OSIPTEL. Se aplicaron términos específicos de interrupciones; la salida conserva solo conteos agregados de contexto, menciones de operador/servicio y coincidencias con nombres distritales del catálogo UBIGEO. No se guardaron texto, usuario ni identificador de publicación.

Los conteos son candidatos de señal, no confirmaciones independientes: `x_reply_search_summary.csv` registra HTTP y evidencia por consulta. La precisión geográfica se limita a coincidencias de nombres y no resuelve ambigüedades ni reemplaza revisión de cada incidente. La fuente permite buscar las respuestas; queda por demostrar el rendimiento como detector con referencias independientes.

## Resultados de la consulta

Las seis consultas (`to:` para respuestas a Movistar, Claro, Entel, Bitel y OSIPTEL; `from:OSIPTEL filter:replies` para respuestas de OSIPTEL) respondieron HTTP 200. La búsqueda encontró 1 respuesta con contexto de interrupción dirigida a Claro y 2 respuestas de OSIPTEL con contexto de interrupción; ninguna coincidió simultáneamente con distrito, operador y servicio. Las consultas sin coincidencias no demuestran ausencia de conversaciones fuera de la ventana o de la cobertura de búsqueda.
