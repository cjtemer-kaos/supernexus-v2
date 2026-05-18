#!/usr/bin/env python3
"""
Git Pre-Commit Scrubber — SuperNEXUS v2

Prevents accidental commit of sensitive data:
- Private IPs (192.168.x.x, 10.x.x.x, 172.16.x.x)
- Usernames (${USERNAME})
- Absolute paths (D:\\ias\\..., C:\\Users\\...)
- API keys, tokens, passwords
- Device names (PC1, Remote Node in specific contexts)

Usage:
    python tools/git_scrubber.py              # Check staged files
    python tools/git_scrubber.py --all        # Check all tracked files
    python tools/git_scrubber.py <file>       # Check specific file
"""

import re
import sys
import os
import subprocess
from pathlib import Path

# Patterns that indicate sensitive data
SENSITIVE_PATTERNS = [
    {
        "name": "Private IP Address",
        "pattern": r'(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})',
        "severity": "HIGH",
        "exclude_files": [".env.example", "git_scrubber.py", "README.md", "docs/", "secrets_scanner.py"]
    },
    {
        "name": "Hardcoded Username (${USERNAME})",
        "pattern": r'(?<!\w)${USERNAME}(?!\w)',
        "severity": "HIGH",
        "exclude_files": [".env.example", "git_scrubber.py"]
    },
    {
        "name": "Absolute Path (D:\\ias\\...)",
        "pattern": r'D:\\ias[\\\/][^\s"\')\]}]+',
        "severity": "HIGH",
        "exclude_files": [".env.example", "git_scrubber.py", "docs/PRIVATE_DATA_AUDIT.md"]
    },
    {
        "name": "Absolute Path (C:\\Users\\...)",
        "pattern": r'C:\\Users\\[^\s\\\/]+[\\\/]',
        "severity": "HIGH",
        "exclude_files": [".env.example", "git_scrubber.py", "docs/PRIVATE_DATA_AUDIT.md"]
    },
    {
        "name": "SSH Password",
        "pattern": r'(?:password|PASSWORD|passwd)\s*[=:]\s*["\'][^"\']{3,}["\']',
        "severity": "CRITICAL",
        "exclude_files": [".env.example", "git_scrubber.py"]
    },
    {
        "name": "Discord Token",
        "pattern": r'MT[A-Za-z0-9]{20,}\.[A-Za-z0-9]{6}\.[A-Za-z0-9_-]{20,}',
        "severity": "CRITICAL",
        "exclude_files": [".env.example", "git_scrubber.py"]
    },
    {
        "name": "OpenAI API Key",
        "pattern": r'sk-[A-Za-z0-9]{20,}',
        "severity": "CRITICAL",
        "exclude_files": [".env.example", "git_scrubber.py"]
    },
    {
        "name": "Anthropic API Key",
        "pattern": r'sk-ant-[A-Za-z0-9_-]{20,}',
        "severity": "CRITICAL",
        "exclude_files": [".env.example", "git_scrubber.py"]
    },
    {
        "name": "Hardcoded Remote Node Reference",
        "pattern": r'"192\.168\.1\.50"',
        "severity": "HIGH",
        "exclude_files": [".env.example", "git_scrubber.py", "docs/"]
    },
    {
        "name": "Home Path with Username",
        "pattern": r'${USER_HOME}/',
        "severity": "HIGH",
        "exclude_files": [".env.example", "git_scrubber.py", "docs/PRIVATE_DATA_AUDIT.md"]
    },
]

def should_exclude(file_path, exclude_patterns):
    """Check if file should be excluded from scanning"""
    for pattern in exclude_patterns:
        if pattern in file_path:
            return True
    return False

def scan_file(file_path):
    """Scan a file for sensitive patterns"""
    findings = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        return [{"line": 0, "pattern": f"Cannot read file: {e}", "severity": "LOW"}]

    for line_num, line in enumerate(lines, 1):
        for pattern_info in SENSITIVE_PATTERNS:
            if should_exclude(file_path, pattern_info.get("exclude_files", [])):
                continue

            if re.search(pattern_info["pattern"], line):
                # Skip comments in .env.example
                if file_path.endswith('.env.example') and line.strip().startswith('#'):
                    continue

                findings.append({
                    "line": line_num,
                    "pattern": pattern_info["name"],
                    "severity": pattern_info["severity"],
                    "content": line.strip()[:100]
                })

    return findings

def get_staged_files():
    """Get list of staged files"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        return []

def get_all_tracked_files():
    """Get list of all tracked files"""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        return []

def main():
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        files = get_all_tracked_files()
        mode = "all tracked files"
    elif len(sys.argv) > 1:
        files = [sys.argv[1]]
        mode = f"file: {sys.argv[1]}"
    else:
        files = get_staged_files()
        mode = "staged files"

    if not files or files == ['']:
        print(f"✅ No {mode} to scan")
        sys.exit(0)

    print(f"🔍 Scanning {len(files)} {mode}...\n")

    total_findings = 0
    critical_findings = 0

    for file_path in files:
        if not file_path or not os.path.exists(file_path):
            continue

        findings = scan_file(file_path)

        if findings:
            print(f"❌ {file_path}:")
            for finding in findings:
                severity_icon = "🔴" if finding["severity"] == "CRITICAL" else "🟠"
                print(f"   {severity_icon} Line {finding['line']}: {finding['pattern']}")
                print(f"      {finding['content']}")
                total_findings += 1
                if finding["severity"] == "CRITICAL":
                    critical_findings += 1
            print()

    if total_findings > 0:
        print(f"\n🚨 Found {total_findings} sensitive data issues ({critical_findings} CRITICAL)")
        print("   Fix these before committing!")
        print("\n   To bypass (NOT recommended): git commit --no-verify")
        sys.exit(1)
    else:
        print(f"✅ No sensitive data found in {mode}")
        sys.exit(0)

if __name__ == "__main__":
    main()
