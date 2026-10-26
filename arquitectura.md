# Arquitectura técnica: detección de caídas de operadores en Perú para formatos trigger (Win)

**Versión:** 9.14  
**Fecha:** 24 de octubre de 2026  
**Estado:** evaluación de viabilidad técnica y validación local; no es producción ni prueba de concepto desplegada.


> **EDICIÓN FINAL CONSOLIDADA v9.14 — 24/10/2026.** Este archivo es la única especificación de trabajo para un agente de programación aún no elegido. El trabajo ejecutable es **solo una prueba de viabilidad de fuentes (PoC de validación)**, no el desarrollo de la plataforma Win. No se integra LLM en el software validado, no se despliega GCP y no se generan activaciones. Todas las afirmaciones de cobertura por operador deben basarse en respuestas observadas, fechadas y guardadas; los antecedentes citados no son validaciones realizadas por el agente.

## Portabilidad de implementación

- Especificación **agnóstica de LLM, proveedor y agente**: no depende de Claude, OpenAI, DeepSeek ni un servicio de inferencia concreto.
- Los conectores y validadores se implementan en Python estándar con interfaces documentadas; ninguna llamada a modelos de IA es obligatoria para validar las fuentes.
- Toda configuración, estado de progreso, decisiones, pruebas y evidencias deben persistirse en archivos versionables para poder cambiar de agente sin perder contexto.
- No usar archivos de instrucciones propietarios como fuente exclusiva de requisitos. Si se crean archivos auxiliares para una herramienta, deben remitir a `ARCHITECTURE.md` y no contradecirlo.

## Actualización v9.6: carpeta única de evidencias obligatoria

**Todas las evidencias generadas o descargadas durante la validación deben almacenarse dentro de una única carpeta raíz `evidencias/` del repositorio.** No se admiten evidencias dispersas en `data/`, `reports/`, la raíz del proyecto ni carpetas temporales como ubicación definitiva. Los informes y tablas de `reports/` son entregables analíticos y deben referenciar las evidencias mediante rutas relativas verificables dentro de `evidencias/`.

Estructura obligatoria (crear subcarpetas cuando se necesiten):

```text
evidencias/
  manifest.jsonl                 # índice de evidencias; una línea JSON por artefacto
  api_responses/<fuente>/        # respuestas crudas JSON, XML, RSS o Atom
  historical/<fuente>/           # incidentes y ventanas históricas consultadas
  geographic/                   # UBIGEO, geometrías, conflictos y coordenadas de referencia
  temporal/                     # marcas de tiempo, frescura y latencia observadas
  quotas/                       # respuestas de límites, cabeceras y simulaciones de consumo
  pricing/                      # capturas/exportaciones permitidas de tarifas y términos oficiales
  licensing/                    # textos/enlaces de licencias y autorizaciones verificadas
  resilience/                   # resultados de simulaciones leave-one-source-out
  errors/                       # fallos HTTP, DNS, timeout, cuota y acceso
  execution/                    # logs, comandos, fechas y versiones de la ejecución
```

Reglas de trazabilidad:

1. Toda consulta efectuada debe registrar fuente, endpoint/URL oficial, parámetros no sensibles, fecha/hora UTC, código de respuesta, latencia, estado, ruta de archivo y hash SHA-256 del contenido cuando corresponda.
2. `evidencias/manifest.jsonl` será el índice maestro y contendrá al menos `evidence_id`, `source_id`, `operator`, `country`, `observed_at_utc`, `source_published_at_utc` (si existe), `artifact_path`, `sha256`, `result_status` y `related_report` (si existe).
3. Guardar respuestas crudas y versiones normalizadas de forma diferenciada, sin sobrescribir observaciones previas. Los errores también generan evidencia; una respuesta vacía no demuestra ausencia de incidentes.
4. Los archivos de `reports/` deben citar `evidence_id` y `artifact_path` para cada conclusión sobre cobertura, costo, licencia, latencia o resiliencia. No aprobar una fuente sin evidencia archivada.
5. No almacenar claves API, tokens, cookies, identificadores personales, direcciones IP de usuarios ni texto sensible sin anonimizar. Sanitizar cabeceras, URLs y cuerpos antes de guardar.
6. La carpeta `evidencias/` puede ignorarse en Git si contiene grandes volúmenes o material restringido, pero debe mantenerse localmente y ser exportable como un único archivo comprimido. Incluir un `README.md` que explique su estructura y política de retención.
7. Al finalizar, verificar automáticamente que todas las rutas del manifiesto existan, que los hashes coincidan y que ningún reporte apunte a una evidencia inexistente.

**Criterio de aceptación:** la validación no está completa si hay resultados sin evidencia trazable dentro de `evidencias/`.

## Actualización v9.5: resiliencia y análisis de pérdida por fuente

- Evaluar **todas las fuentes** con escenarios contrafactuales de indisponibilidad (`leave-one-source-out`), no solo Cloudflare Radar.
- Cuantificar cuánto se pierde en cobertura peruana, oportunidad temporal, corroboración independiente y precisión geográfica al retirar cada fuente, sin inventar métricas ni convertir falta de evidencia en una caída confirmada.
- Proponer reemplazos sin scraping, con licencias verificadas y costos documentados, manteniendo la prueba local en USD 0.
- Evaluar también fallas simultáneas por familia y dependencia compartida, con política de degradación segura.

## Actualización v9.4: planificador gratuito y licencia de Radar

- La ejecución local de la validación mantiene un **costo efectivo de USD 0**: no se contratan servicios, no se habilita facturación ni se consumen créditos de pago.
- La **investigación económica de la futura producción no tiene presupuesto máximo, techo de gasto ni filtro de exclusión por precio**. Se estudian todas las alternativas, gratuitas y pagadas, incluso si no pueden probarse durante la validación.
- El agente investigará precios oficiales, límites, licencias y escenarios de consumo; distinguirá datos confirmados de estimaciones y desconocidos. La decisión de contratar o descartar por costo corresponde posteriormente al responsable del proyecto.
- Una fuente cara puede resultar técnicamente valiosa. Su estado de prueba será `BLOCKED_PAID` si no hay acceso gratuito, pero **no** `NOT_SUITABLE` únicamente por su precio.

## Cambios frente a v8

- Se incorporan como candidatos RIPE Atlas, RIPE RIS Live, RIPEstat, Globalping, OONI y RIPEstat Country Stats. Los servicios previamente presentes se conservan; Globalping deja de ser una mera nota opcional y entra en la matriz de validación.
- Se incorporan como corroboración secundaria las páginas de estado de Infobip, Twilio, Telesign y Sinch, siempre mediante API, RSS, Atom o webhook oficial disponible, nunca scraping.
- Se incorpora USGS como fuente de contexto sísmico, sin poder de activación.
- **La validación se ejecuta localmente desde VS Code y debe costar USD 0.** No se despliega en GCP, no se usan pruebas pagadas, créditos comprados, servicios con facturación ni infraestructura física adicional.
- Se distingue explícitamente la disponibilidad de una API de su cobertura real por operador y zona de Perú. Las nuevas fuentes siguen **pendientes de validación cuantitativa**.
- La arquitectura futura en GCP se conserva como diseño de referencia, pero solo se migrará después de demostrar viabilidad.

## Actualización v9.1: validación geográfica (sin desarrollo de producción)

- Añadir **geoBoundaries (gbOpen)**, **INEI/UBIGEO** y **Nominatim de OpenStreetMap** como fuentes geográficas candidatas, exclusivamente para validación gratuita.
- No asumir que una coordenada obtenida por IP representa la ubicación real de un usuario ni el punto de la caída.
- Validar cobertura de departamentos, provincias y distritos de Perú, disponibilidad de geometrías, coordenadas representativas, consistencia de códigos UBIGEO y ambigüedad de topónimos.
- Nominatim público solo para pruebas manuales/puntuales compatibles con su política de uso; **prohibir geocodificación masiva, consultas sistemáticas y procesos de monitoreo** sobre la instancia pública.
- La incorporación a producción, el uso comercial y la licencia de cada conjunto de datos quedan pendientes de revisión.

## 1. Objetivo

Detectar de forma rápida y confiable interrupciones o degradaciones de internet de **Movistar, Claro, Entel y Bitel en Perú**, para alimentar en el futuro un feed JSON de activación de creatividades dinámicas de Win. El trabajo actual es exclusivamente de **validación técnica gratuita** de fuentes, no de activación publicitaria.

## 2. Restricciones

| Tema | Condición |
|---|---|
| Geografía | Solo Perú; validar operador y zona cuando sea posible |
| Operadores | Movistar, Claro, Entel, Bitel |
| Etapa actual | VS Code + Python + almacenamiento local |
| Costo de validación | **USD 0 obligatorio** |
| Fuentes | API pública gratuita, RSS, Atom, webhook o WebSocket documentado |
| Prohibiciones | Scraping, planes pagos, créditos comprados, tarjeta para habilitar pruebas, despliegues GCP y dispositivos propios |
| GCP | Solo arquitectura futura, no ejecutar en esta etapa |
| Plataforma Win | Sin accesos; formato y frecuencia de lectura por confirmar |
| Prioridad | Preferir no activar antes que activar incorrectamente |
| Uso comercial | Revisar licencias antes de producción; acceso gratis no implica autorización comercial |

## 3. Principios

1. No confundir API accesible con cobertura real de Perú.
2. No considerar dos mediciones derivadas de la misma señal BGP como confirmaciones independientes.
3. Internet es el servicio objetivo. Una señal de datos móviles cuenta como evidencia directa de internet móvil; SMS y voz son corroboración indirecta de una posible falla amplia del operador y nunca demuestran por sí solos una caída de internet.
4. Los eventos sísmicos son contexto, no corroboración automática de indisponibilidad.
5. Toda consulta de validación debe ser gratuita y respetar cuotas, términos y límites de uso.
6. Fallas de consulta, datos viejos o ausencia de cobertura se registran explícitamente; no equivalen a ausencia de caídas.
7. Conservar datos crudos, timestamps de observación y publicación, trazabilidad y evidencias.
8. Ningún proceso de validación publica activaciones a Win.

## 4. Arquitectura de validación local

```text
VS CODE / PYTHON (EJECUCIÓN LOCAL, USD 0)
  |
  +-- Fuentes técnicas: IODA, Cloudflare Radar
  +-- Ruteo/inventario: RIS Live, RIPEstat, RIPEstat Country Stats
  +-- Mediciones: RIPE Atlas (públicas), Globalping (cuota free)
  +-- Mediciones complementarias: OONI
  +-- Estado de carriers: Infobip, Twilio, Telesign, Sinch
  +-- Contexto: USGS
  +-- Referencias geográficas PE: geoBoundaries, INEI UBIGEO, Nominatim (puntual)
  +-- Señales humanas: X / Osiptel (solo acceso autorizado gratuito)
  |
  v
ADAPTADORES (HTTP / RSS / ATOM / WEBSOCKET)
  |
  v
DATOS CRUDOS LOCALES + SQLITE
  |
  v
VALIDADORES
  - cobertura PE / ASN / operador / zona
  - disponibilidad y frescura
  - retraso de publicación
  - calidad, procedencia e independencia
  - costo y licencia
  |
  v
REPORTE JSON + CSV + MARKDOWN
  |
  v
DECISIÓN: APTO / CONDICIONAL / DESCARTAR / SIN EVIDENCIA
```

No se necesitan Cloud Run, BigQuery, Pub/Sub, Firestore ni Secret Manager en la validación. El diseño de adaptadores permitirá migrarlos después a GCP.

## 5. Inventario de fuentes y estado

**Importante:** los estados reflejan viabilidad preliminar o antecedentes, **no** una certificación de cobertura actual. No se han ejecutado en este documento pruebas en vivo concluyentes por los cuatro ASN.

| Fuente | Qué aporta | Acceso gratuito de evaluación | Estado para Perú |
|---|---|---|---|
| IODA | Anomalías de conectividad por ASN, país y región; BGP y otras señales | API pública | Base técnica; validar eventos y retraso por operador |
| Cloudflare Radar | Tráfico, DNS, anomalías y outages | API con token gratuito sujeto a cuotas | Base técnica; validar granularidad, retraso y licencia |
| RIPE Atlas | Mediciones públicas de conectividad | Consultas públicas; **no** crear mediciones que consuman créditos | Pendiente: cobertura activa por ASN y zona |
| RIPE RIS Live | Streaming de anuncios y retiros BGP | WebSocket público | Pendiente: valor incremental frente a IODA |
| RIPEstat | Inventario de ASN, prefijos y rutas | API pública sujeta a condiciones | Auxiliar; confirmar ASN y licencia |
| RIPEstat Country Stats | Estadísticas agregadas asociadas a PE | Endpoint público de RIPEstat | Pendiente; integrar en el mismo adaptador RIPEstat |
| Globalping | Ping, DNS, HTTP, traceroute desde puntos disponibles | Solo cuotas gratuitas | Pendiente: disponibilidad real por operador en Perú |
| OONI | Mediciones públicas DNS/TCP/HTTP y anomalías | API pública | Pendiente: volumen y frescura por operador peruano |
| Infobip | Avisos de degradación SMS/voz por red | RSS/Atom/webhook público, sujeto a verificación de canal | Corroboración secundaria no calibrada; validar casos PE |
| Twilio | Incidentes de entrega SMS/voz | Feed o suscripción oficial pública, por confirmar | Corroboración secundaria no calibrada; validar PE y operador |
| Telesign | Avisos de incidentes de carriers, incluidos antecedentes PE | Feed oficial público, por confirmar | Corroboración secundaria no calibrada; validar recurrencia y oportunidad |
| Sinch | Incidentes SMS/voz por carrier | Feed oficial público, por confirmar | Corroboración secundaria no calibrada; validar caso PE y feed |
| USGS | Sismos próximos a zonas afectadas | API FDSN/GeoJSON pública | Solo contexto; no activa ni incrementa confianza por sí solo |
| geoBoundaries gbOpen | Límites administrativos y polígonos para Perú (ADM1/ADM2/ADM3 si están disponibles) | API y GeoJSON públicos; verificar versión y atribución | Pendiente: integridad y concordancia con UBIGEO |
| INEI UBIGEO | Códigos y nombres oficiales de departamentos, provincias y distritos | Datos abiertos descargables, sujetos a términos | Pendiente: obtener versión y cotejar claves/nombres |
| Nominatim (OSM) | Geocodificación puntual de topónimos peruanos | Instancia pública gratuita con política estricta | Pendiente: solo muestra pequeña, nunca uso masivo |
| X / Osiptel | Quejas locales y comunicados oficiales | **Solo** si hay mecanismo gratuito autorizado | Condicional; no usar proveedores pagos en validación |

### 5.1 ASN candidatos (requieren confirmación)

| Operador | ASN candidato |
|---|---|
| Movistar / Integratel | AS6147 |
| Claro / América Móvil Perú | AS12252 |
| Entel Perú | AS21575 |
| Bitel / Viettel Perú | AS262210 |

Un operador puede utilizar varios ASN, prefijos y redes de acceso. **No atribuir cobertura total a un único ASN sin inventario validado.**

### 5.2 Antecedentes de estado de carriers por verificar

- Infobip: reporte mencionado de degradación SMS hacia Bitel (Viettel Perú).
- Twilio: reportes mencionados de retrasos SMS en redes de Perú, incluido Entel.
- Telesign: antecedentes mencionados de Entel Perú (6 de septiembre de 2026) y Claro Perú (10 de octubre de 2026).
- Sinch: antecedente mencionado de Bitel Perú en junio de 2026.

Estos antecedentes sirven como **casos de búsqueda para la validación histórica**, no como evidencia de caída de internet. Deben verificarse en las fuentes originales, con inicio, fin, servicio, operador y enlace permanente.

## 6. Fuentes descartadas o no priorizadas

Las decisiones previas sobre M-Lab y scraping/carga manual de OSIPTEL se mantienen según la evaluación de las fuentes correspondientes. Los siguientes candidatos quedan **excluidos de la solución actual y cerrados para nuevas pruebas**, salvo que el usuario reabra expresamente una opción o cambie el alcance. Los motivos y la distinción entre prueba real y revisión documental están en [`reports/candidate_services_exclusion.md`](reports/candidate_services_exclusion.md): IsDown, StatusGator, Downdetector Enterprise, GDELT, Google Trends, TikTok Research API, ThousandEyes Internet Insights, Catchpoint, Azure Anomaly Detector/Metrics Advisor, AWS Lookout for Metrics, AWS CloudWatch Internet Monitor, Outage.Report, Awario, Mentionlytics y Brand24.

StatusGator sí se probó: la API autenticó, pero la cobertura encontrada fue no oficial/global y no acreditó señal peruana atribuible. GDELT se consultó, pero la DOC API respondió HTTP 429 y no devolvió artículos; queda excluido sin afirmar que la prueba demostró ausencia de noticias relevantes. Los demás candidatos no se describen como probados cuando no hubo una consulta efectiva. **RIPE Atlas se reconsidera únicamente para consultas de mediciones públicas**, conforme a la decisión registrada para esa fuente.

## 7. Modelo de evidencia y familias independientes

| Familia | Fuentes | Cómo contarla |
|---|---|---|
| BGP / ruteo | IODA BGP, RIS Live, RIPEstat | Una familia correlacionada, no votos independientes |
| Tráfico / DNS agregados | Cloudflare Radar | Evidencia técnica adicional si su procedencia es distinta |
| Mediciones activas | RIPE Atlas, Globalping, OONI | Verificar diversidad de origen, ASN, tiempo y destino |
| Quejas / oficial | X, cuentas de operadores, Osiptel | Independiente si hay volumen y geografía suficientes |
| Mensajería de carriers | Infobip, Twilio, Telesign, Sinch | Corroboración auxiliar de baja confianza; puede ser un problema exclusivo de SMS/voz. Agrupar proveedores que dependan de la misma falla o ruta. |
| Contexto externo | USGS | No cuenta como confirmación de caída |

