"""Gema: code — Programacion, ejecucion y sandbox"""

MANIFEST = {
    "name": "code",
    "tags": ['programming', 'code-review', 'refactoring', 'handoff', 'delegation', 'compile', 'sandbox'],
    "description": "Programacion, ejecucion y sandbox",
    "model": "carstenuhlig/omnicoder-2-9b:q4_k_m",
    # Capability declarations (openfang pattern, MVP — declarative only).
    # See src/plugins/manifest.py for the recommended vocabulary.
    "capabilities": ["fs.read.user", "fs.write.user", "shell.exec"],
}
