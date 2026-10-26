# Opciones de servicios y software para obtener señales de activación

**Fecha de investigación:** 25 de octubre de 2026  
**Propósito:** ampliar la búsqueda más allá de los servicios ya ensayados y evaluar qué opciones pueden aportar evidencia útil para una futura activación por operador y zona. Esta revisión no convierte ninguna fuente en aprobada ni produce una activación.

## Respuesta corta

Sí existen caminos técnicamente plausibles, pero cumplen funciones distintas:

1. **Para obtener experiencia móvil de usuarios en Perú con geografía detallada:** Opensignal ONX es la alternativa comercial más prometedora para solicitar una muestra técnica o sandbox. Su producto describe mediciones reales de usuarios, análisis por geografía y datos integrables; sus informes públicos cubren Movistar, Claro, Entel y Bitel. No se obtuvo acceso al flujo de datos ni se verificó que entregue eventos con latencia adecuada para activar campañas.
2. **Para señales de pruebas de velocidad con operador, ubicación y feed cercano al tiempo real:** Ookla Speedtest Intelligence/SDK es otra candidata fuerte, especialmente por el soporte anunciado a pruebas fallidas o parciales y feeds. La información pública no demuestra que el producto entregue a Win los campos y la granularidad necesarios en Perú. No se probó una cuenta ni un feed.
3. **Como opción abierta comprobada en esta máquina:** Globalping ejecutó mediciones desde Lima, pero no encontró sondas en ninguno de los cuatro ASN objetivo. Sirve para contexto de conectividad regional o diagnóstico de rutas, no para confirmar una caída de Movistar, Claro, Entel o Bitel.
4. **Como medición propia sin equipos dedicados:** un componente opcional en una app o propiedad web participante puede observar conectividad y fallos reales de sus usuarios conectados. Las observaciones deben agregarse por cohorte, operador inferido y zona; no permiten reportar instantáneamente desde un dispositivo que quedó completamente desconectado.
5. **Para sostener la hipótesis de rendimiento:** M-Lab NDT/HERMES ofrece medidas reales de velocidad y RTT, pero los resultados públicos se archivan aproximadamente al día siguiente y HERMES agrega por día. Es mejor para evaluación histórica, calibración y degradaciones sostenidas que para un trigger de minutos.

## Requisitos de una señal que pueda contribuir a la activación

Una observación útil para el detector integrado debe permitir comprobar, al menos:

- qué operador o red de acceso observó;
- si mide internet y, cuando sea posible, si es móvil o fijo;
- cuándo ocurrió y cuándo estuvo disponible para el motor;
- qué geografía representa y si es observada o inferida;
- número de dispositivos/mediciones detrás del agregado;
- qué fallos o anomalías se observaron y cómo se comparan con el comportamiento normal.

Una API que responde, una prueba aislada que falla o una caída de tráfico agregado no bastan por sí solas para inferir que los clientes de un operador en un distrito perdieron internet.

## Evaluación de nuevas opciones

