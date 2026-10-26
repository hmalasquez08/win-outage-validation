# Comprobación actual de sondas RIPE Atlas en los ASN objetivo

Consulta pública de solo lectura realizada el 2026-10-25T08:26:00.059285+00:00. Se revisaron sondas conectadas en Perú, se cotejaron sus ASN en memoria con polígonos distritales INEI y solo se guardaron conteos; no se conservaron identificadores, nombres de distrito ni coordenadas.

| Operador | Sondas conectadas en su ASN | Distritos con sonda | Asignación de distrito incierta |
|---|---:|---:|---:|
| Movistar | 1 | 1 | 1 |
| Claro | 2 | 2 | 0 |
| Entel | 2 | 2 | 0 |
| Bitel | 0 | 0 | 0 |

## Lectura

Atlas sí tiene presencia técnica en tres operadores, pero solo de una o dos sondas/distritos por ASN y ninguna en Bitel. Eso sirve para una prueba pequeña, no para sostener cobertura de interrupciones por zona. Una sonda conectada tampoco significa que haga una prueba reciente ni que represente a los clientes del distrito.

En la revisión anterior de mediciones Atlas, los resultados más recientes devueltos fueron 0 en las cinco mediciones en curso muestreadas para Movistar, Claro y Entel (`reports/atlas_latest_results.csv`, consultado el 24 oct 2026). La prueba actual solo inventarió sondas; no creó mediciones. La API Atlas puede listar resultados existentes por medición y sonda, pero para conseguir series regulares desde esas conexiones habría que tener mediciones activas y resultados recientes. La documentación separa objetos de medición y resultados: [RIPE Atlas: mediciones](https://atlas.ripe.net/docs/apis/rest-api-manual/measurements/) y [resultados](https://atlas.ripe.net/docs/apis/rest-api-manual/measurements/results-and-latest/).

## Qué hace falta para una prueba zonal útil

Aumentar los puntos de medición en los cuatro ASN y las zonas objetivo, con mediciones periódicas de conectividad a destinos estables. Atlas puede probarse primero donde ya hay sondas, pero con esta densidad no cubre Bitel ni da cobertura amplia por distrito. Si se requiere cobertura de más zonas, hace falta desplegar sondas propias o contratar/acceder a una red de medición que ofrezca puntos por ASN y geografía. Cada incidente deberá compararse con varias sondas independientes; la desconexión de una sola sonda no debe activar una zona.

El procesamiento puede hacerse con Python y `httpx` (lectura de APIs), `pandas` (ventanas y agregación) y `shapely` (asignación de puntos a UBIGEO). No hay una librería que sustituya el despliegue y la densidad de las sondas.
