#!/usr/bin/env python3
"""
SuperNEXUS v2 - Build Distribution Script
Crea distribuciones limpias para Windows y Linux.
Uso: python scripts/build_distro.py --platform windows --version 2.0.0
"""

import os
import sys
import shutil
import re
import zipfile
import tarfile
import argparse
from datetime import datetime

# ═══════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DIST_DIR = os.path.join(PROJECT_ROOT, 'dist')

REPLACEMENTS = [
    # Rutas personales -> genericas
    (r'D:\\ias\\proyectos\\supernexus-v2', '${NEXUS_PROJECT_DIR}'),
    (r'D:\\ias\\proyectos', '${NEXUS_PROJECTS_DIR}'),
    (r'D:\\ias\\distros', '${NEXUS_DISTROS_DIR}'),
    (r'D:\\ias\\autopsia', '${NEXUS_AUTOPSIA_DIR}'),
    (r'D:\\ias', '${NEXUS_BASE_DIR}'),
    (r'C:\\Users\\[a-zA-Z0-9_]+', '${USER_HOME}'),
    (r'/home/cjtr', '${USER_HOME}'),
    (r'/home/pc2', '${REMOTE_NODE_PATH}'),
    (r'C:\\Users\\cjtr\\screenshots', '${NEXUS_SCREENSHOTS_DIR}'),
    (r'C:\\Users\\cjtr\\\.nexus', '${NEXUS_BRAIN_DIR}'),
    
    # IPs personales -> genericas
    (r'192\.168\.1\.50', '${REMOTE_NODE_IP}'),
    (r'192\.168\.1\.\d+', '${REMOTE_NODE_IP}'),
    (r'10\.\d+\.\d+\.\d+', '${PRIVATE_IP}'),
    (r'172\.(1[6-9]|2\d|3[01])\.\d+\.\d+', '${PRIVATE_IP}'),
    
    # Referencias a PC2 -> genericas
    (r'\bPC2\b', 'Remote Node'),
    (r'\bpc2\b', 'remote_node'),
    (r'NINJA-PC', '${HOSTNAME}'),
    
    # Nombres de usuario
    (r'\bcjtr\b', '${USERNAME}'),
]

EXCLUDE_DIRS = [
    '.git', '.codegraph', '.nexus', '__pycache__', 'node_modules',
    'memory', 'screenshots', 'deploy', 'legacy', 'dist',
    'data/projects', 'data/brain', 'data/config/apis', 'data/config/drive',
    '.venv', 'venv', '.pytest_cache', '.mypy_cache', '.vscode', '.idea',
]

EXCLUDE_FILE_PATTERNS = [
    r'^\.env$', r'^\.env\.', r'\.key$', r'\.pem$', r'\.p12$',
    r'\.db$', r'\.db-wal$', r'\.db-shm$', r'\.log$', r'\.pid$',
    r'\.pyc$', r'\.pyo$', r'^temp_', r'^check_', r'^read_',
    r'^test_', r'memory\.zip', r'\.tar\.gz$', r'\.tar$',
    r'skills_sync\.zip', r'nexus_core_sync\.zip', r'codex_sync\.tar',
    r'new_skills\.zip', r'scholar_fix\.zip',
]

def should_exclude_dir(dirpath):
    basename = os.path.basename(dirpath)
    rel = os.path.relpath(dirpath, PROJECT_ROOT)
    if basename in EXCLUDE_DIRS:
        return True
    for exc in EXCLUDE_DIRS:
        if rel.startswith(exc + os.sep) or rel == exc:
            return True
    return False

def should_exclude_file(filepath):
    basename = os.path.basename(filepath)
    for pat in EXCLUDE_FILE_PATTERNS:
        if re.match(pat, basename, re.IGNORECASE):
            return True
    _, ext = os.path.splitext(basename)
    if ext in ['.db', '.db-wal', '.db-shm', '.log', '.pid', '.pyc', '.pyo', '.key', '.pem']:
        return True
    return False