| Opción | Qué puede aportar | Evidencia examinada o prueba | Dictamen para Win |
|---|---|---|---|
| **Globalping (API y software abierto)** | Ping, DNS, HTTP y trazas desde sondas distribuidas; el resultado identifica ciudad, ASN y tipo de sonda. | Inventario archivado a las 10:41 UTC: 5,364 sondas online globales, 7 en Perú, todas en Lima. Ninguna estaba en AS6147, AS12252, AS21575 o AS262210. Se hizo una prueba de ping desde cinco sondas peruanas a 1.1.1.1: cuatro respondieron sin pérdida y una perdió los tres paquetes. Las consultas de selección por cada ASN operador devolvieron HTTP 422 `no_probes_found`. | **No sirve hoy como detector por operador peruano.** Puede ser un verificador externo de conectividad/ruta desde Lima o detectar problemas comunes a varias redes, con riesgo de confundir una sonda o ruta particular con una caída. No es sustituto de mediciones desde las redes de clientes. |
| **Opensignal ONX / ONX Broadband** | Mediciones de experiencia real de usuarios; declara métricas de conectividad/calidad y análisis geográfico, con opciones de integración de datos. Su oferta Broadband está dirigida a experiencia fija. | La metodología pública documenta pruebas de experiencia en dispositivos y mediciones automatizadas con consentimiento. El informe público de Perú de febrero de 2025 contiene a los cuatro operadores móviles. ONX describe cambios de experiencia casi en tiempo real, datos geográficos detallados e integración; no se tuvo acceso a su dataset/API para medir frecuencia, cobertura por departamento, lag ni casos fallidos en Perú. | **Candidata prioritaria para una prueba técnica de proveedor.** Pedir una muestra/sandbox de registros anonimizados con hora del evento y de publicación, operador, tecnología, geografía, volumen de muestra y fallos de conectividad; validar por separado disponibilidad de fijo y móvil y la cadencia real. Las afirmaciones comerciales no se tratan como resultados ya comprobados. |
| **Ookla Speedtest Intelligence / Web SDK** | Pruebas de rendimiento de banda ancha fija y móvil; referencias públicas del producto mencionan segmentación por operador/ubicación, pruebas fallidas o parciales y feed de datos cercano al tiempo real. | La ficha pública del SDK indica que los resultados pueden entregarse al servidor del cliente o mediante extracto/feed; para la muestra privada se necesita acceso del proveedor. El dataset público de Ookla descrito por World Bank es trimestral y agregado en mosaicos geográficos, por lo cual no vale para alertas inmediatas. No se consultó un feed privado ni se verificó su cobertura por operador en Perú. | **Candidata prioritaria junto con Opensignal.** Técnicamente parece alinearse con señal de rendimiento y fallos; la confirmación depende de obtener una muestra de feed peruano y comprobar latencia, campos de tipo de acceso, granularidad, volumen y proporción de tests incompletos. La serie pública trimestral sirve para contexto/baseline, no para el trigger. |
| **M-Lab NDT7 / HERMES** | Tests de velocidad, pérdida/latencia y agregados de anomalías por red y geografía. NDT7 puede integrarse en software web/móvil; su data pública permite análisis retrospectivo. | HERMES está en BigQuery y publica normalmente los resultados del día anterior una vez al día; la resolución es diaria. Las pruebas NDT son iniciadas por usuarios. En el proyecto ya se halló una anomalía diaria de Claro en Ica, pero el cotejo NetFlows del mismo evento no pasó la regla persistente. | **Sí aporta datos reales, pero no como fuente rápida de activación.** Mantener para replay, análisis de degradaciones sostenidas o test optativo iniciado por el usuario. Una prueba de velocidad activa consume ancho de banda y no debe lanzarse en segundo plano sin decisión y consentimiento de producto. |
| **Instrumentación opcional en app/PWA/web participante** | Estado de conectividad, fallos de solicitudes, tiempos de respuesta y recuperación observados en usuarios reales que usan esa propiedad. Android expone callbacks de estado de red; el navegador puede enviar pequeños eventos cuando vuelve a tener conexión y el Service Worker puede conservar recursos previamente almacenados. | Documentación oficial de Android confirma callbacks del estado de red. La documentación web describe `sendBeacon()` para eventos analíticos y sincronización en segundo plano al volver la conectividad; la API Network Information del navegador tiene disponibilidad limitada. No se instaló un SDK ni se recopilaron eventos de usuarios. | **Viable como señal propia complementaria** si Win dispone de una app/web con suficiente tráfico o socios que integren un SDK. No genera instantáneamente evidencia desde el dispositivo totalmente offline: puede mostrar contenido que ya estaba cacheado en una app/PWA, pero el envío de esa observación al motor espera a que vuelva la conexión. No atribuye por sí solo el operador fijo/móvil. |
| **OONI y herramientas de censura/medición** | Detectan anomalías de acceso a servicios/destinos concretos desde probes voluntarias; conjuntos de datos abiertos para análisis. | La prueba del proyecto encontró una página muestral de Perú sin mediciones en los ASN objetivo y sin cobertura continua. La documentación de OONI describe sus mediciones como pruebas ejecutadas por OONI Probe y no como monitor general de disponibilidad del ISP. | **No priorizar para este caso.** Útil para bloqueo/interferencia de destinos, no una medición de disponibilidad general del operador que pueda activar por distrito. |

## Prueba reproducible de Globalping

La llamada por operador se repitió para cada ASN y produjo `no_probes_found` en los cuatro casos. La prueba general de Lima sí se completó desde sondas de varias redes, lo que demuestra que el servicio y su API funcionan, pero no que sus sondas representen a los clientes de esos operadores.

