# Fuentes fuera de la PoC recomendada

**Decisión del 25/10/2026.** Esta lista decide qué entra en la PoC inicial de detección de interrupciones de internet. “Excluir” significa que los resultados actuales no justifican incorporarlo a esa solución; no afirma que el servicio nunca pueda servir para otro propósito. Las evidencias originales se conservan en `evidencias/` para auditoría. No se considera que una consulta vacía pruebe ausencia universal.

## Única entrada que continúa a evaluación

| Fuente | Decisión | Base observada | Rol permitido ahora |
|---|---|---|---|
| Cloudflare Radar NetFlows | **CONTINUAR SOLO EN PoC** | Datos comparables en 15/15 pares; mediana normalizada menor en 9/15 y en 6/8 pares OSIPTEL que incluían internet fijo. El comparador semanal no está etiquetado como normal; no son porcentajes de pérdida ni miden tráfico completo. | Candidato experimental a evaluar contra positivos y períodos normales independientes. No está aprobado como detector ni para activar campañas. |

## Excluidas del detector inicial

| Servicio o grupo | Decisión | Motivo observado |
|---|---|---|
| IODA (eventos y señales por ASN) | EXCLUIR COMO ENTRADA | 1 inicio en 15 pares positivos. La coincidencia de Movistar fijo es un caso aislado y no prueba cobertura suficiente. Se retiene como contraste histórico. |
| Cloudflare Radar, anotaciones de outages | EXCLUIR | 0 coincidencias en 15 pares, incluidos 0/10 casos OSIPTEL. El resultado corresponde a este endpoint y muestra, no a NetFlows. |
| RIPE Atlas | EXCLUIR | Inventario y resultados públicos consultados sin mediciones frescas útiles y atribuibles a los ASN candidatos. |
| Globalping | EXCLUIR | Se comprobó inventario gratuito; no había sondas en los ASN candidatos y no se crearon mediciones. Sin observación atribuible de outage. |
| OONI | EXCLUIR | La muestra peruana consultada no contenía observaciones atribuibles a los ASN candidatos. |
| RIPE RIS Live | EXCLUIR COMO CORROBORACIÓN | Observa anuncios/rutas BGP; misma familia causal que IODA y sin evidencia de impacto al abonado o valor incremental. |
| RIPEstat / Country Stats | EXCLUIR COMO DETECTOR | Aporta inventario y estadísticas de recursos de red, no estado de servicio de internet a clientes. |
| Infobip, Twilio, Telesign y Sinch | EXCLUIR | Sus estados consultados describen incidentes de mensajería globales; no se estableció señal de caída de internet peruana por operador. Voz/SMS seguiría siendo auxiliar solo si una fuente futura entrega incidentes coincidentes, caso que aquí no se demostró. |
| X / TwexAPI (respuestas y quejas agregadas) | CANDIDATA A CORROBORACIÓN; NO APROBADA | Se revisaron tres hilos de Claro: 43 respuestas de clientes, 8 quejas explícitas de internet y 2 menciones de distrito. La pestaña Respuestas de las cuatro cuentas respondió HTTP 200, pero aún no se recuperó contexto de padre de manera utilizable. La muestra no prueba caídas ni representa toda la plataforma. Evaluar concentración de autores distintos por operador × zona × ventana temporal frente a referencias independientes; no usar una publicación individual como disparador. |
| RSS/Atom de medios nacionales | NO APROBAR COMO DISPARADOR; CANDIDATA A CORROBORACIÓN EDITORIAL | Se consultaron feeds RSS/XML de los diez medios online más usados según Reuters Institute 2026. Cinco contenían ítems recientes y ninguno reportó un corte en esa captura; ATV produjo una coincidencia léxica irrelevante y Perú21/ATV estaban atrasados. Una búsqueda histórica encontró una nota de Infobae sobre caída de internet fijo de Win en Lima (15/04/2026), basada principalmente en reportes de usuarios/redes, por lo que no es una referencia independiente y no demuestra que el RSS la emitiera oportunamente. Latina, Exitosa y TV Perú no quedaron accesibles por las rutas probadas. Corroboración potencial, con dependencia de la familia social; no usar como disparador único. Ver `peru_news_top10_rss_check.md`. |
| MTC, INDECI/COEN e Indecopi en canales públicos | EXCLUIR COMO DETECTOR | Identidades/canales oficiales comprobados, pero no se obtuvo señal estructurada y atribuible de interrupción de internet de operador. Indecopi no aportó datos de incidentes. |
| OSIPTEL SISREP/SIVSET como feed | EXCLUIR COMO ENTRADA EN VIVO | Los sistemas no expusieron registros públicos estructurados en las rutas probadas. Avisos públicos de OSIPTEL sí se conservan como referencias históricas de evaluación. |
| Checa tu Señal / cobertura declarada | EXCLUIR COMO SEÑAL DE CAÍDA | Datos de cobertura móvil declarada, con corte trimestral; no indican disponibilidad actual y no demuestran el estado de internet fijo. No sumar a confianza de incidente. |
| USGS | EXCLUIR | Contexto sísmico, sin demostrar caída del servicio de internet; no activa ni corrobora el detector. |
| Nominatim | EXCLUIR COMO SEÑAL | Es geocodificación puntual, no detección de interrupciones. Una muestra pequeña no resuelve la ubicación de la avería. |
| geoBoundaries ADM3 | EXCLUIR COMO BASE DISTRITAL | ADM3 distrital no estuvo disponible en la versión consultada; los niveles ADM1/ADM2 no reemplazan la geometría distrital. |
| IsDown, StatusGator, Downdetector Enterprise, GDELT, M-Lab, Google Trends, TikTok Research API, ThousandEyes, Catchpoint, servicios cloud de anomalías, Outage.Report, Awario, Mentionlytics, Brand24 y scraping/carga manual de OSIPTEL | NO REINCORPORAR EN ESTA PoC | La arquitectura ya los deja fuera por no ofrecer una combinación demostrada de cobertura peruana, acceso automatizable y señal directa de internet. No se reabrieron como candidatos en las pruebas actuales; no presentarlos como evaluados en vivo. |

