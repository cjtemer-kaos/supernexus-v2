# 🤖 Integración Hermes Agent ↔ SuperNEXUS v2

> **Conexión DIRECTA del bot Discord a Hermes Gateway** (sin pasar por SuperNEXUS para respuestas)
> **Actualizado**: 2026-08-07

## 📁 Archivos de integración (`hermes-integration/`)

| Archivo | Propósito |
|---------|-----------|
| `discord_bot.py` | Bot Discord "asistente ia" — conecta DIRECTO a Hermes Gateway (`127.0.0.1:8642/api/chat`) |
| `mcp_bridge_wrapper.py` | Wrapper que Hermes ejecuta como subprocess MCP para exponer las 88 tools de SuperNEXUS |
| `start_server.py` | Arranca el API server de SuperNEXUS (puerto 9000/9001) con SelectorEventLoop para Windows |
| `start_silent.py` | Arranca SuperNEXUS oculto (sin ventana de consola) |

## 🔌 Discord Bot → Hermes DIRECT (sin SuperNEXUS)

El bot de Discord ahora habla **directo con el motor de Hermes**:

```
Discord (KAOS Mcs) → discord_bot.py → HERMES_GATEWAY_URL → Hermes responde
```

### Configuración del bot

```python
DISCORD_TOKEN = config.get('DISCORD_TOKEN')          # desde .env
HERMES_GATEWAY_URL = config.get('HERMES_GATEWAY_URL', 'http://127.0.0.1:8642/api/chat')
```

### Comandos en Discord
- `ia <mensaje>` — respuesta directa
- `@asistente ia <mensaje>` — mención
- DM al bot
- `!ping` — latencia
- `!status` — estado

### Invitación OAuth2
```
https://discord.com/api/oauth2/authorize?client_id=1460096814261862524&permissions=2147487936&scope=bot
```

## 🧩 MCP Bridge (SuperNEXUS → Hermes)

Hermes expone las herramientas de SuperNEXUS via MCP:

```yaml
# En ~/.hermes/config.yaml
mcp_servers:
  supernexus:
    command: C:\Users\cjtr\AppData\Local\Programs\Python\Python313\python.exe
    args: [D:\ias\proyectos\supernexus-v2\mcp_bridge_wrapper.py]
    env:
      PYTHONPATH: D:\ias\proyectos\supernexus-v2
      NEXUS_BRAIN: C:\Users\cjtr\.nexus\brain
```

## 🚀 Iniciar SuperNEXUS

```bash
# Normal (puerto 9000)
python start_server.py 9000

# Oculto (sin consola)
python start_silent.py

# Verificar
curl http://localhost:9000/health
```

## 🧠 Brain (memoria compartida)

- **Brain canónico**: `~/.nexus/brain/` — todos los agentes escriben ahí
- **brain_remember** / **brain_recall** — persistencia de contexto
- Si una sesión crashea: `session_search` → extraer → `brain_remember` → nueva sesión `brain_recall`

## ⚠️ Notas

- Los tokens van en `.env` (protegido por `.gitignore`), NUNCA en el código
- El bot requiere Hermes Gateway corriendo en `127.0.0.1:8642`
- SuperNEXUS corre en puerto 9000/9001 (según config)
