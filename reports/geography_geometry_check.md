# Validación estructural de geometrías geoBoundaries

Evidencia derivada: `geoboundaries_geometry_inventory-9c76ba67f6eb`. Fuente original: GeoJSON archivados dentro de `evidencias/api_responses/`.

| Nivel | Features | Tipos | CRS declarado | Extensión lon/lat | Anillos sin cerrar | Vacíos |
|---|---:|---|---|---|---:|---:|
| geoboundaries_adm1_geojson | 26 | {'Polygon': 24, 'MultiPolygon': 2} | {'type': 'name', 'properties': {'name': 'urn:ogc:def:crs:OGC:1.3:CRS84'}} | [-81.3276984651909, -18.359439638481717, -68.64281794578261, -0.014090115964791] | 0 | 0 |
| geoboundaries_adm2_geojson_full | 196 | {'Polygon': 193, 'MultiPolygon': 3} | {'type': 'name', 'properties': {'name': 'urn:ogc:def:crs:OGC:1.3:CRS84'}} | [-81.32823048999995, -18.35092773599996, -68.65227910299996, -0.038605967999956] | 0 | 0 |

Se recorrieron pares de coordenadas y estructura de anillos. La extensión es compatible con ubicación en Perú y las respuestas declaran OGC CRS84 (ejes longitud/latitud); GeoJSON sin CRS explícito se interpreta normalmente en WGS84, pero aquí la fuente sí incluye CRS84. No se hizo validación topológica de auto-intersecciones ni de solapes entre polígonos. ADM1 contiene 26 features y ADM2 196; esto no demuestra correspondencia exacta con las unidades administrativas vigentes. Las propiedades no incluyen campo UBIGEO detectable en el primer feature inspeccionado; el cruce de nombres/códigos queda pendiente hasta validar y archivar un catálogo INEI vigente. ADM3 no está disponible en el endpoint probado (404).


## Cotejo oficial INEI en vivo (2026-10-25 UTC)

El WFS distrital oficial devolvió 1.890 geometrías con los mismos UBIGEO de la capa local archivada: 0 inválidas, 0 solapes de área positivos, 5.326 pares con borde compartido y 0 huecos candidatos a 1e-8 grados. Dos polígonos no tienen vecino en esa tolerancia; el grafo de límites tiene 10 componentes. Faltan geometrías para 120307, 130112 y 160405. El servicio PCM/RENLIM se archivó como referencia oficial de 1.233 tramos, sin afirmar un overlay exhaustivo. Alcance completo y discrepancias de nombres: `official_boundary_continuity_validation.md`.