| Operador / red | ASN | Selección de sonda dentro de Perú | Resultado |
|---|---:|---|---|
| Movistar | 6147 | Ninguna | HTTP 422, `no_probes_found` |
| Claro | 12252 | Ninguna | HTTP 422, `no_probes_found` |
| Entel | 21575 | Ninguna | HTTP 422, `no_probes_found` |
| Bitel | 262210 | Ninguna | HTTP 422, `no_probes_found` |

El ping general a 1.1.1.1 alcanzó 5 sondas listadas en Perú; las respuestas incluyeron redes de centros de datos y una sonda identificada como Red Científica Peruana. Las cinco pruebas terminaron: cuatro tuvieron 0% de pérdida y una 100% de pérdida en solo tres paquetes; esto último es evidencia de una sonda/ruta sin respuesta en esa prueba, **no** un incidente general de Perú ni de un operador objetivo. Los resultados de pruebas activas son públicos y la plataforma aplica límites de uso.

## Qué solución parece técnicamente más viable

La opción con mejor fundamento práctico es **combinar una fuente poblacional de experiencia real con una segunda familia independiente y agregar todo antes de seleccionar una zona**:

1. Probar primero un dataset o sandbox técnico de Opensignal ONX y Speedtest Intelligence, porque ambos se basan en experiencia real de dispositivos y describen datos de red/ubicación; comparar muestras bajo los mismos incidentes históricos.
2. Mantener Cloudflare NetFlows como señal agregada experimental para los cuatro ASN, no como verdad de última milla. La validación histórica del proyecto ya muestra candidatos en algunos incidentes, pero no estima con controles normales independientes la precisión real.
3. Usar quejas públicas y avisos institucionales solo como corroboración colectiva cuando coincidan en operador, zona y tiempo; nunca usar una queja individual como orden de activación.
4. Si existe una app, sitio o socio con audiencia suficiente, evaluar un SDK de medición liviano y voluntario que agregue fallos de conectividad y recuperación. Medir impacto en batería/datos, tamaño de muestra, atribución de proveedor y sesgo de la audiencia antes de ponderarlo.
5. Emitir un evento local de prueba solo cuando la señal principal sea reciente y geográficamente compatible, y haya corroboración que no dependa del mismo conjunto de datos. El formato de salida se define después de demostrar este cruce con datos reales.

### Límite fundamental de entrega

Si el dispositivo está totalmente sin conexión, no puede solicitar una creatividad nueva al servidor por esa conexión. Una app o PWA puede mostrar una creatividad o pantalla que ya tenga almacenada localmente; para segmentar a usuarios que siguen conectados en una zona afectada, el motor puede orientar inventario disponible en esa zona cuando su canal de anuncios aún funcione. El detector y la entrega offline son dos capacidades distintas.

## Próximas validaciones técnicas recomendadas

1. Obtener y analizar un extracto de prueba de **Opensignal ONX** y **Ookla Speedtest Intelligence** para Perú, sin comprometer una selección antes de ver datos. El extracto debe incluir operadores objetivo, timestamps de evento/ingesta, fijo/móvil, unidad geográfica, recuento de muestras y mediciones fallidas/parciales.
2. Ejecutar el mismo replay de incidentes independientes del proyecto sobre esas muestras y sus ventanas normales; no aceptar una métrica comercial agregada si no puede enlazarse al timestamp, operador y zona del incidente.
3. Medir si un componente propio en una propiedad real de Win tendría suficiente volumen por operador × zona × ventana sin hacer tests pesados de velocidad por defecto.
4. Combinar solo las familias que aporten detecciones nuevas o reduzcan candidatos falsos en positivos y controles; conservar una decisión `SUPPRESSED` cuando falte frescura, atribución o corroboración.

## Evidencia archivada del sondeo Globalping

