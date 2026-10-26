# Contraste histórico de eventos anotados de Cloudflare Radar

Se consultó el endpoint oficial de anotaciones de cortes para 15 pares positivos operador-incidente con ventanas horarias. Coincidieron 0/15 anotaciones que incluyen el ASN afectado, ubicación PE e inicio dentro de la ventana. En los 10 pares con referencia de monitoreo OSIPTEL, coincidieron 0.

Esto evalúa anotaciones curadas de cortes, no las series crudas de tráfico ni un detector calibrado. Los casos de referencia no coincidentes no prueban falta general de cobertura: el feed de anotaciones puede no registrar eventos locales o históricos. Sin ventanas normales verificadas no se calcula tasa de falsos positivos; una consulta retrospectiva tampoco revela cuándo Radar publicó por primera vez una anotación.

Los resultados detallados y sus IDs/rutas de evidencia están en `incident_reference_cloudflare_comparison.csv`; el resumen reproducible está en `cloudflare_reference_incident_summary.json`. La API documenta filtros por ASN, país y fechas en https://developers.cloudflare.com/api/resources/radar/subresources/annotations/subresources/outages/methods/get/.
