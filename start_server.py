#!/usr/bin/env python3
"""
SuperNEXUS v2.0 - Server Entry Point
Start with: python -m src.api.server [port]
Default port: 9000
"""
import sys
sys.path.insert(0, '.')
import asyncio
from src.api.server import run_server
port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
asyncio.run(run_server(port))
