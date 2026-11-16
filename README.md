# Win outage validation

Runner manual de una ejecución para evaluar posibles caídas de internet en Perú. Consulta Cloudflare NetFlows/Radar, IODA, RSS, redes sociales (Apify/TWEXAPI) y OSIPTEL. Genera un XML `feedActivador` consolidado; sin decisión calificada, el XML queda vacío. No es daemon ni activa campañas.

## Requisitos e instalación

- Python 3.11+.
- `.env` local con `CLOUDFLARE_API_TOKEN`; para social, `APIFY_TOKEN` o `APIFY` y `TWEXAPI_API_KEY`. Opcional: `APIFY_2` a `APIFY_5`.
- Catálogo `data/ubigeo_hibrido.csv`.

```powershell
python -m pip install -e .
Copy-Item .env.example .env
```

No commitear `.env`. Si ya está trackeado: `git rm --cached .env`; si estuvo expuesto, rotar las claves.

## Prueba completa: Lima, 4 operadores

```powershell
.\prueba-lima.cmd
```

Opciones: `--presupuesto-apify-usd` (5), `--max-posts` (3), `--max-comments` (10), `--confirmar` (permite `activador=true`), `--output`.

Salidas:

- `reports/prueba_lima_latest.json`: consolidado.
- `reports/live_run_latest.json`: último operador.
- `xml/trigger_feed_live.xml`: feed final.

## Un operador

```powershell
python -m win_validation.live_runner --operator movistar --department Lima --window-minutes 180
```

Opciones: `--technology`, `--news-corroboration`, `--minimum-news-outlets`, `--social-corroboration`, `--minimum-social-items`, `--social-platforms`, `--osiptel-news`, `--confirm`, `--creative-url`, `--output`.

## Social y demo

```powershell
python -m win_validation.social --operators movistar,claro,entel,bitel --platforms facebook,instagram,tiktok,x --max-posts 3 --max-comments 10
python -m win_validation.social --operators movistar --platforms facebook,instagram,tiktok,x --dry-run
python -m win_validation.creative_trigger --demo
python -m win_validation.trigger_feed_xml --demo
python -m win_validation.trigger_feed_xml --validate xml/trigger_feed_live.xml
```

## Decisión

NetFlows requiere al menos 8 intervalos de 15 minutos, mediana menor a `-0.02` y 90% o más de los intervalos por debajo del comparador de hace siete días. La señal debe tener 30 minutos o menos de antigüedad.

El XML se valida contra `config/trigger_feed.xsd` y se reemplaza atómicamente. Ante error se escribe un feed vacío con `estadoSistema="degradado"`. Revisar `validoHasta` y `expiraEn`.

## Límites

- Precisión departamental; no hay cobertura distrital.
- NetFlows y Radar son la misma familia; IODA, RSS y redes sociales son contexto.
- Sin eventos no significa red sana; sin datos frescos no hay activación.
- Apify cobra por evento; el presupuesto no cubre TWEXAPI.
- `evidencias/`, `reports/` y los XML de salida no se versionan.
