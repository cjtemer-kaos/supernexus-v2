# Análisis Comparativo SuperNEXUS v2 vs DeepSeek-TUI

**Fecha:** 2026-05-18  
**Fuente:** Análisis de capacidades basado en repositorios clonados

## Brechas Críticas Identificadas

### 1. LSP Diagnostics (Mayor brecha)
- **SuperNEXUS:** Cero soporte LSP
- **DeepSeek-TUI:** Conecta pyright, tsserver, rust-analyzer, gopls, clangd. Inyecta diagnósticos post-edición en el contexto del modelo
- **Acción requerida:** Crear `src/core/lsp_manager.py` con hook post-edición

### 2. Error Taxonomy Unificada
- **SuperNEXUS:** Errores como `{"error": "..."}` sin estructura
- **DeepSeek-TUI:** `ErrorEnvelope` con categoría, severidad, recoverable flag, clasificación heurística
- **Acción requerida:** Crear `src/core/error_taxonomy.py` con clases tipadas

### 3. Workspace Snapshot/Rollback
- **SuperNEXUS:** Solo `cursor_checkpoint.py` básico
- **DeepSeek-TUI:** Side-git snapshots pre/post-turn sin tocar el `.git` del usuario. Comandos `/restore N` y `revert_turn`
- **Acción requerida:** Implementar snapshots en `~/.nexus/snapshots/` con git aislado

### 4. Hook System
- **SuperNEXUS:** Sin sistema de hooks
- **DeepSeek-TUI:** Hooks pre/post ejecución con sinks stdout, JSONL, webhook
- **Acción requerida:** Crear `src/core/hook_dispatcher.py` para observabilidad externa

## Mejoras Importantes

5. **Network Policy Auditing** - Log append-only de llamadas HTTP salientes
6. **Sub-Agent Role Taxonomy** - 7 roles con permisos distintos (explore, plan, review, implementer, verifier, custom, general)
7. **Path Escape Prevention** - Validar paths contra límite del workspace
8. **Handle-based Large Results** - Referencias `var_handle` para transcripts grandes en vez de volcar todo al contexto

## Mejoras Arquitectónicas

9. **Schema Versioning** - Versionar registros persistidos (sesiones, checkpoints, tasks)
10. **Event-Sourced Runtime Threads** - Timeline de eventos replayable en vez de listas simples de mensajes
11. **Session Relay/Handoff** - Artefacto estructurado para continuidad entre sesiones

## Fortalezas de SuperNEXUS

- FTS5 full-text search con BM25 ranking
- Tool call loop guardrails (F22)
- LLM-powered async trajectory compression
- SequenceScrubber para enforcement API
- Self-improvement system con detección patrones error
- DAG goal decomposition
- Mixture-of-agents implementation

## Recomendación

**Priorizar LSP Diagnostics y Error Taxonomy** - son las brechas más grandes y más fáciles de implementar.

---

*Este informe fue generado automáticamente y guardado en memoria compartida para referencia futura.*