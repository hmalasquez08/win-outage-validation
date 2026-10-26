# Guía de revisión

## Propósito y límites

El proyecto evalúa si es técnicamente viable detectar interrupciones o degradaciones de internet de operadores peruanos y producir una señal que pudiera orientar creatividades por zona. La detección objetivo es de internet. Voz y SMS son corroboración auxiliar; datos móviles solo deben interpretarse para la tecnología que representan. Ninguna señal auxiliar, cobertura declarada ni queja individual constituye por sí sola una caída de internet.

La solución no está conectada a un sistema de campañas ni realiza activaciones. El detector principal reproduce reglas sobre evidencia histórica archivada. El colector de noticias permite consultas manuales a feeds RSS/XML; no corre en segundo plano. Los feeds actuales no aportaron candidatos a la consulta y no hay noticias históricas alineadas que permitan medir su valor incremental.

## Orden recomendado de lectura

1. [`arquitectura.md`](arquitectura.md): requisitos y criterios de aceptación de referencia.
2. [`reports/architecture_compliance.md`](reports/architecture_compliance.md): cotejo de requisitos, resultados y brechas conocidas.
3. [`EXECUTIVE_PROPOSAL.md`](EXECUTIVE_PROPOSAL.md): síntesis ejecutiva para Win; separa resultados de replay, estado de las fuentes y trabajo pendiente.
4. [`reports/robust_detector_replay.md`](reports/robust_detector_replay.md): reglas, métricas históricas y limitaciones del detector.
5. [`reports/creative_activation_readiness.md`](reports/creative_activation_readiness.md) y [`reports/current_candidate_crosscheck.md`](reports/current_candidate_crosscheck.md): evaluación del candidato más reciente y motivos de supresión.
6. [`reports/final_decisions.md`](reports/final_decisions.md) y [`reports/candidate_services_exclusion.md`](reports/candidate_services_exclusion.md): decisiones sobre fuentes y servicios excluidos.
7. [`evidencias/README.md`](evidencias/README.md) y [`evidencias/manifest.jsonl`](evidencias/manifest.jsonl): índice, hashes y rutas de las respuestas originales.
8. Código en `src/win_validation/`, en especial `detector.py`, `news.py`, `candidate_crosscheck.py` y `creative_trigger.py`; pruebas en `tests/`.

`SESSION_HANDOFF.md` es un resumen de continuidad, no sustituye `arquitectura.md` ni el cotejo de cumplimiento.

## Estado funcional

| Componente | Estado comprobado | Límite principal |
|---|---|---|
| Replay del detector | Cloudflare NetFlows/Radar, IODA, X/TwexAPI y M-Lab HERMES se evalúan con datos archivados. | No es una ingesta continua ni una política de activación. Los resultados son exploratorios. |
| RSS de noticias | `python -m win_validation.detector --fetch-news` consulta siete feeds configurados y guarda estado/candidatos. | Consulta manual; resultados actuales sin candidatos. Las noticias no cuentan en métricas históricas sin alineación y revisión de independencia. |
| Fuentes auxiliares de voz/SMS o incidencias móviles | Consideradas como posible corroboración, no como objetivo independiente. | No están integradas en el PoC; las fuentes probadas no dieron una señal actual local y alineada. |
| Geografía | UBIGEO y geometrías se usan como referencia auxiliar. | Hay códigos distritales pendientes; consultar los informes geográficos antes de asumir segmentación distrital. |
| Activación | Simulador local con escenarios sintéticos. | Sin conexión a campañas; no usar resultados como activaciones reales. |

El replay puede etiquetar candidatos por familias auxiliares para comparar reglas. Esto es una función de evaluación retrospectiva; el flujo objetivo requiere primero evidencia de afectación de internet y usa otras señales solo para corroborar.

## Reproducción local

Desde la raíz, en PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python -m win_validation.cli audit
python -m win_validation.detector
python -m win_validation.candidate_crosscheck
python -m win_validation.creative_trigger --demo
```

Las cuatro últimas comprobaciones anteriores leen datos locales; `--demo` usa escenarios sintéticos. `python -m win_validation.detector --fetch-news`, `--fetch-controls` y `win_validation.cli validate ...` realizan solicitudes de red y guardan nueva evidencia. Úsalos solo si se quiere repetir consultas externas.

## Secretos y conservación de evidencia

`.env` contiene credenciales locales y está excluido por `.gitignore`; no copiar su contenido a tickets, informes, capturas ni commits. `.env.example` contiene solo nombres y marcadores de configuración. La carpeta `evidencias/` es la fuente de auditoría de las consultas y sus hashes; no borrar ni reorganizar sus archivos sin actualizar sus manifiestos y referencias. `data/validation.sqlite` es un índice derivado de esa evidencia, no reemplaza las respuestas originales ni el manifiesto.

## Control de versiones

Al preparar esta guía, la carpeta no tenía directorio `.git`. Por ello no existe rama, historial ni estado Git limpio que el revisor pueda comparar. El contenido puede revisarse directamente como carpeta; si hace falta una revisión de cambios por commit, primero debe entregarse o inicializarse en un repositorio Git con un baseline acordado.