Una publicación sobre SMS puede estar causada por rutas de mensajería o interconexión, sin afectar internet. Nunca autoriza una alerta de caída de internet por sí sola. Si coincide en operador, zona y tiempo con evidencia directa de internet, puede elevar cualitativamente la confianza en una falla amplia; no convertirla en una prueba de qué tecnología de internet está afectada.

## 8. Zonas y granularidad

Zonas objetivo: Lima Norte, Lima Sur, Lima Este, Lima Centro, Callao y departamentos del Perú. No se puede inferir una zona distrital a partir de un evento nacional o de un ASN completo. Para publicar una zona se exige evidencia geográfica compatible.

### 8.1 Validación geográfica específica para Perú

**Objetivo:** determinar si cada fuente aporta una localización útil y verificable; **no** construir todavía un motor de geolocalización de producción.

1. Descargar una versión identificable de los límites administrativos de Perú desde geoBoundaries gbOpen y un catálogo UBIGEO del INEI. Registrar fecha, URL, licencia y hash del archivo.
2. Comprobar que los polígonos están en un sistema de referencia conocido (normalizar a WGS84 / EPSG:4326) y evaluar su cobertura por departamento, provincia y distrito. No asumir que ADM3 coincide exactamente con el catálogo distrital sin verificarlo.
3. Cruzar nombres y jerarquías administrativas con UBIGEO, registrando coincidencias, homónimos, ausencias y discrepancias; nunca asignar automáticamente un distrito ambiguo.
4. Probar Nominatim **solo con una muestra manual pequeña** de topónimos peruanos y respetando su política vigente. Si no se permiten las pruebas previstas, marcar `BLOCKED_POLICY`; no intentar eludir límites.
5. Evaluar por fuente de incidentes qué porcentaje trae coordenadas originales, zona textual explícita, ubicación de medición, región estimada por IP o ningún dato geográfico.
6. Si la única evidencia es GeoIP, mantener `location_verified=false` y no convertir esa ubicación en distrito confirmado. Un centroide administrativo es **referencial**, nunca la coordenada exacta de la caída.
7. Si hay conflicto entre localizaciones, registrar `location_conflict=true`, conservar todas las evidencias y dejar la zona sin resolver si no hay corroboración suficiente.

**Campos mínimos de evidencia geográfica:** `country`, `department`, `province`, `district`, `ubigeo`, `latitude`, `longitude`, `coordinate_type` (`observed`, `representative`, `ip_estimated`, `unknown`), `location_source`, `location_precision` (`country`, `department`, `province`, `district`, `point`, `unknown`), `location_verified`, `location_conflict`, `geometry_reference`, `source_timestamp`.

**Criterio de aceptación:** emitir una matriz por fuente y operador con porcentaje de registros geolocalizables a cada nivel, porcentaje de coordenadas observadas frente a referenciales, tasa de conflictos y cobertura del catálogo administrativo. No interpretar una coordenada de una sonda como ubicación exacta de la avería.

## 9. Validaciones automáticas

Cada adaptador debe devolver:

- `api_reachable`: respuesta correcta, error, timeout, cuota o autenticación.
- `peru_evidence`: resultado específico de Perú, no solo parámetro `PE` aceptado.
- `operator_coverage`: operador y ASN realmente presentes en los datos.
- `zone_coverage`: ubicación de la medición o del incidente, si existe.
- `observed_at`, `published_at`, `collected_at`: medir retraso real sin confundir tiempos.
- `sample_count`: volumen suficiente por operador y ventana.
- `signal_family`, `upstream_origin`: independencia y duplicación.
- `historical_access`: capacidad de recuperar eventos pasados.
- `free_access`: confirmación de uso gratuito dentro de cuotas.
- `commercial_license`: permitido, restringido o pendiente de revisión.

### Estados del resultado

| Estado | Interpretación |
|---|---|
| `PASS` | Datos reales de Perú y criterios medidos satisfechos |
| `CONDITIONAL` | Fuente útil con cobertura, latencia o granularidad limitada |
| `NO_COVERAGE` | Consulta válida pero sin cobertura suficiente de Perú/operador |
| `UNAVAILABLE` | Error de acceso, no se concluye ausencia de datos |
| `BLOCKED_PAID` | Exige pago o créditos facturables: no consultar |
| `LICENSE_REVIEW` | Uso comercial por confirmar |
| `NOT_TESTED` | Pendiente de ejecutar |

### Criterios de aceptación propuestos

- Respuesta real de API/feed y evidencia archivada de Perú.
- Al menos una muestra atribuible a un operador peruano; para producción se requiere volumen representativo, no solo una muestra.
- Frescura compatible con ventanas de 15 minutos **para fuentes de activación**; las fuentes históricas o contextuales pueden tener otra periodicidad.
- Identificación de duplicados y fuentes dependientes.
- Ningún costo y ninguna solicitud que active facturación durante la prueba.
- Reporte claro de qué operadores y zonas quedan sin cobertura.

Los umbrales definitivos de volumen, disponibilidad y retraso se fijarán con datos, no con cifras inventadas.

## 10. Diseño de proyecto VS Code

```text
win-outage-validation/
├── config/
│   ├── operators.yaml
│   ├── sources.yaml
│   ├── geography.yaml
│   └── thresholds.yaml
├── src/
│   ├── collectors/
│   │   ├── ioda.py
│   │   ├── cloudflare.py
│   │   ├── ripe_atlas.py
│   │   ├── ripe_ris.py
│   │   ├── ripestat.py
│   │   ├── globalping.py
│   │   ├── ooni.py
│   │   ├── carrier_status.py
│   │   ├── usgs.py
│   │   ├── geoboundaries.py
│   │   ├── inei_ubigeo.py
│   │   ├── nominatim.py
│   │   └── x.py
│   ├── validators/
│   │   ├── coverage.py
│   │   ├── geo_validation.py
│   │   ├── freshness.py
│   │   ├── latency.py
│   │   ├── independence.py
│   │   ├── licensing.py
│   │   └── cost_guard.py
│   ├── storage/sqlite.py
│   └── reports/generator.py
├── data/raw/
├── data/processed/
├── reports/
├── tests/
├── .env.example
├── requirements.txt
└── main.py
```

Usar Python, HTTP, lector de feeds y WebSocket, SQLite local y exportación JSON/CSV/Markdown. Secretos únicamente en `.env` local, excluido del repositorio. **No ejecutar automáticamente fuentes de costo incierto**.

## 11. Orden de validación

1. **Prueba de acceso gratuito:** confirmar endpoints, términos, límites y ausencia de facturación. Bloquear toda fuente de pago.
2. **Cobertura por operador:** consultar Perú y ASN; obtener conteos y fechas reales, no solo páginas promocionales.
3. **Historial:** contrastar incidentes documentados de carriers con eventos IODA/Cloudflare, cuando haya datos disponibles.
4. **Monitoreo local:** realizar consultas dentro de cuotas gratuitas; almacenar disponibilidad, frescura y retraso.
5. **Análisis de independencia:** comparar familias y orígenes de datos; evitar consenso artificial.
6. **Validación geográfica:** cruzar geoBoundaries con UBIGEO y una muestra puntual de Nominatim; medir precisión y conflictos sin confiar en GeoIP.
7. **Reporte final:** clasificar cada fuente y documentar brechas de cobertura.

La validación local solo corre mientras se ejecute el proceso en el equipo; no se promete monitoreo continuo con la computadora apagada.

## 12. Motor de decisión futuro (no implementar todavía)

Conservar el enfoque de v8: señales por operador × zona × 15 minutos; líneas base robustas por hora/día; umbrales de volumen; consenso entre familias; estados `candidato → activo → recuperando → cerrado`; histéresis, caducidad y enfriamiento; bitácora y corte automático.

Reglas críticas:

- Pico humano fuerte + corroboración técnica u oficial compatible: posible activación.
- Caída técnica grande verificada: activación solo con atribución de operador y alcance geográfico suficientemente sustentados.
- Solo alerta regional de IODA: candidato, no activar.
- Solo SMS/voz: nunca declarar ni activar una caída de internet. Si coincide con evidencia directa de internet en operador, zona y tiempo, puede corroborar cualitativamente una falla amplia del operador; contar la familia mensajería como máximo una vez.
- Una caída de datos móviles es evidencia directa para un incidente de internet móvil. Puede sugerir una falla amplia del operador, pero no confirma por sí sola una caída de internet fijo; conservar las etiquetas y decisiones por tecnología.
- Cobertura declarada: contexto para determinar dónde se esperaba servicio, nunca evidencia de una caída actual ni incremento de confianza.
- Solo sismo: nunca activar.
- Señales atrasadas o contradictorias: no activar.
- No convertir múltiples proveedores con causa común en votos independientes.
- Si tres o más operadores muestran anomalías simultáneas, investigar automáticamente un evento transversal o un problema de medición; no asumir sin evidencia que siempre es un fallo de nuestras fuentes.

## 13. Arquitectura futura en GCP (fuera de la validación)

| Función | Servicio previsto |
|---|---|
| Colectores periódicos | Cloud Scheduler + Cloud Run |
| Streaming RIS Live | Servicio con conexión persistente, reconexión y control de costos |
| Mensajería y reintentos | Pub/Sub |
| Historial y datos crudos | BigQuery + Cloud Storage |
| Estado de incidentes | Firestore |
| Clasificador de X | Gemini Flash-Lite con JSON estructurado |
| Feed JSON | Cloud Run o Cloud Storage |
| Monitoreo | Cloud Monitoring |
| Secretos | Secret Manager |

El diseño debe contemplar idempotencia, retención limitada, minimización de datos personales, frescura por fuente y recuperación ante fallas. La decisión de migrar a GCP dependerá de los resultados de la validación gratuita.

## 14. Feed futuro para Win

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-10-24T20:15:00-05:00",
  "valid_until": "2026-10-24T20:30:00-05:00",
  "system_status": "ok",
  "events": [
    {
      "operator": "movistar",
      "zone": "lima-sur",
      "state": "active",
      "confidence": 0.82,
      "started_at": "2026-10-24T20:04:00-05:00",
      "expires_at": "2026-10-25T02:04:00-05:00"
    }
  ]
}
```

**Ejemplo ficticio de formato, no incidente real.** Si vence `valid_until`, Win debe tratarlo como ausencia de activación. El consumidor también debe definir el comportamiento seguro para `degraded` y `down`. Integración, autenticación, frecuencia y formato definitivo pendientes de acuerdo con Win.

## 15. Datos para validación y futura producción

Tablas o entidades lógicas: `raw_events`, `source_health`, `network_inventory`, `atlas_measurements`, `bgp_events`, `carrier_incidents`, `external_events`, `signals_15m`, `incidents`, `decisions_log`, `labels` y `validation_results`.

Durante la etapa local se almacenan en SQLite y archivos; no se requiere BigQuery.

Las etiquetas automáticas derivadas de IODA y Cloudflare tienen sesgo y no son verdad independiente. Las métricas calculadas con ellas no equivalen a precisión real frente a todas las caídas de internet, especialmente fallas móviles o locales.

## 16. Validación económica y estudio de costos (sin techo presupuestario)

### 16.1 Restricción de ejecución local

La PoC debe ejecutarse con **gasto efectivo USD 0**. No activar facturación, no registrar tarjetas, no comprar créditos, no contratar planes, no desplegar GCP y no utilizar pruebas con cobro automático posterior. Las consultas gratuitas deben respetar cuotas, licencias y términos de uso. Cuando un proveedor requiera pago, documentar sus precios y capacidades mediante fuentes oficiales, pero **no ejecutar** su API pagada. El estado `BLOCKED_PAID` describe únicamente la imposibilidad de probarla gratis.

### 16.2 Investigación de costos de futura producción

**No existe presupuesto máximo para la investigación ni para la selección técnica.** No descartar, ocultar ni degradar la recomendación de una fuente por superar un importe arbitrario. El responsable del proyecto decidirá posteriormente qué costos acepta.

Para **cada fuente**, incluidas las bloqueadas para pruebas gratuitas, registrar:

| Campo | Contenido exigido |
|---|---|
| `pricing_model` | Gratuito, por solicitud, por crédito, suscripción, volumen, enterprise o mixto |
| `free_tier` | Capacidades, cuotas, caducidad y restricciones del acceso gratuito |
| `rate_limits` | Límites por segundo, minuto, hora, día y mes cuando se publiquen |
| `paid_plans` | Planes y precios oficiales; moneda, región, impuestos y periodicidad |
| `overage_cost` | Costos por excedente o bloqueo por cuota, si existen |
| `commercial_use` | Compatibilidad de licencia y restricciones de redistribución/uso comercial |
| `auth_requirements` | Token, cuenta, tarjeta, contrato o autorización especial |
| `pricing_source` | URL oficial exacta, no únicamente comparadores de terceros |
| `verified_at` | Fecha UTC de consulta de precios y términos |
| `pricing_status` | `VERIFIED`, `ESTIMATED`, `UNKNOWN`, `CONTACT_SALES` |
| `currency` | Moneda de origen y conversión a USD solo con tasa fechada y citada |
| `estimated_monthly_cost` | Estimación por escenario y desglose de supuestos |

**Escenarios de consumo:** calcular por fuente al menos intervalos de consulta de 1, 5, 15 y 30 minutos, cuando el modelo de API sea por consulta. Para 30 días, una consulta por ciclo equivale a 43,200; 8,640; 2,880; y 1,440 consultas respectivamente. Multiplicar por operadores, zonas, endpoints, paginación, reintentos y cantidad de mediciones por consulta según corresponda. No aplicar este cálculo indiscriminadamente a WebSockets, webhooks, RSS, planes por volumen de datos o modelos por crédito: usar su unidad real de cobro.

Para el futuro despliegue, estimar por separado GCP (Cloud Run, Scheduler, Pub/Sub, BigQuery, Storage, Firestore, Monitoring, Secret Manager, red y egreso), APIs de pago, posibles servicios de clasificación de texto y auditoría. Los LLM **no se integran en la validación**, pero sus precios futuros pueden investigarse sin elegir modelo. Mostrar costos **por fuente**, **por escenario** y **total por escenario**, con rango de incertidumbre; nunca imponer un presupuesto límite.

**Escenarios comparativos:** consumo bajo, medio y alto, definidos por volúmenes de consultas y datos explícitos, no por importes monetarios. Mostrar también sensibilidad a duplicación de llamadas, crecimiento por zona y límites de cuotas. Si no hay precio público, indicar `CONTACT_SALES` y no inventar cifras. Si no se puede comprobar licencia comercial, marcar `UNKNOWN` y señalar el bloqueo legal para producción.

**Separación de resultados:** `TECHNICALLY_USEFUL` no implica `FREE_TO_TEST`, `COMMERCIALLY_LICENSED` ni `ECONOMICALLY_PREFERRED`. La evaluación técnica no debe confundirse con la decisión posterior de contratación.

### 16.3 Entregables económicos

- `reports/source_pricing.csv`: una fila por fuente y plan, con campos anteriores y enlaces de respaldo.
- `reports/cost_scenarios.csv`: fuente, escenario, unidad de consumo, volumen mensual, tarifa, costo estimado, supuestos e incertidumbre.
- `reports/economic_feasibility.md`: comparativa completa de costos, límites, licencias, sensibilidad y alternativas de contratación **sin ranking automático basado en un techo presupuestario**.
- `reports/pricing_unknowns.md`: precios no publicados, contacto comercial necesario y verificaciones pendientes.

La validación se considera completa aunque haya fuentes de pago sin probar, siempre que queden registradas como no ejecutadas y se investigue su viabilidad económica con evidencia verificable.

## 17. Riesgos y bloqueos

1. Cobertura insuficiente por operador y zona en Perú.
2. Poca frecuencia de mediciones de RIPE Atlas, Globalping u OONI.
3. Duplicación de evidencia BGP entre IODA y RIS Live.
4. Avisos SMS/voz que no correspondan a caídas de internet.
5. Publicación tardía de incidentes en status pages.
6. Limitaciones de cuotas gratuitas o cambios de endpoints.
7. Licencias de uso comercial de datos gratuitos; revisar especialmente restricciones de atribución y uso no comercial.
8. X sin acceso gratuito autorizado; no sustituir por scraping.
9. Riesgo de atribuir un evento nacional a un distrito sin evidencia local.
10. Etiquetas automáticas sesgadas y falsos negativos en fallas pequeñas.

## 18. Condiciones para cerrar la validación

### 18.1 Decisión de viabilidad inmediata

Cuando el responsable pregunte si el proyecto puede funcionar o si conviene continuar, emitir de inmediato una conclusión provisional basada en la evidencia disponible, indicando qué está demostrado, qué es inferencia y qué sigue desconocido. Separar explícitamente:

- **Viabilidad técnica en esta etapa:** evaluar acceso técnico, cobertura peruana y por operador, señales, frescura disponible, geografía, independencia y capacidad de operar dentro de las restricciones de la prueba.
- **Revisiones diferidas:** licencias, permisos comerciales, contratación y criterios de lanzamiento pertenecen a una etapa posterior; no bloquean ni cambian la conclusión técnica actual.
- **Cierre de la PoC técnica:** describir lo observado y sus límites; las pruebas pendientes no condicionan una respuesta inicial de viabilidad.

No posponer una respuesta de viabilidad por pruebas pendientes. Presentar la recomendación técnica actual y señalar solo las pruebas concretas que podrían confirmarla o cambiarla. Mantener la respuesta dentro del alcance que se está validando: acceso, fuentes, cobertura, señal, frescura, geografía e independencia. No introducir revisiones legales/comerciales ni componentes de etapas posteriores salvo que el responsable lo solicite.

No recomendar una espera temporal para poder responder ni presentar la duración de observación como pendiente de cierre; expresar las incertidumbres con la evidencia disponible.

El reporte técnico debe incluir por fuente: URL oficial del endpoint/feed, timestamp de prueba, código de respuesta, ejemplo de dato peruano, ASN/operador detectado, zonas observadas, número de muestras, retraso medible, cuota/límite observado, dependencia respecto de otras fuentes y decisión razonada. La revisión de licencias se documentará en su etapa posterior y no será criterio de viabilidad técnica.

Una fuente no se considera **validada para Perú** solo por aceptar `country=PE` ni por mostrar un incidente antiguo aislado. Debe demostrar utilidad para el objetivo y la ventana de detección prevista.

## 19. Enlaces de referencia para pruebas

- IODA: https://ioda.inetintel.cc.gatech.edu/
- Cloudflare Radar: https://developers.cloudflare.com/radar/
- RIPE Atlas: https://atlas.ripe.net/api/v2/probes/?country_code=PE&status=1
- RIS Live: https://ris-live.ripe.net/manual/
- RIPEstat: https://stat.ripe.net/docs/data_api
- RIPEstat Country Stats: https://stat.ripe.net/data/country-resource-stats/data.json?resource=PE
- Globalping: https://globalping.io/docs/api.globalping.io
- OONI: https://api.ooni.io/
- Infobip: https://external-connectivity-status.infobip.com/
- Twilio: https://status.twilio.com/
- Telesign: https://status.telesign.com/
- Sinch: https://status.sinch.com/
- USGS: https://earthquake.usgs.gov/fdsnws/event/1/

**Nota:** enlaces de referencia, no prueba de acceso ni de cobertura en tiempo real. Validar cada endpoint y los términos vigentes desde el proyecto local.

---

**Decisión actual:** congelar la incorporación de nuevas fuentes. Ejecutar primero la validación local gratuita de las candidatas y utilizar los resultados para decidir cuáles pasarán a la arquitectura productiva en GCP.

---

## 20. Contrato de implementación agnóstico al agente y al modelo (instrucciones operativas)

> **Especificación independiente de proveedor, modelo, IDE y agente.** Puede ejecutarla Claude Code, Codex, DeepSeek u otro agente de programación con acceso a archivos, terminal y red. No se requieren instrucciones propietarias, herramientas MCP específicas ni características exclusivas de un proveedor. **Este documento es la fuente de requisitos para el agente.** Implementa un proyecto local ejecutable para VALIDAR fuentes, no una plataforma de producción. No afirmes que una fuente funciona en Perú hasta guardar evidencia de una respuesta real. No inventes endpoints, resultados, credenciales, cuotas ni cobertura.

### 20.1 Resultado que debes entregar

Construye un repositorio Python instalable con CLI, adaptadores aislados, almacenamiento SQLite, datos crudos reproducibles, tests automatizados y reportes en Markdown/CSV/JSON. Debe ejecutarse localmente desde VS Code o cualquier editor/terminal compatible, en Windows, macOS o Linux. No implementes despliegue cloud, campañas, activación publicitaria ni un feed operativo.

### 20.2 Restricciones innegociables

- **Costo de validación exactamente USD 0.** Prohibidos pagos, trials con tarjeta, servicios facturables, créditos comprados y cualquier despliegue en GCP. Las llamadas a servicios gratuitos deben respetar sus cuotas y términos; si el acceso gratuito no está confirmado, no hacer la llamada y registrar `NEEDS_REVIEW` o `BLOCKED_PAID` según corresponda.
- **Sin scraping:** no extraer contenido HTML de páginas de estado, ni automatizar navegadores, ni utilizar APIs privadas/no documentadas. Únicamente endpoints oficiales, feeds RSS/Atom, webhooks o WebSockets públicos documentados. Para status pages, comprobar el feed/API oficial antes de codificarlo; no asumir que todas usan el mismo proveedor o formato.
- **Solo Perú:** filtrar país `PE` y validar por separado los cuatro operadores. No atribuir un evento al Perú porque una empresa sea multinacional. No atribuir eventos regionales a distritos sin evidencia explícita.
- **Sin hardware, sondas propias ni infraestructura física.** Se permiten mediciones públicas preexistentes y pruebas gratuitas realizadas mediante plataformas externas, cuando sus condiciones lo autoricen.
- **No credenciales inventadas:** Cloudflare Radar solo con token gratuito aportado por el usuario y sin imprimirlo. X queda `BLOCKED_PAID`/`NEEDS_REVIEW` si no hay una vía oficial gratuita autorizada. Nunca pedir tarjeta.
- **No crear costos inadvertidos:** por defecto desactivar cualquier operación que cree mediciones de pago o consuma créditos (incluidos créditos de RIPE Atlas); permitir únicamente lecturas de datos públicos. No instalar servicios que impliquen facturación.
- Las APIs pueden cambiar. Antes de implementar cada adaptador, contrastar endpoint, autenticación, límites y licencia con documentación oficial; registrar URL y fecha de revisión en un manifiesto. Si no hay documentación comprobable, `NOT_TESTED`.

### 20.3 Organización mínima del repositorio

```text
win-outage-validation/
  README.md
  ARCHITECTURE.md              # especificación agnóstica, idéntica para cualquier agente
  pyproject.toml
  .env.example
  .gitignore
  config/
    operators.yaml
    sources.yaml
    validation.yaml
  src/win_validation/
    __init__.py
    cli.py
    models.py
    http_client.py
    database.py
    registry.py
    adapters/
      base.py
      ioda.py
      cloudflare.py
      ripe_atlas.py
      ripe_ris_live.py
      ripestat.py
      globalping.py
      ooni.py
      carrier_status.py
      usgs.py
      x_official.py
    analysis/
      coverage.py
      freshness.py
      correlation.py
      independence.py
      scoring.py
    reporting/
      generate.py
  tests/
    fixtures/
    test_normalization.py
    test_peru_filter.py
    test_cost_guard.py
    test_failure_modes.py
    test_reports.py
  evidencias/                # TODAS las evidencias y manifest.jsonl
  data/                      # solo datos temporales de trabajo, sin evidencias finales
  reports/                   # generado, sin datos personales
