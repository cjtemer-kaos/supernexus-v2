---
name: book-to-skill
description: "Convierte libros/documentos (PDF, EPUB, DOCX, HTML, URL) en skills estructurados para Scholar. Usa Chrome CDP para capturar contenido web cuando es necesario."
allowed-tools:
  - shell_command
  - Read
  - Write
  - Glob
  - Grep
  - browser_navigate
  - browser_snapshot
  - browser_screenshot
  - browser_evaluate
argument-hint: <path-to-document-or-url> [skill-name-slug]
gem-delegation: scholar
---

# book-to-skill para Scholar

Convierte un libro, documento PDF, EPUB, DOCX, o URL en un **skill estructurado** para el agente Scholar.

El output es un skill con:
- `SKILL.md` maestro (~4K tokens) — frameworks principales
- `chapters/` — resúmenes por capítulo (800-1200 tokens c/u)
- `glossary.md` — términos clave (<1500 tokens)
- `patterns.md` — patrones y mental models (<2000 tokens)
- `cheatsheet.md` — referencia rápida (<1000 tokens)

## Pipeline

### Fase 0: Detectar fuente
- Si es URL → usar `browser_navigate` + `browser_snapshot` para capturar
- Si es PDF/EPUB/DOCX → buscar `scripts/extract.py` y ejecutar
- Si es ruta local → leer directamente

### Fase 1: Extraer texto (ejecutar extract.py)
```bash
python src/skills/book-to-skill/scripts/extract.py <path> --mode <technical|text> --install-missing ask
```
Si falla, usar Chrome CDP como fallback:
- Navegar a la URL con `browser_navigate`
- Extraer contenido con `browser_evaluate`: `document.body.innerText`

### Fase 2: Analizar estructura
- Título, autor, capítulos detectados
- Temas centrales y frameworks
- Costo estimado de tokens

### Fase 3: Preguntar propósito al usuario
"¿Cómo planeas usar este libro? ¿Referencia técnica, estudio, enseñanza?"

### Fase 4: Generar skill
1. Crear directorio `~/.nexus/skills/<slug>/`
2. Generar resúmenes de capítulos (plantilla 8 secciones)
3. Generar glossary, patterns, cheatsheet
4. Generar SKILL.md maestro con topic index
5. Registrar en SkillRegistry (`src/skills/skill_registry_system.py`)

## Plantilla de resumen de capítulo
```markdown
# Capítulo N: Título

## Core Idea
## Frameworks Introducidos
## Key Concepts
## Mental Models
## Anti-patrones
## Code Examples
## Reference Tables
## Key Takeaways
## Conecta Con
```

## Reglas de calidad
1. Extrae estructura, no resúmenes
2. Preserva nombres exactos del autor
3. Densidad sobre completitud
4. Voz de practicante ("Usa X cuando Y")
5. SKILL.md front-loaded (lo importante primero)
6. Chapter files on-demand via topic index
7. Nunca copies texto raw del libro
8. Topic index crítico para navegación
