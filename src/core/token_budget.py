"""
Token Budget Enforcement — F5

Hard cap on token spend per team run with alerts.
Applies globally: Director, Ollama, API, and all agents.
"""

import logging
import time
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("nexus-budget")


@dataclass
class BudgetConfig:
    max_tokens_per_run: int = 50000
    max_tokens_per_message: int = 8000
    max_tokens_per_hour: int = 200000
    alert_threshold: float = 0.8
    hard_cap: bool = True


@dataclass
class BudgetState:
    run_id: str = ""
    tokens_this_run: int = 0
    tokens_this_hour: int = 0
    messages_this_run: int = 0
    run_start: float = 0.0
    hour_start: float = 0.0
    alerts_sent: List[str] = field(default_factory=list)
    hard_cap_triggered: bool = False

    def __post_init__(self):
        now = time.time()
        if not self.run_start:
            self.run_start = now
        if not self.hour_start:
            self.hour_start = now


class TokenBudget:
    """Enforces token budget across the entire system"""

    def __init__(self, config: Optional[BudgetConfig] = None):
        self.config = config or BudgetConfig()
        self.state = BudgetState(run_id=datetime.now().strftime("%Y%m%d_%H%M%S"))
        self._callbacks: List[Callable] = []

    def register_alert_callback(self, callback: Callable):
        self._callbacks.append(callback)

    def _send_alert(self, alert_type: str, message: str):
        if alert_type not in self.state.alerts_sent:
            self.state.alerts_sent.append(alert_type)
            logger.warning(f"TOKEN BUDGET ALERT [{alert_type}]: {message}")
            for cb in self._callbacks:
                try:
                    cb(alert_type, message)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")

    def _check_hour_reset(self):
        if time.time() - self.state.hour_start > 3600:
            self.state.tokens_this_hour = 0
            self.state.hour_start = time.time()

    def _check_run_reset(self):
        pass

    def record_tokens(self, tokens: int, source: str = "unknown") -> Dict:
        """Record token usage and check budget"""
        self._check_hour_reset()

        self.state.tokens_this_run += tokens
        self.state.tokens_this_hour += tokens
        self.state.messages_this_run += 1

        run_pct = self.state.tokens_this_run / self.config.max_tokens_per_run
        hour_pct = self.state.tokens_this_hour / self.config.max_tokens_per_hour

        # Alert thresholds
        if run_pct >= self.config.alert_threshold and "run_80" not in self.state.alerts_sent:
            self._send_alert("run_80", f"Run at {run_pct*100:.0f}% of budget ({self.state.tokens_this_run}/{self.config.max_tokens_per_run})")

        if hour_pct >= self.config.alert_threshold and "hour_80" not in self.state.alerts_sent:
            self._send_alert("hour_80", f"Hour at {hour_pct*100:.0f}% of budget ({self.state.tokens_this_hour}/{self.config.max_tokens_per_hour})")

        # Hard cap enforcement
        if self.config.hard_cap:
            if self.state.tokens_this_run >= self.config.max_tokens_per_run:
                self.state.hard_cap_triggered = True
                self._send_alert("run_cap", f"Run token cap reached ({self.state.tokens_this_run})")
                return {
                    "allowed": False,
                    "reason": "run_token_cap_exceeded",
                    "tokens_used": self.state.tokens_this_run,
                    "limit": self.config.max_tokens_per_run,
                }

            if self.state.tokens_this_hour >= self.config.max_tokens_per_hour:
                self._send_alert("hour_cap", f"Hourly token cap reached ({self.state.tokens_this_hour})")
                return {
                    "allowed": False,
                    "reason": "hourly_token_cap_exceeded",
                    "tokens_used": self.state.tokens_this_hour,
                    "limit": self.config.max_tokens_per_hour,
                }

            if tokens > self.config.max_tokens_per_message:
                return {
                    "allowed": False,
                    "reason": "message_token_limit_exceeded",
                    "tokens": tokens,
                    "limit": self.config.max_tokens_per_message,
                }

        return {
            "allowed": True,
            "tokens_recorded": tokens,
            "run_total": self.state.tokens_this_run,
            "run_remaining": self.config.max_tokens_per_run - self.state.tokens_this_run,
            "run_percent": round(run_pct * 100, 1),
            "hour_total": self.state.tokens_this_hour,
            "hour_remaining": self.config.max_tokens_per_hour - self.state.tokens_this_hour,
        }

    def is_within_budget(self) -> bool:
        return not self.state.hard_cap_triggered

    def get_status(self) -> Dict:
        run_pct = (self.state.tokens_this_run / max(self.config.max_tokens_per_run, 1)) * 100
        hour_pct = (self.state.tokens_this_hour / max(self.config.max_tokens_per_hour, 1)) * 100
        return {
            "run_id": self.state.run_id,
            "tokens_this_run": self.state.tokens_this_run,
            "max_tokens_per_run": self.config.max_tokens_per_run,
            "run_percent": round(run_pct, 1),
            "tokens_this_hour": self.state.tokens_this_hour,
            "max_tokens_per_hour": self.config.max_tokens_per_hour,
            "hour_percent": round(hour_pct, 1),
            "messages_this_run": self.state.messages_this_run,
            "hard_cap_triggered": self.state.hard_cap_triggered,
            "alerts_sent": self.state.alerts_sent,
        }

    def reset_run(self):
        self.state = BudgetState(run_id=datetime.now().strftime("%Y%m%d_%H%M%S"))
        logger.info(f"Token budget reset. New run: {self.state.run_id}")

    def configure(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Budget config updated: {key} = {value}")
