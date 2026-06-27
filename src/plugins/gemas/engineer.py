"""Gema: engineer — Operaciones de sistema"""

MANIFEST = {
    "name": "engineer",
    "tags": ["engineering", "tools", "automation", "scripting", "cli", "build", "filesystem", "terminal"],
    "description": "Operaciones de sistema: listar archivos, buscar en codigo, ejecutar comandos.",
    "model": "carstenuhlig/omnicoder-2-9b:q4_k_m",
    "capabilities": ["fs.read.user", "fs.write.user", "shell.exec", "fs.list"],
}
