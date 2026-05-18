# 🚣 RowboatGem - AI Coworker Integration

**Tipo:** Meta-Gema (Knowledge Graph + Memory)  
**Versión:** 1.0  
**Fuente:** https://github.com/rowboatlabs/rowboat  
**Dependencias:** Rowboat Desktop/SDK, MCP

## Función

Integra Rowboat (open-source AI coworker con memoria persistente) con NEXUS IA. Mantiene knowledge graph en Markdown + MCP bridge para comunicación.

## Capacidades

- **Knowledge Graph:** Obsidian-compatible vault con backlinks
- **Email Integration:** Acceso a contexto de emails
- **Meeting Notes:** Procesa meeting notes y decisiones
- **Document Generation:** Crea docs/decks desde contexto
- **MCP Bridge:** Comunica con NEXUS IA vía Model Context Protocol

## Arquitectura

```
Rowboat (Desktop/Backend)
    ↓ (MCP)
RowboatGem (NEXUS IA)
    ↓
DirectorGem + 15 Gemas (acceso a knowledge graph)
```

## Funciones Principales

### 1. Conectar a Rowboat
```python
from rowboat_gem import RowboatGem

rg = RowboatGem(rowboat_path="C:\\Users\\${USERNAME}\\Rowboat")
rg.connect()  # Conecta vía MCP al servidor Rowboat
```

### 2. Buscar en Knowledge Graph
```python
results = rg.buscar("machine learning", filtros={"tipo": "decisión"})
```

### 3. Guardar Contexto
```python
rg.guardar_contexto(
    tipo="decision",
    contenido="...",
    tags=["project-x"],
    relacionado_con=["email-id-123"]
)
```

### 4. Obtener Resumen de Proyecto
```python
resumen = rg.obtener_proyecto_resumen("ProjectName")
```

## Integración con BibliotecaGem

- Rowboat: Memoria viva + interacciones
- BibliotecaGem: Archivo de investigaciones ScholarGem

Ambas sincronizadas para contexto completo.

## Base de Datos

- **Vault:** `~/.rowboat/vault/` (Markdown notes)
- **Knowledge Graph:** Sqlite en Rowboat backend
- **Bridge DB:** `${NEXUS_BASE_DIR}\01_CORE\memory\rowboat_sync.db`

## Requisitos

- Rowboat Desktop instalado
- Node.js (para servidor Rowboat MCP)
- NEXUS IA corriendo en puerto 9000

## Comandos

```python
# Sincronizar
rg.sync()

# Stats
rg.estadisticas()

# Exportar
rg.exportar_vault("output/vault.zip")
```
