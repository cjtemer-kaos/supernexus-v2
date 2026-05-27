#!/usr/bin/env python3
"""
SuperNEXUS v2 - Setup Wizard
Primer uso: crea cuenta admin para proteger el sistema.
"""

import sys
import os
import getpass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.security.auth import AuthManager


def setup_wizard():
    print("=" * 60)
    print("  SuperNEXUS v2 - Setup Wizard")
    print("=" * 60)
    print()

    auth = AuthManager()

    if auth.has_users():
        print("[OK] SuperNEXUS ya tiene cuentas configuradas.")
        print("     Usuarios existentes:")
        for user in auth.list_users():
            status = "active" if user["is_active"] else "disabled"
            print(f"       - {user['username']} ({user['role']}, {status})")
        print()
        resp = input("Crear otra cuenta? (s/N): ").strip().lower()
        if resp not in ("s", "si", "y", "yes"):
            print("Setup completado.")
            return True
    else:
        print("[!] Primera ejecucion detectada.")
        print("    Debes crear una cuenta ADMIN para proteger el sistema.")
        print()

    while True:
        username = input("Username (min 3 chars): ").strip()
        if len(username) < 3:
            print("  Error: minimo 3 caracteres.")
            continue
        if len(username) > 50:
            print("  Error: maximo 50 caracteres.")
            continue
        break

    while True:
        password = getpass.getpass("Password (min 6 chars): ")
        if len(password) < 6:
            print("  Error: minimo 6 caracteres.")
            continue
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("  Error: las contrasenas no coinciden.")
            continue
        break

    success, message = auth.create_user(username, password, role="admin")
    if success:
        print()
        print(f"[OK] Cuenta '{username}' creada exitosamente.")
        print()
        print("Para iniciar SuperNEXUS:")
        print(f"  python -m src.api.server")
        print()
        print("Para login via API:")
        print(f"  POST /api/auth/login")
        print(f'  {{"username": "{username}", "password": "..."}}')
        print()
        return True
    else:
        print(f"[ERROR] {message}")
        return False


if __name__ == "__main__":
    ok = setup_wizard()
    sys.exit(0 if ok else 1)