```

### 20.4 Comandos que deben funcionar

Usar una CLI reproducible (por ejemplo, Typer o argparse), con estos comandos exactos o equivalentes documentados:

```bash
python -m win_validation.cli doctor
python -m win_validation.cli sources
python -m win_validation.cli validate --source ripestat --country PE
python -m win_validation.cli validate --all --country PE --safe-free-only
python -m win_validation.cli historical --days 30 --country PE --safe-free-only
python -m win_validation.cli report --format all
python -m pytest -q
```

`doctor` comprueba versión Python, configuración, conectividad y credenciales opcionales sin ejecutar consultas costosas. `sources` muestra documentación, tipo de acceso, estado y cuota. `validate` ejecuta un adaptador o todos con límites. `historical` usa solo datos históricos disponibles de forma gratuita, sin suponer que todas las APIs soportan 30 días. `report` produce resultados verificables.

### 20.5 Contrato de cada adaptador

Implementar interfaz común con métodos `check_access()`, `discover_peru_coverage()`, `fetch_recent()`, `fetch_history(start,end)` si aplica, y `normalize()`. Cada adaptador debe declarar `source_id`, `evidence_family`, `access_type`, `documentation_url`, `requires_auth`, `free_tier_verified`, `rate_limit_policy`, `commercial_terms_status` y `supports_operator_filter`.

Los registros normalizados deben tener, como mínimo:

```json
{
  "source_id": "example",
  "source_event_id": "example-id",
  "country": "PE",
  "operator": null,
  "asn": null,
  "zone": null,
  "service_type": "unknown",
  "evidence_family": "unknown",
  "event_type": "unknown",
  "observed_at": null,
  "published_at": null,
  "collected_at": "2026-10-24T00:00:00Z",
  "source_url": "https://example.org/",
  "raw_reference": "sha256:example",
  "is_peru_explicit": false,
  "operator_attribution_method": "none"
}
```

**El JSON anterior es un ejemplo de esquema, no una observación real.** Conservar también `http_status`, duración de la consulta, tamaño, fecha de acceso, versión del adaptador, error y metadatos de cuota. Identificar operador por ASN validado, MCC/MNC validado o nombre explícito, con método y confianza de atribución; evitar emparejamientos ambiguos como `Claro` en países distintos.

### 20.6 Validación específica por fuente

| Adaptador | Prueba obligatoria | Qué NO se puede concluir |
|---|---|---|
| IODA | Consultar entidades de Perú y ASN, registrar señales y eventos reales accesibles | Que una alerta regional identifica un distrito o una caída móvil |
| Cloudflare Radar | Validar acceso con token gratuito, filtros PE/ASN, frescura y restricciones de licencia | Que aceptar `PE` demuestra cobertura útil por operador |
| RIPE Atlas | Contar sondas conectadas en PE por ASN; verificar existencia y antigüedad de mediciones públicas | Que una sonda conectada equivale a pruebas recientes de caída |
| RIS Live | Abrir conexión documentada con timeout, suscribir solo prefijos/ASN pertinentes, guardar eventos recibidos | Que no recibir eventos durante la prueba significa que la red está sana |
| RIPEstat / Country Stats | Verificar ASN/prefijos y datos de país con timestamp | Que inventario BGP equivale a un incidente confirmado |
| Globalping | Consultar disponibilidad documentada por PE/ASN y, solo si está permitido en free tier, ejecutar prueba limitada | Que una prueba desde Lima cubre todos los operadores y zonas |
| OONI | Consultar mediciones `PE` con timestamps y ASN; contar volumen y frescura | Que mediciones ocasionales son monitoreo continuo |
| Infobip / Twilio / Telesign / Sinch | Identificar feed/API oficial, recuperar incidentes, comprobar país y operador explícitos | Que un fallo de SMS/voz prueba caída de internet |
| USGS | Consultar sismos por coordenadas/región temporal de Perú y registrar magnitud/ubicación | Que un sismo implica indisponibilidad de un operador |
| geoBoundaries | Descargar geometrías PE y verificar ADM1/ADM2/ADM3, vigencia, licencia y consistencia | Que un centroide representa el lugar exacto de una caída |
| INEI UBIGEO | Descargar catálogo oficial, verificar versión y cotejar códigos, nombres y jerarquías | Que un nombre ambiguo identifica un distrito único |
| Nominatim | Consultar solo muestra puntual autorizada de topónimos PE, registrar ambigüedad y límites | Que GeoIP o geocodificación nominal verifica una incidencia |
| X / Osiptel | Verificar si existe acceso autorizado gratuito y documentado | Consultar APIs no oficiales o de pago por defecto |

Si una fuente tiene solo documentación pero no datos peruanos observables, marcar `COVERAGE_UNVERIFIED`; si devuelve cero eventos en una ventana, registrar `NO_EVENTS_IN_WINDOW`, **no** `NO_COVERAGE`.

### 20.7 Criterios de aceptación y decisión

Generar por fuente y operador: número de eventos/mediciones peruanas reales, porcentaje con operador identificable, zonas, timestamp más reciente, distribución de antigüedad, errores, cuotas, latencia observada cuando sea medible, historial disponible, dependencia con otras fuentes y términos comerciales.

Estados permitidos: `PASS`, `FAIL`, `NOT_TESTED`, `BLOCKED_PAID`, `NEEDS_REVIEW`, `COVERAGE_UNVERIFIED`, `NO_EVENTS_IN_WINDOW`, `UNAVAILABLE`. No usar `PASS` si solo se comprobó un HTTP 200; distinguir `ACCESS_PASS` de `UTILITY_PASS`. Un incidente histórico aislado acredita presencia histórica, no cobertura continua ni detección rápida. La latencia real de publicación solo puede estimarse si hay timestamps fiables de inicio del incidente y publicación; de lo contrario, `UNKNOWN`.

Clasificar las fuentes en `PRIMARY_CANDIDATE`, `CORROBORATION_ONLY`, `CONTEXT_ONLY`, `INVENTORY_ONLY` o `REJECT`, siempre con justificación y evidencia. No establecer umbrales de calidad arbitrarios como verdades: proponerlos en `config/validation.yaml`, explicarlos y permitir modificarlos.

### 20.8 Reglas de ejecución segura

- Timeouts explícitos, backoff exponencial, `Retry-After`, límites por host, concurrencia baja y máximo de solicitudes por ejecución configurable; no reintentar indefinidamente.
- Un fallo DNS, 401, 403, 429, timeout o 5xx debe producir estado propio y evidencia; nunca convertirse en cero incidentes.
- Deshabilitar por defecto pruebas activas que gasten créditos, incluso si son créditos promocionales. Sin suscripciones pagas ni APIs de terceros no oficiales.
- SQLite con escrituras idempotentes; guardar JSON crudo con hash SHA-256 y timestamp, sin exponer tokens, identificadores personales o texto de usuarios en reportes.
- No utilizar datos sintéticos en métricas de cobertura real. Se permiten fixtures simuladas **solo para tests**, marcadas explícitamente.
- Los reportes deben incluir `executed_at_utc`, `environment`, `query`, `status`, `sample_count`, `evidence_path` y limitaciones.

### 20.9 Fases de trabajo para cualquier agente de programación

**Fase A — Preparación:** inspeccionar este documento; crear repositorio, entorno virtual, configuración, CLI, SQLite, logging, cliente HTTP, tests y README. Ejecutar `pytest`. No inventar que los conectores ya funcionan.

**Fase B — Inventario y fuentes técnicas:** implementar RIPEstat, IODA, RIPE Atlas, Cloudflare y RIS Live; probar solo accesos gratuitos documentados. Guardar respuestas y reportar cobertura por ASN peruano.

**Fase C — Medición y contexto:** implementar Globalping, OONI y USGS; comprobar presencia de Perú, frecuencia y limitaciones.

**Fase D — Estado de carriers:** integrar Infobip, Twilio, Telesign y Sinch usando exclusivamente mecanismos oficiales. Normalizar país, operador, servicio, inicio, actualización y cierre.

**Fase E — Comparación y reporte:** correlacionar eventos por tiempo, operador y zona sin contar BGP duplicado como familia independiente; generar matriz final y lista de bloqueos.

**Fase F — Rondas locales:** habilitar ejecuciones locales opcionales, con límite de consultas configurables; nunca prometer cobertura continua si el equipo está apagado. Comparar rondas solo cuando el responsable solicite esa medición.

Al finalizar cada fase, registrar comandos ejecutados, tests aprobados/fallidos, evidencia guardada, limitaciones y siguiente fase en archivos del repositorio; no depender de la memoria de conversación del agente. Si un bloqueo requiere decisión del usuario (token, licencia o permiso), detener solo ese adaptador y continuar con los demás.

### 20.10 Entregables obligatorios

**Evidencia centralizada:** entregar `evidencias/` con sus subcarpetas, `manifest.jsonl` y verificación de integridad. Todos los informes deben enlazar a archivos de esta carpeta.

1. Proyecto Python local funcional, instalable con instrucciones para VS Code.
2. `reports/source_matrix.csv`: una fila por fuente × operador, incluyendo estados y cobertura real.
3. `reports/validation_report.md`: hallazgos con enlaces oficiales, timestamps, ejemplos anonimizados, errores y recomendaciones.
4. `reports/validation_results.json`: resultados estructurados para reutilizar posteriormente en GCP.
5. `reports/blockers.md`: licencias, límites, credenciales opcionales, endpoints no comprobados y fuentes sin cobertura.
6. Pruebas unitarias y de integración aisladas, sin llamadas externas por defecto.
8. `reports/source_pricing.csv`, `reports/cost_scenarios.csv`, `reports/economic_feasibility.md` y `reports/pricing_unknowns.md` para investigación económica sin límite de presupuesto.
7. README con instalación, ejecución, cuotas y advertencia explícita de que **no hay feed de activación en esta etapa**.

### 20.11 Instrucción inicial para cualquier agente de programación

Este prompt puede pegarse sin modificaciones en Claude Code, Codex, DeepSeek o herramientas equivalentes. La ejecución requiere capacidades de lectura/escritura de archivos y terminal; si faltan, el agente debe declararlo y no simular resultados.

```text
Lee íntegramente ARCHITECTURE.md y trátalo como especificación de referencia.
Implementa únicamente la validación local gratuita de fuentes para Perú.
Guarda TODAS las evidencias en evidencias/ con manifest.jsonl, hashes y rutas
relativas; los reportes deben referenciarlas y validar su existencia.
No uses scraping, GCP, hardware, APIs de pago, créditos consumibles ni tarjetas.
Valida también geoBoundaries, INEI UBIGEO y Nominatim únicamente en condiciones
gratuitas y permitidas. Evalúa precisión geográfica y latitud/longitud,
pero no infieras ubicación exacta de una caída a partir de GeoIP o centroides.
Primero crea el esqueleto del proyecto, tests, CLI y salvaguardas de costo.
Investiga también precios oficiales y escenarios de operación futura sin fijar presupuesto máximo ni descartar fuentes por precio; no contrates ni ejecutes servicios de pago.
Después implementa los adaptadores por fases, verificando documentación oficial
antes de fijar endpoints. Ejecuta consultas reales solo cuando el acceso gratuito
esté confirmado. Guarda evidencia y distingue acceso API de cobertura útil para
Movistar, Claro, Entel y Bitel. Nunca inventes resultados ni declares cobertura
peruana sin datos observados. Ejecuta tests y genera los reportes requeridos.
```

**Criterio final:** la validación está completa cuando se puede ejecutar el proyecto localmente y obtener un reporte auditable por fuente y operador, incluso si varias fuentes resultan no aptas. El objetivo es descubrir límites reales, no forzar resultados positivos.


### Referencias geográficas para validar (no asumir disponibilidad sin consultar)

- geoBoundaries API: https://www.geoboundaries.org/api/current/gbOpen/PER/ADM3/ (verificar ADM1/ADM2/ADM3 y versión de respuesta).
- Catálogo UBIGEO en portal de datos abiertos del Perú / INEI: https://www.datosabiertos.gob.pe/ (localizar recurso oficial vigente).
- Nominatim API y política de uso: https://nominatim.org/release-docs/latest/api/Search/ y https://operations.osmfoundation.org/policies/nominatim/ .


## 21. Validación temporal (obligatoria para cerrar la PoC)

**Objetivo:** demostrar si cada fuente llega a tiempo para un trigger publicitario y diferenciar latencia de la fuente de latencia del colector.

Por cada evento guardar, si existen, `event_started_at`, `source_first_seen_at`, `source_published_at`, `source_updated_at`, `collected_at`, `event_ended_at`, `timestamp_provenance` y `clock_uncertainty_seconds`. Todos los timestamps en UTC, preservando la zona original. Si una fuente no informa la primera publicación, marcar `UNKNOWN`; nunca sustituirla por la hora de consulta.

Calcular `publication_lag = source_published_at - event_started_at` únicamente si ambos tiempos son verificables; `collection_lag = collected_at - source_published_at` si aplica; `incident_duration = event_ended_at - event_started_at` si existe cierre. Reportar mediana, p90 y muestra por fuente y operador; si no hay muestra suficiente, `INSUFFICIENT_DATA`. Evaluar explícitamente si el retraso observado permitiría una ventana de 15 minutos. No declarar tiempo real por la mera presencia de WebSocket, RSS o API.

**Pruebas:** fixtures con zona horaria -05:00, datos tardíos, eventos editados, duplicados, eventos sin inicio, reloj invertido y feeds sin fecha de publicación. No calcular latencias negativas como si fueran normales.

## 22. Correlación, independencia y no doble conteo

**Objetivo:** distinguir corroboración real de fuentes que observan el mismo fenómeno o reutilizan los mismos datos.

Cada registro debe llevar `evidence_family`, `measurement_origin`, `upstream_dependencies`, `operator_match_basis`, `geo_match_basis`, `temporal_overlap`, `independence_status` (`INDEPENDENT`, `DEPENDENT`, `UNKNOWN`) y `incident_match_id`.

Familias sugeridas: `bgp_routing` (IODA BGP, RIS Live, RIPEstat routing), `active_reachability` (IODA active probing, RIPE Atlas, Globalping, sujetos a dependencias reales), `traffic_dns` (Cloudflare), `human_reports` (X), `carrier_messaging` (Infobip, Twilio, Telesign, Sinch), `external_context` (USGS) y `network_inventory` (RIPEstat inventario). OONI debe clasificarse según el test y no considerarse una familia adicional por defecto. Una fuente puede aportar más de un tipo de medición; etiquetar a nivel de observación.

Para cruzar incidentes, exigir coincidencia comprobable de operador, intervalo temporal y alcance geográfico; la coincidencia de ASN y una fecha no confirma un distrito. Conservar `UNKNOWN` ante dependencias o zonas no resueltas. En la PoC **no** desarrollar un motor de activación ni probabilidades; solo producir una matriz de coincidencias y discrepancias, con ejemplos auditables.

## 23. Cobertura por tecnología y pertinencia para Win

Para cada fuente y operador, clasificar la evidencia en `fixed_internet`, `mobile_data`, `sms`, `voice`, `bgp_routing`, `dns_http`, `declared_coverage`, `external_context`, `unknown`, permitiendo múltiples etiquetas solo cuando el dato lo respalde. Guardar `technology_basis` y `technology_confidence` como calidad de clasificación, no probabilidad de caída. Añadir `signal_role` con `DIRECT_INTERNET`, `CORROBORATION_ONLY`, `CONTEXT_ONLY` o `UNKNOWN`: internet fijo/móvil puede ser directo para su tecnología; SMS/voz solo corroboración; mapas de cobertura declarada solo contexto.

**Regla de inferencia:** la alerta objetivo requiere evidencia directa de internet fijo o móvil, y debe conservar cuál tecnología está respaldada. Señales SMS/voz alineadas en operador, zona y tiempo pueden elevar la confianza cualitativa en una falla amplia, pero no sustituyen evidencia directa ni identifican la tecnología afectada. Varias fuentes de mensajería correlacionadas cuentan como una sola familia. Cobertura declarada no es señal de incidente ni incrementa confianza. No asignar pesos numéricos hasta calibrarlos con incidentes y negativos independientes. BGP no prueba interrupción de una antena o distrito; sismos no prueban falla de telecomunicaciones; coordenadas de una medición no son coordenadas de una avería. La matriz final debe mostrar explícitamente las brechas de internet fijo y móvil y la granularidad geográfica para los cuatro operadores.

## 24. Política de costo cero, licencia y seguridad de ejecución

- Costo **USD 0 efectivo** durante la PoC. No introducir tarjeta, contratar plan, iniciar prueba con cobro posterior, consumir créditos facturables ni desplegar servicios cloud. Un servicio que requiere pago se marca `BLOCKED_PAID`. Si un servicio requiere token gratuito, solo se usa tras verificar términos y cuotas; nunca imprimir el secreto.
- Consultas públicas de RIPE Atlas solamente: no lanzar mediciones nuevas que consuman créditos sin aprobación explícita y comprobación de que son gratuitos. Globalping: no lanzar pruebas activas si no se ha verificado antes la cuota gratuita y sus condiciones.
- Solo endpoints oficiales, feeds oficiales, archivos de datos públicos y WebSockets documentados. Prohibidos scraping HTML, eludir autenticación, automatizar interfaces web y proveedores no oficiales de X. X/Osiptel queda `BLOCKED_NO_FREE_API` cuando no haya acceso gratuito autorizado; no sustituirlo con scraping.
- La disponibilidad pública o gratuidad no demuestra licencia comercial. Registrar `license_status` (`VERIFIED_COMPATIBLE`, `RESTRICTED`, `UNKNOWN`), URL de términos, fecha de consulta y restricciones. `UNKNOWN` bloquea recomendación de producción, pero no necesariamente una consulta de evaluación permitida.
- Respetar robots/condiciones aplicables, límites, `Retry-After`, backoff, timeout, presupuesto de peticiones por ejecución y cache. Evitar recolectar identificadores personales; anonimizar ejemplos.
- Fallos de DNS, timeout, HTTP 429/403, ausencia de registros y falta de cobertura deben tener estados diferentes. Ninguno equivale a «no hay incidentes».

## 25. Entregables adicionales y puerta de salida

Además de los entregables de la sección 20, generar:

- `reports/temporal_validation.csv`: fuente, operador, tamaño de muestra, retraso de publicación y de recolección (mediana/p90), intervalos de observación, campos desconocidos.
- `reports/evidence_independence.csv`: parejas de fuentes, familias, dependencias conocidas, grado de independencia y eventos coincidentes.
- `reports/technology_coverage.csv`: fuente × operador × tecnología × granularidad, con evidencia y frescura.
- `reports/geo_validation.csv`: fuente × operador, lat/lon disponible, procedencia, precisión, conflictos, códigos UBIGEO y porcentaje de registros ubicables, **sin equiparar centroides a ubicación de falla**.
- `reports/free_access_and_licensing.md`: evidencia del acceso gratuito, límites, autorización comercial, bloqueos y fecha de verificación.
- `reports/execution_manifest.json`: commit o versión del código, fecha UTC, entorno, fuentes intentadas, parámetros no sensibles, cantidad de consultas, cuotas y paths de evidencia.

**Cierre:** la PoC se considera ejecutada cuando todos los adaptadores están evaluados o bloqueados con motivo documentado, las pruebas automatizadas pasan y existen informes auditables. No exige que todas las fuentes resulten aptas. Una fuente pasa a `CANDIDATE_FOR_PRODUCTION` solo si demuestra utilidad peruana real, frescura compatible, cobertura por operador, licencia revisable y costos documentados (sin imponer un límite); de lo contrario `SECONDARY_ONLY`, `INSUFFICIENT_DATA`, `NOT_SUITABLE` o `BLOCKED`. Esta decisión es una recomendación técnica, no un despliegue.

## 27. Planificador de consultas y validación del free tier (solo simulación en esta PoC)

**Objetivo:** durante la validación medir cuántas consultas necesita realmente cada fuente y diseñar un planificador con límites configurables, para aprovechar el acceso gratuito cuando sea viable sin sacrificar innecesariamente la velocidad de detección. **No desarrollar el planificador de producción ni ejecutar monitoreo comercial en esta PoC.**

Para cada fuente registrar: `provider`, `endpoint`, `country=PE`, `operator_asn`, `request_cost_unit`, `requests_per_cycle`, `tests_per_request`, `free_quota_value`, `free_quota_period`, `quota_reset_policy`, `rate_limit_headers`, `auth_required`, `webhook_available`, `data_publication_interval`, `observed_freshness`, `cache_ttl`, `estimated_monthly_calls`, `estimated_monthly_billable_units`, `quota_headroom`, `quota_source_url`, `quota_verified_at` y `confidence_of_estimate`. No confundir llamadas HTTP con pruebas facturables o créditos; documentar la unidad real de cada proveedor. Si un límite no se confirma oficialmente, marcar `UNKNOWN` y no inferir que el servicio es ilimitado.

Evaluar **sin exceder cuotas** tres perfiles *hipotéticos* por adaptador: `normal` (15-30 min), `suspected_incident` (5 min durante una ventana limitada) y `quota_protection` (reducir frecuencia o suspender). Son valores iniciales para simulación, **no** compromisos operativos ni frecuencias garantizadas. Priorizar webhooks y feeds incrementales cuando estén disponibles; evitar consultas repetidas si la fuente publica con menor frecuencia. Estimar cobertura temporal efectiva y retraso adicional introducido por el polling. Si la fuente actualiza cada 60 minutos, consultar cada 5 minutos no aumenta la frescura.

Aplicar límites conservadores por fuente, `Retry-After`, backoff con jitter, caché, deduplicación, `ETag`/`If-Modified-Since` cuando proceda y un interruptor `dry_run` por defecto. La PoC debe simular el consumo de 30 días y escenarios de baja/media/alta demanda **sin emitir esas solicitudes**. Las pruebas reales se harán solo con un número acotado de peticiones gratuitas documentadas. No consumir créditos que puedan generar cobros ni activar suscripciones. Si la frecuencia necesaria excede el free tier, documentar la diferencia y estimar la opción de pago **sin descartar la fuente por precio**.

**Entregables:** `reports/query_budget_by_source.csv`, `reports/free_tier_simulation.csv`, `reports/polling_vs_freshness.md` y pruebas unitarias del simulador. Cada cifra debe incluir fórmula, supuesto, fuente de cuota y fecha de verificación. Estado final por fuente: `FREE_TIER_FEASIBLE`, `FREE_TIER_CONDITIONAL`, `FREE_TIER_INSUFFICIENT` o `UNKNOWN`.

## 28. Cloudflare Radar: bloqueo de licencia comercial y ruta de resolución

La disponibilidad de la API y su token gratuito **no conceden por sí mismos autorización comercial**. La documentación de Radar indica condiciones de licencia CC BY-NC 4.0 para datos de Radar; verificar los términos vigentes y su alcance exacto por endpoint en la documentación oficial: https://developers.cloudflare.com/radar/ . Registrar evidencia documental, fecha, versión de términos y si existe alguna excepción específica.

**Durante la PoC:** permitir únicamente consultas de evaluación compatibles con los términos aplicables. Mantener `commercial_authorization=PENDING`, `production_eligible=false` y `license_status=RESTRICTED_OR_PENDING_REVIEW` mientras no exista autorización escrita o licencia compatible. No activar publicidad, no redistribuir datos crudos y no afirmar que una cuenta Pro/Business/Enterprise cambia automáticamente los derechos de Radar.

**Para resolverlo antes de producción:** consultar a `radar@cloudflare.com` (verificar canal oficial vigente) y solicitar confirmación escrita sobre: uso comercial de datos agregados para detectar interrupciones en operadores peruanos; almacenamiento de series e indicadores derivados; uso interno de indicadores para disparar creatividades publicitarias; atribución y redistribución; endpoints cubiertos; costo de licencia o excepción. Guardar la respuesta como evidencia de autorización, con alcance y vencimiento. Si se deniega o no se responde, conservar Radar como `NOT_PRODUCTION_AUTHORIZED` y evaluar la arquitectura sin sus señales; no suponer equivalencia exacta con IODA, RIPE Atlas o Globalping.

**Entregables:** `reports/cloudflare_radar_license_review.md` con citas a condiciones oficiales, preguntas abiertas y estado de autorización; `reports/with_without_radar.md` con brechas técnicas y riesgos de operar sin Radar. No contactar a Cloudflare ni enviar correo automáticamente durante la PoC sin instrucción expresa del responsable.

## 29. Instrucción única para cualquier agente de código

```text
Lee ARCHITECTURE.md íntegramente antes de escribir código. Este proyecto es SOLO
una PoC local de validación de fuentes de caídas de internet en Perú para
Movistar, Claro, Entel y Bitel. NO construyas el producto Win: sin feed, sin
motor de decisiones, sin UI, sin alertas de campaña, sin GCP y sin LLM integrado.
Costo efectivo de EJECUCIÓN USD 0, sin hardware, scraping, APIs pagadas ni créditos
consumibles. INVESTIGA precios de servicios gratuitos y pagados sin presupuesto máximo para producción. Verifica documentación oficial, licencias y límites antes de cada
conector. Implementa adaptadores mínimos reutilizables y pruebas aisladas.
Consulta datos reales peruanos cuando el acceso gratuito esté comprobado.
Valida geografía/UBIGEO/lat-lon, temporalidad, independencia entre señales y
cobertura por tecnología. Mide consumo real acotado y SIMULA un planificador
de consultas con límites configurables y protección de free tier, sin desplegarlo.
Revisa la licencia comercial de Cloudflare Radar, registra bloqueo para
producción hasta autorización escrita y documenta la alternativa sin Radar. Guarda evidencia cruda fechada, distingue claramente
ERROR, SIN DATOS, SIN COBERTURA y BLOQUEADO. No inventes endpoints, respuestas,
incidentes, porcentajes ni resultados. Genera todos los reportes definidos, incluidos los económicos sin techo de gasto,
ejecuta tests y registra limitaciones. Mantén el repositorio agnóstico al
agente de programación (Claude Code, Codex, DeepSeek u otro).
```


## 30. Análisis de dependencia, resiliencia y pérdida por retiro de CADA fuente (obligatorio)

**Propósito:** determinar cuánto pierde el futuro detector de Win si cualquier servicio deja de estar disponible, pierde su plan gratuito, cambia la API, retrasa datos, deja de cubrir Perú o prohíbe uso comercial. Esta validación se aplica a **todas** las fuentes del inventario, incluidas las geográficas y las de contexto, no solo a Cloudflare Radar. **No implementar el detector de producción**: ejecutar análisis offline sobre evidencias recolectadas y simulaciones reproducibles.

### 30.1 Escenarios por fuente

Para cada adaptador, ejecutar y documentar:

1. **Base:** conjunto completo de fuentes con evidencias realmente disponibles.
2. **Sin la fuente:** retirar completamente sus registros y recalcular métricas observables (`leave-one-source-out`).
3. **Fuente atrasada:** excluir datos fuera de su ventana de frescura medida; evaluar pérdida por demoras.
4. **Fuente intermitente:** simular indisponibilidad de 1 h, 6 h y 24 h sobre registros históricos, señalando expresamente que es una simulación.
5. **Fuente no autorizada comercialmente:** excluirla de un escenario de futura producción, aunque sea técnicamente válida en la PoC.
6. **Fuente de pago inaccesible:** mantenerla como opción investigada, pero excluir sus datos no obtenidos; nunca fingir mediciones.
7. **Familia caída:** repetir el análisis retirando familias completas (BGP, tráfico, mediciones activas, reportes humanos, mensajería, contexto y geografía).
8. **Dependencias comunes:** evaluar fallas conjuntas de fuentes que comparten upstream, plataforma, datos o proveedor.

### 30.2 Métricas obligatorias de pérdida

Reportar por **operador (Movistar, Claro, Entel, Bitel)** y, cuando existan datos, por **departamento/provincia/distrito**:

- **Cobertura:** incidentes de referencia detectables con todas las fuentes frente al escenario sin una fuente; distinguir incidentes con referencia independiente de los inferidos.
- **Oportunidad:** cambio en tiempo hasta primera señal útil, percentiles y ventanas perdidas; si no hay timestamp de inicio confiable, usar solo demora relativa entre fuentes y declararlo.
- **Corroboración:** número y proporción de ventanas con evidencia de dos familias realmente independientes; no contar IODA BGP y RIS Live como dos familias.
- **Granularidad:** pérdida de incidentes localizables por departamento, provincia y distrito, y pérdida de coordenadas/polígonos respaldados.
- **Cobertura tecnológica:** variación para internet fijo, móvil, BGP, DNS/HTTP y avisos SMS/voz, sin tratar mensajería como prueba de caída de internet.
- **Resiliencia:** porcentaje de tiempo en que el sistema hipotético conservaría señales frescas suficientes para corroborar, sin publicar campañas.
- **Costos:** diferencia estimada de gasto y cuotas al retirar la fuente, y costo de sustitutos, sin techo presupuestario.
- **Cumplimiento:** impacto de retirar fuentes cuya licencia comercial esté pendiente, restringida o prohibida.

Usar `delta = metric_full - metric_without_source` solo para métricas comparables. Reportar denominadores, intervalos temporales, tamaño de muestra, supuestos y procedencia. Si no hay incidentes o referencias suficientes, escribir **`INSUFFICIENT_EVIDENCE`** en vez de porcentajes inventados. **No estimar precisión, recall ni falsos positivos reales sin verdad de referencia independiente**; las etiquetas de IODA/Cloudflare pueden introducir sesgo circular.

### 30.3 Sustitutos y planes de contingencia

Para cada fuente producir una ficha con: función única, familias compartidas, alternativas ya evaluadas, posibles alternativas nuevas con API/feed oficial (sin scraping), cobertura **verificada** en Perú, compatibilidad comercial, latencia, cuotas, costos y pérdida residual que ningún reemplazo cubre. No recomendar automáticamente un sustituto por tener soporte global o parámetro `country=PE`.

Ejemplos de hipótesis, **no equivalencias probadas**:

| Si falla... | Qué revisar | Qué no asumir |
|---|---|---|
| IODA | Cloudflare, RIS Live, RIPE Atlas y Globalping | Que BGP equivale a conectividad de usuario final |
| Cloudflare Radar | IODA, RIPE Atlas, Globalping y X | Que existe reemplazo gratuito idéntico para tráfico HTTP/DNS |
| RIPE Atlas / Globalping | La otra fuente de mediciones activas, si hay cobertura por ASN y zona | Que todas las redes peruanas están representadas |
| RIS Live | IODA BGP y otros datos públicos de rutas | Que las fuentes BGP son independientes |
| RIPEstat | Inventarios ASN/prefijos alternativos verificables | Que un ASN corresponde a un solo servicio o zona |
| X / Osiptel | Señales técnicas y avisos oficiales disponibles | Que las fuentes técnicas detectan caídas móviles barriales |
| Infobip / Twilio / Telesign / Sinch | Los otros feeds oficiales de mensajería | Que una falla de SMS confirma falla de internet |
| OONI | Mediciones activas existentes | Que OONI tiene cadencia continua en Perú |
| USGS | Continuar sin contexto sísmico | Que un sismo prueba interrupción de conectividad |
| geoBoundaries / INEI / Nominatim | Catálogos locales previamente obtenidos y con licencia adecuada | Que una coordenada GeoIP representa la ubicación real |

### 30.4 Entregables y criterios de aceptación

Generar `reports/source_dependency_matrix.csv`, `reports/source_loss_analysis.json`, `reports/source_loss_analysis.md`, `reports/fallback_plans.md` y `reports/dependency_graph.json` (o formatos equivalentes documentados). Cada resultado debe registrar `source_id`, `operator`, `zone`, `scenario`, `reference_period`, `sample_size`, `baseline_value`, `without_source_value`, `delta`, `evidence_status`, `assumptions`, `alternative_sources`, `commercial_license_status` y `evaluated_at`.

La validación **no se considera cerrada** hasta que cada fuente tenga una evaluación de retiro, incluso si el resultado es `INSUFFICIENT_EVIDENCE` o `BLOCKED_PAID`, y se documenten explícitamente las funciones sin sustituto comprobado en Perú. El análisis debe ser reproducible con fixtures y datos observados, sin llamadas facturables, sin scraping, sin GCP y sin LLM integrado.

### 30.5 Instrucción obligatoria para el agente de programación

Además de las tareas anteriores, implementar y ejecutar el análisis de pérdida por fuente y por familia, generar los cinco entregables de resiliencia y **no recomendar la arquitectura final por cantidad de APIs conectadas**. Priorizar evidencia peruana, diversidad real de señales, frescura, atribución geográfica y capacidad de operar con fuentes ausentes. Conservar todas las restricciones de validación local y la investigación de costos futuros sin presupuesto máximo.


## 31. Priorización de ejecución y filtros de viabilidad (actualización v9.7)

**Propósito:** reducir trabajo innecesario durante la validación local, sin convertir una ausencia de resultados en un descarte automático ni dejar fuentes sin evaluar. La secuencia es una prioridad de ejecución, no una dependencia que impida estudiar fuentes alternativas. Mantener costo efectivo USD 0, sin GCP, sin scraping, sin LLM integrado y sin presupuesto máximo para la investigación de costos futuros.

### 31.1 Primera pasada: densidad real de datos técnicos peruanos

Comenzar por **IODA, Cloudflare Radar y RIPEstat**, aprovechando la Fase B ya definida. Consultar datos de los **últimos 30 días** cuando el endpoint lo permita y dentro de las cuotas gratuitas. Si una API limita la ventana histórica, dividir las consultas en rangos válidos sin exceder cuotas. Verificar los ASN **candidatos**, nunca tratarlos como asignaciones definitivas sin corroboración: Movistar AS6147, Claro AS12252, Entel AS21575 y Bitel AS262210. Identificar también otros ASN/prefijos relevantes del operador si el inventario muestra que el ASN candidato no cubre su red de acceso.

Para IODA y Cloudflare medir: número de observaciones no vacías, cobertura temporal efectiva, granularidad país/ASN/región, fechas de origen y publicación, lag observable, interrupciones detectadas y si el dato corresponde específicamente a Perú. **No confundir un endpoint accesible o una serie con ceros con evidencia de incidentes.** RIPEstat debe comprobar titularidad/relación de ASN, prefijos y metadatos de rutas; **no exigirle registros de caídas**, pues es una fuente auxiliar de inventario y enrutamiento.

Emitir `reports/phase_b_peru_coverage.md` y `reports/phase_b_peru_coverage.csv`, con `source`, `operator`, `asn`, `time_range`, `sample_count`, `data_density`, `freshness`, `geographic_scope`, `access_status`, `evidence_ids`, `limitations` y `next_action`. Guardar respuestas crudas, metadatos y errores en `evidencias/`.

**Regla de avance:** una densidad insuficiente simplifica las pruebas avanzadas de ESA fuente, pero no cancela la evaluación de otras fuentes ni autoriza descartes definitivos sin examinar filtros, cuotas, retrasos, cobertura alternativa y sesgos de muestreo. Usar `INSUFFICIENT_EVIDENCE` cuando corresponda.

### 31.2 Segunda pasada: RIPE Atlas y Globalping por red y geografía

El primer objetivo es responder: **¿cuántos puntos de medición activos y utilizables hay en Perú para cada operador y ASN candidato?** Registrar el conteo por operador, ASN, estado, departamento cuando esté disponible, fecha de última actividad y si existen mediciones recientes apropiadas. Distinguir explícitamente entre:

- Puntos de medición existentes, puntos activos y puntos con resultados recientes.
- Puntos localizados por metadatos confiables frente a localizaciones inferidas por GeoIP.
- Puntos en redes de acceso del operador frente a infraestructura corporativa, tránsito, hosting o redes ajenas.
- Ausencia de puntos, error de API, endpoint sin inventario, consulta incompleta y cuota agotada.

No asumir que la API de Globalping permite enumerar exhaustivamente todos los puntos de medición por ASN; comprobar sus capacidades documentadas. Si solo hay resultados de pruebas y no un inventario, registrar la cobertura observada y **no presentar el conteo como total de sondas vivas**. No consumir mediciones pagadas ni créditos facturables. Si la cobertura es cercana a cero, clasificar como utilidad limitada para ese ASN o zona, sin descartar otros operadores o usos específicos. Registrar la distribución territorial y la cadencia, no solo el total nacional.

Entregables: `reports/probe_density_peru.csv` y `reports/probe_density_peru.md`, con evidencias trazables en `evidencias/api_responses/`, `evidencias/geographic/` y `evidencias/temporal/`.

### 31.3 Tercera pasada: canales institucionales de Osiptel e Indecopi

Investigar **formalmente**, sin scraping, si Osiptel e Indecopi ofrecen mecanismos oficiales y automatizables para incidentes de telecomunicaciones en Perú: APIs públicas, RSS/Atom, archivos de datos abiertos descargables o canales institucionales sindicados. Verificar acceso gratuito, licencia, periodicidad, esquema, cobertura por operador y zona, latencia de publicación y existencia de interrupciones reales frente a reclamos administrativos.

Priorizar Osiptel por su competencia sectorial. Considerar Indecopi como fuente secundaria y no equiparar reclamos de consumidores con fallas verificadas de internet. Una página web sin API/feed/archivo público utilizable **no autoriza implementar scraping**. Si no se encuentra un mecanismo oficial válido, registrar `NO_OFFICIAL_MACHINE_READABLE_SOURCE_CONFIRMED` y conservar evidencia de las búsquedas, URLs oficiales consultadas y fecha de revisión; no afirmar que el mecanismo no existe universalmente.

Entregable: `reports/peru_institutional_sources.md`, con referencias y evidencias en `evidencias/`.

### 31.4 Cuarta pasada: evaluación integral proporcionada

Una vez completadas las comprobaciones iniciales, aplicar las validaciones geográfica, temporal, tecnológica, de independencia, económica, licencias, cuotas y resiliencia **según la información realmente disponible por fuente**. No crear modelos de pérdida numérica, tasas de falsos positivos ni latencias de detección que no puedan respaldarse con datos. Toda fuente del inventario debe recibir una decisión y un registro de evidencia, aunque las pruebas avanzadas terminen como `INSUFFICIENT_EVIDENCE`, `BLOCKED_PAID` o `NOT_APPLICABLE` justificado.

Evaluar en particular qué se pierde al retirar cada fuente, qué fuentes alternativas **verificadas para Perú** quedan y cuáles son las dependencias compartidas. Mantener los costos futuros sin límite presupuestario de selección; la ejecución local sigue sin generar cargos.

### 31.5 Requisitos de salida y documentación posterior

El informe de validación conserva **todas** las fuentes, incluidas las rechazadas y pendientes, con evidencias. En cambio, el **blueprint técnico futuro** debe contener **solo fuentes aprobadas y componentes que realmente se implementarán**, sin opciones descartadas o especulativas. El blueprint lógico describirá interfaces, flujo y requisitos, sin imponer decisiones de infraestructura GCP: esas corresponden al arquitecto cloud. La propuesta ejecutiva para Win resumirá metodología, resultados, selección, principales descartes y riesgos, con trazabilidad al informe técnico.

**No desarrollar todavía** blueprint definitivo, plataforma de producción, motor de activación ni propuesta comercial final: estos son entregables de una etapa posterior a la validación. Al cerrar esta PoC entregar `reports/validation_decision_register.csv`, con decisión `VIABLE`, `PARTIALLY_VIABLE`, `NOT_VIABLE` o `INSUFFICIENT_EVIDENCE`, alcance peruano observado, motivo y enlaces a evidencias. No promocionar una fuente al blueprint solo porque su API responda.


## 32. Accesos, cuentas, tokens y autenticación por fuente (actualización v9.8)

**Objetivo:** distinguir qué fuentes pueden validarse sin registro de cuáles requieren una cuenta gratuita, token, clave o configuración de suscripción. La validación debe comenzar por accesos públicos y **no debe generar cargos**. Las condiciones actuales se verifican contra documentación oficial durante la ejecución: la tabla es una hipótesis de acceso, no evidencia de autenticación exitosa.

| Fuente | Cuenta para pruebas públicas | Token/API key para pruebas públicas | Acción inicial |
|---|---|---|---|
| IODA | No prevista | No previsto | Consultar API v2 pública y verificar respuesta |
| Cloudflare Radar | Sí | Sí, token de lectura Radar | Preparar cuenta gratuita y token con mínimo privilegio; si falta, `BLOCKED_AUTH` |
| RIPE Atlas | No para consultas públicas | No para consultas públicas | Solo datos y mediciones públicas; no crear mediciones que consuman créditos |
| RIPE RIS Live | No prevista | No previsto | Probar WebSocket público con sesión acotada y reconexión controlada |
| RIPEstat / Country Stats | No prevista | No previsto | Consultar endpoints públicos con límites documentados |
| Globalping | No para cuota anónima | Opcional para mayor cuota gratuita | Probar sin cuenta primero; registrar cuota y costo por prueba/ubicación |
| OONI Explorer | No prevista | No previsto | Consultar API pública y filtrar explícitamente Perú |
| Infobip, Twilio, Telesign y Sinch (status) | No para estado público, sujeto a verificación | No para feeds públicos, sujeto a verificación | Identificar RSS/Atom o API de estado oficial; webhook solo si es viable y gratuito |
| USGS | No prevista | No previsto | Consultar API pública de eventos sísmicos |
| geoBoundaries | No prevista | No previsto | Descargar límites abiertos de Perú con metadatos de licencia |
| INEI / UBIGEO | No para datos abiertos | No previsto para archivos públicos | Obtener catálogo oficial y registrar versión/fecha |
| Nominatim público | No prevista | No previsto | Solo consultas puntuales; respetar política de uso y límites |
| X / cuenta de Osiptel en X | Normalmente sí para API oficial | Normalmente sí para API oficial | Investigar acceso y precios; no usar acceso de pago durante la PoC |
| Osiptel / Indecopi institucional | Depende del canal oficial | Depende del canal oficial | Buscar API, feed o datos abiertos; nunca scraping |

### 32.1 Preparación mínima de credenciales

Para empezar **no se requiere registrarse en todas las plataformas**. Ejecutar primero las pruebas públicas. Si el usuario decide preparar Cloudflare Radar, crear un token de acceso con permisos de lectura mínimos (comprobar el nombre exacto del permiso vigente en el panel oficial). La ausencia de token no debe detener las demás fuentes. Globalping con cuenta gratuita es opcional; la API oficial de X queda condicionada a confirmar que exista una modalidad gratuita y autorizada para la prueba.

Crear `.env.example` sin valores secretos y mantener `.env` fuera del control de versiones y de las evidencias:

```dotenv
CLOUDFLARE_API_TOKEN=
GLOBALPING_API_TOKEN=
X_API_BEARER_TOKEN=
```

Los nombres son interfaces de configuración propuestas, no una obligación de que todas las APIs acepten el mismo tipo de credencial. No imprimir ni persistir tokens, cookies de sesión, encabezados `Authorization`, URLs con claves ni otros secretos. Aplicar redacción a metadatos y logs **sin modificar el cuerpo crudo de respuesta salvo que contenga datos sensibles**; si los contiene, conservar únicamente una versión segura y documentar la omisión. Nunca almacenar credenciales en `evidencias/manifest.jsonl`.

### 32.2 Validación de autenticación y cuotas

Para cada fuente registrar en `reports/source_access_matrix.csv`: `source_id`, `official_auth_documentation_url`, `account_required`, `auth_type`, `free_access_confirmed`, `free_quota`, `quota_reset`, `commercial_use_status`, `tested_at`, `http_status`, `result`, `evidence_ids` y `next_action`. No confundir `401/403` con ausencia de cobertura en Perú. Registrar `BLOCKED_AUTH`, `BLOCKED_PAID`, `RATE_LIMITED` o `INSUFFICIENT_EVIDENCE` según corresponda, sin intentar saltar autenticación, protecciones o cuotas.

Para cada consulta guardar fecha/hora UTC, URL sanitizada, parámetros no sensibles, duración, estado HTTP y respuesta original permitida, dentro de `evidencias/`. Separar los resultados procesados y vincularlos por ID/hash SHA-256. La investigación de costos y condiciones comerciales puede estudiar planes de pago sin suscribirse ni realizar consultas facturables.

### 32.3 Secuencia recomendada para el agente

1. Ejecutar las fuentes públicas sin credenciales, respetando los límites gratuitos.
2. Probar Cloudflare Radar únicamente cuando se proporcione voluntariamente un token gratuito con permisos mínimos; de lo contrario dejar evidencia del bloqueo y continuar.
3. Probar Globalping de manera anónima; solicitar token opcional solo si mejora significativamente la evaluación y no implica cargos.
4. Investigar las condiciones oficiales de X y los canales institucionales; no solicitar tarjetas, pagos ni suscripciones para desbloquear pruebas.
5. Entregar una matriz de accesos y una lista exacta de acciones que el usuario tendría que realizar manualmente, separadas de las validaciones que el agente ya ejecutó.

**Criterio de cierre:** todas las fuentes del inventario deben tener un estado de acceso documentado con evidencia, incluso cuando no se pueda obtener una credencial gratuita. No marcar una fuente como validada por el mero hecho de haber creado una cuenta o generado un token. La PoC sigue siendo local, con costo efectivo USD 0, sin GCP, scraping, LLM integrado ni desarrollo de producción.


---

## 33. Validación de noticias peruanas mediante feeds oficiales (`peru_news`) — actualización v9.10

**Alcance:** evaluar exclusivamente la utilidad incremental de medios **peruanos** como fuente de contexto y corroboración de interrupciones de internet de Movistar, Claro, Entel y Bitel. Es una evaluación de fuentes, **no** una implementación del motor de noticias ni un reemplazo aprobado en producción. No utilizar Google News ni scraping como mecanismo de ingesta.

### 33.1 Cinco medios candidatos (no aprobados)

| Medio peruano | Hipótesis de valor | Acceso automático a verificar | Estado inicial |
|---|---|---|---|
| RPP Noticias | Cobertura nacional y avisos regionales | RSS oficial vigente y condiciones de reutilización | `PENDING_VALIDATION` |
| Agencia Andina | Comunicados institucionales y emergencias | RSS/API/feed oficial vigente | `PENDING_VALIDATION` |
| Diario Correo | Noticias locales y regionales | RSS/API/feed oficial vigente | `PENDING_VALIDATION` |
| La República | Incidentes y reportes regionales | RSS/API/feed oficial vigente | `PENDING_VALIDATION` |
| El Comercio | Incidentes de impacto nacional | RSS/API/feed oficial vigente | `PENDING_VALIDATION` |

La existencia de un medio o una URL histórica de RSS **no demuestra** que su feed funcione hoy, tenga noticias pertinentes o permita procesamiento comercial. Verificar cada mecanismo con fuente oficial y respuesta real; no usar recopiladores RSS de terceros como sustituto de autorización. Si no hay acceso oficial permitido y gratuito para la validación, registrar bloqueo y no ejecutar la integración. Una URL candidata como `https://rpp.pe/rss` se trata como hipótesis hasta comprobar su disponibilidad y condiciones vigentes.