## Datos auxiliares que sí se conservan

| Recurso | Decisión | Límite |
|---|---|---|
| Avisos oficiales de incidentes OSIPTEL | CONSERVAR COMO REFERENCIAS | Sirven para etiquetar positivos históricos; no se encontró un feed estructurado de incidentes para operación continua. |
| SISCONCODE/UBIGEO 2026 e INEI WFS | CONSERVAR COMO GEOGRAFÍA PARCIAL | Catálogo con 1.893 códigos y 1.890 polígonos INEI cotejados. Faltan 120307, 130112 y 160405 en la capa base; el parche de 130112 es candidato derivado, no geometría oficial publicada. No prometer cobertura distrital completa. |
| Identificación de operadores por ASN | CONSERVAR SOLO COMO ATRIBUCIÓN CANDIDATA | Los ASN probados no representan necesariamente toda la red minorista ni distinguen fijo de móvil. |

## Decisión para el alcance actual

La PoC mantiene **Cloudflare NetFlows** como única entrada técnica experimental, con **OSIPTEL como referencia histórica**, la geografía INEI/UBIGEO como tabla auxiliar parcial y **X como candidata a corroboración agregada, aún no aprobada ni ponderada**. X solo puede aportar si varias personas distintas informan problemas de internet coincidentes por operador, zona y tiempo; no sustituye la evidencia técnica ni activa por sí sola. IODA y los demás servicios excluidos no se incorporan como entradas con los resultados actuales. `reports/approved_sources.json` permanece vacío porque ninguna fuente ha demostrado todavía rendimiento suficiente para operación.

El material actual no permite cerrar precisión, falsos positivos, frescura de primera detección ni valor incremental del detector completo: falta evaluar una regla fijada previamente contra períodos normales independientes. Eso es una limitación de la evidencia y no se maquilla asignando a las fuentes descartadas una utilidad hipotética.
