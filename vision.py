"""
Pure visual perception. No business logic. Input -> output.
capture / ocr / pixel_diff / is_blank / changed
"""

import base64, hashlib, io, logging, os, re, sys
from typing import Optional

logger = logging.getLogger("vision")
IS_WIN = sys.platform == "win32"

# ── Screenshot ──

def capture(bbox: tuple) -> Optional[object]:
    """Take screenshot of region (left, top, right, bottom). Returns PIL Image."""
    try:
        from PIL import Image
        if IS_WIN:
            from PIL import ImageGrab
            return ImageGrab.grab(bbox=bbox)
        else:
            import subprocess, tempfile
            tmp = tempfile.mktemp(suffix=".png")
            w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
            subprocess.run(["screencapture","-x","-R",f"{bbox[0]},{bbox[1]},{w},{h}",tmp], timeout=5)
            img = Image.open(tmp)
            try: os.remove(tmp)
            except: pass
            return img
    except Exception as e:
        logger.error(f"capture: {e}")
    return None

def hash_img(img) -> str:
    try: return hashlib.md5(img.resize((160,120)).tobytes()).hexdigest()
    except: return ""

def pixel_diff(a, b) -> float:
    """0.0=identical, 1.0=completely different."""
    try:
        import numpy as np
        aa = np.array(a.resize((160,120)).convert("L"), dtype=np.float32)
        bb = np.array(b.resize((160,120)).convert("L"), dtype=np.float32)
        return float(np.abs(aa-bb).mean()/255.0)
    except: return 0.0

def is_blank(img) -> tuple[bool, str]:
    """Check if image is black/white/uniform."""
    try:
        import numpy as np
        arr = np.array(img.convert("L"))
        m, s = arr.mean(), arr.std()
        if m<5: return True, "black"
        if m>250: return True, "white"
        if s<2: return True, "uniform"
        return False, "ok"
    except: return False, "skip"

def to_base64(img) -> str:
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# ── OCR ──

def ocr(img, lang="chi_sim+eng") -> str:
    """Extract all text from image."""
    try:
        import pytesseract
        return pytesseract.image_to_string(img, lang=lang).strip()
    except: return ""

def text_in_image(img, needle: str, threshold: float = 0.3) -> bool:
    """Fuzzy check: does needle text appear in image?"""
    text = ocr(img)
    if not text: return False
    if needle in text: return True
    chunks = [c for c in re.split(r"[,，.。!！?？\s]+", needle) if len(c)>=3]
    if not chunks: return False
    return sum(1 for c in chunks if c in text)/len(chunks) >= threshold

def changed(before, after, threshold: float = 0.005) -> bool:
    """Did the screen change meaningfully?"""
    return pixel_diff(before, after) > threshold
