#!/usr/bin/env python3
"""
SuperNEXUS v2.0 - Diagnostic Entry Point
Shows system status, gemas, memory, and connectivity.
"""
import asyncio
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("supernexus")

async def main():
    from src.core.director import DirectorNexus
    from src.core.gema_host import GemaHost

    print("=" * 60)
    print("  SuperNEXUS v2.0 - Director Diagnostic")
    print("=" * 60)
    print()

    director = DirectorNexus(project="default")
    dstatus = director.get_status()
    print(f"Director: {dstatus['identity']['name']} v{dstatus['identity']['version']}")
    print(f"Project: {dstatus['current_project']}")
    print(f"Gemas: {dstatus['gemas_count']}")
    print()

    gemas = GemaHost()
    manifests = gemas.get_all_manifests()
    print(f"Gemas loaded: {len(manifests)}")
    for m in manifests[:5]:
        print(f"  - {m.get('name', '?')}: {m.get('description', '')[:60]}")
    print()

    print("System ready.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
