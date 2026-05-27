"""
KnowledgeSync - Compartir conocimiento entre nodos para SuperNEXUS v2.0

Características:
- Sincronización bidireccional de conocimiento entre Windows ↔ PC2
- Merge por timestamp y confidence score
- Resolución automática de conflictos
- Sincronización incremental
"""

import logging
import json
import hashlib
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class SyncDirection(Enum):
    PUSH = "push"
    PULL = "pull"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class SyncRecord:
    """Registro de sincronización"""
    id: str
    node: str
    content_hash: str
    timestamp: str
    content: str
    metadata: Dict = field(default_factory=dict)


class KnowledgeSync:
    """
    Sistema de sincronización de conocimiento entre nodos.
    """
    
    def __init__(
        self,
        node_id: str = "local",
        storage_path: str = None,
        sync_interval: int = 60,
    ):
        self.node_id = node_id
        self.storage_path = Path(storage_path) if storage_path else None
        self.sync_interval = sync_interval
        
        self.local_records: Dict[str, SyncRecord] = {}
        self.remote_records: Dict[str, SyncRecord] = {}
        self.sync_log: List[Dict] = []
        self._last_sync = 0
        
        if self.storage_path and self.storage_path.exists():
            self.load()
    
    def add_local_record(self, content: str, metadata: Dict = None) -> str:
        """Agrega registro local"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        record_id = hashlib.md5(f"{content_hash}{time.time()}".encode()).hexdigest()[:12]
        
        record = SyncRecord(
            id=record_id,
            node=self.node_id,
            content_hash=content_hash,
            timestamp=datetime.now().isoformat(),
            content=content,
            metadata=metadata or {},
        )
        
        self.local_records[record_id] = record
        logger.debug(f"Local record added: {record_id}")
        
        return record_id
    
    def sync_with_remote(self, remote_records: Dict[str, SyncRecord], direction: SyncDirection = SyncDirection.BIDIRECTIONAL) -> Dict:
        """Sincroniza con registros remotos"""
        now = time.time()
        
        if now - self._last_sync < self.sync_interval:
            return {"status": "skipped", "reason": "sync_too_frequent"}
        
        merged = 0
        conflicts = 0
        skipped = 0
        
        if direction in [SyncDirection.PULL, SyncDirection.BIDIRECTIONAL]:
            for record_id, remote_record in remote_records.items():
                if record_id in self.local_records:
                    local_record = self.local_records[record_id]
                    
                    if local_record.content_hash == remote_record.content_hash:
                        skipped += 1
                        continue
                    
                    local_time = datetime.fromisoformat(local_record.timestamp)
                    remote_time = datetime.fromisoformat(remote_record.timestamp)
                    
                    if remote_time > local_time:
                        self.local_records[record_id] = remote_record
                        merged += 1
                        logger.info(f"Record updated from remote: {record_id}")
                    else:
                        conflicts += 1
                        logger.debug(f"Conflict skipped (local newer): {record_id}")
                else:
                    self.local_records[record_id] = remote_record
                    merged += 1
                    logger.info(f"Record added from remote: {record_id}")
        
        if direction in [SyncDirection.PUSH, SyncDirection.BIDIRECTIONAL]:
            for record_id, local_record in self.local_records.items():
                if record_id not in remote_records:
                    remote_records[record_id] = local_record
                    merged += 1
        
        self._last_sync = now
        
        sync_result = {
            "status": "completed",
            "merged": merged,
            "conflicts": conflicts,
            "skipped": skipped,
            "total_local": len(self.local_records),
            "total_remote": len(remote_records),
            "timestamp": datetime.now().isoformat(),
        }
        
        self.sync_log.append(sync_result)
        
        if len(self.sync_log) > 100:
            self.sync_log = self.sync_log[-100:]
        
        self._save()
        
        return sync_result
    
    def get_pending_changes(self, remote_records: Dict[str, SyncRecord]) -> Dict[str, SyncRecord]:
        """Obtiene cambios pendientes"""
        pending = {}
        
        for record_id, local_record in self.local_records.items():
            if record_id not in remote_records:
                pending[record_id] = local_record
            else:
                remote_record = remote_records[record_id]
                if local_record.content_hash != remote_record.content_hash:
                    local_time = datetime.fromisoformat(local_record.timestamp)
                    remote_time = datetime.fromisoformat(remote_record.timestamp)
                    
                    if local_time > remote_time:
                        pending[record_id] = local_record
        
        return pending
    
    def get_sync_stats(self) -> Dict:
        """Obtiene estadísticas de sincronización"""
        return {
            "node_id": self.node_id,
            "local_records": len(self.local_records),
            "remote_records": len(self.remote_records),
            "last_sync": datetime.fromtimestamp(self._last_sync).isoformat() if self._last_sync > 0 else "never",
            "sync_log_count": len(self.sync_log),
            "recent_syncs": self.sync_log[-5:],
        }
    
    def _save(self):
        """Guarda en disco"""
        if not self.storage_path:
            return
        
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "node_id": self.node_id,
            "local_records": {
                record_id: {
                    "id": record.id,
                    "node": record.node,
                    "content_hash": record.content_hash,
                    "timestamp": record.timestamp,
                    "content": record.content,
                    "metadata": record.metadata,
                }
                for record_id, record in self.local_records.items()
            },
            "sync_log": self.sync_log,
            "last_sync": self._last_sync,
        }
        
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def load(self):
        """Carga desde disco"""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        with open(self.storage_path, "r") as f:
            data = json.load(f)
        
        self.node_id = data.get("node_id", "local")
        self._last_sync = data.get("last_sync", 0)
        
        self.local_records = {
            record_id: SyncRecord(
                id=record["id"],
                node=record["node"],
                content_hash=record["content_hash"],
                timestamp=record["timestamp"],
                content=record["content"],
                metadata=record.get("metadata", {}),
            )
            for record_id, record in data.get("local_records", {}).items()
        }
        
        self.sync_log = data.get("sync_log", [])
        
        logger.info(f"Knowledge sync loaded: {len(self.local_records)} records")
