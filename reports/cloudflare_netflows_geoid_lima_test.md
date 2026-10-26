# Cloudflare NetFlows con filtro GeoID de Lima

La API respondió HTTP 200 para los cuatro ASN y entregó 668 puntos por serie. **Eso valida acceso y aceptación sintáctica del filtro, pero no valida cobertura útil:** los puntos de la serie Lima actual fueron cero para Movistar, Claro, Entel y Bitel; las cuatro respuestas tuvieron contenido idéntico. Una respuesta en ceros no prueba que el servicio estuviera caído ni que la ciudad no tuviera tráfico de internet. La cobertura geográfica y la diferenciación por operador para esta consulta quedan **sin demostrar**.

Como control, durante el mismo periodo el NetFlows de todo Perú y el filtro Perú + AS6147 devolvieron series no nulas y diferentes. La consulta con GeoID de Lima volvió a ceros incluso sin filtro ASN. Esto apunta a falta de observaciones utilizables en esa serie de ciudad, por lo que **no se recomienda usarla para activar creatividades**.

| Operador | ASN | HTTP | Puntos | Puntos actuales en cero | Respuesta compartida |
|---|---:|---:|---:|---:|---|
| Movistar | AS6147 | 200 | 668 | 668 | Sí |
| Claro | AS12252 | 200 | 668 | 668 | Sí |
| Entel | AS21575 | 200 | 668 | 668 | Sí |
| Bitel | AS262210 | 200 | 668 | 668 | Sí |

Cloudflare documenta `geoId` como identificador GeoNames y `asn` como filtro ASN en NetFlows. La documentación confirma que esos parámetros existen, pero los datos devueltos aquí no demuestran cobertura funcional en Lima ([referencia oficial de la API](https://developers.cloudflare.com/api/resources/radar/subresources/netflows/methods/timeseries/)).

**Alcance probado:** consulta remota aceptada. **No probado:** observabilidad de tráfico en Lima, atribución fiable a cada operador dentro de ese GeoID, detección de interrupciones, segmentación por distrito UBIGEO o disponibilidad de internet de usuarios finales. Los intentos que combinaron `location=PE` y `geoId` se rechazaron por filtro repetido; las pruebas posteriores sin `location=PE` son las resumidas aquí.

Las respuestas e IDs de evidencia están en el CSV/JSON y en `evidencias/manifest.jsonl`.