| Consulta | Evidence ID | Resultado | SHA-256 |
|---|---|---|---|
| Inventario actual de sondas Globalping | `globalping_probe_inventory_current-0eaf8d502b64` | HTTP 200; 5,364 sondas globales, 7 de Perú; 0 de los cuatro ASN objetivo | `0eaf8d502b648cb40acd937f2651cc5b99a4561402bf8cda988ba388449847b3` |
| Ping desde sondas de Perú a 1.1.1.1 | `globalping_peru_candidate_ping-a02f9c5f22f1` | HTTP 200; respuesta agregada minimizada; 5 sondas seleccionadas | `a02f9c5f22f15872f6760899b52e5d20673d5b25215c9b867664098e5f04573a` |
| Selección de sonda Movistar | `globalping_operator_probe_movistar-3ee1dd61014a` | HTTP 422; sin sonda coincidente | `3ee1dd61014ab9dc2587bba555a7618f117663beb50ebc1b682f27cbbe9e79ac` |
| Selección de sonda Claro | `globalping_operator_probe_claro-3ee1dd61014a` | HTTP 422; sin sonda coincidente | `3ee1dd61014ab9dc2587bba555a7618f117663beb50ebc1b682f27cbbe9e79ac` |
| Selección de sonda Entel | `globalping_operator_probe_entel-3ee1dd61014a` | HTTP 422; sin sonda coincidente | `3ee1dd61014ab9dc2587bba555a7618f117663beb50ebc1b682f27cbbe9e79ac` |
| Selección de sonda Bitel | `globalping_operator_probe_bitel-3ee1dd61014a` | HTTP 422; sin sonda coincidente | `3ee1dd61014ab9dc2587bba555a7618f117663beb50ebc1b682f27cbbe9e79ac` |

