# Replay de NetFlows de Cloudflare en incidentes de referencia

Se compararon 15 ventanas positivas con el mismo día/hora de la semana anterior. En 9 pares el valor normalizado mediano fue menor durante la ventana de incidente; en 6 fue mayor. El CSV conserva las series, diferencias por puntos, nivel de confianza, IDs y rutas de evidencia.

El control de la semana previa no está verificado como normal. `MIN0_MAX` se calcula de forma común dentro de cada pareja; la diferencia está en unidades normalizadas, no es un porcentaje ni una caída absoluta de tráfico. NetFlows representa tráfico observado por Cloudflare desde el ASN filtrado y no todo el tráfico del operador; el filtro PE no localiza una incidencia por distrito. Por ello esta comparación puede identificar señales candidatas, pero no estima falsos positivos ni valida por sí sola un detector local.

La API documenta NetFlows por ASN, ubicación y fechas en https://developers.cloudflare.com/api/resources/radar/subresources/netflows/methods/timeseries/.
