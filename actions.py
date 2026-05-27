"""
agent-bridge: Pure action module for desktop automation.
Agent-callable. No visual logic. Just keyboard, mouse, window control.

Usage:
    from actions import click, type_text, press_key, activate_window, find_window, get_screen_size
    click(500, 300)
    type_text("Hello")
    press_key("enter")
"""

import logging, os, sys, time
from typing import Optional

logger = logging.getLogger("actions")
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

# ── Mouse ──

def click(x: int, y: int) -> bool:
    """Click at screen coordinates. Returns True on success."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.click(x, y)
        return True
    except Exception as e:
        logger.error(f"click({x},{y}): {e}")
        return False

def move(x: int, y: int) -> bool:
    try:
        import pyautogui; pyautogui.FAILSAFE = True; pyautogui.moveTo(x, y); return True
    except: return False

def get_position() -> tuple[int, int]:
    try:
        import pyautogui; return pyautogui.position()
    except: return (0, 0)

def get_screen_size() -> tuple[int, int]:
    try:
        import pyautogui; s = pyautogui.size(); return (s.width, s.height)
    except: return (1920, 1080)

# ── Keyboard ──

def type_text(text: str, interval: float = 0.03) -> bool:
    """Type text character by character."""
    try:
        import pyautogui; pyautogui.FAILSAFE = True
        pyautogui.write(text, interval=interval)
        return True
    except Exception as e:
        logger.error(f"type_text: {e}")
        return False

def press_key(key: str) -> bool:
    """Press a single key. e.g. 'enter', 'tab', 'esc'."""
    try:
        import pyautogui; pyautogui.FAILSAFE = True; pyautogui.press(key); return True
    except: return False

def hotkey(*keys: str) -> bool:
    """Press key combination. e.g. hotkey('ctrl', 'a'), hotkey('command', 'v')."""
    try:
        import pyautogui; pyautogui.FAILSAFE = True; pyautogui.hotkey(*keys); return True
    except: return False

# ── Window ──

def find_window(keywords: list[str], process_names: list[str] = None) -> Optional[tuple[int, int, int, int]]:
    """
    Find window by title keywords. Returns (left, top, right, bottom) or None.
    Strategies: title match → process name → fullscreen fallback.
    """
    process_names = process_names or []

    # Strategy 1: title keywords
    if IS_WIN:
        try:
            import pygetwindow as gw
            for w in gw.getWindowsWithTitle(""):
                t = (w.title or "").lower()
                if any(k.lower() in t for k in keywords):
                    return (w.left, w.top, w.right, w.bottom)
        except: pass
    elif IS_MAC:
        try:
            import subprocess
            for kw in keywords:
                s = ('tell application "System Events"\n'
                    ' repeat with p in every process\n  try\n   repeat with w in every window of p\n'
                    f'    if name of w contains "{kw}" then\n'
                    '     set wp to position of w\n     set ws to size of w\n'
                    '     return ((item 1 of wp) as text)&","&((item 2 of wp) as text)&","'
                    '           &((item 1 of wp)+(item 1 of ws))&","&((item 2 of wp)+(item 2 of ws))\n'
                    '    end if\n   end repeat\n  end try\n end repeat\n return ""\nend tell')
                r = subprocess.run(["osascript","-e",s], capture_output=True,text=True,timeout=8)
                o = r.stdout.strip()
                if o and "," in o:
                    p = o.replace(", ",",").split(",")
                    if len(p)==4: return (int(p[0]),int(p[1]),int(p[2]),int(p[3]))
        except: pass

    # Strategy 2: process names
    if process_names:
        if IS_WIN:
            try:
                import pygetwindow as gw
                for w in gw.getAllWindows():
                    t = (w.title or "").lower()
                    if t and any(k.lower() in t for k in process_names+keywords):
                        return (w.left, w.top, w.right, w.bottom)
            except: pass
        elif IS_MAC:
            try:
                import subprocess
                for pn in process_names:
                    s = ('tell application "System Events"\n'
                        f' if exists (first process whose name contains "{pn}") then\n'
                        f'  set frontmost of (first process whose name contains "{pn}") to true\n'
                        '  delay 0.3\n'
                        f'  tell first process whose name contains "{pn}"\n'
                        '   try\n    set wp to position of front window\n    set ws to size of front window\n'
                        '    return ((item 1 of wp) as text)&","&((item 2 of wp) as text)&","'
                        '          &((item 1 of wp)+(item 1 of ws))&","&((item 2 of wp)+(item 2 of ws))\n'
                        '   on error\n    return ""\n   end try\n  end tell\n end if\n return ""\nend tell')
                    r = subprocess.run(["osascript","-e",s], capture_output=True,text=True,timeout=8)
                    o = r.stdout.strip()
                    if o and "," in o:
                        p = o.replace(", ",",").split(",")
                        if len(p)==4: return (int(p[0]),int(p[1]),int(p[2]),int(p[3]))
            except: pass

    # Strategy 3: fullscreen fallback
    try:
        import pyautogui
        w, h = pyautogui.size()
        return (0, 0, w.width if hasattr(w,'width') else w, h.height if hasattr(h,'height') else h)
    except:
        try:
            import pyautogui; w, h = pyautogui.size(); return (0, 0, w, h)
        except: pass

    return None

def activate_window(keywords: list[str], process_names: list[str] = None) -> bool:
    """Bring window to front. Returns True if successful."""
    process_names = process_names or []
    if IS_WIN:
        try:
            import pygetwindow as gw
            for kw in keywords:
                for w in gw.getWindowsWithTitle(""):
                    if kw.lower() in (w.title or "").lower():
                        w.activate(); time.sleep(0.3); return True
        except: pass
    elif IS_MAC:
        try:
            import subprocess
            for pn in process_names:
                s = ('tell application "System Events"\n'
                    f' if exists (first process whose name contains "{pn}") then\n'
                    f'  set frontmost of (first process whose name contains "{pn}") to true\n'
                    '  return "ok"\n end if\n return ""\nend tell')
                r = subprocess.run(["osascript","-e",s], capture_output=True,text=True,timeout=5)
                if "ok" in (r.stdout or ""): time.sleep(0.3); return True
        except: pass
    return False

def validate_rect(rect, min_w: int = 400, min_h: int = 300) -> bool:
    return rect and len(rect)==4 and (rect[2]-rect[0])>=min_w and (rect[3]-rect[1])>=min_h
