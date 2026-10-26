# Validación local de fuentes de interrupciones (Perú)

Proyecto de evaluación local basado en `arquitectura.md`. El objetivo es detectar interrupciones o degradaciones de internet en Perú; otras señales, como voz/SMS, solo podrían corroborar un incidente y no sustituir evidencia de internet. El proyecto no activa campañas ni despliega infraestructura. Requiere Python 3.11+.

Para orientar una revisión, empezar por [`REVIEWER_GUIDE.md`](REVIEWER_GUIDE.md), que establece el orden de lectura, las limitaciones y los comandos reproducibles. `arquitectura.md` contiene los requisitos de referencia; [`EXECUTIVE_PROPOSAL.md`](EXECUTIVE_PROPOSAL.md) es la síntesis para Win.

Las consultas con red son explícitas: `python -m win_validation.cli validate --all --country PE --safe-free-only`. No hay monitoreo automático. Las credenciales son optativas, se mantienen en `.env` local y no deben guardarse en informes o evidencias. `python -m win_validation.cli report --format all` genera informes sobre la ejecución existente.

La validación disponible cubre respuestas observadas de endpoints públicos y no equivale a una garantía de confiabilidad. La revisión actual se centra en viabilidad técnica; licencias quedan para después. Revisar `reports/` y `evidencias/`.

Replay retrospectivo del detector por reglas, a partir de datos históricos archivados y sin solicitudes de red: `python -m win_validation.detector`. Para volver a consultar los 17 controles históricos de Cloudflare y guardar evidencia, ejecutar `python -m win_validation.detector --fetch-controls`. Los resultados son exploratorios; no equivalen a desempeño operativo ni activan campañas.

Consulta manual de noticias para corroboración: `$env:PYTHONPATH="src"; python -m win_validation.detector --fetch-news`. Consulta los siete feeds RSS/XML configurados, analiza únicamente los metadatos y el texto incluidos en los feeds (no abre páginas de artículos), y genera `reports/current_news_feed_status.csv` y `reports/current_news_candidates.csv`, además de archivar las respuestas. Un candidato requiere menciones de internet, interrupción, operador y zona UBIGEO; no confirma por sí solo un incidente ni activa una creatividad. El colector no se ejecuta en segundo plano.

Simulador local de decisión para creatividades, exclusivamente con escenarios sintéticos y sin llamadas externas: en PowerShell, `$env:PYTHONPATH="src"; python -m win_validation.creative_trigger --demo`. Genera `reports/creative_trigger_simulation.md` y `.json`; el contrato está en `config/creative_trigger_event.schema.json`. Requiere señal directa de internet, corroboración independiente, zona peruana verificada y evidencia fresca; la lógica de activación/caducidad se prueba en local. No consume eventos reales ni activa campañas. La conexión de salida se define al final.

Evaluación reproducible de candidatos con datos reales archivados (sin volver a consultar fuentes): `$env:PYTHONPATH="src"; python -m win_validation.candidate_crosscheck`. Genera `reports/current_candidate_crosscheck.md/.json` y `reports/creative_activation_readiness.md/.json`. El candidato real más reciente fue Movistar-Ica en Cloudflare NetFlows: pasó persistencia, pero se suprimió por desfase de 85.8 minutos y geografía no verificada; no se generó una activación.