### 33.2 Pruebas mínimas del adaptador de validación

1. Identificar y registrar URL oficial del feed/API, tipo (RSS/Atom/JSON), fecha de verificación, condiciones de acceso, atribución, almacenamiento, retención y reutilización comercial. Registrar `BLOCKED_LICENSE`, `NO_OFFICIAL_FEED_CONFIRMED`, `BLOCKED_AUTH` o `BLOCKED_PAID` según corresponda.
2. Con consultas autorizadas y sin scraping, conservar **respuesta original** y metadatos HTTP (incluidos ETag/Last-Modified cuando existan) en `evidencias/api_responses/peru_news/<medio>/`; usar peticiones condicionales para reducir consumo cuando sean compatibles.
3. Buscar noticias vinculadas a cortes de internet, pérdida de conectividad, interrupciones de fibra, afectación de internet fijo/móvil y los cuatro operadores. Registrar coincidencias y falsos positivos; no confundir cortes eléctricos, problemas de apps, facturación o SMS con una caída de internet.
4. Verificar que cada noticia se refiera efectivamente a Perú. Extraer operador, zona mencionada, tecnología afectada, `published_at`, `updated_at` si existe, y `collected_at` UTC. No deducir la ubicación desde IP ni inventar coordenadas.
5. Comparar los eventos encontrados con incidentes de referencia de IODA, Cloudflare u otras fuentes disponibles. Medir retraso respecto al inicio del incidente **solo si existe un inicio confiable**; en caso contrario registrar `INSUFFICIENT_EVIDENCE`.
6. Deduplicar noticias por URL canónica o identificador disponible, titular normalizado, hora y atribución de comunicado. Varios medios que reproducen una misma nota o comunicado **no constituyen varias confirmaciones independientes**.
7. Evaluar utilidad incremental: incidentes peruanos adicionales, mejora de precisión geográfica, cobertura de operadores no detectados por otras fuentes y demora. Reportar cero hallazgos como observación limitada al período probado, no como prueba de inexistencia de cobertura.
8. Investigar términos comerciales aun si la consulta pública es gratuita; no integrar a producción hasta confirmar permiso aplicable al procesamiento y uso publicitario de indicadores derivados.

