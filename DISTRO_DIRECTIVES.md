# Directivas para la versión Distro de SuperNEXUS v2

## Arquitectura
SuperNEXUS v2 es un orquestador de agentes IA local-first con:
- **DirectorNexus** — Cerebro determinista (sin LLM para decisiones críticas)
- **22 Gemas** — Agentes especializados (code, scholar, creative, etc.)
- **Protocolos** — MCP + A2A + ACP para comunicación inter-agente
- **Memoria** — Jerárquica (working/episodic/semantic) + RAG + Brain
- **UI** — React + Vite + Tailwind (servida en `/ui/`)

## Reglas de la versión limpia (distro)

### NO incluir (eliminar antes de distribuir):
- **Configuraciones personales**: IPs, hosts, URLs específicas
- **Credenciales**: API keys, tokens, passwords, secretos
- **Referencias a nodos específicos**: Nombres de máquinas personales
- **Rutas personales**: /home/user/, C:\Users\username\, etc.
- **Nombres de usuario personales**
- **Bridges específicos locales**: Configuraciones hardcodeadas
- **Scripts de deploy personal**

### SÍ incluir:
- **Código core funcional**: DirectorNexus, gemas, memoria, protocolos, tools
- **Herramientas disponibles**: Lista de todas las herramientas/skills del sistema
- **Documentación de instalación**: README con instrucciones para empezar de cero
- **Ejemplos de configuración**: .env.example con variables genéricas (sin valores reales)
- **Módulos de seguridad**: credential_manager, tool_guardrails, ai_defence, etc.
- **UI completa**: Interfaz web React buildiada

### Variables de entorno genéricas:
- `REMOTE_NODE_*` (no `PC2_*`)
- `OLLAMA_URL=http://localhost:11434`
- `OPENAI_API_KEY=your_key_here`
- `ANTHROPIC_API_KEY=your_key_here`

### Nomenclatura:
- Usar "remote_node" en lugar de nombres de máquina específicos
- Usar "local" en lugar de referencias a máquinas personales
- Documentar que el usuario debe configurar sus propios nodos remotos

### Checklist antes de distribuir:
1. [ ] Eliminar referencias a IPs personales
2. [ ] Eliminar credenciales hardcodeadas
3. [ ] Eliminar rutas personales
4. [ ] Eliminar nombres de usuario personales
5. [ ] Renombrar variables de PC2 a remote_node genérico
6. [ ] Verificar que .env.example no tenga valores reales
7. [ ] Actualizar README con instrucciones limpias
8. [ ] Ejecutar búsqueda de nombres personales en todo el código
9. [ ] Verificar que `python -m pytest tests/` pase limpio
10. [ ] Verificar que `python -m src.api.server` inicie sin errores
