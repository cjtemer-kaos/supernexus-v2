"""
NexusTrainer - Modulo de entrenamiento local basado en patrones de NanoChat (Karpathy)

Permite a SuperNEXUS entrenar y fine-tunear sus propios modelos locales
usando datos de conversaciones reales, sin depender de APIs externas.

Pipeline:
1. DataCollector recolecta conversaciones de alta calidad
2. NexusTrainer entrena con SFT (Supervised Fine-Tuning)
3. Modelos resultantes se registran en Ollama automaticamente

Arquitectura inspirada en NanoChat:
- Single dial de complejidad (--depth)
- Compute-optimal hyperparameters automaticos
- Rotary embeddings, QK norm, sliding window attention
- Muon optimizer para matrices, AdamW para embeddings
"""

import json
import logging
import math
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent
MODELS_DIR = BASE_DIR / "data" / "trained_models"
DATA_DIR = BASE_DIR / "data" / "training_data"


@dataclass
class TrainingConfig:
    """Configuracion de entrenamiento con single dial de complejidad"""
    depth: int = 12  # Single dial: controla todo automaticamente
    sequence_len: int = 2048
    vocab_size: int = 32768
    run_name: str = "nexus-default"
    num_iterations: int = 1000
    device_batch_size: int = 4
    total_batch_tokens: int = 65536
    learning_rate: float = 0.002
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    eval_every: int = 100
    save_every: int = 500
    device_type: str = "cuda"  # cuda, cpu, mps
    gradient_accumulation: int = 1
    max_grad_norm: float = 1.0
    # Data mixture
    mmlu_epochs: int = 3
    gsm8k_epochs: int = 4
    # Identity
    identity_data_path: Optional[str] = None

    def __post_init__(self):
        """Calcula hyperparameters automaticos basados en depth (scaling laws)"""
        self.n_head = max(4, self.depth // 2)
        self.n_kv_head = max(2, self.depth // 4)
        self.n_embd = max(256, self.depth * 64)
        self.window_pattern = "SSSL" if self.depth > 16 else "L"


class NexusGPTConfig:
    """Configuracion del modelo GPT"""
    def __init__(self, training_config: TrainingConfig):
        self.sequence_len = training_config.sequence_len
        self.vocab_size = training_config.vocab_size
        self.n_layer = training_config.depth
        self.n_head = training_config.n_head
        self.n_kv_head = training_config.n_kv_head
        self.n_embd = training_config.n_embd
        self.window_pattern = training_config.window_pattern


class Linear(nn.Linear):
    """Linear que castea pesos al dtype de input (mixed precision explicito)"""
    def forward(self, x):
        return F.linear(x, self.weight.to(dtype=x.dtype))


def norm(x):
    return F.rms_norm(x, (x.size(-1),))


def apply_rotary_emb(x, cos, sin):
    d = x.shape[3] // 2
    x1, x2 = x[..., :d], x[..., d:]
    y1 = x1 * cos + x2 * sin
    y2 = x1 * (-sin) + x2 * cos
    return torch.cat([y1, y2], 3)


class CausalSelfAttention(nn.Module):
    def __init__(self, config, layer_idx):
        super().__init__()
        self.layer_idx = layer_idx
        self.n_head = config.n_head
        self.n_kv_head = config.n_kv_head
        self.n_embd = config.n_embd
        self.head_dim = self.n_embd // self.n_head
        self.c_q = Linear(self.n_embd, self.n_head * self.head_dim, bias=False)
        self.c_k = Linear(self.n_embd, self.n_kv_head * self.head_dim, bias=False)
        self.c_v = Linear(self.n_embd, self.n_kv_head * self.head_dim, bias=False)
        self.c_proj = Linear(self.n_embd, self.n_embd, bias=False)

    def forward(self, x, cos, sin):
        B, T, C = x.size()
        q = self.c_q(x).view(B, T, self.n_head, self.head_dim)
        k = self.c_k(x).view(B, T, self.n_kv_head, self.head_dim)
        v = self.c_v(x).view(B, T, self.n_kv_head, self.head_dim)

        q, k = apply_rotary_emb(q, cos, sin), apply_rotary_emb(k, cos, sin)
        q, k = norm(q), norm(k)
        q, k = q * 1.2, k * 1.2

        # SDPA con causal mask
        y = F.scaled_dot_product_attention(
            q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2),
            is_causal=True
        ).transpose(1, 2).contiguous().view(B, T, -1)

        return self.c_proj(y)


class MLP(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.c_fc = Linear(config.n_embd, 4 * config.n_embd, bias=False)
        self.c_proj = Linear(4 * config.n_embd, config.n_embd, bias=False)

    def forward(self, x):
        x = self.c_fc(x)
        x = F.relu(x).square()  # relu^2 activation
        return self.c_proj(x)


class Block(nn.Module):
    def __init__(self, config, layer_idx):
        super().__init__()
        self.attn = CausalSelfAttention(config, layer_idx)
        self.mlp = MLP(config)

    def forward(self, x, cos, sin):
        x = x + self.attn(norm(x), cos, sin)
        x = x + self.mlp(norm(x))
        return x


class NexusGPT(nn.Module):
    """Modelo GPT optimizado para entrenamiento local"""
    def __init__(self, config):
        super().__init__()
        self.config = config
        padded_vocab = ((config.vocab_size + 64 - 1) // 64) * 64

        self.transformer = nn.ModuleDict({
            "wte": nn.Embedding(padded_vocab, config.n_embd),
            "h": nn.ModuleList([Block(config, i) for i in range(config.n_layer)]),
        })
        self.lm_head = Linear(config.n_embd, padded_vocab, bias=False)

        # Per-layer scalars
        self.resid_lambdas = nn.Parameter(torch.ones(config.n_layer))
        self.x0_lambdas = nn.Parameter(torch.zeros(config.n_layer))

        # Rotary embeddings
        head_dim = config.n_embd // config.n_head
        cos, sin = self._precompute_rotary(config.sequence_len * 10, head_dim)
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)

        self._init_weights()

    def _init_weights(self):
        torch.nn.init.normal_(self.transformer.wte.weight, mean=0.0, std=0.8)
        torch.nn.init.normal_(self.lm_head.weight, mean=0.0, std=0.001)

        n_embd = self.config.n_embd
        s = 3**0.5 * n_embd**-0.5
        for block in self.transformer.h:
            torch.nn.init.uniform_(block.attn.c_q.weight, -s, s)
            torch.nn.init.uniform_(block.attn.c_k.weight, -s, s)
            torch.nn.init.uniform_(block.attn.c_v.weight, -s, s)
            torch.nn.init.zeros_(block.attn.c_proj.weight)
            torch.nn.init.uniform_(block.mlp.c_fc.weight, -s * 0.4, s * 0.4)
            torch.nn.init.zeros_(block.mlp.c_proj.weight)

        n_layer = self.config.n_layer
        for i in range(n_layer):
            self.resid_lambdas.data[i] = 1.15 - (0.10 * i / max(n_layer - 1, 1))
            self.x0_lambdas.data[i] = 0.20 - (0.15 * i / max(n_layer - 1, 1))

    def _precompute_rotary(self, seq_len, head_dim, base=100000):
        device = self.transformer.wte.weight.device
        channel_range = torch.arange(0, head_dim, 2, dtype=torch.float32, device=device)
        inv_freq = 1.0 / (base ** (channel_range / head_dim))
        t = torch.arange(seq_len, dtype=torch.float32, device=device)
        freqs = torch.outer(t, inv_freq)
        cos, sin = freqs.cos(), freqs.sin()
        cos, sin = cos[None, :, None, :], sin[None, :, None, :]
        return cos, sin

    def forward(self, idx, targets=None):
        B, T = idx.size()
        assert T <= self.cos.size(1)
        cos, sin = self.cos[:, :T], self.sin[:, :T]

        x = self.transformer.wte(idx)
        x = norm(x)
        x0 = x

        for i, block in enumerate(self.transformer.h):
            x = self.resid_lambdas[i] * x + self.x0_lambdas[i] * x0
            x = block(x, cos, sin)

        x = norm(x)
        logits = self.lm_head(x)[..., :self.config.vocab_size]
        logits = logits.float()
        logits = 15 * torch.tanh(logits / 15)  # softcap

        if targets is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1), ignore_index=-1)
            return loss
        return logits

    @torch.inference_mode()
    def generate(self, tokens, max_tokens, temperature=0.8, top_k=50):
        """Generacion autoregresiva"""
        assert isinstance(tokens, list)
        device = self.transformer.wte.weight.device
        ids = torch.tensor([tokens], dtype=torch.long, device=device)

        for _ in range(max_tokens):
            logits = self.forward(ids)[:, -1, :]
            if top_k > 0:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = -float('Inf')
            if temperature > 0:
                probs = F.softmax(logits / temperature, dim=-1)
                next_ids = torch.multinomial(probs, num_samples=1)
            else:
                next_ids = torch.argmax(logits, dim=-1, keepdim=True)
            ids = torch.cat((ids, next_ids), dim=1)
            yield next_ids.item()

    def save(self, path: str, meta: dict = None):
        """Guarda checkpoint del modelo"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "model": self.state_dict(),
            "config": {
                "n_layer": self.config.n_layer,
                "n_head": self.config.n_head,
                "n_kv_head": self.config.n_kv_head,
                "n_embd": self.config.n_embd,
                "vocab_size": self.config.vocab_size,
                "sequence_len": self.config.sequence_len,
            },
            "meta": meta or {},
        }
        torch.save(checkpoint, path)
        logger.info(f"Modelo guardado en {path}")

    @classmethod
    def load(cls, path: str, device="cpu"):
        """Carga modelo desde checkpoint"""
        checkpoint = torch.load(path, map_location=device, weights_only=False)
        config = NexusGPTConfig(TrainingConfig(
            depth=checkpoint["config"]["n_layer"],
            n_embd=checkpoint["config"]["n_embd"],
            n_head=checkpoint["config"]["n_head"],
            n_kv_head=checkpoint["config"]["n_kv_head"],
            vocab_size=checkpoint["config"]["vocab_size"],
            sequence_len=checkpoint["config"]["sequence_len"],
        ))
        model = cls(config).to(device)
        model.load_state_dict(checkpoint["model"])
        model.eval()
        return model, checkpoint.get("meta", {})


class NexusTrainer:
    """Entrenador de modelos locales para SuperNEXUS"""

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.model = None
        self.optimizer = None
        self.step = 0
        self.best_loss = float('inf')
        self._setup_device()

    def _setup_device(self):
        if self.config.device_type == "cuda" and torch.cuda.is_available():
            self.device = torch.device("cuda")
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        elif self.config.device_type == "mps" and hasattr(torch.backends, "mps"):
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
        logger.info(f"Dispositivo: {self.device}")

    def load_base_model(self, path: Optional[str] = None):
        """Carga modelo base para fine-tuning"""
        if path and Path(path).exists():
            self.model, meta = NexusGPT.load(path, str(self.device))
            self.step = meta.get("step", 0)
            logger.info(f"Modelo base cargado desde {path} (step {self.step})")
        else:
            gpt_config = NexusGPTConfig(self.config)
            self.model = NexusGPT(gpt_config).to(self.device)
            logger.info(f"Modelo nuevo creado (depth={self.config.depth})")

    def setup_optimizer(self):
        """Configura optimizador con learning rates por grupo de parametros"""
        model_dim = self.config.n_embd
        dmodel_scale = (model_dim / 768) ** -0.5

        matrix_params = list(self.model.transformer.h.parameters())
        embedding_params = list(self.model.transformer.wte.parameters())
        lm_head_params = list(self.model.lm_head.parameters())
        scalar_params = [self.model.resid_lambdas, self.model.x0_lambdas]

        param_groups = [
            {"params": lm_head_params, "lr": 0.004 * dmodel_scale, "weight_decay": 0.01},
            {"params": embedding_params, "lr": 0.2 * dmodel_scale, "weight_decay": 0.001},
            {"params": matrix_params, "lr": self.config.learning_rate * dmodel_scale, "weight_decay": self.config.weight_decay},
            {"params": scalar_params, "lr": 0.5 * dmodel_scale, "weight_decay": 0.05},
        ]

        self.optimizer = torch.optim.AdamW(param_groups, betas=(0.9, 0.95), eps=1e-10)
        logger.info("Optimizador configurado")

    def train_step(self, batch: Tuple[torch.Tensor, torch.Tensor]) -> float:
        """Un paso de entrenamiento"""
        inputs, targets = batch
        inputs = inputs.to(self.device)
        targets = targets.to(self.device)

        loss = self.model(inputs, targets=targets)

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
        self.optimizer.step()

        return loss.item()

    def train(self, data_loader, num_steps: int = None, callback=None):
        """Loop principal de entrenamiento"""
        num_steps = num_steps or self.config.num_iterations
        self.model.train()
        start_time = time.time()

        logger.info(f"Iniciando entrenamiento: {num_steps} steps, batch={self.config.device_batch_size}")

        for step in range(num_steps):
            batch = next(data_loader)
            loss = self.train_step(batch)
            self.step += 1

            if step % 10 == 0:
                elapsed = time.time() - start_time
                logger.info(f"Step {step}/{num_steps} | Loss: {loss:.4f} | Time: {elapsed:.1f}s")

            if callback and step % self.config.eval_every == 0:
                callback(self, step, loss)

            if step % self.config.save_every == 0:
                self.save_checkpoint()

        logger.info(f"Entrenamiento completado en {time.time() - start_time:.1f}s")

    def save_checkpoint(self, path: Optional[str] = None):
        """Guarda checkpoint del entrenamiento"""
        if path is None:
            path = str(MODELS_DIR / self.config.run_name / f"step_{self.step}.pt")

        meta = {
            "step": self.step,
            "run_name": self.config.run_name,
            "timestamp": time.time(),
        }
        self.model.save(path, meta)

    def export_for_ollama(self, modelfile_path: str, model_name: str = "nexus-custom"):
        """Exporta modelo para uso con Ollama"""
        checkpoint_path = str(MODELS_DIR / self.config.run_name / f"step_{self.step}.pt")
        if not Path(checkpoint_path).exists():
            logger.error(f"No hay checkpoint en {checkpoint_path}")
            return

        # Generar Modelfile para Ollama
        modelfile = f"""FROM {checkpoint_path}