**Top 5:** producir un listado de **hasta cinco noticias pertinentes por incidente o ventana evaluada**, ordenadas por coincidencia de operador, zona, actualidad y evidencia; no inventar cinco resultados si hay menos. El ranking es una salida de evaluación, no un feed operativo de Win. Las noticias no activan campañas por sí solas.

**Entregables:** `reports/peru_news_feeds.csv`, `reports/peru_news_relevance.csv`, `reports/peru_news_top5.md`, `reports/peru_news_incremental_value.md`. Todos con IDs del manifiesto y rutas de evidencias originales. Si no existe feed oficial utilizable, reportar el bloqueo en lugar de hacer scraping.

### 33.3 Decisión de inclusión

El adaptador `peru_news` solo será candidato al blueprint futuro si demuestra cobertura peruana real, aportación incremental frente a las señales existentes, oportunidad temporal útil y condiciones de uso comercial viables. Si la cobertura es esporádica o tardía, podrá clasificarse como contexto histórico o `NOT_VIABLE` para activación. No promover medios por reputación o popularidad.

## 34. Validación reforzada de OSIPTEL: SISREP y sistemas de medición de calidad — actualización v9.10

**Objetivo:** investigar específicamente si los sistemas institucionales de OSIPTEL ofrecen datos oficiales automatizables de interrupciones o calidad de internet en Perú. Este apartado amplía la sección 31.3; **no revierte la prohibición de scraping**.

