# Revisión RSS de los diez medios online de mayor alcance semanal en Perú

**Consulta:** 2026-10-25, aproximadamente 21:56 UTC.  
**Criterio de selección:** diez primeras marcas online del Digital News Report 2026 para Perú, publicado por Reuters Institute. El alcance es recuerdo de uso de noticias durante la última semana en una encuesta; no representa analítica web ni participación de mercado. Fuente: [Reuters Institute, Digital News Report 2026: Peru](https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2026/peru).

## Método y límites

Se consultaron únicamente endpoints RSS/XML directos. Se analizaron los títulos, descripciones y fechas contenidos en los feeds para buscar vocabulario explícito de interrupciones de internet. No se abrieron ni extrajeron páginas de artículos. La búsqueda léxica es un filtro exploratorio: una coincidencia debe revisarse semánticamente y una captura sin coincidencias no demuestra que el medio nunca publique noticias sobre cortes.

## Resultado de la lectura

| Puesto | Medio (alcance semanal) | Endpoint consultado | Resultado | Ítems | Coincidencias estrictas | Frescura del ítem más reciente |
|---:|---|---|---|---:|---:|---:|
| 1 | Latina Noticias (26%) | `latinanoticias.pe/rss`, `/feed`, `/rss.xml` | No se confirmó endpoint RSS operativo; `/rss.xml` respondió 404 y las otras rutas no dieron respuesta utilizable. | — | — | — |
| 2 | RPP Noticias (24%) | [rpp.pe/rss](https://rpp.pe/rss) | XML válido | 60 | 0 | 7,7 min |
| 3 | El Comercio (23%) | [feed de portada](https://elcomercio.pe/arc/outboundfeeds/rss/?outputType=xml) | XML válido | 100 | 0 | 7,9 min |
| 4 | La República (23%) | [larepublica.pe/rss/home.xml](https://larepublica.pe/rss/home.xml) | XML válido | 200 | 0 | 2,1 min |
| 5 | América Noticias (22%) | [americatv.com.pe/noticias/feed](https://www.americatv.com.pe/noticias/feed) | XML válido | 33 | 0 | 28,5 min |
| 6 | Infobae.com (21%) | [feed RSS](https://www.infobae.com/arc/outboundfeeds/rss/) | XML válido; feed general, no exclusivamente Perú | 100 | 0 | 1,8 min |
| 7 | Perú21 (17%) | [peru21.pe/rss](https://peru21.pe/rss/) | XML válido | 20 | 0 | 87,0 h |
| 8 | ATV Noticias (16%) | [atv.pe/rss](https://www.atv.pe/rss/) | XML válido, pero feed observado no era oportuno | 20 | 1 coincidencia léxica; 0 pertinentes | 28,2 días |
| 9 | Exitosa Noticias (15%) | `exitosanoticias.pe/rss`, `/feed` | Ambas rutas respondieron 404 | — | — | — |
| 10 | TV Perú (14%) | `tvperu.gob.pe/rss`, `/feed` | Ambas rutas respondieron 403 | — | — | — |

El único acierto del filtro en ATV fue una nota de videojuegos que usó la palabra “internet”; no reportaba interrupción ni telecomunicaciones. Es un falso positivo del filtro de texto y demuestra por qué el conteo de palabras no debe activar por sí solo una creatividad.

## Evidencia histórica adicional encontrada por búsqueda de noticias

La búsqueda por términos de caída encontró una nota de Infobae del 15 de abril de 2026 sobre una interrupción de internet fijo de Win en Lima. La nota informa reportes de usuarios y respuestas de soporte que describían una falla masiva, y una recuperación progresiva. La cobertura se alinea con el servicio y operador objetivo del proyecto, por lo que demuestra que un medio del top 10 sí puede publicar una señal potencialmente útil. Sin embargo, la nota dice basarse principalmente en reportes de usuarios y redes sociales; no constituye una referencia independiente de esos reportes ni prueba que el RSS la hubiera entregado durante el incidente. Por ello sirve como caso para el replay histórico y como posible corroboración editorial, no como prueba de precisión ni como disparador autónomo. [Nota de Infobae sobre la caída de Win](https://www.infobae.com/peru/2026/04/15/internet-de-win-con-caida-masiva-usuarios-reportan-fallas-desde-la-manana-del-15-de-abril/).

## Interpretación para el detector

La prueba confirma acceso reciente a cinco feeds de alto alcance, pero en esta captura ninguno contenía una señal pertinente de corte. A la vez, la búsqueda histórica encontró un reporte de Infobae sobre una caída real reportada de Win; esto demuestra valor potencial de la prensa como fuente de contexto/corroboración para eventos visibles, no capacidad operacional del feed. Perú21 y ATV tenían contenido reciente demasiado antiguo para la consulta. Latina, Exitosa y TV Perú no quedaron conectados mediante los endpoints probados. Infobae es una fuente general y requiere filtro estricto por Perú.

Los medios pueden aportar corroboración editorial cuando una nota identifica internet, operador, lugar y tiempo. En el caso hallado de Infobae, la información parece derivada de reportes sociales, así que debe tratarse como dependiente de esa familia al combinar evidencias. No se recomienda el texto de noticias como disparador único. La evaluación histórica previa de RPP, La República, Andina, Correo y El Comercio encontró cero coincidencias pertinentes en las capturas archivadas (`peru_news_feeds.csv` y `peru_major_newspaper_feeds.md`).

## Valores de alcance publicados

Reuters Institute reporta uso de marcas para noticias en línea durante la última semana: Latina 26%, RPP 24%, El Comercio 23%, La República 23%, América Noticias 22%, Infobae 21%, Perú21 17%, ATV 16%, Exitosa 15% y TV Perú 14%. El propio informe aclara que son medidas basadas en recuerdo de encuestados, no métricas de tráfico ni un inventario exhaustivo de todos los medios.
