# Win outage validation

Runner manual de una sola ejecución para evaluar una posible caída de internet en Perú. Consulta Cloudflare Radar, IODA y, opcionalmente, feeds RSS y posts/comentarios sociales vía Apify y TWEXAPI. Genera siempre un feed XML en formato `feedActivador`: si no hay una decisión calificada, el feed no contiene eventos. No activa campañas ni corre como daemon.

## Requisitos

- Python 3.11 o superior.
- `CLOUDFLARE_API_TOKEN` con acceso de lectura a Cloudflare Radar.
- `APIFY_TOKEN` para Facebook, Instagram y TikTok si se usa `--social-corroboration`.
- `TWEXAPI_API_KEY` para X/Twitter si se usa `--social-corroboration`.
- Opcionalmente `APIFY_2`, `APIFY_3`, `APIFY_4` y `APIFY_5` para cuentas Apify adicionales. También se acepta `APIFY` como clave principal.
- El catálogo en `data/ubigeo_hibrido.csv`.

## Instalación

```powershell
python -m pip install -e .
Copy-Item .env.example .env
# completar CLOUDFLARE_API_TOKEN y, para corroboración social, APIFY_TOKEN y TWEXAPI_API_KEY
```

`.env` está en `.gitignore`. Si el archivo ya fue trackeado, sacarlo del índice con `git rm --cached .env`. Nunca commitear credenciales. Si estuvo expuesto en el historial, rotar el token antes de usarlo.

## Ejecución

Ejecutar desde la raíz del proyecto para que `data/`, `evidencias/` y `reports/` se resuelvan correctamente.

### Prueba real manual: cuatro operadores en Lima

Desde PowerShell, ejecutar un solo comando:

```powershell
.\prueba-lima.cmd
```

Consulta datos reales de Movistar, Claro, Entel y Bitel para el departamento de Lima: Cloudflare, IODA, RSS, redes sociales mediante Apify y TWEXAPI, y comunicados de OSIPTEL. La ejecución es manual; no instala una tarea programada. Muestra el avance en la terminal y escribe un único `xml/trigger_feed_live.xml`, que se crea o reemplaza en cada ejecución. Los eventos de los cuatro operadores se consolidan en memoria; no se generan XML por operador ni archivos temporales. Los mensajes de avance se envían a stderr y el XML final a stdout. El detalle de los cuatro operadores queda en `reports/prueba_lima_latest.json`.

Por defecto, el XML solo contiene candidatos con `activador=false`. Para permitir `activador=true` en eventos que cumplan las reglas, se debe indicar expresamente `--confirmar`; los creativos siguen siendo URLs de ejemplo. La precisión geográfica nunca será más fina que la evidencia disponible: esta ejecución no supone que un evento departamental afecte a un distrito concreto.

La consulta social y los feeds RSS comparten los resultados entre los cuatro operadores para evitar repetir las consultas comunes. La consulta social tiene un tope conservador predeterminado de US$ 5 en límites reservados para cargos de actores Apify, sumados entre las cuentas; se puede modificar con `--presupuesto-apify-usd`. Si no alcanza, la parte social se informa como parcial y el feed queda degradado. El límite de cargos de actores no es una garantía sobre otros posibles cargos de plataforma, computación o transferencia; revisar también los límites de cada cuenta en Apify.

Ejemplo con otro límite:

```powershell
.\prueba-lima.cmd --presupuesto-apify-usd 2
```

Para ampliar la cobertura social por encima de los valores predeterminados (3 publicaciones y 10 comentarios por cuenta):

```powershell
.\prueba-lima.cmd --presupuesto-apify-usd 10 --max-posts 5 --max-comments 20
```

La prueba consulta publicaciones y comentarios limitados por actor; una ausencia de resultados no demuestra ausencia de corte. Las consultas reales y actores pueden tardar varios minutos.

### Evaluación de un operador

```powershell
python -m win_validation.live_runner --operator movistar --department Lima --window-minutes 180
```

Operadores disponibles: `movistar`, `claro`, `entel`, `bitel`.

Opciones principales:

- `--department`: nombre, código de 2 dígitos o UBIGEO completo.
- `--window-minutes`: mínimo 120 para obtener al menos ocho intervalos de 15 minutos.
- `--technology`: `fixed`, `mobile` o `internet_unspecified`.
- `--news-corroboration`: incluye candidatos RSS actuales como familia de apoyo; requiere revisión manual.
- `--minimum-news-outlets`: mínimo de medios para la corroboración RSS (por defecto 2).
- `--social-corroboration`: incluye posts/comentarios de cuentas oficiales vía Apify y TWEXAPI como familia de apoyo.
- `--minimum-social-items`: mínimo de items sociales alineados para la corroboración (por defecto 1).
- `--social-platforms`: plataformas separadas por coma (`facebook,instagram,tiktok,x` por defecto).
- `--osiptel-news`: consulta el listado oficial de comunicados de OSIPTEL como contexto para revisión.
- `--confirm`: escribe el feed en `state=active`; sin este flag queda en `state=candidate`.
- `--creative-url`: URL HTTPS de ejemplo en `example.com`, `example.org` o `example.net`; por defecto se genera una URL de ejemplo.
- `--output`: ruta del XML (por defecto `xml/trigger_feed_live.xml`).