### 34.1 Sistemas y canales a investigar

| Candidato | Información potencial | Pregunta decisiva |
|---|---|---|
| **SISREP (Sistema de Información y Registro de Interrupciones)** | Interrupciones reportadas por operadores, mantenimiento, inicio, duración y áreas afectadas, si tales campos están disponibles | ¿Existe API, RSS, archivo abierto descargable o convenio de acceso institucional autorizado para obtener eventos recientes? |
| **Sistemas de medición de calidad de OSIPTEL** | Indicadores de velocidad, latencia, pérdida y calidad por operador/área, según disponibilidad | ¿Se ofrecen datos con granularidad y frescura suficientes para incidentes, no solo informes agregados? |
| **Datos abiertos y publicaciones oficiales de OSIPTEL** | Series históricas, interrupciones y reportes sectoriales | ¿Existen datasets descargables, frecuencia de actualización, licencia y cobertura por operador? |
| **Canales de Indecopi** | Reclamos o comunicaciones relacionados con telecomunicaciones | ¿Aportan información adicional, o solo reclamos tardíos sin validación de caída? |

**Referencia institucional inicial a comprobar:** `https://www.gob.pe/33307-sistema-de-informacion-y-registro-de-interrupciones-sisrep`. La existencia de una página informativa de SISREP **no implica** que exista una API pública o que el público pueda descargar los registros. No confundir datos internos del regulador con datos disponibles para terceros.

### 34.2 Protocolo de validación

1. Consultar documentación oficial, catálogos de datos abiertos, términos de uso y canales de acceso documentados; registrar URLs, fecha, licencia y si el acceso es público, restringido o requiere convenio.
2. Solo cuando haya endpoint/feed/archivo oficialmente accesible y gratuito para la PoC, ejecutar una muestra permitida y guardar el resultado crudo en `evidencias/api_responses/osiptel/` o `evidencias/historical/osiptel/`.
3. Determinar si los registros identifican operador (Movistar, Claro, Entel, Bitel), servicio (fijo/móvil), fecha de inicio y fin, departamento/provincia/distrito/UBIGEO, severidad y momento de publicación. Registrar nulos en vez de inferir valores.
4. Comparar, cuando sea posible, incidentes peruanos con IODA, Cloudflare y otras fuentes, midiendo **valor incremental** y retraso. No atribuir causalidad ni usar reportes agregados como confirmación de una caída puntual.
5. Investigar formalmente si existe acceso institucional autorizado aunque no sea público, y documentar **requisitos, precio publicado si lo hubiera, condiciones y siguiente acción**; no simular accesos, eludir autenticación ni afirmar disponibilidad no probada.
6. Diferenciar `OFFICIAL_DATA_CONFIRMED`, `ACCESS_RESTRICTED`, `NO_OFFICIAL_MACHINE_READABLE_SOURCE_CONFIRMED`, `INSUFFICIENT_EVIDENCE` y `NOT_USEFUL_FOR_REAL_TIME`, con evidencia verificable. La ausencia de API pública encontrada no significa que el regulador carezca de datos.
7. Evaluar qué se pierde si OSIPTEL no está disponible y qué señales independientes permanecen, conforme a la sección de resiliencia. Los comunicados oficiales en X se evalúan separadamente y solo mediante acceso autorizado.

**Entregables:** `reports/osiptel_sisrep_access.md`, `reports/osiptel_quality_data.md`, `reports/peru_institutional_sources.md` actualizado y entradas correspondientes en `reports/validation_decision_register.csv`. Evidencias en `evidencias/` con hashes SHA-256 y fechas UTC.

## 35. Orden de ejecución, cierre y traspaso documental — actualización v9.10

- Mantener primero la comprobación de IODA, Cloudflare Radar y RIPEstat, y la densidad real de RIPE Atlas y Globalping por ASN peruano. En paralelo, investigar la disponibilidad oficial de SISREP y feeds de los cinco medios; **no bloquear las fuentes principales** esperando autorizaciones institucionales.
- Ejecutar `peru_news` y OSIPTEL con el mismo control de cuotas, licencias, costos, temporalidad, geografía e independencia exigido al resto. La ejecución de la PoC sigue siendo **local, sin GCP, sin scraping, sin LLM integrado y con costo efectivo USD 0**. Investigar tarifas comerciales futuras sin fijar presupuesto máximo y sin consumir servicios facturables.
- Conservar toda evidencia, incluidos errores y bloqueos, **solo dentro de `evidencias/`**. Los informes de `reports/` deben apuntar a evidencia identificable, fechada y verificable. Nunca inventar feeds, incidentes, permisos, densidades, latencias o precios.
- Toda fuente añadida debe figurar en la matriz de acceso, la matriz de utilidad para Perú, el registro de decisiones y el análisis de resiliencia, aun si su estado final es `INSUFFICIENT_EVIDENCE` o `NOT_VIABLE`.
- **Después de la validación**, el blueprint técnico/lógico contendrá únicamente las fuentes aprobadas y los componentes necesarios; las descartadas y pendientes quedarán documentadas en el informe de validación. El arquitecto cloud definirá posteriormente la infraestructura GCP. La propuesta ejecutiva para Win utilizará los resultados verificados, no hipótesis.

**Criterio de aceptación de v9.10:** no considerar `peru_news`, SISREP ni las mediciones institucionales como aprobadas por aparecer en este documento. Solo una prueba autorizada, reproducible y con cobertura peruana demostrada permite proponer su incorporación a la arquitectura objetivo.


## 36. Propósito operativo preciso: algoritmo propio y activación programática (aclaración v9.10)

### 36.1 Qué construirá Win después de la validación

La solución futura **no comercializará ni republicará los datos originales de terceros**. Su finalidad será crear un **algoritmo propio de detección y corroboración** que procese señales autorizadas y produzca indicadores derivados de interrupciones o degradación de internet en Perú, por operador y zona, para alimentar decisiones de activación publicitaria programática.

Flujo lógico objetivo, **solo de referencia en esta PoC**:

1. Fuentes externas autorizadas (conectividad, BGP, tráfico, reportes humanos, incidencias oficiales y contexto) aportan observaciones.
2. El algoritmo propio normaliza, correlaciona y verifica temporalidad, operador, tipo de servicio, calidad de la señal y localización. Aplica reglas conservadoras para evitar falsos positivos.
3. Si existe evidencia suficiente, produce un indicador derivado de incidente con operador, zona validada, vigencia, confianza, evidencia trazable y estado; si no, no recomienda activar.
4. Una capa futura transforma el indicador en **criterios de segmentación geográfica o radio** compatibles con la plataforma programática, según las capacidades efectivamente confirmadas con Win.
5. La plataforma programática selecciona audiencias que cumplan esos criterios y muestra creatividades de Win. No se asume identificación individual de clientes de un operador a partir de una caída o de su IP.

**Ejemplo ilustrativo, no incidente comprobado:** si se confirma una interrupción de Claro en una zona de Lima, el sistema podrá emitir una señal de activación para esa zona o un radio justificado, con vigencia limitada; la plataforma programática podrá mostrar una creatividad de Win a usuarios elegibles ubicados en esa segmentación. La precisión del radio y la correspondencia entre zona afectada y audiencia deben validarse; un ASN o GeoIP aislado no justifican una ubicación física.

### 36.2 Diferenciar usos de datos

- **Consulta de evaluación:** probar APIs y feeds autorizados, conservar muestras permitidas y documentar cobertura de Perú sin activar campañas.
- **Procesamiento propio:** generar métricas, correlaciones e indicadores derivados mediante un algoritmo desarrollado por el equipo.
- **Activación programática:** usar esos indicadores para decidir dónde y cuándo activar creatividades publicitarias; la segmentación y la entrega dependen de la plataforma de medios.
- **Redistribución:** publicar o revender datos originales de terceros es una actividad distinta y **no forma parte del alcance previsto**.

El carácter propio del algoritmo y la ausencia de reventa **no garantizan** que toda licencia permita usar las observaciones de origen para decisiones publicitarias. Se debe verificar si los términos de cada fuente permiten la consulta, el almacenamiento, la transformación, la generación de indicadores derivados y su utilización para activar publicidad. Evitar repetir esta advertencia en cada sección: centralizar los hallazgos en la matriz de derechos de uso y registrar bloqueos concretos por fuente.

### 36.3 Qué se valida ahora y qué se deja para después

**En la validación actual (local, USD 0, sin scraping, sin GCP y sin LLM integrado):** verificar que las fuentes aporten evidencia real de Perú, operador, servicio, zona, latencia y valor incremental; investigar cuotas, costos y permisos para indicadores derivados usados en publicidad. Conservar respuestas originales permitidas, timestamps, hashes y trazabilidad en `evidencias/`. Puede simularse *offline* un caso ilustrativo de indicador para comprobar disponibilidad de campos, sin implementar el motor real ni activar campañas.

**Después de la validación:** definir el algoritmo, los umbrales, los estados, el esquema del indicador, el blueprint lógico y la integración programática. El blueprint mostrará solo fuentes aprobadas; los descartes y su justificación quedarán en el informe de validación. El arquitecto cloud diseñará por separado la infraestructura GCP.

### 36.4 Matriz única de derechos de uso para indicadores derivados

Incorporar o actualizar `reports/data_usage_rights_matrix.csv` con una fila por fuente y los campos: `source`, `terms_url`, `checked_at_utc`, `evaluation_access`, `raw_data_storage`, `derived_indicators`, `advertising_activation`, `attribution_required`, `redistribution_allowed`, `authorization_required`, `authorization_status`, `evidence_path`, `notes`. Utilizar `CONFIRMED`, `RESTRICTED`, `PENDING_PERMISSION` o `UNKNOWN` y **no deducir permiso por silencio**.

Para Cloudflare Radar, conservar la revisión específica de la sección 28 y consultar el permiso para **señales derivadas utilizadas internamente en activación programática**, aclarando que no se redistribuirán datos crudos. Aplicar el mismo criterio a todas las demás fuentes sin convertirlo en un impedimento para las pruebas gratuitas que sí estén autorizadas.

**Criterio de aceptación adicional:** los reportes deben distinguir claramente entre una fuente útil para detectar caídas y una fuente cuyo uso en activación publicitaria futura está permitido, pendiente o restringido. Ninguna fuente se promoverá al blueprint definitivo sin resolver ambas dimensiones.


## 37. Contrato de salida obligatorio: JSON, XML o feed consumible por Sonata (actualización v9.12)

### 37.1 Objetivo de negocio y frontera del sistema

**El producto final del motor de detección no es un dashboard ni una plataforma de compra de medios: es un estado de activación estructurado, actualizado y consumible por Sonata o la plataforma programática que confirme Win.** Debe indicar cuándo, dónde y para qué operador competidor existe evidencia suficiente de interrupción o degradación de internet. Sonata aplicará sus reglas de creatividad dinámica y segmentación. No asumir que Sonata admite un formato, endpoint, método de autenticación, geofencing o frecuencia de polling determinados hasta confirmarlo formalmente.

Flujo objetivo:

```text
Fuentes aprobadas para Perú (solo las que superen la validación)
  -> normalización / control de frescura y calidad
  -> correlación de familias independientes / atribución de operador y zona
  -> estados de incidente y salvaguardas
  -> indicador propio y política de activación
  -> adaptador de publicación JSON / XML / feed (según contrato confirmado)
  -> Sonata / plataforma programática de Win
  -> regla trigger + segmentación geográfica + creatividad de Win
  -> desactivación por recuperación, expiración o degradación de confianza
```

**Límite de la PoC actual:** no desarrollar ninguno de los módulos productivos anteriores, no publicar un feed real, no activar creatividades y no integrar Sonata. Durante la validación se debe **investigar y documentar** los requisitos del contrato de salida y la disponibilidad de los campos que lo alimentarán; se permiten ejemplos estáticos y pruebas de esquema totalmente offline.

### 37.2 Preguntas obligatorias para Win / Sonata (pendientes, no inventar respuestas)

| Tema | Pregunta de integración | Resultado esperado |
|---|---|---|
| Interfaz | ¿Sonata consume una URL externa por polling, recibe push/webhook o requiere una integración intermediaria? | Método y contrato oficial |
| Formato | ¿JSON, XML, RSS/Atom, CSV u otro esquema propio? ¿Acepta arrays de incidentes? | Formato y versión acordados |
| Frecuencia | ¿Cada cuánto lee el feed? ¿Cuál es el retraso máximo tolerado? | SLA de lectura y propagación |
| Seguridad | ¿Token, firma, allowlist IP, mTLS o URL firmada? | Requisitos de autenticación |
| Geografía | ¿Qué segmentos acepta: departamentos, distritos, códigos internos, coordenadas, radios o polígonos? | Catálogo de zonas / radios soportados |
| Creatividad | ¿Puede cambiar creatividad existente, activar/desactivar reglas o ambas? | Mapeo trigger -> acción |
| Semántica | ¿Cómo interpreta ausencia de eventos, `false`, expiración, `degraded` y `down`? | Comportamiento fail-safe |
| Datos | ¿Qué campos mínimos, límites de tamaño, latencia, caché y tasa de errores admite? | Esquema y restricciones |
| Pruebas | ¿Existe ambiente de pruebas o modo sombra para validar el feed sin servir publicidad? | Plan de homologación |
| Operación | ¿Quién controla las reglas y la segmentación? ¿Quién puede hacer rollback? | Responsabilidades y soporte |

