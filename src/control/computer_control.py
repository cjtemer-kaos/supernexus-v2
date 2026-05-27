"""
Computer Control System - Async version para SuperNEXUS v2
Maneja mouse, teclado, screenshots y automatizacion
"""

import asyncio
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    pyautogui.FAILSAFE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui no disponible (entorno sin GUI)")

    class _MockPyAutoGUI:
        def __getattr__(self, name):
            def mock_fn(*args, **kwargs):
                logger.warning(f"Simulando pyautogui.{name} (sin GUI)")
                return None
            return mock_fn
    pyautogui = _MockPyAutoGUI()


class ComputerControl:
    """Control autonomo de PC con soporte async"""

    def __init__(self, screenshot_dir: str = None):
        if screenshot_dir:
            self.screenshot_dir = Path(screenshot_dir)
        elif os.name == 'nt':
            self.screenshot_dir = Path(os.getenv("NEXUS_SCREENSHOT_DIR", Path.cwd() / "screenshots"))
        else:
            self.screenshot_dir = Path(os.getenv("NEXUS_SCREENSHOT_DIR", Path.home() / "ias" / "screenshots"))
        self.screenshot_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"ComputerControl initialized (screenshots: {self.screenshot_dir})")

    def _require_gui(self) -> bool:
        if not PYAUTOGUI_AVAILABLE:
            logger.error("pyautogui no disponible")
            return False
        return True

    async def mouse_click(self, x: int, y: int, button: str = 'left', clicks: int = 1) -> bool:
        if not self._require_gui():
            return False
        await asyncio.to_thread(pyautogui.click, x, y, button=button, clicks=clicks)
        logger.info(f"Mouse click at ({x},{y}) button={button} clicks={clicks}")
        return True

    async def mouse_move(self, x: int, y: int, duration: float = 0.5) -> bool:
        if not self._require_gui():
            return False
        await asyncio.to_thread(pyautogui.moveTo, x, y, duration=duration)
        logger.info(f"Mouse moved to ({x},{y})")
        return True

    async def type_text(self, text: str, interval: float = 0.05) -> bool:
        if not self._require_gui():
            return False
        await asyncio.to_thread(pyautogui.typewrite, text, interval=interval)
        logger.info(f"Typed: {text[:50]}...")
        return True

    async def key_press(self, key: str, presses: int = 1, interval: float = 0.1) -> bool:
        if not self._require_gui():
            return False
        await asyncio.to_thread(pyautogui.press, key, presses=presses, interval=interval)
        logger.info(f"Key pressed: {key}")
        return True

    async def key_combination(self, *keys) -> bool:
        if not self._require_gui():
            return False
        await asyncio.to_thread(pyautogui.hotkey, *keys)
        logger.info(f"Key combination: {'+'.join(keys)}")
        return True

    async def screenshot(self, filename: str = None) -> Optional[Path]:
        if not self._require_gui():
            return None
        if filename is None:
            filename = f"screenshot_{int(time.time())}.png"
        filepath = self.screenshot_dir / filename
        img = await asyncio.to_thread(pyautogui.screenshot)
        await asyncio.to_thread(img.save, str(filepath))
        logger.info(f"Screenshot saved: {filepath}")
        return filepath

    async def get_mouse_position(self) -> Optional[Tuple[int, int]]:
        if not self._require_gui():
            return None
        return await asyncio.to_thread(pyautogui.position)

    async def scroll(self, x: int, y: int, clicks: int = 5) -> bool:
        if not self._require_gui():
            return False
        await asyncio.to_thread(pyautogui.moveTo, x, y)
        await asyncio.to_thread(pyautogui.scroll, clicks)
        return True

    async def drag_to(self, x: int, y: int, duration: float = 1.0, button: str = 'left') -> bool:
        if not self._require_gui():
            return False
        await asyncio.to_thread(pyautogui.drag, x, y, duration=duration, button=button)
        return True

    async def read_clipboard(self) -> Optional[str]:
        try:
            import pyperclip
            return await asyncio.to_thread(pyperclip.paste)
        except Exception as e:
            logger.error(f"Clipboard read error: {e}")
            return None

    async def write_clipboard(self, text: str) -> bool:
        try:
            import pyperclip
            await asyncio.to_thread(pyperclip.copy, text)
            return True
        except Exception as e:
            logger.error(f"Clipboard write error: {e}")
            return False

    async def launch_program(self, program_path: str) -> bool:
        try:
            await asyncio.to_thread(subprocess.Popen, program_path)
            logger.info(f"Program launched: {program_path}")
            return True
        except Exception as e:
            logger.error(f"Program launch error: {e}")
            return False

    async def wait(self, seconds: float) -> bool:
        await asyncio.sleep(seconds)
        return True
