"""
system_scanner — Escaneo de seguridad del sistema operativo para SuperNEXUS.

Detecta:
  - Certificados raíz falsos o sospechosos (MITM)
  - Estado de Windows Defender (deshabilitado, sin protección en tiempo real)
  - Activadores/ KMS / software potencialmente no deseado
  - Configuraciones proxy que habiliten interceptación
  - Integridad de la cuenta Microsoft (IdentityCRL, tokens)
  - Servicios de túnel/ C2

Uso:
    from src.security.system_scanner import SystemScanner

    scanner = SystemScanner()
    report = scanner.run_full_scan()
    for finding in report.findings:
        print(f"[{finding.severity}] {finding.title}")
"""

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

try:
    from src.observability.event_stream import emit, EventType
except ImportError:
    async def emit(*args, **kwargs): pass

    class EventType:
        SECURITY_FINDING = "SECURITY_FINDING"

logger = logging.getLogger(__name__)

SUSPICIOUS_CERT_PATTERNS = [
    r"CN\s*=\s*cjtr",
    r"CN\s*=\s*.*kms",
    r"CN\s*=\s*.*activador",
    r"CN\s*=\s*.*hack",
    r"CN\s*=\s*.*crack",
]

KNOWN_ACTIVATORS = {
    "KMSpico": {
        "paths": [
            r"C:\\Program Files\\KMSpico",
            r"C:\\Program Files \(x86\)\\KMSpico",
        ],
        "services": ["Service KMSELDI"],
        "desc": "Activador KMS con certificado MITM + deshabilita Defender"
    },
    "AutoKMS": {
        "paths": [r"C:\\WINDOWS\\AutoKMS"],
        "services": ["AutoKMS"],
        "desc": "Servicio persistente de reactivación KMS"
    },
    "WinScript": {
        "paths": [
            r"C:\\Program Files\\WinScript",
            r"C:\\Program Files \(x86\)\\WinScript",
        ],
        "services": [],
        "desc": "Activador con perfil EBWebView (posible robo de credenciales)"
    },
    "Microsoft Toolkit": {
        "paths": [
            r"C:\\Program Files\\Microsoft Toolkit",
            r"C:\\Program Files \(x86\)\\Microsoft Toolkit",
        ],
        "services": [],
        "desc": "Activador de Office/Windows"
    },
}

SUSPICIOUS_SERVICES = [
    "playit_gg",
    "playit",
    "frpc",
    "frps",
    "ngrok",
    "cloudflared",
    "chisel",
    "bore",
]

SUSPICIOUS_TUNNEL_PATHS = [
    r"C:\\Program Files\\playit_gg",
    r"C:\\Program Files\\cloudflared",
    r"C:\\Program Files\\ngrok",
]


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class Finding:
    category: str
    severity: Severity
    title: str
    description: str
    remediation: str = ""
    evidence: str = ""


@dataclass
class ScanReport:
    timestamp: str = ""
    findings: List[Finding] = field(default_factory=list)
    hostname: str = ""
    os_version: str = ""

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.MEDIUM)

    def summary(self) -> str:
        return (f"Escaneo completado: {self.critical_count} críticos, "
                f"{self.high_count} altos, {self.medium_count} medios, "
                f"{len(self.findings) - self.critical_count - self.high_count - self.medium_count} bajos/info")


