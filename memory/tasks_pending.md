# TAREAS PENDIENTES - NEXUS HIVE
# Fecha: 2026-05-18
# Estado: ABIERTO

## TAREA 1: Limpieza del Tablero Compartido
- PROBLEMA: 703k mensajes acumulados
- ACCIÓN: Archivar mensajes > 24h, dejar solo activos
- HERRAMIENTA: nexus-sovereign (disponible para claude-code, antigravity, etc.)
- ESTADO: PENDIENTE

## TAREA 2: Migración de Estados a Memoria
- PROBLEMA: Estados repetitivos en el tablero
- ACCIÓN: Mover a memory_set (agent_status, active_task, etc.)
- ESTADO: PENDIENTE

## TAREA 3: Verificación de DB
- ACCIÓN: Confirmar que Protocolo y Análisis están en nexus_memory.db
- ESTADO: COMPLETADO (opencode guardó ambos)

## NOTAS
- Opencode NO tiene acceso a nexus-sovereign
- Opencode usa DB y archivos locales para persistencia
- Demás agentes SÍ tienen acceso a nexus-sovereign