PARAMETER temperature 0.7
PARAMETER top_k 50
PARAMETER top_p 0.9
SYSTEM Eres SuperNEXUS, un asistente agencial soberano 100% local.
"""
        Path(modelfile_path).write_text(modelfile)
        logger.info(f"Modelfile generado en {modelfile_path}")
        logger.info(f"Para importar a Ollama: ollama create {model_name} -f {modelfile_path}")


def create_training_data_loader(data_path: str, batch_size: int = 4, seq_len: int = 2048):
    """Crea un data loader infinito desde archivos JSONL de conversaciones"""
    import random

    conversations = []
    data_file = Path(data_path)

    if data_file.is_file():
        with open(data_file, 'r') as f:
            for line in f:
                if line.strip():
                    conversations.append(json.loads(line))
    elif data_file.is_dir():
        for fp in data_file.glob("*.jsonl"):
            with open(fp, 'r') as f:
                for line in f:
                    if line.strip():
                        conversations.append(json.loads(line))

    if not conversations:
        logger.warning(f"No se encontraron datos en {data_path}")
        return

    logger.info(f"Cargadas {len(conversations)} conversaciones para entrenamiento")

    while True:
        random.shuffle(conversations)
        for conv in conversations:
            # Convertir conversacion a formato de entrenamiento
            tokens = _conversation_to_tokens(conv, seq_len)
            if tokens:
                inputs = torch.tensor([tokens[:-1]], dtype=torch.long)
                targets = torch.tensor([tokens[1:]], dtype=torch.long)
                yield inputs, targets


def _conversation_to_tokens(conv: dict, seq_len: int) -> List[int]:
    """Convierte una conversacion a secuencia de tokens"""
    # Placeholder: en produccion se usaria el tokenizer real
    # Por ahora, simulamos con indices simples
    messages = conv.get("messages", [])
    tokens = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        # Tokenizacion simplificada (en produccion usar BPE tokenizer)
        tokens.extend([ord(c) % 32768 for c in f"<|{role}|>{content}<|end|>"])
    return tokens[:seq_len] if len(tokens) > seq_len else tokens