class SystemScanner:
    """Escáner de seguridad del sistema operativo"""

    def __init__(self, emit_events: bool = True):
        self.emit_events = emit_events
        self._findings: List[Finding] = []

    def _add_finding(self, category: str, severity: Severity, title: str,
                     description: str, remediation: str = "", evidence: str = ""):
        finding = Finding(
            category=category,
            severity=severity,
            title=title,
            description=description,
            remediation=remediation,
            evidence=evidence,
        )
        self._findings.append(finding)
        logger.warning("[%s] %s: %s", severity.value, category, title)
        if self.emit_events:
            try:
                emit(EventType.SECURITY_FINDING, data={
                    "severity": severity.value, "category": category, "title": title
                })
            except Exception:
                pass

    def _check_path_exists(self, path: str) -> bool:
        try:
            return os.path.exists(os.path.expandvars(path))
        except Exception:
            return False

    def scan_certificates(self):
        """Busca certificados raíz falsos o sospechosos en almacenes del sistema"""
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-ChildItem Cert:\\LocalMachine\\Root, Cert:\\CurrentUser\\Root | "
                 "Where-Object { $_.Subject -notmatch 'Microsoft|VeriSign|DigiCert|GlobalSign|"
                 "Comodo|Entrust|GoDaddy|Let\\sEncrypt|thawte|GeoTrust|USERTrust|Baltimore|"
                 "CyberTrust|SSL\\.com|Network\\sSolutions|GTS|Amazon|Google|Sectigo|"
                 "Certum|Secom|Telstra|Deutsche|SwissSign|Buypass|QuoVadis|ACCV|"
                 "FNMT|T-Systems|D\\-Trust|TWCA|Chunghwa|CertPlus' } | "
                 "Select-Object Subject, Thumbprint, NotAfter, @{N='Store';E={$_.PSParentPath -replace '.*\\\\',''}} | "
                 "ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=30,
            )
            if result.stdout and result.stdout.strip() not in ("[]", ""):
                try:
                    import json
                    certs = json.loads(result.stdout)
                    if not isinstance(certs, list):
                        certs = [certs]
                    for cert in certs:
                        subject = cert.get("Subject", "?")
                        thumbprint = cert.get("Thumbprint", "?")
                        not_after = cert.get("NotAfter", "?")
                        store = cert.get("Store", "?")
                        if any(re.search(p, subject, re.IGNORECASE) for p in SUSPICIOUS_CERT_PATTERNS):
                            sev = Severity.CRITICAL
                        else:
                            sev = Severity.HIGH
                        self._add_finding(
                            category="certificates",
                            severity=sev,
                            title=f"Certificado no autorizado en {store}: {subject}",
                            description=f"Certificado raíz no emitido por una CA reconocida. "
                                        f"Permite MITM a cualquier tráfico HTTPS.",
                            remediation="Eliminar el certificado usando: certutil -delstore Root <thumbprint>",
                            evidence=f"Subject: {subject} | Thumbprint: {thumbprint} | "
                                     f"Expira: {not_after} | Store: {store}",
                        )
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.debug("Error escaneando certificados: %s", e)

    def scan_defender(self):
        """Verifica el estado de Windows Defender"""
        checks = [
            ("AMServiceEnabled", "Antimalware service"),
            ("AntivirusEnabled", "Antivirus"),
            ("RealTimeProtectionEnabled", "Protección en tiempo real"),
        ]
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-MpComputerStatus | Select-Object AMServiceEnabled, AntivirusEnabled, "
                 "RealTimeProtectionEnabled, IsTamperProtected, IoavProtectionEnabled | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15,
            )
            if result.stdout:
                import json
                status = json.loads(result.stdout)
                for key, label in checks:
                    if status.get(key) is False:
                        self._add_finding(
                            category="defender",
                            severity=Severity.CRITICAL,
                            title=f"Windows Defender: {label} DESHABILITADO",
                            description=f"La protección '{label}' está desactivada. "
                                        f"El sistema está expuesto a malware.",
                            remediation="Reactivar con: Set-MpPreference -DisableRealtimeMonitoring $false",
                            evidence=f"{key}={status.get(key)}",
                        )
                if status.get("IsTamperProtected") is False:
                    self._add_finding(
                        category="defender",
                        severity=Severity.HIGH,
                        title="Windows Defender: Tamper Protection deshabilitada",
                        description="La protección contra manipulaciones está apagada. "
                                    "Malware puede desactivar Defender sin ser detectado.",
                        remediation="Activar Tamper Protection en Windows Security > Protección contra virus y amenazas",
                        evidence="IsTamperProtected=False",
                    )
        except Exception as e:
            self._add_finding(
                category="defender",
                severity=Severity.MEDIUM,
                title="No se pudo verificar Windows Defender",
                description=f"Error consultando estado de Defender: {e}",
                remediation="Verificar manualmente en Windows Security",
            )

    def scan_activators(self):
        """Detecta activadores KMS y software potencialmente no deseado"""
        for name, info in KNOWN_ACTIVATORS.items():
            found_paths = [p for p in info["paths"] if self._check_path_exists(p)]
            found_services = []
            for svc in info["services"]:
                try:
                    r = subprocess.run(
                        ["sc", "query", svc],
                        capture_output=True, text=True, timeout=10,
                    )
                    if "RUNNING" in r.stdout or "STOPPED" in r.stdout:
                        found_services.append(svc)
                except Exception:
                    pass
            if found_paths or found_services:
                sev = Severity.HIGH if "KMS" in name else Severity.MEDIUM
                self._add_finding(
                    category="activators",
                    severity=sev,
                    title=f"Activador detectado: {name}",
                    description=info["desc"],
                    remediation=f"Eliminar {name} manualmente y reactivar protección del sistema.",
                    evidence=f"Paths: {found_paths} | Services: {found_services}",
                )

    def scan_tunnels(self):
        """Detecta servicios de túnel que pueden ser usados como C2"""
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_Service | Where-Object { $_.Name -match "
                 "'playit|frpc|ngrok|cloudflared|chisel|bore' } | "
                 "Select-Object Name, State, StartMode, PathName | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15,
            )
            if result.stdout and result.stdout.strip() not in ("[]", ""):
                import json
                services = json.loads(result.stdout)
                if not isinstance(services, list):
                    services = [services]
                for svc in services:
                    self._add_finding(
                        category="tunnels",
                        severity=Severity.MEDIUM,
                        title=f"Servicio de túnel activo: {svc.get('Name', '?')}",
                        description="Servicio que puede establecer conexiones de salida "
                                    "no autorizadas (C2/exfiltración).",
                        remediation="Verificar si el servicio es necesario. "
                                    "Detener con: sc stop <nombre> && sc delete <nombre>",
                        evidence=f"Name: {svc.get('Name')} | State: {svc.get('State')} | "
                                 f"Path: {svc.get('PathName', '?')[:120]}",
                    )
        except Exception:
            pass
        for path in SUSPICIOUS_TUNNEL_PATHS:
            if self._check_path_exists(path):
                self._add_finding(
                    category="tunnels",
                    severity=Severity.LOW,
                    title=f"Software de túnel instalado: {path}",
                    description="Cliente de tunneling presente en el sistema.",
                    remediation="Verificar si es necesario. Desinstalar si no.",
                    evidence=f"Path: {path}",
                )

    def scan_proxy(self):
        """Verifica configuración de proxy que pueda interceptar tráfico"""
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\"
                 "Internet Settings' | Select-Object ProxyEnable, ProxyServer, ProxyOverride "
                 "| ConvertTo-Json"],
                capture_output=True, text=True, timeout=10,
            )
            if result.stdout:
                import json
                proxy = json.loads(result.stdout)
                if proxy.get("ProxyEnable") == 1:
                    self._add_finding(
                        category="proxy",
                        severity=Severity.MEDIUM,
                        title="Proxy HTTP configurado — posible interceptación",
                        description=f"Proxy: {proxy.get('ProxyServer', '?')}. "
                                    "Puede estar interceptando tráfico HTTPS.",
                        remediation="Deshabilitar si no es necesario: "
                                    "Set-ItemProperty -Path 'HKCU:\\...Internet Settings' "
                                    "-Name ProxyEnable -Value 0",
                        evidence=f"ProxyServer={proxy.get('ProxyServer')} | "
                                 f"ProxyOverride={proxy.get('ProxyOverride')}",
                    )
        except Exception:
            pass

    def scan_microsoft_account(self):
        """Verifica integridad de la cuenta Microsoft almacenada"""
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\IdentityCRL\\"
                 "UserExtendedProperties\\*' | Select-Object PSChildName, puid, cid "
                "| ConvertTo-Json"],
                capture_output=True, text=True, timeout=10,
            )
            if result.stdout and result.stdout.strip() not in ("[]", ""):
                import json
                accounts = json.loads(result.stdout)
                if not isinstance(accounts, list):
                    accounts = [accounts]
                for acc in accounts:
                    email = acc.get("PSChildName", "?")
                    puid = acc.get("puid", "?")
                    self._add_finding(
                        category="microsoft_account",
                        severity=Severity.INFO,
                        title=f"Cuenta Microsoft en sistema: {email}",
                        description=f"Credenciales de Microsoft Account almacenadas "
                                    f"localmente (PUID: {puid}). "
                                    "Verificar que el alias no haya sido cambiado.",
                        remediation="Si la cuenta fue comprometida, cambiar contraseña y "
                                    "activar 2FA en account.live.com",
                        evidence=f"Email: {email} | PUID: {puid}",
                    )
        except Exception:
            pass

    def run_full_scan(self) -> ScanReport:
        from datetime import datetime
        self._findings = []
        logger.info("Iniciando escaneo completo de seguridad del sistema...")
        self.scan_certificates()
        self.scan_defender()
        self.scan_activators()
        self.scan_tunnels()
        self.scan_proxy()
        self.scan_microsoft_account()
        report = ScanReport(
            timestamp=datetime.now().isoformat(),
            findings=self._findings,
            hostname=os.environ.get("COMPUTERNAME", "?"),
            os_version=getattr(self, "_os_version", "?"),
        )
        logger.info("Escaneo completado: %s", report.summary())
        return report
