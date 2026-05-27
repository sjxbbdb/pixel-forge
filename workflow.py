"""
Verified action pipeline combining vision + actions.
Every step: snap_before -> act -> snap_after -> verify -> OK | retry.

Usage:
    from workflow import Pipeline
    pipe = Pipeline(keywords=["飞鸽","feige"], process_names=["Feige"])
    await pipe.startup()
    changed = await pipe.poll()
    result = await pipe.send_text("hello")
"""

import asyncio, hashlib, logging, random, sys, time
from typing import Optional

from vision import capture, ocr, pixel_diff, is_blank, hash_img, text_in_image
from actions import click, type_text, press_key, hotkey, find_window, activate_window, validate_rect

logger = logging.getLogger("workflow")

class Pipeline:
    """
    Verified desktop pipeline: find window -> activate -> screenshot -> write text.
    Platform-agnostic. Works with any desktop application window.
    """

    def __init__(self,
                 keywords: list[str],
                 process_names: list[str] = None,
                 send_key: str = "enter",
                 poll_interval: float = 3.0,
                 reply_min_delay: float = 2.0):
        self.keywords = keywords
        self.process_names = process_names or []
        self.send_key = send_key
        self.rect = None
        self._prev_hash = ""
        self.poll_interval = poll_interval
        self.reply_min_delay = reply_min_delay

    # ══════════════════════  Startup  ══════════════════════

    async def startup(self, retries: int = 15) -> bool:
        """Find and activate window. Returns True if ready."""
        for _ in range(retries):
            self.rect = find_window(self.keywords, self.process_names)
            if validate_rect(self.rect):
                break
            await asyncio.sleep(2)

        if not validate_rect(self.rect):
            logger.error("Window not found")
            return False

        if not activate_window(self.keywords, self.process_names):
            logger.error("Cannot activate")
            return False

        await asyncio.sleep(0.5)
        img = capture(self.rect)
        if not img or is_blank(img)[0]:
            logger.error("Blank after activation")
            return False

        logger.info(f"Ready, rect={self.rect}")
        return True

    # ══════════════════════  Poll for changes  ══════════════════════

    async def poll(self) -> bool:
        """Check if screen changed. Returns True if something new appeared."""
        if not validate_rect(self.rect):
            self.rect = find_window(self.keywords, self.process_names)
            if not validate_rect(self.rect):
                return False

        img = capture(self.rect)
        if not img or is_blank(img)[0]:
            return False

        h = hash_img(img)
        if h == self._prev_hash and self._prev_hash:
            return False
        self._prev_hash = h
        return True

    async def read_text(self) -> str:
        """OCR current window content. Returns all visible text."""
        if not validate_rect(self.rect):
            return ""
        img = capture(self.rect)
        return ocr(img) if img else ""

    async def read_image(self) -> Optional[object]:
        """Return current screenshot for external analysis."""
        if not validate_rect(self.rect):
            return None
        return capture(self.rect)

    # ══════════════════════  Send text (verified)  ══════════════════════

    async def send_text(self, text: str, delay: float = None) -> dict:
        """
        Type text into the window, send it, verify it appeared.

        Verified steps:
          1. Click input area (5 positions tried)
          2. Select all (Ctrl+A)
          3. Type text
          4. Press send key (Enter / Ctrl+Enter)
          5. Post-send OCR verification

        Returns {"ok": bool, "error": str, "steps": [...]}
        """
        if not validate_rect(self.rect):
            return {"ok": False, "error": "Window invalid"}

        delay = delay or self.reply_min_delay
        await asyncio.sleep(delay + random.uniform(0, 2))

        activate_window(self.keywords, self.process_names)
        await asyncio.sleep(0.3)

        steps = []
        cx = (self.rect[0] + self.rect[2]) // 2

        # Step 1: Click input area
        positions = [
            (self.rect[3]-50, "bottom-50"),
            (self.rect[3]-80, "bottom-80"),
            (self.rect[3]-30, "bottom-30"),
            (self.rect[3]-120, "bottom-120"),
            (self.rect[1] + (self.rect[3]-self.rect[1])*3//4, "lower-quarter"),
        ]
        clicked = False
        for cy, label in positions:
            before = capture(self.rect)
            click(cx, cy)
            await asyncio.sleep(0.3)
            after = capture(self.rect)
            d = pixel_diff(before, after) if before and after else 0
            steps.append({"step":"click", "ok": d>0.005, "diff":round(d,4), "strategy":label})
            if d > 0.005:
                clicked = True; break

        if not clicked:
            return {"ok": False, "error": "Click failed", "steps": steps}

        # Step 2: Select all
        hotkey("ctrl", "a") if sys.platform=="win32" else hotkey("command", "a")
        await asyncio.sleep(0.1)

        # Step 3: Type text
        type_text(text)
        await asyncio.sleep(0.2)
        after = capture(self.rect)
        typed_ok = text_in_image(after, text) if after else False
        steps.append({"step":"type", "ok":typed_ok, "detail":"verified" if typed_ok else "unverified"})

        # Step 4: Send
        await asyncio.sleep(0.2)
        before = capture(self.rect)
        keys_to_try = ["enter", "ctrl+enter", "command+enter"]
        for key in keys_to_try:
            if "+" in key:
                k1, k2 = key.split("+")
                hotkey(k1, k2)
            else:
                press_key(key)
            await asyncio.sleep(0.5)
            after = capture(self.rect)
            if after and is_blank(after)[0]:
                continue
            d = pixel_diff(before, after) if before and after else 0
            steps.append({"step":"send", "ok": d>0.02, "diff":round(d,4), "key":key})
            if d > 0.02:
                # Post-verify
                await asyncio.sleep(1.0)
                post = capture(self.rect)
                if post and text_in_image(post, text):
                    steps.append({"step":"verify", "ok":True, "detail":"confirmed"})
                else:
                    steps.append({"step":"verify", "ok":False, "detail":"not-found"})
                return {"ok": True, "error": "", "steps": steps}

        steps.append({"step":"send", "ok":False, "detail":"all-keys-exhausted"})
        return {"ok": False, "error": "Send failed", "steps": steps}
