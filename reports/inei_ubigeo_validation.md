# Catálogo UBIGEO vigente del INEI

SISCONCODE versión 2026 se consultó en su sitio oficial y se recorrió jerárquicamente con 222 respuestas HTTP 200 archivadas. La exportación contiene 1,893 filas distritales, 1,893 códigos únicos y cero duplicados. El código 120307 corresponde a Sangani, Junín, y aparece en esta versión. La Ley 32729 se archivó como `sangani_creation_law_ley_32729-a92ce719b3de`.

El catálogo se cruzó código por código con la capa distrital INEI IDE de vintage 2023: 1,890/1,893 códigos tienen polígono (99.8415%); faltan 120307, 130112, 160405. No hay códigos geométricos fuera del catálogo 2026. Las diferencias normalizadas de nombre en la jerarquía de atributos son 13; el detalle está en `inei_sisconcode_2026_geometry_crosswalk.csv`.

El WFS distrital oficial en vivo del INEI (`Interoperabilidad:ig_distrito`) devolvió los mismos 1.890 códigos que el GeoPackage disponible, con 0 polígonos inválidos, 0 solapes de área positivos, 5.326 pares de bordes compartidos y 0 pares con hueco candidato a tolerancia 1e-8 grados. Hay 2 polígonos sin vecino dentro de esa tolerancia y 10 componentes de red, que se dejan señalados para revisión; la prueba no incluye los tres distritos ausentes. El WFS tiene fecha de registro 2022-07-22 y cobertura equivalente a la capa INEI previa, así que valida topología de la geometría disponible, no aporta una geometría independiente 2026. Se detectaron seis variantes de nombre entre el distrito WFS y SISCONCODE 2026. El servicio oficial PCM/RENLIM se archivó con 1.233 tramos; por ser una capa lineal registral no se afirma que complete la cobertura poligonal. El detalle, incluyendo límites del cotejo, está en `official_boundary_continuity_validation.md` y `.json`. MINAM también se comparó y resultó una capa histórica que no cubre los códigos recientes. geoBoundaries ADM1/ADM2 se contrastó por nombres; no aporta polígonos ADM3 ni un cruce distrital por UBIGEO.

Archivos: `inei_sisconcode_ubigeo_2026.csv`, `inei_sisconcode_ubigeo_2026.json`, `inei_sisconcode_2026_geometry_crosswalk.csv`, `minam_ubigeo_crosscheck.json`, `geometry_topology_validation.json` y `ubigeo_legal_references.json`. Evidencias de todas las consultas SISCONCODE están listadas en el JSON.


## Resolución de anomalías y polígonos nuevos

Los dos polígonos sin vecino a tolerancia 1e-8 grados son Anapia (`211302`) y Amantaní (`210103`). Mincetur documenta ambos como distritos insulares/islas del Titicaca ([Anapia](https://consultasenlinea.mincetur.gob.pe/fichaInventario/index.aspx?cod_Ficha=11759), [Amantaní](https://consultasenlinea.mincetur.gob.pe/fichaInventario/index.aspx?cod_Ficha=958)); se clasifican como aislamiento esperado.

Para Alto Trujillo (`130112`) se produjo un parche reproducible con cuatro tramos oficiales PCM/RENLIM. Es válido, sin solapes, y conserva el área unionada de los antiguos padres `130102` y `130104` dentro de `2.89e-18` grados². Es un candidato local, no una capa nacional oficial publicada. Para Sangani (`120307`) y Santa Rosa de Loreto (`160405`) no se obtuvo geometría vectorial completa en los servicios probados; el reporte de continuidad describe las fuentes legales y los límites de cada una.