Ejemplo con corroboración RSS y feed activo:

```powershell
python -m win_validation.live_runner --operator movistar --department Lima --window-minutes 180 --news-corroboration --minimum-news-outlets 2 --confirm --creative-url "https://example.com/creativity.xml"
```

Ejemplo con corroboración social:

```powershell
python -m win_validation.live_runner --operator movistar --department Lima --window-minutes 180 --social-corroboration --social-platforms facebook,instagram,tiktok,x
```

Ejemplo con comunicados oficiales de OSIPTEL:

```powershell
python -m win_validation.live_runner --operator movistar --department Lima --osiptel-news
```

También se puede ejecutar el colector social por separado, sin evaluar NetFlows/IODA:

```powershell
python -m win_validation.social --operators movistar,claro,entel,bitel --platforms facebook,instagram,tiktok,x --max-posts 3 --max-comments 10
```

Para inspeccionar los actores y límites sin gastar crédito de Apify:

```powershell
python -m win_validation.social --operators movistar --platforms facebook,instagram,tiktok,x --dry-run
```

## Corroboración social

Cuentas oficiales configuradas:

- Movistar: `movistarperu` (Facebook/Instagram), `@movistarperu_oficial` (TikTok), `@MovistarPeru` (X).
- Claro: `AmericaMovilPeruSAC` (Facebook), `claroperu` (Instagram/X), `@claro_peru` (TikTok).
- Entel: `EntelPeru` (Facebook/X), `Entel_Peru` (Instagram), `@entel_peru` (TikTok).
- Bitel: `BitelPeru` (Facebook), `bitel_peru` (Instagram/TikTok), `bitelperu` (X).
- OSIPTEL: `OsiptelOficial` (Facebook), `osipteloficial` (Instagram) y `OSIPTEL` (X). Se consulta junto con la operadora; para atribuir un resultado debe mencionarla explícitamente.
- RPP Noticias: `rppnoticias` (Facebook, Instagram, TikTok y X). Diario Correo: `CorreoPeru` (Facebook), `diario_correo` (Instagram) y `diariocorreo` (X). Sus publicaciones y comentarios se muestran como contexto, sin sumarlos a la corroboración social para evitar contar el mismo medio también por RSS. Los perfiles de América Noticias quedan pendientes de verificación.

Actores Apify: `apify/facebook-posts-scraper`, `apify/facebook-comments-scraper`, `apify/instagram-scraper`, `clockworks/tiktok-scraper` y `clockworks/tiktok-comments-scraper`. Para X se usa la API REST de TWEXAPI: una página de publicaciones y, para cada publicación seleccionada, una página de respuestas recientes, hasta el límite de comentarios. TWEXAPI consume sus propios créditos; el presupuesto de Apify no cubre esos cargos. Una página de respuestas puede contener más resultados que el límite que conserva el proyecto, y el proveedor puede cobrar los resultados devueltos.

Las credenciales Apify configuradas se distribuyen entre llamadas. Ante un rechazo explícito de credencial, permiso, pago o límite se prueba otra cuenta; ante un timeout, error de red o error del servidor no se reintenta automáticamente porque el actor podría haber comenzado y generar un cobro duplicado. Los reportes registran solo el nombre de la variable utilizada, nunca el token.

Los feeds RSS se reintentan hasta dos veces con una espera corta solo ante timeout, HTTP 429, HTTP 5xx o XML inválido; un HTTP 4xx definitivo no se reintenta. Cada intento queda archivado como evidencia.

Instagram, Facebook y X requieren dos fases: primero se obtienen posts recientes y luego comentarios/respuestas desde sus URLs. TikTok puede obtener comentarios directamente por perfil. Si Apify agota su presupuesto, se siguen intentando las cuentas X mediante TWEXAPI; los proveedores no se tratan como fuentes sociales independientes entre sí.

## Salidas

