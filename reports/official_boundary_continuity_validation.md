# Cotejo de continuidad con geometría oficial equivalente

## Fuentes

- WFS distrital oficial del INEI, capa `Interoperabilidad:ig_distrito`: [GetCapabilities](https://geoespacial.inei.gob.pe/Interoperabilidad/ig_distrito/wfs?service=WFS&request=GetCapabilities). Evidencia archivada: `inei_ide_district_wfs_current_2026-1a02b9903c35`. Responde con 1.890 polígonos y fecha común de registro `2022-07-22T01:39:29Z`.
- Registro GeoIDEP de servicios WFS: https://www.geoidep.gob.pe/catalogo-nacional-de-servicios-web/servicio-de-descarga-wfs.
- Servicio oficial de tramos PCM/RENLIM: [FeatureServer](https://services5.arcgis.com/S6BNcv6j9C2h1n1d/ArcGIS/rest/services/RENLIM_POSTGIS/FeatureServer/1/query). Se archivaron 1.233 segmentos como `pcm_renlim_official_segments_2026-7c1f064dbd70`.

## Resultados del WFS INEI

| Control | Resultado |
|---|---:|
| Códigos UBIGEO del catálogo SISCONCODE 2026 | 1.893 |
| Polígonos del WFS | 1.890 |
| Códigos coincidentes | 1.890 |
| UBIGEO sin geometría en el WFS oficial INEI base | 120307, 130112, 160405 (para 130112 ya existe parche candidato local) |
| Polígonos inválidos | 0 |
| Pares con solape de área positivo | 0 |
| Pares con borde compartido | 5.326 |
| Pares con hueco cercano a tolerancia `1e-8` grados | 0 |
| Polígonos sin vecino dentro de tolerancia | 2 (Anapia 211302 y Amantaní 210103; islas confirmadas) |
| Componentes conectados de la red de límites | 10 |
| Diferencias de área simétrica máxima vs GeoPackage INEI archivado | 3.9503e-08 grados² |
| Diferencias de área simétrica media | 2.2426e-09 grados² |

Las coordenadas no son idénticas punto por punto; las diferencias de área simétrica son pequeñas. No se confunde redondeo/precisión de coordenadas con discrepancia de código. Los controles de topología demuestran continuidad de los límites compartidos entre las geometrías disponibles, con dos polígonos aislados que corresponden a Anapia y Amantaní; Mincetur los documenta como distritos/islas del Titicaca ([Anapia](https://consultasenlinea.mincetur.gob.pe/fichaInventario/index.aspx?cod_Ficha=11759), [Amantaní](https://consultasenlinea.mincetur.gob.pe/fichaInventario/index.aspx?cod_Ficha=958)). Se resuelve así la anomalía como geografía insular esperada, no como hueco topológico.

## Diferencias de nombres

El WFS y el catálogo 2026 difieren en seis nombres normalizados: `010517` San Francisco de Yeso / San Francisco del Yeso; `250201` Raymondi / Raimondi; `051010` Hualla / Huaya; `030407` Ihuayllo / Huayllo; `060506` Santa Cruz de Toledo / Santa Cruz de Toled; `050707` San Francisco de Rivacayco / San Francisco de Ravacayco. Se preservan ambas variantes para resolverlas con la fuente administrativa competente; no se normalizan por conjetura.

## Alcance

El cotejo oficial de continuidad queda ejecutado para los 1.890 polígonos presentes. El WFS comparte cobertura/vintage de la capa distrital INEI disponible, por lo que no constituye una fuente independiente ni completa el catálogo 2026. No se ha validado el perímetro exterior del país contra una geometría independiente, ni se han creado geometrías para los tres UBIGEO sin polígono. RENLIM se archivó como registro oficial de tramos, pero no se interpreta como una cobertura poligonal equivalente ni se afirma que se haya completado un overlay nacional línea-polígono. El detalle reproducible está en `official_boundary_continuity_validation.json`.


## Geometría candidata para Alto Trujillo (130112)

El servicio oficial PCM/RENLIM contiene cuatro tramos: Alto Trujillo–Huanchaco, Alto Trujillo–El Porvenir, Alto Trujillo–La Esperanza y Alto Trujillo–Florencia de Mora, asociados a la Ley 31644. Los cuatro polygonizan un anillo cerrado y válido. El artefacto `evidencias/geographic/district_boundary_candidates/alto_trujillo_pcm_candidate_patch.geojson` añade el polígono 130112 y recorta el área correspondiente de las geometrías antiguas 130102 y 130104. La unión de área antes y después difiere en `2.89e-18` grados²; no quedan solapes positivos entre las tres geometrías y el candidato no sale del área original. Evidencia: `alto_trujillo_pcm_candidate_patch-2385d8e15210`.

El WFS INEI tiene registro de 2022-07-22, anterior a la creación de Alto Trujillo. El parche completa el candidato en ese sector, pero no es una capa nacional INEI publicada para 2026. Para Sangani (120307), la Ley 32729 contiene memoria UTM y anexo cartográfico, pero no hay vector completo en los servicios probados. Para Santa Rosa de Loreto (160405), los dos segmentos PCM publicados no cierran un polígono; no se infiere el límite exterior faltante.
