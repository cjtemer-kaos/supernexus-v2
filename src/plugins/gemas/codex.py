"""
Codex Gema - Delegacion de codigo y sandbox
"""

MANIFEST = {
    "name": "codex",
    "tags": ["codex", "delegation", "compilation", "sandbox", "execution"],
    "description": "Delegacion de codigo y ejecucion en sandbox",
    "model": "carstenuhlig/omnicoder-2-9b:q4_k_m",
    "capabilities": ["fs.read.user", "fs.write.user", "shell.exec", "fs.list"],
}
