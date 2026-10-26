# Validación de respuestas en X: conversaciones de operadores

**Corrección metodológica:** la consulta anterior se limitó a `to:HANDLE` con términos de búsqueda y no recorrió adecuadamente los hilos de las publicaciones oficiales. Esta ronda prueba por separado búsqueda de respuestas dirigidas a la cuenta, cronología de la cuenta oficial y endpoint paginado de respuestas de cada publicación. TwexAPI documenta la búsqueda paginada y el endpoint de respuestas por ID de publicación.

Se revisó un máximo de tres páginas de respuestas dirigidas por operador y hasta tres publicaciones oficiales con respuestas en los últimos 90 días; para hilos con ≥20 respuestas declaradas se consultaron hasta dos páginas. Se conservaron exclusivamente conteos agregados, fechas y hashes irreversibles de raíces oficiales; el texto y las identidades se procesaron solo en memoria.

## Respuestas dirigidas a las cuentas oficiales

| Operador | Páginas devueltas | Respuestas únicas | Autores únicos | Quejas explícitas de internet | Menciones de distrito |
|---|---:|---:|---:|---:|---:|
| Movistar | 3 | 1 | 1 | 0 | 0 |
| Claro | 3 | 20 | 14 | 1 | 0 |
| Entel | 3 | 54 | 39 | 2 | 0 |
| Bitel | 3 | 3 | 1 | 1 | 0 |

## Respuestas a publicaciones oficiales

| Operador | Publicaciones de cuenta revisadas | Hilos muestreados | Respuestas de clientes recuperadas | Quejas explícitas de internet | Menciones de distrito |
|---|---:|---:|---:|---:|---:|
| Movistar | 20 | 0 | 0 | 0 | 0 |
| Claro | 20 | 3 | 43 | 8 | 2 |
| Entel | 20 | 0 | 0 | 0 | 0 |
| Bitel | 20 | 0 | 0 | 0 | 0 |

Llamadas de solo lectura: 20. Los detalles agregados están en `x_thread_replies_by_operator.csv`, `x_thread_replies_by_thread.csv`, `x_thread_replies_daily.csv` y `x_thread_replies_districts.csv`. Las ubicaciones son menciones textuales; un nombre distrital homónimo no se considera ubicación resuelta.

## Interpretación para la señal de Win

Una queja individual no es un corte. El valor potencial de X es detectar un aumento de **usuarios distintos que reportan problemas de internet para el mismo operador, en una zona y período**, como corroboración agregada de otra señal técnica. El resultado operacional sería una decisión por zona/segmento, no una creatividad dirigida a quien publicó la queja. Las respuestas del propio operador no cuentan como usuarios afectados.

El conteo de quejas es una señal social que puede incluir problemas del router, facturación, casos individuales o errores de percepción. Los valores de esta muestra no son umbrales ni tasas poblacionales. Se necesita comparar su concentración por zona/tiempo con casos independientes y períodos normales antes de fijar cuánto aumenta la confianza.

## Alcance y límites

- La búsqueda de respuestas `to:HANDLE` solo recoge publicaciones que dirigen respuesta a la cuenta; no equivale a todas las respuestas en hilos de publicaciones oficiales.
- La lectura de hilos por ID cubre solo las publicaciones oficiales muestreadas y las páginas consultadas; no es un censo de X.
- La cuenta oficial peruana no demuestra que cada autor esté en Perú; solo una localización explícita y no ambigua puede aportar geografía.
- La deduplicación de usuarios se hizo en memoria y por operador; no se guardaron identificadores personales.
- No se asigna puntuación numérica ni se afirma que una queja confirme una caída.

Evidencias agregadas archivadas: 20 respuestas en `evidencias/api_responses/twexapi_operator_thread_replies/`; ver referencias en `evidencias/manifest.jsonl`.


## Ampliación: paginación de cronologías y menciones explícitas (25/10/2026)

Para resolver si la página inicial de cronología estaba ocultando hilos, se siguieron hasta cinco páginas de hasta 20 publicaciones por cuenta; se seleccionaron hasta tres hilos nuevos con mayor número de respuestas y se consultó la ruta documentada de respuestas. También se probó por separado una página de menciones explícitas a cada handle. No se mezclan las menciones con `to:cuenta` como si fueran una muestra única.

### Hilos adicionales recuperados

| Operador | Páginas de cronología | Posts con respuestas en la ventana | Hilos nuevos consultados | Respuestas cliente | Quejas explícitas de internet | Menciones de distrito |
|---|---:|---:|---:|---:|---:|---:|
| Movistar | 5 | 0 | 0 | 0 | 0 | 0 |
| Claro | 5 | 3 | 0 | 0 | 0 | 0 |
| Entel | 5 | 0 | 0 | 0 | 0 | 0 |
| Bitel | 5 | 0 | 0 | 0 | 0 | 0 |

### Menciones explícitas a las cuentas

| Operador | Posts únicos | Autores únicos | Quejas explícitas de internet | Menciones de distrito |
|---|---:|---:|---:|---:|
| Movistar | 20 | 18 | 0 | 0 |
| Claro | 20 | 12 | 0 | 0 |
| Entel | 20 | 9 | 0 | 0 |
| Bitel | 20 | 13 | 1 | 0 |

Llamadas adicionales: 24. Resultados por hilo y operador actualizados en los CSV. Totales de `to:cuenta`, menciones y respuestas en hilos **no se suman**: las mismas publicaciones pueden aparecer por más de una vía.
