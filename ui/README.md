# NEXUS UI - SuperNEXUS v2.0

## Estructura de la UI (adaptada de Goose)

```
ui/
├── apps/
│   ├── main/                 # Electron main process
│   │   ├── src/
│   │   │   └── main.ts       # Entry point
│   │   └── package.json
│   ├── renderer/             # React UI (Vite)
│   │   ├── src/
│   │   │   ├── App.tsx       # Main app
│   │   │   ├── components/
│   │   │   │   ├── Chat.tsx       # Chat principal
│   │   │   │   ├── Sidebar.tsx    # Sidebar con selectores
│   │   │   │   ├── RightPanel.tsx # Tools, files, context
│   │   │   │   ├── GemSelector.tsx # Selector de gemas
│   │   │   │   └── ProjectSelector.tsx # Selector de proyectos
│   │   │   └── main.tsx      # React entry
│   │   └── vite.config.ts
│   └── preload/              # Electron preload
│       └── src/
│           └── preload.ts
└── package.json
```

## Branding
- **Nombre:** NEXUS IA
- **Logo:** Cerebro multicolor
- **Colores:** Gradiente multicolor (purple, blue, green, orange)

## Backend Connection
- HTTP a NEXUS Backend: `http://localhost:9000`
- WebSocket para streaming en tiempo real
- REST API para todas las operaciones

## Nota
La UI se clonara de Goose y se adaptara con:
- Branding NEXUS IA
- Selector de gemas
- Selector de proyectos con memoria selectiva
- Knowledge Graph viewer
- Agent status panel
- Tailscale nodes panel
