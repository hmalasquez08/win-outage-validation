# Win outage validation

Runner manual de una sola ejecución para evaluar una posible caída de internet en Perú. Consulta Cloudflare Radar/NetFlows, IODA, feeds RSS, publicaciones y comentarios de cuentas oficiales vía Apify/TWEXAPI, y comunicados de OSIPTEL. Genera un XML `feedActivador` consolidado; si no hay una decisión calificada, el XML no contiene eventos. No corre como daemon ni activa campañas.

> Estado: prototipo de validación. Los reportes son evidencia de una ejecución concreta, no un monitoreo continuo.

## Requisitos

- Python 3.11 o superior.
- `CLOUDFLARE_API_TOKEN` con acceso de lectura a Cloudflare Radar.
- `APIFY_TOKEN` (o `APIFY`) para Facebook, Instagram y TikTok.
- Opcionalmente `APIFY_2`, `APIFY_3`, `APIFY_4` y `APIFY_5` para repartir llamadas entre cuentas Apify.
- `TWEXAPI_API_KEY` para X/Twitter.
- Catálogo local `data/ubigeo_hibrido.csv`.

## Instalación

```powershell
python -m pip install -e .
Copy-Item .env.example .env
```

Completar `.env` con las credenciales. `.env.example` es la plantilla versionada; `.env` es local.

## Credenciales

- No agregar `.env` al índice de Git ni subirlo al repositorio.
- Si `.env` ya está trackeado: `git rm --cached .env`.
- Si las credenciales estuvieron expuestas en el historial, rotarlas antes de usarlas.
- Los reportes solo registran el nombre de la variable de entorno utilizada, nunca el token.

## Ejecución rápida: Lima, cuatro operadores

Desde la raíz del proyecto:

```powershell
.\prueba-lima.cmd
```

El comando consulta Movistar, Claro, Entel y Bitel para el departamento de Lima y escribe:

- `reports/prueba_lima_latest.json`: consolidado de los cuatro operadores.
- `reports/live_run_latest.json`: último resultado por operador; se sobrescribe en cada iteración.
- `xml/trigger_feed_live.xml`: feed consolidado final.

La ejecución es manual y no instala tareas programadas. Los mensajes de avance van a stderr y el XML final a stdout.

### Opciones de `prueba-lima`

| Opción | Default | Uso |
|---|---|---|
| `--presupuesto-apify-usd` | `5.00` | Tope conservador de cargos de actores Apify, sumado entre cuentas. |
| `--max-posts` | `3` | Publicaciones por cuenta y plataforma. |
| `--max-comments` | `10` | Comentarios o respuestas por publicación. |
| `--confirmar` | desactivado | Permite `activador=true` en eventos que cumplan las reglas. Sin este flag solo se generan candidatos. |
| `--output` | `xml/trigger_feed_live.xml` | Ruta del XML consolidado. |

Ejemplos:

```powershell
.\prueba-lima.cmd --presupuesto-apify-usd 2
.\prueba-lima.cmd --presupuesto-apify-usd 10 --max-posts 5 --max-comments 20
```

La consulta social y los feeds RSS se comparten entre los cuatro operadores para evitar repetir llamadas comunes. Si el presupuesto Apify no alcanza, la parte social queda parcial y el feed se marca como degradado.

## Evaluación de un operador

```powershell
python -m win_validation.live_runner --operator movistar --department Lima --window-minutes 180
```

También disponible como script instalado:

```powershell
win-outage-live --operator movistar --department Lima --window-minutes 180
```

Operadores: `movistar`, `claro`, `entel`, `bitel`.

Opciones principales:

- `--department`: nombre, código de 2 dígitos o UBIGEO completo.
- `--window-minutes`: mínimo 120 para obtener al menos ocho intervalos de 15 minutos.
- `--technology`: `fixed`, `mobile` o `internet_unspecified`.
- `--news-corroboration`: incluye candidatos RSS actuales como familia de apoyo; requiere revisión manual.
- `--minimum-news-outlets`: mínimo de medios para la corroboración RSS (default 2).
- `--social-corroboration`: incluye posts/comentarios de cuentas oficiales vía Apify y TWEXAPI.
- `--minimum-social-items`: mínimo de items sociales alineados (default 1).
- `--social-platforms`: plataformas separadas por coma (`facebook,instagram,tiktok,x`).
- `--osiptel-news`: consulta comunicados oficiales de OSIPTEL como contexto.
- `--confirm`: escribe `state=active` y `trigger=true`; sin este flag queda en `state=candidate`.
- `--creative-url`: URL HTTPS de ejemplo en `example.com`, `example.org` o `example.net`.
- `--output`: ruta del XML (default `xml/trigger_feed_live.xml`).

Ejemplo con corroboración RSS y feed activo:

```powershell
python -m win_validation.live_runner --operator movistar --department Lima --window-minutes 180 --news-corroboration --minimum-news-outlets 2 --confirm --creative-url "https://example.com/creativity.xml"
```

Ejemplo con corroboración social:

```powershell
python -m win_validation.live_runner --operator movistar --department Lima --window-minutes 180 --social-corroboration --social-platforms facebook,instagram,tiktok,x
```

Ejemplo con comunicados de OSIPTEL:

```powershell
python -m win_validation.live_runner --operator movistar --department Lima --osiptel-news
```

## Colector social independiente

```powershell
python -m win_validation.social --operators movistar,claro,entel,bitel --platforms facebook,instagram,tiktok,x --max-posts 3 --max-comments 10
```

Inspección sin gastar crédito Apify:

