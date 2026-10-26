# Acceso y cuota de TwexAPI

La autenticación Bearer y el endpoint de búsqueda respondieron HTTP 200 para nueve cuentas verificadas. Se respetó un intervalo de al menos 5,1 segundos entre solicitudes. La documentación pública describe 20,000 créditos Starter, 7 días de validez, 0.2 QPS y 5 créditos por búsqueda sin resultados; las 18 consultas de esta ronda representarían aproximadamente 90 créditos según ese precio publicado. No se consultó de nuevo el saldo al cierre; el saldo exacto posterior no está observado. No se hicieron solicitudes de escritura.

La recuperación técnica funciona, pero las respuestas vacías no prueban ausencia de publicaciones. Las respuestas con resultados se guardan minimizadas; no se conserva texto, ID ni identificador de usuario. Evidencias de consultas: `x_official_accounts_inventory.csv` y `evidencias/manifest.jsonl`.
