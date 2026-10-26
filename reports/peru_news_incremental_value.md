# Valor incremental de prensa

Los endpoints RSS/Atom responden y se parsean. Ninguno de los ítems de la captura produjo una coincidencia con la regla estricta de conectividad, así que no hay observaciones para probar detección de incidentes ni aporte sobre las señales técnicas. La ausencia de coincidencias en esta captura no significa que el feed no sea útil. No se calculan falsos positivos, precisión, recall ni incremento frente a otras fuentes. Ver `peru_news_feeds.csv` y `peru_news_relevance.csv`.


## Medios nacionales adicionales

La ampliación probó ocho endpoints RSS de Perú21, Gestión, Trome, El Peruano y Expreso sin scraping de artículos. Solo dos feeds distintos se parsearon con contenido: Perú21 (20 ítems, con duplicado entre URLs) y Gestión Tecnología (1); no hubo coincidencias estrictas. Los resultados HTTP por endpoint están en `peru_major_newspaper_feeds.csv`. En esta muestra no hay señal que añadir a las fuentes ya evaluadas.