- `reports/live_run_latest.json`: resultado completo de la última ejecución.
- `reports/current_news_*.csv`: solo si se usa `--news-corroboration`.
- `reports/social_candidates.csv` y `reports/social_run_latest.json`: solo si se usa la corroboración social.
- `reports/social_dry_run.json`: plan de actores generado con `--dry-run`.
- `reports/osiptel_news_latest.json`: comunicados relevantes si se usa `--osiptel-news`.
- `evidencias/`: respuestas crudas archivadas y `manifest.jsonl` con hashes.
- `xml/trigger_feed_live.xml`: feed XML final; contiene eventos solo si la decisión califica. Se crea o reemplaza atómicamente en cada ejecución. Sin evento calificado se escribe un feed vacío, evitando conservar un evento anterior.

El XML se comprueba contra `config/trigger_feed.xsd` y las reglas de fechas y UBIGEO antes de publicarse mediante reemplazo atómico. En una excepción del runner se intenta reemplazar el resultado anterior por un feed vacío con `estadoSistema="degradado"`. El consumidor debe comprobar `validoHasta` y `expiraEn`: si no se puede escribir el archivo por un error de almacenamiento, el productor no puede retirar un archivo anterior.

Los eventos generados en modo demo llevan `simulacion="true"` y no pueden activar. Los identificadores se mantienen estables por operador, servicio y zona en instantáneas sucesivas; se reutilizan si hay un incidente posterior en el mismo ámbito. El contrato definitivo de lectura, caducidad, reconciliación y compatibilidad con Sonata aún debe confirmarse con el consumidor.

El reporte incluye `netflows.age_minutes` para distinguir "sin caída" de "dato demasiado viejo".

El runner también consulta IODA por `geoasn` y Cloudflare Radar (anomalías y anotaciones). Los resultados y su estado están en `ioda_geoasn` y `radar_context` de `reports/live_run_latest.json`. Son contexto de investigación: la ausencia de eventos no implica una red sana, y no se inventan ASN ni áreas faltantes. La resolución IODA se rechaza si el nombre geográfico es ambiguo o no aparece en la respuesta. Los intervalos IODA sin dato se mantienen como ausentes.

## Regla de NetFlows

La señal de degradación exige como mínimo:

- 8 intervalos de 15 minutos emparejados.
- Mediana de la caída menor a `-0.02`.
- Al menos 90% de los intervalos por debajo del comparador de hace siete días.

## Límites

- Las coordenadas del catálogo son referencias de capitales distritales, no polígonos de cobertura ni prueba de una caída. Algunos campos son históricos o están vacíos.
- Cloudflare entrega el departamento como ADM1 (`geoId`); no hay evidencia de cobertura distrital. Una señal no representa una caída de todo el ISP ni de todo el país.
- NetFlows tiene retraso de ingesta. En pruebas reales el último punto disponible tenía entre 76 y 86 minutos. Con la política actual de 30 minutos, una señal basada solo en NetFlows se suprime aunque el tráfico haya caído.
- Las noticias RSS no son una familia independiente verificada; `--news-corroboration` es para revisión manual y no convierte el runner en un activador de producción.
- Los posts y comentarios sociales tampoco son una confirmación de corte: solo aportan contexto de usuarios en la cuenta oficial. La corroboración social nunca activa por sí sola.
- OSIPTEL se consulta desde su listado HTML oficial, no mediante RSS. Sus fechas sin hora no permiten verificar la ventana de 30 minutos, por lo que son solo contexto y no se incorporan como señales de decisión. Un comunicado y una noticia que lo reproduce tampoco constituyen fuentes independientes.
- Apify cobra por evento y la cuenta actual está en plan `FREE`; cada ejecución social completa puede consumir crédito. Usar `--dry-run` primero y límites pequeños.
- El actor de Instagram puede devolver solo una parte de los comentarios; Facebook, Instagram y X dependen de las URLs de posts que devuelva la primera fase.
- El runner no reemplaza una fuente directa de monitoreo con datos frescos.
- NetFlows y las anotaciones y anomalías de Radar pertenecen a la misma familia Cloudflare. Las nuevas consultas IODA geoASN y Radar no cambian por sí solas la decisión hasta validar cobertura, atribución y frescura en más casos.

## Fuentes del catálogo UBIGEO

El catálogo conserva los códigos y nombres de la base local etiquetada 2026. Sus metadatos referenciales proceden de [ubigeos_peru, INEI 2025](https://github.com/MichaelSuarez0/ubigeos_peru/tree/3e2ed18eb246dd9a81b129352be6a3b6b8a96ea0) y [ubigeo-peru-aumentado, 2021](https://github.com/jmcastagnetto/ubigeo-peru-aumentado/tree/5e98222bb010243592ae02bfafb0a3658d6c4bd8). Se copiaron únicamente para códigos y nombres administrativos coincidentes; para las coordenadas se exigió también la coincidencia de la capital. Los campos de 2021 y la población son históricos y deben verificarse antes de otros usos.

MIT License

Copyright (c) 2025 MichaelSuarez0
Copyright (c) 2021 Jesus M. Castagnetto

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
