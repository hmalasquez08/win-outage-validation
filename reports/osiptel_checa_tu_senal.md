# Revisión de Checa tu Señal de OSIPTEL

**Consulta:** 2026-10-25. **URL oficial:** https://checatusenal.osiptel.gob.pe/

## Qué es y qué información expone

La página vigente presenta un mapa para consultar cobertura móvil por departamento/provincia/distrito/centro poblado, operador, tecnología 2G/3G/4G/5G y tipo de cobertura garantizada/total. La propia interfaz indica que la información es reportada trimestralmente por las operadoras y que la carga visible corresponde al 2 de septiembre de 2026 (corte 2026-II). OSIPTEL define “cobertura total” como cobertura garantizada más capacidad adicional; esta última puede tener desempeño variable. La información es una declaración de cobertura, no una observación continua de disponibilidad.

El material institucional más reciente de OSIPTEL también describe Checa tu Señal como consulta comparativa de cobertura reportada por operador; menciona información de internet fijo, pero la página principal abierta describe el mapa como cobertura móvil y sus selectores son 2G/3G/4G/5G. No queda probado que el aplicativo represente servicio fijo cableado/fibra de forma equivalente; no atribuirle esa cobertura.

## Evaluación para esta validación

| Uso | Evaluación |
|---|---|
| Detectar una interrupción en curso | No: la actualización trimestral y las declaraciones de cobertura no prueban disponibilidad instantánea. |
| Confirmar operador y tecnología esperados en una zona | Referencia contextual potencial, sujeta a declaración de la operadora y fecha del corte. No equivale a calidad real ni a inventario de abonados afectados. |
| Geometría distrital / UBIGEO | La UI ofrece navegación administrativa, pero no se confirmó un archivo GIS o endpoint de descarga público y documentado. No se usaron endpoints internos/no documentados ni se extrajeron mosaicos del mapa. |
| Detector de servicio fijo | No demostrado; la información de mapa visible es móvil por tecnología. El posible internet fijo inalámbrico no equivale a fibra/cable. |
| Feed de incidentes | No se encontró en la página consultada un listado público, RSS, API o exportación documentada de incidentes. La herramienta antigua “Señal OSIPTEL” sí permitía reportar interrupciones, según una nota institucional de 2022, pero eso describe envío de reportes por usuarios, no un feed consultable de eventos. |

## Decisión

Registrar como **referencia contextual de cobertura móvil**, no como fuente detectora de interrupciones ni de geometría oficial descargable. Aporta contexto de cobertura declarada; no es una señal del estado actual ni incrementa confianza de una caída. En el replay actualizado, IODA registró 1/15 inicios y las anotaciones de Radar 0/15. Para utilizar cobertura como capa geográfica verificable se necesita un archivo o API oficial documentado que pueda archivarse y cotejarse; para incidentes se necesita un canal de eventos público y estructurado distinto.

## Fuentes oficiales consultadas

- [Checa tu Señal](https://checatusenal.osiptel.gob.pe/) — mapa, selectores, fecha y periodicidad declaradas en la interfaz.
- [OSIPTEL: “Checa tu señal: así puedes verificar la cobertura móvil en tu distrito”](https://www.osiptel.gob.pe/portal-del-usuario/noticias/checa-tu-senal-asi-puedes-verificar-la-cobertura-movil-en-tu-distrito) — cobertura 2G/3G/4G/5G, áreas garantizada/total y datos declarados por operadoras.
- [OSIPTEL: herramientas digitales, 13 de junio de 2026](https://www.osiptel.gob.pe/portal-del-usuario/noticias/en-el-inicio-del-mundial-conoce-la-alineacion-titular-de-herramientas-que-te-ayudaran-a-elegir-mejor-tu-servicio-movil/) — menciona la cobertura reportada y que también ofrece información de internet fijo.
- [OSIPTEL: nota sobre Señal OSIPTEL, 28 de octubre de 2022](https://www.osiptel.gob.pe/media/0qtjja02/np28102022-checa-senal.pdf) — la versión histórica permitía a usuarios reportar una interrupción mediante formulario; no acredita consulta pública de registros.