Otras referencias verificables: [Globalping API y límites](https://github.com/jsdelivr/globalping/blob/master/public/v1/spec.yaml), [M-Lab HERMES: cadencia y cobertura](https://www.measurementlab.net/tests/hermes/quickstart/), [M-Lab NDT7 e integración](https://github.com/m-lab/knowledgebase/blob/main/src/content/articles/test-ndt.md), [Opensignal ONX](https://www.opensignal.com/onx), [metodología de experiencia Opensignal](https://www.opensignal.com/our-approach), [informe de Perú de Opensignal](https://insights.opensignal.com/reports/2025/02/peru/mobile-network-experience), [SDK web de Speedtest en npm](https://www.npmjs.com/package/@ookla/speedtest-js-sdk), [Android ConnectivityManager](https://developer.android.com/reference/android/net/ConnectivityManager), [Beacon API](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/sendBeacon), [Background Synchronization](https://developer.mozilla.org/en-US/docs/Web/API/Background_Synchronization_API) y [Service Worker](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API).


## Pruebas ejecutadas y resultado (25 de octubre de 2026)

| Opción | Prueba observada | Qué demuestra | Decisión para el trigger |
|---|---|---|---|
| **OSIPTEL, Checa tu internet móvil** | Se abrió el tablero público y se consultó su vista Perú, septiembre de 2026, 4G. Mostró velocidad de subida/bajada, tiempo de cobertura, latencia, pérdida de paquetes y ranking, desglosados por Movistar, Claro, Entel y Bitel; también se eligió la región Lima y el panel recalculó los valores por operador. | Existe una fuente real, pública, con operador y geografía regional para experiencia móvil. La presentación mensual está aproximadamente un período mensual detrás del día de consulta; el informe público indica más de 150 millones de mediciones mensuales en más de 600 distritos. | **No activa caídas en tiempo real.** Mantener para baseline/calibrar y para contexto de degradación móvil. No representa internet fijo y sus medias mensuales no prueban una interrupción actual. El tablero muestra selectores de provincia/distrito, pero esta prueba no logró obtener una tabla distrital. La descarga del dataset quedó cargando/deshabilitada y no apareció un archivo descargado; no quedó probada una exportación masiva automatizable. |
| **M-Lab Locate + NDT7** | GET de Locate v2 para país PE respondió HTTP 200 y devolvió dos servidores cercanos en Lima; la evidencia guardada elimina los tokens de sesión. No se ejecutó NDT7 sobre la conexión del usuario. | Una web/app participante puede resolver un servidor peruano y lanzar pruebas propias desde software. Los clientes abiertos disponibles incluyen JavaScript, Go, Android e iOS. | **Complemento técnico viable solo como test voluntario iniciado por el usuario**. Una prueba consume ancho de banda y no es una observación pasiva; el archivo público de resultados aparece alrededor de 24 h después. El resultado mostrado por la app de Win podría recibirse al terminar y servir como señal fresca de ese usuario, pero no permite detección representativa por zona sin suficiente audiencia y agregación. |
| **Ookla Open Data (Q3 2026)** | HEAD de los objetos Parquet públicos de fijo y móvil respondió HTTP 200. Ambos archivos existen; fechas de última modificación 9 oct 2026; tamaños 189.6 MB móvil y 365.1 MB fijo. No se descargó el contenido. | Hay agregados geográficos de resultados Speedtest para los dos tipos de acceso, actualizados trimestralmente. Su esquema público resume promedio de velocidad/latencia, número de tests/dispositivos y tile; no identifica operador ni fila de falla individual. | **No sirve como trigger** por agregación trimestral y falta de operador; sí para comparaciones históricas/espaciales generales. La disponibilidad de un feed privado de Intelligence no se probó. |
| **Opensignal ONX / Speedtest Intelligence privado** | Se revisó lo público; no hay credenciales de proveedor, dataset de prueba o sandbox disponible en esta sesión. | La documentación comercial describe capacidades, pero no valida que estén accesibles para Perú ni que expongan los campos/latencia que necesitamos. | **No confirmados.** No afirmar capacidad de integración o rendimiento sin una muestra real. Si se habilita prueba técnica, solicitar datos anonimizados con evento/ingesta, operador, tecnología, zona y cantidad de muestras. |
| **Telemetría ligera en propiedad digital participante** | No se instaló código ni había una app/propiedad de Win identificada con acceso al repositorio y volumen de usuarios para observar. | Desde software se podrían agregar fallos de navegación/solicitudes y estado de red; los mensajes en cola solo llegarían al recuperar conectividad. Un SDK también podría inferir ASN por IP mientras hay conexión, pero no identifica con certeza el acceso fijo detrás de Wi-Fi. | **Mejor ruta para conseguir observación fresca en producto, todavía no probada en audiencia real.** Antes de usarla como detector hacen falta integración en una app/web participante, conteos por zona/operador y medición de sesgo/cobertura. Una desconexión total tampoco puede pedir un anuncio nuevo por esa misma conexión; puede mostrarse contenido previamente almacenado. |

### Lectura de decisión

De las fuentes públicas nuevas probadas, **OSIPTEL y M-Lab sí aportan datos reales**, pero con roles distintos: OSIPTEL aporta una referencia móvil mensual por operador/región; M-Lab permite obtener una medida puntual iniciada voluntariamente desde software. **Ookla Open Data no aporta tiempo ni operador suficientes para activar.** ONX e Intelligence siguen siendo posibilidades de proveedor sin feed comprobado. Para una señal actual y escalable por zona, la ruta técnica que puede construirse sin hardware dedicado es agregar telemetría ligera de usuarios reales que ya usan una propiedad digital participante, y cruzarla con NetFlows/Radar/X existentes; esto aún requiere instrumentación y validación con volumen real.

La consulta directa no autenticada a los endpoints de datos del tablero OSIPTEL devolvió HTTP 401; no se reconstruyó su mecanismo interno de navegador. Los valores citados aquí se leyeron desde la interfaz pública. La selección de distrito queda pendiente de extracción/validación independiente y la descarga de dataset no terminó en la prueba.

### Evidencias nuevas

- Observación agregada OSIPTEL: `evidencias/api_responses/osiptel_mobile_dashboard/20261025_dashboard_observation.json` (incluye tabla nacional y de Lima).
- M-Lab Locate v2, respuesta saneada sin tokens: `evidencias/api_responses/mlab_locate_pe_test/`.
- Metadatos HEAD de Ookla fijo/móvil Q3 2026: entradas `ookla_fixed_q3_2026` y `ookla_mobile_q3_2026` en `evidencias/manifest.jsonl`; se guardó metadato, no el archivo de cientos de MB.


Fuentes primarias para estas pruebas: [tablero OSIPTEL](https://checatuinternetmovil.osiptel.gob.pe/), [reporte OSIPTEL de agosto 2026 y volumen de mediciones/distritos](https://sociedadtelecom.pe/2026/09/12/panel-de-monitoreo-de-internet-movil-analisis-de-indicadores-a-nivel-departamental-agosto-2026/), [guía oficial de desarrollo M-Lab](https://www.measurementlab.net/develop/), [integración NDT7 en app/web](https://www.measurementlab.net/tests/ndt/), [repositorio de datos abiertos de Ookla](https://github.com/teamookla/ookla-open-data).
