# Prueba de RSS de diarios nacionales adicionales

Se probaron únicamente URLs RSS/Atom directas o publicadas en las páginas RSS oficiales de los medios. No se descargaron ni analizaron páginas de artículos. Una respuesta HTTP exitosa se considera feed útil solo cuando se parsea como XML y contiene señales del tema; un endpoint que devuelve HTML o error no confirma un feed.

El CSV contiene ocho endpoints de Perú21, Gestión, Trome, El Peruano y Expreso, con conteos de ítems y coincidencias del vocabulario de conectividad. Los términos son un filtro inicial: una coincidencia no confirma una interrupción y un cero no demuestra falta de cobertura.

La revisión se amplió después a los diez medios online de mayor alcance semanal en Perú y a un caso histórico de caída de internet de Win reportado por Infobae. Ver `peru_news_top10_rss_check.md`; la comprobación adicional no descarga páginas de artículos para la prueba RSS.


## Resultados observados

De ocho endpoints adicionales, tres respuestas se parsearon como XML: dos URLs de Perú21 (20 ítems cada una; contenido/digest duplicado) y un feed de tecnología de Gestión (1 ítem). Ningún ítem tuvo coincidencia estricta de conectividad. Gestión Perú/Política y ambos endpoints probados de Trome respondieron 404; El Peruano respondió 502 y Expreso 403. Esos errores describen solo las URLs probadas. El archivo `peru_major_newspaper_feeds.csv` conserva estado HTTP y evidencia por endpoint. No se accedió a páginas de artículos.
