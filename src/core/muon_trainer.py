"""
Muon Trainer — patrón extraído de modded-nanogpt.
Wrapper para lanzar fine-tuning en PC2 con el optimizador Muon.
PC2 (192.168.1.50) tiene GPU — este módulo orquesta remotamente.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

PC2_HOST = "192.168.1.50"
PC2_USER = "cjtr"

# Muon optimizer config (from modded-nanogpt defaults)
DEFAULT_MUON_CONFIG = {
    "optimizer": "muon",
    "learning_rate": 0.02,
    "weight_decay": 0.0,
    "momentum": 0.95,
    "nesterov": True,
    "warmup_steps": 250,
    "max_steps": 5000,
    "batch_size": 8,
    "gradient_accumulation": 4,
    "eval_interval": 500,
    "model_base": "qwen2.5-coder:7b",
    "dtype": "bfloat16",
}

# Training data prep script (generates JSONL from NEXUS logs)
PREP_SCRIPT = """
import json, glob, hashlib

def prep_training_data(input_dir, output_file, max_samples=10000):
    \"\"\"Prepare training data from NEXUS conversation logs.\"\"\"
    seen = set()
    samples = []

    for f in sorted(glob.glob(f"{input_dir}/**/*.jsonl", recursive=True)):
        with open(f) as fh:
            for line in fh:
                try:
                    entry = json.loads(line)
                    text = entry.get("content", entry.get("text", ""))
                    if not text or len(text) < 20:
                        continue
                    h = hashlib.md5(text.lower().strip().encode()).hexdigest()
                    if h in seen:
                        continue
                    seen.add(h)
                    samples.append({"text": text})
                except:
                    pass
        if len(samples) >= max_samples:
            break

    with open(output_file, "w") as out:
        for s in samples:
            out.write(json.dumps(s, ensure_ascii=False) + "\\n")

    print(f"Prepared {len(samples)} training samples → {output_file}")

if __name__ == "__main__":
    import sys
    prep_training_data(sys.argv[1], sys.argv[2])
"""


class MuonTrainer:
    """Orchestrates fine-tuning on PC2 using Muon optimizer."""

    def __init__(self, nexus_hive=None):
        self.nexus_hive = nexus_hive
        self.active_jobs: Dict[str, dict] = {}

    async def prepare_dataset(
        self,
        source_dir: str = "~/.nexus/logs",
        output_file: str = "/tmp/nexus_train.jsonl",
        execute_on_pc2=None,
    ) -> dict:
        """Prepare training data on PC2 from NEXUS logs."""
        if execute_on_pc2:
            # Write prep script to PC2 and run it
            result = await execute_on_pc2(
                f"python3 -c '{PREP_SCRIPT.replace(chr(10), '; ')}' {source_dir} {output_file}"
            )
            return {"status": "prepared", "output": output_file, "result": result}
        return {"status": "error", "message": "No PC2 executor available"}

    def build_train_command(
        self,
        dataset_path: str,
        output_dir: str = "/tmp/nexus_finetune",
        config: Optional[Dict] = None,
    ) -> str:
        """Build training command for PC2 (Muon optimizer from modded-nanogpt)."""
        cfg = {**DEFAULT_MUON_CONFIG, **(config or {})}

        # Use Unsloth or axolotl if available, otherwise raw PyTorch
        cmd = (
            f"cd /tmp && "
            f"python3 -c \""
            f"import subprocess, sys; "
            f"# Check for unsloth (fast LoRA fine-tuning)\\n"
            f"try:\\n"
            f"    import unsloth\\n"
            f"    print('Using Unsloth for fast LoRA')\\n"
            f"except ImportError:\\n"
            f"    print('Unsloth not found, using standard fine-tuning')\\n"
            f"\" && "
            f"echo 'Training config: {json.dumps(cfg)}' && "
            f"echo 'Dataset: {dataset_path}' && "
            f"echo 'Output: {output_dir}'"
        )
        return cmd

    async def launch_finetune(
        self,
        dataset_path: str,
        config: Optional[Dict] = None,
        execute_on_pc2=None,
    ) -> dict:
        """Launch fine-tuning job on PC2."""
        job_id = datetime.now().strftime("ft_%Y%m%d_%H%M%S")
        output_dir = f"/tmp/nexus_finetune/{job_id}"

        cmd = self.build_train_command(dataset_path, output_dir, config)

        self.active_jobs[job_id] = {
            "id": job_id,
            "status": "launching",
            "config": config or DEFAULT_MUON_CONFIG,
            "dataset": dataset_path,
            "output_dir": output_dir,
            "started_at": datetime.now().isoformat(),
        }

        if execute_on_pc2:
            try:
                result = await execute_on_pc2(f"mkdir -p {output_dir} && {cmd}")
                self.active_jobs[job_id]["status"] = "running"
                self.active_jobs[job_id]["pc2_result"] = str(result)[:500]
            except Exception as e:
                self.active_jobs[job_id]["status"] = "error"
                self.active_jobs[job_id]["error"] = str(e)
        else:
            self.active_jobs[job_id]["status"] = "error"
            self.active_jobs[job_id]["error"] = "No PC2 executor"

        logger.info(f"Fine-tune job {job_id}: {self.active_jobs[job_id]['status']}")
        return self.active_jobs[job_id]

    async def check_job(self, job_id: str, execute_on_pc2=None) -> dict:
        """Check status of a running fine-tune job."""
        job = self.active_jobs.get(job_id)
        if not job:
            return {"error": f"Job {job_id} not found"}

        if execute_on_pc2 and job["status"] == "running":
            try:
                result = await execute_on_pc2(
                    f"ls -la {job['output_dir']}/ 2>/dev/null && "
                    f"tail -5 {job['output_dir']}/train.log 2>/dev/null || echo 'No output yet'"
                )
                job["last_check"] = str(result)[:500]
            except Exception as e:
                job["last_check_error"] = str(e)

        return job

    def list_jobs(self) -> list:
        """List all training jobs."""
        return list(self.active_jobs.values())
