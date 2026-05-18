"""
SkillSync - Sincronizacion de skills entre nodos para SuperNEXUS v2.0

Principios:
- Cada nodo es INDEPENDIENTE (funciona solo)
- Sync CUANDO ambos estan online (no obligatorio)
- Merge inteligente: el mas reciente gana
- Solo transfiere metadata, no contenido (el contenido se carga lazy)
- Resolucion de conflictos por timestamp
"""

import logging
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SyncStats:
    """Estadisticas de sincronizacion"""
    last_sync: str = "never"
    total_syncs: int = 0
    skills_imported: int = 0
    skills_exported: int = 0
    conflicts_resolved: int = 0
    errors: int = 0


class SkillSync:
    """
    Sincronizacion de skills entre Windows y Remote Node.
    
    Uso:
        sync = SkillSync(local_registry, node_id="local")
        
        # Exportar skills a otro nodo
        export_data = sync.export_for_sync()
        
        # Importar skills de otro nodo
        sync.import_from_remote(remote_data)
        
        # Sync automatico via HTTP (si ambos estan online)
        await sync.auto_sync(remote_url=f"http://{os.getenv('SUPER_NEXUS_Remote Node_IP', 'localhost')}:9000")
    """
    
    def __init__(
        self,
        local_registry,
        node_id: str = "local",
        sync_interval: int = 3600,
        storage_path: str = None,
    ):
        self.local_registry = local_registry
        self.node_id = node_id
        self.sync_interval = sync_interval
        self.storage_path = Path(storage_path) if storage_path else None
        
        self.stats = SyncStats()
        self._last_sync = 0
        
        self._load_stats()
    
    def export_for_sync(self) -> Dict:
        """Exporta indice de skills para enviar a otro nodo"""
        return self.local_registry.export_index()
    
    def import_from_remote(self, remote_data: Dict) -> Dict:
        """Importa skills de otro nodo"""
        if not remote_data or "skills" not in remote_data:
            return {"status": "error", "message": "Invalid remote data"}
        
        remote_node = remote_data.get("node_id", "unknown")
        imported = 0
        updated = 0
        conflicts = 0
        
        for skill_id, remote_skill in remote_data["skills"].items():
            local_skill = self.local_registry.metadata_cache.get(skill_id)
            
            if not local_skill:
                self.local_registry.import_index({"skills": {skill_id: remote_skill}}, merge=True)
                imported += 1
            else:
                remote_modified = remote_skill.get("last_modified", "")
                local_modified = local_skill.last_modified
                
                if remote_modified > local_modified:
                    self.local_registry.import_index({"skills": {skill_id: remote_skill}}, merge=True)
                    updated += 1
                elif remote_modified != local_modified:
                    conflicts += 1
                    logger.debug(f"Conflict for skill {skill_id}: keeping local (newer)")
        
        self.stats.total_syncs += 1
        self.stats.skills_imported += imported
        self.stats.last_sync = datetime.now().isoformat()
        self.stats.conflicts_resolved += conflicts
        
        self._save_stats()
        self.local_registry._save_index()
        
        return {
            "status": "success",
            "imported": imported,
            "updated": updated,
            "conflicts": conflicts,
            "remote_node": remote_node,
        }
    
    async def auto_sync(self, remote_url: str = None) -> Dict:
        """Intenta sync automatico con otro nodo via HTTP"""
        if not remote_url:
            Remote Node_ip = os.getenv("SUPER_NEXUS_Remote Node_IP", "localhost")
            if self.node_id == "local":
                remote_url = f"http://{Remote Node_ip}:9000"
            else:
                remote_url = "http://127.0.0.1:9000"
        
        now = time.time()
        if (now - self._last_sync) < self.sync_interval:
            return {"status": "skipped", "reason": "sync_too_frequent"}
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{remote_url}/api/skills/export")
                
                if response.status_code == 200:
                    remote_data = response.json()
                    result = self.import_from_remote(remote_data)
                    
                    export_data = self.export_for_sync()
                    await client.post(
                        f"{remote_url}/api/skills/import",
                        json=export_data,
                    )
                    
                    self._last_sync = now
                    
                    return result
                else:
                    return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            self.stats.errors += 1
            return {"status": "offline", "message": str(e)}
    
    def get_sync_status(self) -> Dict:
        """Estado de sincronizacion"""
        return {
            "node_id": self.node_id,
            "local_skills": len(self.local_registry.metadata_cache),
            "last_sync": self.stats.last_sync,
            "total_syncs": self.stats.total_syncs,
            "skills_imported": self.stats.skills_imported,
            "conflicts_resolved": self.stats.conflicts_resolved,
            "errors": self.stats.errors,
        }
    
    def _load_stats(self):
        """Carga estadisticas desde disco"""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            
            self.stats = SyncStats(**data)
        except:
            pass
    
    def _save_stats(self):
        """Guarda estadisticas en disco"""
        if not self.storage_path:
            return
        
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.storage_path, "w") as f:
            json.dump({
                "last_sync": self.stats.last_sync,
                "total_syncs": self.stats.total_syncs,
                "skills_imported": self.stats.skills_imported,
                "skills_exported": self.stats.skills_exported,
                "conflicts_resolved": self.stats.conflicts_resolved,
                "errors": self.stats.errors,
            }, f, indent=2)