Si no hay respuestas, documentar `SONATA_CONTRACT_PENDING` y no presentar como confirmada la integración. El contrato final es responsabilidad conjunta del equipo de desarrollo y el equipo de Sonata/Win; el arquitecto GCP definirá posteriormente el despliegue.

### 37.3 Esquema lógico independiente del formato

Campos mínimos sugeridos (no son aún un contrato acordado):

| Campo | Propósito | Regla |
|---|---|---|
| `schema_version` | Evolución compatible | Versionado explícito |
| `generated_at` | Fecha UTC de generación | ISO 8601 con zona |
| `valid_until` | Caducidad global del documento | Si expira, no activar |
| `system_status` | `ok`, `degraded`, `down` | Fallar de forma segura |
| `events[].incident_id` | Identificador estable e idempotente | No incluir datos personales |
| `events[].operator` | `movistar`, `claro`, `entel`, `bitel` | Catálogo cerrado |
| `events[].service_type` | `fixed`, `mobile`, `unknown` | No inferir tecnología |
| `events[].incident_type` | `outage`, `degradation`, `unknown` | No equiparar SMS con internet |
| `events[].state` | `candidate`, `active`, `recovering`, `closed` | Solo `active` elegible para trigger |
| `events[].trigger` | Booleano de activación | Requiere reglas y evidencia suficiente |
| `events[].confidence` | Confianza calibrada, si existe | No confundir con severidad ni porcentaje de afectados |
| `events[].severity` | Severidad estimada | Opcional y fundamentada |
| `events[].zone` | Zona normalizada compatible con Sonata | No inferir de ASN o IP aislada |
| `events[].ubigeo` | Identificador administrativo cuando corresponda | Catálogo oficial validado |
| `events[].geo_precision` | `country`, `department`, `province`, `district`, `unknown` | Separar precisión de evidencia |
| `events[].latitude/longitude` | Punto representativo opcional | No representa ubicación exacta de la caída |
| `events[].radius_m` | Radio opcional | Solo si hay justificación geográfica y Sonata lo admite |
| `events[].started_at` | Inicio estimado del incidente | Diferente de la fecha de publicación |
| `events[].expires_at` | Caducidad por incidente | No exceder política de seguridad |

No publicar textos de quejas, identificadores de usuarios, IP de clientes ni datos crudos. El contrato final podrá usar identificadores geográficos propios de Sonata y no necesariamente coordenadas.

### 37.4 Ejemplo de salida JSON (FICTICIO; no incidente real)

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-10-24T20:15:00-05:00",
  "valid_until": "2026-10-24T20:30:00-05:00",
  "system_status": "ok",
  "events": [
    {
      "incident_id": "demo-pe-claro-lima-norte-001",
      "operator": "claro",
      "service_type": "unknown",
      "incident_type": "outage",
      "state": "active",
      "trigger": true,
      "confidence": 0.92,
      "zone": "lima-norte",
      "ubigeo": null,
      "geo_precision": "unknown",
      "latitude": null,
      "longitude": null,
      "radius_m": null,
      "started_at": "2026-10-24T20:04:00-05:00",
      "expires_at": "2026-10-24T21:00:00-05:00"
    }
  ]
}
```

La etiqueta `lima-norte` es **una zona comercial ilustrativa**, no un distrito oficial ni un polígono validado. El ejemplo **no** constituye evidencia real ni implica que Sonata acepte ese valor. La confianza numérica también es ficticia; solo se publicará como probabilidad si existe calibración suficiente.

### 37.5 Ejemplo equivalente XML (FICTICIO)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<triggerFeed schemaVersion="1.0" systemStatus="ok"
  generatedAt="2026-10-24T20:15:00-05:00"
  validUntil="2026-10-24T20:30:00-05:00">
  <event id="demo-pe-claro-lima-norte-001">
    <operator>claro</operator>
    <serviceType>unknown</serviceType>
    <incidentType>outage</incidentType>
    <state>active</state>
    <trigger>true</trigger>
    <confidence>0.92</confidence>
    <zone>lima-norte</zone>
    <geoPrecision>unknown</geoPrecision>
    <startedAt>2026-10-24T20:04:00-05:00</startedAt>
    <expiresAt>2026-10-24T21:00:00-05:00</expiresAt>
  </event>
</triggerFeed>
```

**JSON y XML son representaciones alternativas de un mismo estado lógico**, no dos productos distintos. Un "feed" es el mecanismo de entrega/actualización, no necesariamente un tercer formato. RSS/Atom solo se utilizarán si Sonata los acepta y su semántica de caducidad y estado puede representarse sin ambigüedad.

### 37.6 Reglas fail-safe del feed objetivo

1. Si `valid_until` venció, Sonata debe tratarlo como **sin activación**; confirmar que puede aplicar esta regla o diseñar un adaptador compatible.
2. Si `system_status=down`, no habilitar nuevas activaciones y retirar las existentes según la política acordada.
3. Si `system_status=degraded`, la regla conservadora por defecto es **no habilitar activaciones no corroboradas**; precisar si se mantienen algunas activaciones verificadas y vigentes.
4. `candidate`, `recovering` y `closed` no generan un nuevo trigger activo; el cierre debe propagarse y verificarse.
5. Si el documento es inválido, está vacío por error, no es autenticable o no puede leerse, el comportamiento debe ser no activar.
6. Aplicar expiración por evento, histéresis, enfriamiento y límites de activaciones antes de emitir `trigger=true`.
7. Una anomalía técnica sin zona comprobable no debe convertirse en un radio inventado. La ausencia de coordenadas es un resultado válido.
8. Distinguir **incidente detectado**, **segmento geográfico disponible** y **audiencia realmente alcanzable**: no inferir que todos los usuarios del segmento pertenecen al operador afectado.

### 37.7 Criterios de aceptación del futuro adaptador de salida (NO ejecutar en esta PoC)

- Esquema versionado con validación JSON Schema / XSD según el formato aprobado.
- Pruebas de idempotencia, orden temporal, expiración, recuperación, error de fuente y documentos vacíos.
- Pruebas de contrato con Sonata en entorno de homologación, sin activar publicidad real.
- Medición de latencia extremo a extremo: inicio del incidente -> disponibilidad de la señal -> feed actualizado -> lectura por Sonata -> aplicación de regla.
- Control de caché para que Sonata no consuma un estado obsoleto.
- Registro de publicación y lectura cuando la plataforma permita obtener acuses; sin afirmar confirmación si no existe.
- Autenticación, protección contra modificaciones, minimización de datos y mecanismo de rollback.

### 37.8 Entregables adicionales de la validación actual

Crear, sin construir integración de producción:

- `reports/sonata_integration_questions.md`: preguntas anteriores, responsables y respuestas confirmadas o `PENDING`.
- `reports/output_contract_feasibility.md`: mapeo de campos disponibles desde fuentes validadas hacia el esquema lógico y vacíos detectados.
- `reports/trigger_geography_feasibility.csv`: operador, granularidad real, zonas soportadas y restricciones para radio/segmentación; sin ubicaciones inventadas.
- `reports/feed_format_decision.md`: JSON/XML/feed recomendado **solo después** de confirmar las capacidades de Sonata.
- `evidencias/integration/`: documentos de integración aportados/autorizados, ejemplos estáticos y pruebas de esquema offline, registrados en `manifest.jsonl`.

Los documentos de salida deben señalar que **el blueprint definitivo incluirá solo las fuentes aprobadas** y finalizará en un adaptador JSON/XML/feed para Sonata. El informe de validación conservará las fuentes descartadas, costos, licencias y evidencias. El arquitecto cloud será responsable de seleccionar y diseñar la infraestructura GCP después de definir la arquitectura lógica.

### 37.9 Criterio final de alcance

La PoC se considera concluida cuando permite responder **qué fuentes peruanas sirven, qué tan rápido detectan, qué geografía justifican, qué se pierde si faltan y qué campos pueden alimentar el futuro trigger**. No se exige que el agente implemente el algoritmo final, una audiencia publicitaria, un feed productivo o una integración Sonata para cerrar esta fase.


---

## 38. Validación de X mediante TwexAPI: cuentas oficiales peruanas y selección automática

**Estado:** candidato de validación; no aprobado para producción. **Alcance:** exclusivamente prueba local de cobertura, utilidad y costos, sin construir un colector productivo ni un feed Sonata. Se conserva la prohibición de scraping realizado por el proyecto. Dado que TwexAPI es un intermediario que puede obtener datos mediante scraping, **su mecanismo y condiciones de uso deben investigarse y registrarse expresamente**; consumir su API no demuestra por sí solo que el acceso sea autorizado por X. Si la política del proyecto prohíbe también datos obtenidos por terceros mediante scraping, marcar `BLOCKED_POLICY` y no consultar hasta que se autorice expresamente la excepción. Nunca eludir controles de acceso.

### 38.1 Objetivo y alcance geográfico

Determinar si los mensajes públicos dirigidos a **cuentas oficiales peruanas** de Movistar, Claro, Entel y Bitel, junto con publicaciones institucionales de OSIPTEL y entidades del Gobierno del Perú, ofrecen señales oportunas y específicas sobre caídas o degradaciones de internet en Perú. Evitar búsquedas globales genéricas como `Claro caído`, que mezclan países. La pertenencia de una cuenta al Perú es un filtro de entrada, **no prueba de que cada autor o incidente esté ubicado en Perú**.

### 38.2 Cuentas candidatas y validación de identidad

| Grupo | Cuentas candidatas (identidad/handle por verificar) | Captura prioritaria | Rol de señal |
|---|---|---|---|
| Operadores | Movistar Perú, Claro Perú, Entel Perú, Bitel Perú | Respuestas a posts oficiales, publicaciones dirigidas a la cuenta y menciones | Quejas de usuarios únicos |
| Regulador | OSIPTEL | Comunicados propios y respuestas/menciones pertinentes | Confirmación institucional o contexto |
| Telecomunicaciones | Ministerio de Transportes y Comunicaciones (MTC) | Comunicados oficiales sobre conectividad | Contexto institucional |
| Emergencias | INDECI y COEN (comprobar si tienen cuentas distintas) | Comunicados oficiales de emergencias con impacto en conectividad | Contexto externo |
| Consumidor | Indecopi | Avisos oficiales relevantes, sin consultar conversaciones generales indiscriminadamente | Contexto secundario |

Antes de cada consulta: verificar el handle exacto, país, identidad oficial, URL, fecha de verificación y evidencia; no inventar identificadores ni asumir que el nombre de marca corresponde a una cuenta peruana. Registrar cambios de handle y cuentas cerradas. Si una entidad carece de cuenta verificable, marcar `NOT_VERIFIED` y no consultar.

### 38.3 Acceso y prueba gratuita de TwexAPI

- Sitio candidato: https://twexapi.io/ ; inicio/registro: https://twexapi.io/get-started .
- **Oferta de prueba mencionada en la investigación previa, pendiente de confirmar al ejecutar:** 20 000 créditos por siete días, sin tarjeta. **No tratar estas cifras como condiciones vigentes garantizadas**; verificar página oficial, panel de cuenta, créditos reales, vencimiento, límites, endpoint de búsqueda y costo por resultado, conservando evidencia fechada.
- No comprar créditos, no añadir tarjeta, no habilitar renovación automática ni consumir funciones facturables. Si la prueba no está disponible bajo estas condiciones, registrar `BLOCKED_PAID` o `BLOCKED_ACCESS` y continuar.
- Crear un adaptador opcional `twexapi_x.py` con credenciales desde `.env` (`TWEXAPI_API_KEY=`), nunca incrustadas en código, Git, logs ni evidencias. Guardar una plantilla `.env.example` sin secretos.
- Consultar exclusivamente endpoints oficialmente documentados por el proveedor; **no inventar rutas ni parámetros**. Registrar versión de API y URL de documentación. Validar que admite respuestas/hilos, `to:`, menciones, paginación y filtros de fechas; si alguna función no existe, indicarlo y medir la cobertura perdida.
- Guardar los metadatos y respuestas originales permitidos por los términos del proveedor, con redacción o acceso restringido para datos personales. Para informes y muestras compartibles usar identificadores seudonimizados y extractos mínimos; no publicar textos completos de usuarios.

### 38.4 Estrategia de consultas (sin keywords globales)

1. Verificar las cuatro cuentas peruanas de operadores y consultar **respuestas a sus publicaciones**, publicaciones dirigidas a ellas (`to:HANDLE`, si la API lo admite) y menciones explícitas.
2. No equiparar `to:HANDLE` con todas las respuestas a todos los hilos: medir por separado las capacidades reales de cada modalidad y su cobertura.
3. Para OSIPTEL, consultar publicaciones oficiales sobre interrupciones y respuestas ciudadanas relevantes. Para MTC, INDECI, COEN e Indecopi, priorizar **publicaciones oficiales** relacionadas con telecomunicaciones o emergencias; ampliar a respuestas solo si existe evidencia de valor adicional.
4. Usar términos como `sin internet`, `sin señal`, `caída`, `intermitencia`, `fibra`, `datos móviles` **solo como filtros de clasificación dentro del universo de cuentas verificadas**, no como búsquedas globales iniciales.
5. Separar internet fijo, internet móvil, telefonía, SMS, facturación, fallas de apps y atención comercial. No confundir quejas de telefonía/SMS con cortes de acceso a internet.
6. Deduplicar por ID de publicación, conversación y usuario seudonimizado; no contar las respuestas del operador como clientes afectados. Detectar campañas coordinadas y republicaciones.
7. Geolocalizar solo cuando el texto o una fuente confiable aporta un lugar verificable. Un perfil, IP o mención a cuenta peruana no basta para asignar departamento o distrito.
8. Tratar el volumen de quejas solo como corroboración agregada por operador × zona × ventana temporal. Una publicación individual no confirma una caída y no puede usarse para seleccionar o dirigir la creatividad a su autor; la eventual activación es para un segmento geográfico, no para una persona.

### 38.5 Descarte automático de cuentas sin valor demostrado

La selección de cuentas será **basada en evidencia**, no en prestigio institucional. Medir por cuenta y por ventana de observación: publicaciones consultadas, respuestas disponibles, usuarios únicos, quejas de conectividad relevantes, incidentes o comunicados útiles, operador, zonas explícitas, latencia de publicación/consulta, duplicados y créditos consumidos.

| Situación observada | Estado de validación | Acción |
|---|---|---|
| Mensajes o comunicados relevantes y oportunos | `KEEP_CANDIDATE` | Continuar evaluación de costo, independencia y cobertura |
| Respuestas numerosas pero ninguna relacionada con conectividad | `LOW_VALUE` | Excluir del polling frecuente; conservar evidencias |
| No se observan respuestas ni comunicados relevantes | `INSUFFICIENT_EVIDENCE` | No aprobar la cuenta; indicar la comprobación técnica faltante |
| Cuenta institucional sin respuestas, pero con comunicados de interrupción | `KEEP_CANDIDATE` | Mantener como señal oficial; no exigir interacción ciudadana |
| Datos repetidos de otra cuenta sin aporte adicional | `REDUNDANT` | Evaluar exclusión o menor frecuencia |
| API inaccesible, historial insuficiente o cuota agotada | `INSUFFICIENT_EVIDENCE` / `BLOCKED_ACCESS` | No descartar por ausencia de resultados no observables |
| Cuenta no oficial o no peruana | `REJECT_ACCOUNT` | Excluir y conservar justificación |

**No establecer un umbral arbitrario universal de mensajes.** Diferenciar `0 mensajes observados` de `0 mensajes existentes`. Una cuenta con poca actividad puede ser útil en eventos raros; no se aprobará ni descartará solo por el volumen observado. Evaluar utilidad, atribución y frescura con la evidencia disponible.

### 38.6 Métricas y viabilidad económica

Generar por cuenta y por tipo de consulta: solicitudes realizadas, resultados brutos, resultados relevantes, usuarios únicos, incidentes candidatos, porcentaje de mensajes con zona verificable, demora observable, tasa de duplicados, créditos usados y **créditos por mensaje útil**. Estimar consumo para intervalos de 5, 15 y 30 minutos sin ejecutar cargas innecesarias; simular modos normal/sospecha/protección de cuota. No asumir que el costo depende únicamente de llamadas: validar el esquema real de facturación de TwexAPI. Investigar precios y licencia de producción sin fijar presupuesto máximo; la prueba local debe costar USD 0.

### 38.7 Evidencias y reportes obligatorios

Toda la evidencia dentro de `evidencias/`, registrada en `evidencias/manifest.jsonl` con timestamp, origen, parámetros sin credenciales, hash SHA-256, licencia/restricciones y resultado. Crear subcarpeta `evidencias/x_accounts/` para identidad de cuentas, respuestas permitidas, metadatos de solicitudes, errores, límites y muestras anonimizadas.

Generar:

- `reports/x_official_accounts_inventory.csv`: entidad, cuenta, handle verificado, URL, grupo, país, fecha y evidencia.
- `reports/x_account_value_matrix.csv`: métricas por cuenta, ventana efectiva, costo, valor incremental, decisión y justificación.
- `reports/x_twexapi_access_pricing.md`: prueba gratuita vigente o no, cuotas, credenciales, condiciones, mecanismo de obtención y riesgos de continuidad/licencia.
- `reports/x_peru_signal_quality.md`: quejas relevantes por operador, tipo de servicio, precisión geográfica, falsos positivos observables y limitaciones.
- `reports/x_account_exclusions.md`: cuentas descartadas provisional o definitivamente, evidencia y condiciones de reingreso.
- `reports/x_source_resilience.md`: qué cobertura humana se pierde al retirar TwexAPI o cada grupo de cuentas, sin inventar métricas cuando falten datos.

### 38.8 Criterios de aceptación y frontera de alcance

El adaptador se considera evaluado solo si existe evidencia reproducible de: acceso permitido, identidad peruana de cuentas, capacidad real de recuperar conversaciones, cantidad de quejas útiles por operador, frescura, geografía, cuota/costo y valor incremental frente a fuentes técnicas. Si no hay acceso gratuito válido, registrar bloqueo y no afirmar cobertura. **No construir clasificador LLM, detector final, audiencia publicitaria ni feed productivo** durante esta PoC. La selección final de cuentas será un insumo del blueprint posterior; solo las cuentas aprobadas aparecerán en la arquitectura objetivo, mientras las excluidas permanecerán en el informe de validación.


---

## 39. Evaluación automática final basada exclusivamente en evidencias

### 39.1 Responsabilidad y alcance

Al finalizar la validación, **el agente de programación debe ejecutar un evaluador reproducible** que genere automáticamente la selección técnica de servicios y cuentas de X a partir de métricas y evidencias almacenadas. La selección no será una opinión libre del modelo ni una decisión basada en prestigio de proveedores. Debe poder recalcularse sin LLM mediante código Python, reglas declarativas y datos observados. El agente implementa, ejecuta, explica y audita el evaluador; **no contrata proveedores, concede permisos comerciales ni despliega producción**.

La selección técnica automática se usará como insumo del blueprint posterior. No implica autorización contractual, aprobación de inversión ni habilitación automática de fuentes para campañas de Win. Una restricción contractual no resuelta impide etiquetar una fuente como lista para producción aunque sea técnicamente útil.

### 39.2 Estados finales obligatorios

| Estado | Condición | Tratamiento posterior |
|---|---|---|
| `APPROVED` | Evidencia suficiente de cobertura peruana, aporte incremental, frescura y calidad acordes con su función; sin bloqueos conocidos incompatibles | Candidato seleccionado para blueprint lógico, con capacidades y límites documentados |
| `REJECTED` | Evidencia suficiente de ausencia de valor incremental, incompatibilidad técnica o imposibilidad de uso conforme a requisitos | Excluir del blueprint; conservar evidencia y motivo |
| `CONDITIONAL` | Utilidad técnica demostrada, pero pendiente acceso técnico, cobertura, frescura, granularidad o requisito operativo concreto | Registrar condición técnica verificable y alternativa |
| `INSUFFICIENT_EVIDENCE` | Errores, cobertura insuficiente o falta de incidentes de referencia impiden concluir | No aprobar ni rechazar definitivamente; indicar prueba técnica faltante |

Los estados `BLOCKED_PAID`, `BLOCKED_ACCESS`, `BLOCKED_LICENSE`, `NOT_TESTED`, `UNAVAILABLE` y otros estados operativos de las fases anteriores **se conservan como motivos o subestados**, sin sustituir los cuatro estados finales. Una API que responde HTTP 200 no basta para `APPROVED`. La ausencia de incidentes durante un período tranquilo tampoco basta para `REJECTED`.

### 39.3 Criterios y reglas reproducibles

Crear `config/final_evaluation.yaml` (umbrales y reglas versionados) y `src/evaluation/final_evaluation.py` (evaluador determinista). Las reglas deben considerar, según la función real de cada fuente:

- Cobertura observada en **Perú** y, cuando aplique, desagregación por Movistar, Claro, Entel y Bitel; no asumir que un ASN representa toda la red comercial.
- Densidad y calidad de las observaciones disponibles, distinguiendo ausencia de datos de falta de cobertura; no exigir una duración predeterminada como condición de viabilidad técnica.
- Latencia y frescura de publicación, tiempo hasta detectar eventos de referencia y capacidad para ventanas útiles a triggers.
- Granularidad geográfica, precisión de coordenadas y riesgo de errores GeoIP; no inferir una zona afectada de un centroide o ASN sin corroboración.
- Tipo de servicio observado: internet fijo, móvil, ruteo, SMS/voz, noticias o contexto; no tratarlos como equivalentes.
- Independencia real de familias de evidencia y valor incremental sobre las fuentes ya seleccionadas; identificar dependencias BGP compartidas.
- Confiabilidad, cuotas y posibilidad de realizar la prueba bajo las restricciones técnicas actuales. Licencias, contratación y uso comercial se revisan después y no forman parte de la decisión de viabilidad técnica.
- Resiliencia: cambio medible en cobertura, latencia y corroboración al retirar cada fuente individualmente, con `INSUFFICIENT_EVIDENCE` si no es calculable.

No inventar pesos, puntuaciones o umbrales con apariencia científica. Proponerlos en configuración como **hipótesis explícitas**, justificar cada uno y ejecutar análisis de sensibilidad. Si no existen suficientes eventos de referencia, reportar que precisión, recall o falsas alarmas **no son estimables**; no declarar una fuente precisa basándose solo en coincidencias con IODA/Cloudflare.

### 39.4 Decisión automática sobre cuentas oficiales de X

Aplicar los mismos principios a las cuentas peruanas verificadas de Movistar, Claro, Entel, Bitel, OSIPTEL, MTC, INDECI, COEN e Indecopi. Evaluar por cuenta: respuestas y menciones realmente recuperables, usuarios únicos, mensajes de conectividad relevantes, comunicados oficiales útiles, zona identificable, retraso, duplicidad y créditos consumidos. Las palabras clave se usan para **clasificar conversaciones de cuentas peruanas**, no como búsqueda global indiscriminada.

- Mantener cuentas que demuestren quejas o avisos útiles, aunque su volumen sea bajo si aportan incidentes únicos.
- No aprobar cuentas sin señales relevantes observadas; conservar la evidencia y señalar qué comprobación técnica concreta falta.
- No rechazar una cuenta institucional solo porque no recibe respuestas si publica comunicados relevantes.
- No interpretar `0 resultados recuperados` como `0 mensajes existentes` cuando la API está limitada o incompleta.
- Rechazar cuentas no oficiales o no peruanas con evidencia de identidad; las no verificables permanecen pendientes.

La selección automática de cuentas debe ser **reversible** ante nuevos datos. No se autoriza contratación ni consumo pagado de TwexAPI o X durante la validación.

### 39.5 Trazabilidad y protección de evidencia

Cada decisión debe registrar: `source_id` o `account_id`, `evaluation_version`, `ruleset_hash`, datos disponibles, indicadores calculados, criterios aprobados/fallidos, estado final, razones, dependencias, incertidumbres y rutas relativas a archivos dentro de `evidencias/`. Conservar respuestas originales permitidas, fecha UTC de consulta, origen, parámetros sin secretos y hash SHA-256 en `evidencias/manifest.jsonl`.

Las evidencias que contengan datos personales se guardarán minimizadas o con acceso restringido; los informes no deben publicar textos íntegros de usuarios ni credenciales. Las métricas procesadas deben poder regenerarse desde los insumos conservados conforme a las condiciones de cada proveedor. No fabricar datos de prueba como si fueran mediciones reales.

### 39.6 Entregables automáticos adicionales

Generar obligatoriamente:

1. `reports/final_decisions.md`: tabla de **todas** las fuentes y cuentas evaluadas, estado, función, métricas, razones, riesgos y vínculos a evidencia.
2. `reports/approved_sources.json`: **solo** fuentes con estado `APPROVED`, identificador, cobertura demostrada, operador/zona/tecnología, capacidades, límites y evidencia. No incluir fuentes `CONDITIONAL` como aprobadas.
3. `reports/rejected_sources.md`: descartes, redundancias, justificación, evidencia y condiciones de reevaluación.
4. `reports/conditional_sources.md`: dependencias concretas de acceso, disponibilidad técnica, cobertura o granularidad y siguiente acción requerida.
5. `reports/insufficient_evidence.md`: vacíos, limitaciones técnicas y prueba concreta necesaria para resolverlos.
6. `reports/x_final_account_decisions.csv`: selección por cuenta oficial, estado, métricas y razón de inclusión/exclusión.
7. `reports/decision_sensitivity.md`: impacto de variar umbrales, pesos y ventanas de observación; marcar decisiones inestables.
8. `reports/blueprint_input.json`: resumen **exclusivamente de capacidades aprobadas**, interfaces lógicas requeridas, restricciones verificadas y salida objetivo JSON/XML/feed para Sonata. No crear todavía el blueprint, infraestructura GCP, algoritmo productivo ni feed funcional.

`reports/approved_sources.json` y `reports/blueprint_input.json` deben validarse contra esquemas JSON y contener referencias a evidencias existentes. El archivo `reports/final_decisions.md` debe enlazar a los demás resultados, y un script debe comprobar integridad de hashes, rutas y consistencia de estados.

### 39.7 Pruebas de aceptación del evaluador

Implementar tests que demuestren al menos que: una fuente sin evidencia no se aprueba; un HTTP 200 sin datos de Perú no se aprueba; una cuenta institucional sin respuestas pero con comunicado relevante no se descarta por ese motivo; la licencia pendiente no cambia la clasificación técnica; una fuente redundante no se cuenta como confirmación independiente; y retirar una fuente sin historial suficiente devuelve `INSUFFICIENT_EVIDENCE` en lugar de una pérdida inventada.

Ejecutar el evaluador al concluir las pruebas disponibles, dejando constancia de pruebas bloqueadas y datos faltantes. Los resultados deberán poder reproducirse localmente, sin LLM, sin GCP, sin scraping y **sin gasto efectivo**.

### 39.8 Uso posterior de los resultados

La selección técnica automática será la base para elaborar después un **blueprint lógico limpio**, limitado a fuentes aprobadas, flujos de normalización/correlación, controles de calidad y contrato de publicación JSON/XML/feed consumible por Sonata. Los descartes y las fuentes pendientes permanecerán en el informe de validación, no en el diagrama objetivo. La infraestructura GCP se definirá posteriormente por el arquitecto cloud; la propuesta ejecutiva para Win se sustentará en las mismas evidencias, sin inventar cifras ni capacidades.

## 40. Política obligatoria de reintentos, recuperación de evidencia y reevaluación automática

**Objetivo:** impedir que un error temporal, una consulta mal parametrizada, una ventana histórica tranquila o una cuota gratuita momentáneamente agotada se conviertan en un descarte definitivo. Esta política es una condición previa a ejecutar `final_evaluation` y se aplica a todas las fuentes, feeds, servicios geográficos y cuentas de X, con límites específicos por proveedor.

### 40.1 Estados operativos y distinción entre error y ausencia de evidencia

Cada ejecución registrará `attempt_status`, `http_status` cuando exista, `error_class`, `query_signature`, `source_id`, `operator`, `country`, `window_start`, `window_end`, `attempted_at_utc`, `next_retry_at_utc` cuando corresponda y `evidence_path`. Distinguir:

- `TRANSIENT_ERROR`: timeout, DNS, conexión, HTTP 500/502/503/504 u otros errores recuperables.
- `RATE_LIMITED`: HTTP 429 o cuota temporal alcanzada.
- `AUTH_BLOCKED`: HTTP 401/403 por credenciales, permisos o restricciones; no reintentar en bucle.
- `EMPTY_VALID_RESPONSE`: respuesta técnicamente válida sin registros para los filtros consultados; **no equivale** a ausencia de cobertura.
- `LOW_DENSITY`: registros reales insuficientes para evaluar cobertura o utilidad.
- `DATA_STALE`: datos demasiado antiguos para el propósito de la fuente.
- `SUCCESS_WITH_EVIDENCE`: respuesta verificable con datos relevantes y metadatos completos.
- `BLOCKED_PAID`, `BLOCKED_LICENSE` y `UNAVAILABLE`: conservar motivo, fecha y evidencia; nunca eludir límites de acceso.

### 40.2 Reintentos técnicos por tipo de fallo

| Situación | Acción permitida | Condición de parada |
|---|---|---|
| HTTP 429 | Respetar `Retry-After` y cuotas; reprogramar si corresponde. | No sobrepasar el free tier ni generar cargos. |
| HTTP 500/502/503/504 | Hasta 3 intentos iniciales con backoff exponencial y jitter; configurable por API. | Detener al alcanzar el límite y programar otra ronda. |
| Timeout, DNS o fallo de conexión | Reintentar con backoff, registrar duración y causa observable. | Evitar bucles y fallos en cascada. |
| HTTP 401/403 | Revisar token, scopes, permisos y documentación. | No repetir sin corregir la causa; marcar `AUTH_BLOCKED`. |
| Respuesta válida vacía | Revisar país, ASN, nombres, endpoints, zona horaria y fechas. | No repetir consultas idénticas sin hipótesis nueva. |
| Cuota gratuita agotada | Esperar reinicio de cuota o dejar prueba pendiente. | Prohibido pagar o usar cuentas alternativas para eludir límites. |
| Datos atrasados | Medir frescura y revisar periodicidad oficial. | No inventar fecha de evento a partir de fecha de consulta. |

La configuración estará versionada en `config/retry_policy.yaml`, con `max_attempts`, `base_delay_seconds`, `max_delay_seconds`, `jitter`, `max_validation_rounds`, `quota_guard`, `historical_windows` y límites específicos por fuente. Los valores iniciales son hipótesis operativas, no SLA garantizados.

### 40.3 Ampliación de evidencia ante poca densidad

Cuando haya pocos registros peruanos o ningún incidente, ejecutar, según las capacidades documentadas de cada fuente:

1. Confirmar identidad del operador y ASN candidatos; consultar prefijos o ASN alternativos solo cuando exista evidencia de su relación con el operador.
2. Verificar que los filtros de país `PE`, departamentos, fechas, paginación y tipos de evento no excluyan resultados válidos.
3. Ampliar la consulta a ventanas históricas adicionales **dentro de la retención, cuotas y permisos oficiales**, evitando confundir datos históricos con señal de tiempo real.
4. Contrastar días normales con fechas de incidentes de referencia, sin usar una fuente como verdad absoluta de sí misma.
5. En RIPE Atlas y Globalping, separar puntos activos, ubicación declarada, ASN de acceso y mediciones recientes; una respuesta vacía no prueba que no existan puntos de medición.
6. En cuentas de X, ampliar a respuestas, menciones e hilos de las cuentas peruanas verificadas; no realizar búsquedas globales indiscriminadas por palabras clave. Revisar límites de paginación y profundidad histórica del proveedor.
7. Para feeds de noticias, SMS/voz y fuentes oficiales, evaluar tanto publicaciones recientes como incidentes históricos disponibles; un período sin incidentes no implica que el canal sea inútil.
8. Registrar cada hipótesis, cambio de parámetros y resultado. No efectuar pruebas redundantes sin un motivo explícito.

La ausencia de registros tras ampliar evidencia solo justifica `REJECTED` si el criterio de descarte es verificable y existe suficiente cobertura observacional. De lo contrario, usar `INSUFFICIENT_EVIDENCE`.

### 40.4 Rondas de reevaluación y cierre de pendientes

Realizar una ronda inicial y, cuando corresponda, rondas posteriores espaciadas en el tiempo, siempre dentro de las restricciones gratuitas. Los pendientes por problemas transitorios o baja densidad deberán conservar una `next_action`, una condición de reintento y una fecha elegible para nueva evaluación. No prometer ejecución futura en segundo plano: las rondas se ejecutarán cuando el proceso local esté activo o se lance de nuevo.

El evaluador automático **no puede emitir `REJECTED` basándose solo en el fallo de una llamada, una respuesta vacía o una ventana tranquila**. Antes de cerrar cada decisión, verificar el cumplimiento de esta política. Los estados `CONDITIONAL` e `INSUFFICIENT_EVIDENCE` son resultados válidos y no deben forzarse a una clasificación binaria.

### 40.5 Evidencias y entregables obligatorios

Guardar dentro de `evidencias/` todas las respuestas originales permitidas, errores, metadatos de solicitud sin secretos, ventanas históricas, cambios de filtros y resultados de cada intento. Actualizar `evidencias/manifest.jsonl` con fecha UTC y hash SHA-256; mantener los datos crudos separados de los normalizados.

Generar:

- `reports/retry_history.csv`: fuente/cuenta, ronda, intento, endpoint sin secretos, fecha UTC, error, estado HTTP, espera, cambio de parámetros, resultado y ruta de evidencia.
- `reports/revalidation_queue.json`: pendientes, causa, siguiente acción, condiciones de desbloqueo y fecha elegible, si existe.
- `reports/low_density_analysis.md`: cobertura observada, ventanas, hipótesis probadas, límites y motivo de suficiencia o insuficiencia de evidencia.
- `reports/retry_policy_compliance.md`: verificación de que ninguna fuente fue rechazada por un fallo aislado y de que se respetaron cuotas y restricciones.

Actualizar `reports/final_decisions.md`, `reports/insufficient_evidence.md` y `reports/x_final_account_decisions.csv` con el historial de reevaluación y vínculos a las evidencias. Incluir tests para errores 429, 5xx, 401/403, respuestas vacías, datos escasos, paginación incompleta y recuperación posterior. El resultado final debe ser reproducible, sin scraping implementado, sin GCP, sin LLM integrado y con **costo efectivo de validación USD 0**.