```powershell
python -m win_validation.social --operators movistar --platforms facebook,instagram,tiktok,x --dry-run
```

## Demo local y validación del XML

```powershell
python -m win_validation.creative_trigger --demo
python -m win_validation.trigger_feed_xml --demo
python -m win_validation.trigger_feed_xml --validate xml/trigger_feed_live.xml
```

La demo es sintética y no consulta fuentes externas.

## Corroboración social

Cuentas oficiales configuradas:

- Movistar: `movistarperu` (Facebook/Instagram), `@movistarperu_oficial` (TikTok), `@MovistarPeru` (X).
- Claro: `AmericaMovilPeruSAC` (Facebook), `claroperu` (Instagram/X), `@claro_peru` (TikTok).
- Entel: `EntelPeru` (Facebook/X), `Entel_Peru` (Instagram), `@entel_peru` (TikTok).
- Bitel: `BitelPeru` (Facebook), `bitel_peru` (Instagram/TikTok), `bitelperu` (X).
- OSIPTEL: `OsiptelOficial` (Facebook), `osipteloficial` (Instagram), `OSIPTEL` (X). Se consulta junto con la operadora; para atribuir un resultado debe mencionarla explícitamente.
- RPP Noticias y Diario Correo: contexto, sin sumarlos a la corroboración social para no contar el mismo medio también por RSS.

Actores Apify: `apify/facebook-posts-scraper`, `apify/facebook-comments-scraper`, `apify/instagram-scraper`, `clockworks/tiktok-scraper` y `clockworks/tiktok-comments-scraper`. Para X se usa la API REST de TWEXAPI: una página de publicaciones y, por cada publicación seleccionada, una página de respuestas recientes.

Las credenciales Apify se distribuyen entre llamadas. Ante rechazo explícito de credencial, permiso, pago o límite se prueba otra cuenta; ante timeout, error de red o error del servidor no se reintenta automáticamente para evitar cobros duplicados.

RSS se reintenta hasta dos veces solo ante timeout, HTTP 429, HTTP 5xx o XML inválido. Un HTTP 4xx definitivo no se reintenta. Cada intento queda archivado como evidencia.

## Decisión y feed

La señal de NetFlows exige:

- Al menos 8 intervalos de 15 minutos emparejados.
- Mediana de la caída menor a `-0.02`.
- Al menos 90% de los intervalos por debajo del comparador de hace siete días.

La edad máxima de una señal es de 30 minutos. NetFlows suele tener retraso de ingesta; si el último punto es más viejo que la política, la señal se suprime aunque el tráfico haya caído.

El XML se valida contra `config/trigger_feed.xsd` y se reemplaza atómicamente. Ante una excepción se intenta escribir un feed vacío con `estadoSistema="degradado"`. El consumidor debe revisar `validoHasta` y `expiraEn`.

Los eventos de demo llevan `simulacion="true"` y no pueden activar. Los identificadores se mantienen estables por operador, servicio y zona. El contrato definitivo con Sonata aún debe confirmarse.

## Salidas

- `reports/prueba_lima_latest.json`: consolidado de la prueba de Lima.
- `reports/live_run_latest.json`: último resultado por operador.
- `reports/current_news_*.csv`: solo con `--news-corroboration`.
- `reports/social_candidates.csv` y `reports/social_run_latest.json`: solo con corroboración social.
- `reports/social_dry_run.json`: plan de actores con `--dry-run`.
- `reports/osiptel_news_latest.json`: comunicados si se usa `--osiptel-news`.
- `reports/creative_trigger_simulation.*`: demo sintética.
- `evidencias/`: respuestas crudas y `manifest.jsonl` con hashes.
- `xml/trigger_feed_live.xml`: feed final; se crea o reemplaza en cada ejecución.

`evidencias/`, `reports/` y los XML de salida están fuera del repositorio por `.gitignore`.

## Límites

- Las coordenadas del catálogo son referencias de capitales distritales, no polígonos de cobertura ni prueba de una caída.
- Cloudflare entrega el departamento como ADM1 (`geoId`); no hay evidencia de cobertura distrital.
- Una señal no representa una caída de todo el ISP ni de todo el país.
- NetFlows y las anotaciones/anomalías de Radar pertenecen a la misma familia Cloudflare y no son fuentes independientes.
- IODA se usa como contexto; la ausencia de eventos no implica una red sana.
- Las noticias RSS y los posts sociales no son confirmación de corte; son contexto para revisión manual.
- OSIPTEL se consulta desde su listado HTML oficial. Sus fechas sin hora no permiten verificar la ventana de 30 minutos y no se incorporan como señal de decisión.
- Apify cobra por evento. Usar `--dry-run` y límites pequeños; el presupuesto configurado no cubre cargos de TWEXAPI ni otros cargos de plataforma.
- El runner no reemplaza una fuente directa de monitoreo con datos frescos.

## Estructura

```text
src/win_validation/
  live_runner.py        # evaluación por operador, NetFlows, IODA, Radar y decisión
  prueba_lima.py        # ejecución consolidada para Lima
  social.py             # Apify, TWEXAPI y evidencia social
  news.py               # RSS y snapshot compartido
  osiptel_news.py       # comunicados oficiales
  trigger_feed_xml.py   # construcción, validación y escritura del XML
  creative_trigger.py   # reglas de decisión y simulación local
  ioda_geoasn.py        # consulta IODA por geoASN
  radar_context.py      # anomalías y anotaciones de Cloudflare Radar
  http.py               # cliente HTTP, evidencia y carga de .env
```