def clean_content(content):
    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    return content

def copy_clean_file(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        with open(src, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        cleaned = clean_content(content)
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        return True
    except:
        try:
            shutil.copy2(src, dst)
            return True
        except:
            return False

def build_distro(platform, version, build_dir):
    """Construye la distribucion limpia"""
    print(f'Building {platform} distro v{version}...')
    
    # Copiar archivos limpios
    copied = 0
    errors = 0
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if not should_exclude_dir(os.path.join(root, d))]
        for f in files:
            filepath = os.path.join(root, f)
            if not should_exclude_file(filepath):
                rel = os.path.relpath(filepath, PROJECT_ROOT)
                dst = os.path.join(build_dir, rel)
                if copy_clean_file(filepath, dst):
                    copied += 1
                else:
                    errors += 1
    
    print(f'  Copied: {copied}, Errors: {errors}')
    
    # Crear directorios vacios necesarios
    for d in ['memory', 'data/projects', 'data/gemas', 'screenshots']:
        os.makedirs(os.path.join(build_dir, d), exist_ok=True)
    
    return copied, errors

def create_zip(name, source_dir, output_dir):
    """Crea archivo ZIP"""
    zip_path = os.path.join(output_dir, f'{name}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d != 'node_modules']
            for f in files:
                filepath = os.path.join(root, f)
                arcname = os.path.relpath(filepath, source_dir)
                zf.write(filepath, arcname)
    size = os.path.getsize(zip_path)
    print(f'  Created: {zip_path} ({size / (1024*1024):.1f} MB)')
    return zip_path

def create_tarball(name, source_dir, output_dir):
    """Crea archivo tar.gz"""
    tar_path = os.path.join(output_dir, f'{name}.tar.gz')
    with tarfile.open(tar_path, 'w:gz') as tf:
        tf.add(source_dir, arcname=name)
    size = os.path.getsize(tar_path)
    print(f'  Created: {tar_path} ({size / (1024*1024):.1f} MB)')
    return tar_path

def main():
    parser = argparse.ArgumentParser(description='Build SuperNEXUS v2 distribution')
    parser.add_argument('--platform', choices=['windows', 'linux', 'both'], default='both',
                        help='Platform to build for')
    parser.add_argument('--version', default='2.0.0', help='Version number')
    args = parser.parse_args()
    
    print('=' * 60)
    print(f'  SuperNEXUS v{args.version} - Build Distribution')
    print('=' * 60)
    print()
    
    # Crear directorio de distribucion
    os.makedirs(DIST_DIR, exist_ok=True)
    
    platforms = ['windows', 'linux'] if args.platform == 'both' else [args.platform]
    
    for platform in platforms:
        print(f'\n[1/3] Building {platform} distribution...')
        build_name = f'supernexus-v2-{args.version}-{platform}'
        build_dir = os.path.join(DIST_DIR, build_name)
        
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir)
        
        copied, errors = build_distro(platform, args.version, build_dir)
        
        print(f'\n[2/3] Creating archive...')
        if platform == 'windows':
            create_zip(build_name, build_dir, DIST_DIR)
        else:
            create_tarball(build_name, build_dir, DIST_DIR)
        
        # Limpiar build dir
        shutil.rmtree(build_dir)
        
        print(f'\n[3/3] Verifying...')
        # Verificar que no queden datos sensibles
        archives = [f for f in os.listdir(DIST_DIR) if f.startswith(build_name)]
        for archive in archives:
            print(f'  [OK] {archive}')
    
    print()
    print('=' * 60)
    print('  Build completed!')
    print('=' * 60)
    print()
    print('Files in dist/:')
    for f in sorted(os.listdir(DIST_DIR)):
        size = os.path.getsize(os.path.join(DIST_DIR, f))
        print(f'  {f} ({size / (1024*1024):.1f} MB)')
    print()

if __name__ == '__main__':
    main()
