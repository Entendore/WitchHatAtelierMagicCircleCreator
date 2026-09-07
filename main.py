#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sigil Atelier — an interactive spellcraft workbench inspired by the
magic system of *Witch Hat Atelier* (Tongari Boushi no Atelier).

Fourth edition: Glaives (quick-cast seal slots), the Toggle sign (spell
pulsing), wheel sigil cycling, ghost-sign hover preview, stroke smoothing
with RDP simplification, sigil path caching, QSettings persistence and
cast statistics — on top of sign rotation, chain casting, practice drills,
undo, PNG export, async sound, the GPU post pipeline and all fallbacks.

Requires:  pip install PySide6
Run:       python sigil_atelier.py
"""

import json
import math
import os
import random
import struct
import sys
import tempfile
import threading
import time
import wave
from dataclasses import dataclass, field

from PySide6.QtCore import (Qt, QElapsedTimer, QPointF, QObject, QSettings,
                            QTimer, QRectF, QUrl, Signal, QByteArray)
from PySide6.QtGui import (QAction, QColor, QFont, QImage, QKeySequence,
                           QShortcut, QPainter, QPainterPath, QPen, QPolygonF,
                           QRadialGradient)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox,
                               QFileDialog, QGridLayout, QGroupBox, QHBoxLayout,
                               QInputDialog, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
                               QPushButton, QSlider, QSplitter, QToolButton,
                               QVBoxLayout, QWidget, QWidgetAction)

try:
    from PySide6.QtMultimedia import QSoundEffect
    HAS_MULTIMEDIA = True
except Exception:
    HAS_MULTIMEDIA = False

try:
    from PySide6.QtGui import QOffscreenSurface, QOpenGLContext, QSurfaceFormat
    from PySide6.QtOpenGL import (QOpenGLFramebufferObject, QOpenGLShader,
                                  QOpenGLShaderProgram, QOpenGLTexture)
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    HAS_GL_MODULES = True
except Exception:
    HAS_GL_MODULES = False

GRIMOIRE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grimoire.json")
SFX_DIR = os.path.join(tempfile.gettempdir(), "sigil_atelier_sfx")
CAST_SECONDS = 3.0
SR = 22050
TICK_MS = 16
IDLE_MS = 120
IDLE_AFTER = 10.0
GLAIVE_COOLDOWN_MS = 1000

class GLC:
    TRIANGLE_STRIP   = 0x0005
    BLEND            = 0x0BE2
    COLOR_BUFFER_BIT = 0x4000
    FLOAT            = 0x1406
    TEXTURE_2D       = 0x0DE1
    TEXTURE0         = 0x84C0
    RENDERER         = 0x1F01
    LINEAR           = 0x2601
    CLAMP_TO_EDGE    = 0x812F
    TEXTURE_MIN_FILTER = 0x2801
    TEXTURE_MAG_FILTER = 0x2800
    TEXTURE_WRAP_S   = 0x2802
    TEXTURE_WRAP_T   = 0x2803
    FRAMEBUFFER      = 0x8D40

# ----------------------------------------------------------------------------
# Lore data
# ----------------------------------------------------------------------------
SIGILS = {
    "FIRE":       {"label": "🔥 Fire",       "noun": "flame",     "color": QColor("#ff7a33")},
    "WATER":      {"label": "💧 Water",      "noun": "water",     "color": QColor("#4fa8ff")},
    "EARTH":      {"label": "⛰ Earth",       "noun": "stone",     "color": QColor("#c8a06a")},
    "WIND":       {"label": "🌪 Wind",       "noun": "gale",      "color": QColor("#9be3d8")},
    "LIGHT":      {"label": "✨ Light",      "noun": "radiance",  "color": QColor("#ffe27a")},
    "SOUND":      {"label": "🔊 Sound",      "noun": "resonance", "color": QColor("#c39bff")},
    "TIME":       {"label": "⏳ Time",       "noun": "temporal ripple", "color": QColor("#5ce8c8")},
    "REPETITION": {"label": "🔁 Repetition", "noun": "echo",      "color": QColor("#ff8f9c")},
}
SIGIL_FLAVOR = {
    "FIRE": "The fire sigil is anchored — the ink warms beneath your hand.",
    "WATER": "The water sigil settles — the lines flow smooth and cool.",
    "EARTH": "The earth sigil takes root — the seal grows heavy and sure.",
    "WIND": "The wind sigil catches — the ink stirs as if breathing.",
    "LIGHT": "The light sigil kindles — faint gold threads through the lines.",
    "SOUND": "The sound sigil hums — the vellum carries a low tone.",
    "TIME": "The time sigil turns — for a moment the ink dries backwards.",
    "REPETITION": "The repetition sigil echoes — each line seems drawn twice.",
}
SIGNS = {
    "LEVITATION": {"label": "Levitation", "phrase": "levitating"},
    "COLUMN":     {"label": "Column",     "phrase": "projected as a jet"},
    "EXPANSION":  {"label": "Expansion",  "phrase": "expanding outward"},
    "ROTATION":   {"label": "Rotation",   "phrase": "spiraling"},
    "INVERSION":  {"label": "Inversion",  "phrase": "inverted"},
    "TOGGLE":     {"label": "Toggle",     "phrase": "pulsing on and off"},
}
FORM_ORDER = ["COLUMN", "LEVITATION", "EXPANSION", "ROTATION", "INVERSION", "TOGGLE"]
SIGN_FLAVOR = {
    "LEVITATION": "A levitation sign — the spell lifts from the page.",
    "COLUMN": "A column sign — the magic will surge in a straight line.",
    "EXPANSION": "An expansion sign — the effect will bloom outward.",
    "ROTATION": "A rotation sign — the spell takes a turning.",
    "INVERSION": "An inversion sign — the effect runs contrary to its nature.",
    "TOGGLE": "A toggle sign — the spell will breathe: on, off, on, off.",
}

HELP_TEXT = """
<h3>The Three Parts of a Seal</h3>
<p><b>Ring</b> — trace it freehand in Ring mode (strokes are smoothed before
grading). A live ghost circle shows your <i>Ring Quality</i> as you draw.</p>
<p><b>Sigil</b> — the heart of the spell. The Primary Tetrad (Fire, Water, Earth,
Wind) plus Light, Sound, Time and Repetition. <i>Scroll the wheel</i> over the
canvas to cycle sigils. Intensity = sigil size = power.</p>
<p><b>Signs</b> — modifiers (levitate, column, expand, rotate, invert,
<b>toggle</b>). A ghost preview follows your cursor in Sign mode. Drag signs to
move them, right-click to erase; spread them evenly — or rotate them — or the
spell <b>drifts</b> where the chevrons point.</p>
<h3>The Toggle Sign</h3>
<p>Lore of <i>spell toggling</i>: a seal that activates and deactivates by
design. With a toggle sign, the magic <b>pulses</b> in waves instead of
streaming — the sigil's glow breathes with the rhythm.</p>
<h3>Glaives (⚔)</h3>
<p>Tools that hold pre-drawn seals. Bind the current seal to one of four glaive
slots (the ⚔ Bind button, or right-click a slot), then cast it instantly any
time with <b>Ctrl+1…4</b> or by clicking the slot. A short cooldown follows
every cast.</p>
<h3>Nested Seals & Practice</h3>
<p>Rings fully inside/outside others: power ×1.25 each (max ×2.0).
🎯 Practice grades your circles (roundness/center/size) with streaks;
the best is remembered between sessions.</p>
<h3>Chain Casting (🔗) & Undo</h3>
<p>Mark grimoire seals with 🔗 Toggle Chain and they cast in sequence.
Ctrl+Z rewinds rings, signs, clears and loads.</p>
<h3>GPU Layer</h3>
<p>Bloom, heat shimmer, ripple, time warp, wind streaks, chromatic aberration,
grain, shake and flash run as GLSL shaders (✧ Effects menu) with a pure-QPainter
fallback. All toggles are remembered.</p>
<h3>Forbidden Magic</h3>
<p><span style="color:#ff6b81"><b>Certain sigils must never be drawn.</b></span>
The atelier will not stop you. It will only watch.</p>
<p><i>Inspired by <b>Witch Hat Atelier</b> by Kamome Shirahama.</i></p>
"""

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def solve3(a, b):
    det = (a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])
         - a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])
         + a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]))
    if abs(det) < 1e-9:
        return None
    def repl(col):
        m = [row[:] for row in a]
        for i in range(3):
            m[i][col] = b[i]
        d = (m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])
           - m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])
           + m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]))
        return d / det
    return repl(0), repl(1), repl(2)

def _precision(pts, cx, cy, r):
    if not pts or r <= 0:
        return 0.0
    res = [abs(math.hypot(p.x()-cx, p.y()-cy) - r) for p in pts]
    rms = math.sqrt(sum(v*v for v in res) / len(res))
    return clamp(1.0 - (rms / r) * 3.0, 0.0, 1.0)

def fit_circle(pts):
    if len(pts) < 3:
        return None
    sx = sy = sxx = syy = sxy = sxz = syz = sz = 0.0
    for p in pts:
        x, y = p.x(), p.y()
        z = x*x + y*y
        sx += x; sy += y; sxx += x*x; syy += y*y
        sxy += x*y; sz += z; sxz += x*z; syz += y*z
    sol = solve3([[sxx, sxy, sx], [sxy, syy, sy], [sx, sy, float(len(pts))]],
                 [sxz, syz, sz])
    if sol is None:
        return None
    d, e, f = sol
    cx, cy = -d / 2.0, -e / 2.0
    rr = cx*cx + cy*cy - f
    if rr <= 1:
        return None
    r = math.sqrt(rr)
    return cx, cy, r, _precision(pts, cx, cy, r)

def smooth_pts(pts, passes=2, win=2):
    """Moving-average smoothing — steadies the hand before grading."""
    for _ in range(passes):
        if len(pts) < 5:
            break
        out = [pts[0]]
        for i in range(1, len(pts)-1):
            a, b = max(0, i-win), min(len(pts), i+win+1)
            n = b - a
            out.append(QPointF(sum(p.x() for p in pts[a:b])/n,
                               sum(p.y() for p in pts[a:b])/n))
        out.append(pts[-1])
        pts = out
    return pts

def rdp_points(pts, eps=0.7):
    """Ramer–Douglas–Peucker simplification — smaller storage, cheaper paints."""
    if len(pts) < 3:
        return pts
    keep = [False]*len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts)-1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        ax, ay = pts[i].x(), pts[i].y()
        bx, by = pts[j].x(), pts[j].y()
        dx, dy = bx-ax, by-ay
        L = math.hypot(dx, dy) or 1e-9
        best, bd = -1, -1.0
        for k in range(i+1, j):
            px, py = pts[k].x(), pts[k].y()
            d = abs((px-ax)*dy - (py-ay)*dx) / L
            if d > bd:
                bd, best = d, k
        if bd > eps:
            keep[best] = True
            stack.append((i, best))
            stack.append((best, j))
    return [p for p, f in zip(pts, keep) if f]

def compass_word(ang):
    dirs = ("east", "southeast", "south", "southwest", "west", "northwest", "north", "northeast")
    k = int(((ang + math.pi/8) % (2*math.pi)) // (math.pi/4))
    return dirs[k % 8]

def lerp_color(c1, c2, t):
    return QColor(int(c1.red()+(c2.red()-c1.red())*t),
                  int(c1.green()+(c2.green()-c1.green())*t),
                  int(c1.blue()+(c2.blue()-c1.blue())*t))

def rune_segs():
    segs = []
    for _ in range(random.randint(3, 4)):
        x1, y1 = random.uniform(-1, 0.2), random.uniform(-1, 1)
        segs.append((x1, y1, x1 + random.uniform(0.3, 0.8), y1 + random.uniform(-0.5, 0.5)))
    return segs

def app_font_family():
    return QApplication.font().family() or "Sans Serif"

# ----------------------------------------------------------------------------
# Procedural sound synthesis (stdlib WAV) — built on a background thread
# ----------------------------------------------------------------------------
def _save_wav(name, gen):
    path = os.path.join(SFX_DIR, name + ".wav")
    try:
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes(b"".join(
                struct.pack("<h", int(max(-1.0, min(1.0, s)) * 30000)) for s in gen()))
    except Exception:
        return None
    return path

def _g_fire():
    n = int(SR * 1.3); lp = 0.0; crack = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        lp += 0.10 * (x - lp)
        if random.random() < 0.012:
            crack = 1.0
        crack *= 0.82
        rumble = 0.55 * math.sin(2*math.pi*52*t) * math.exp(-1.5*t)
        env = min(1.0, t/0.02) * math.exp(-1.1*t)
        yield (lp*1.5 + crack*x*1.2 + rumble) * env * 0.85

def _g_water():
    n = int(SR * 1.2); l1 = l2 = 0.0
    bph = 0.0; bamp = 0.0; bf = 400.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        l1 += 0.30*(x-l1); l2 += 0.06*(x-l2)
        if random.random() < 0.008:
            bamp = 0.5; bf = 250 + random.random()*500
        bamp *= 0.97
        bph += 2*math.pi*bf/SR
        bub = math.sin(bph) * bamp
        sweep = 0.35 * math.sin(2*math.pi*(900*t - 380*t*t))
        env = min(1.0, t/0.02) * math.exp(-1.8*t)
        yield ((l1-l2)*1.6 + sweep*0.4 + bub*0.7) * env * 0.8

def _g_wind():
    n = int(SR * 1.5); l1 = l2 = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        l1 += 0.045*(x-l1); l2 += 0.012*(x-l2)
        lfo = 0.5 + 0.5*math.sin(2*math.pi*0.7*t + 1.5*math.sin(2*math.pi*0.21*t))
        env = min(1.0, t/0.35) * math.exp(-0.9*max(0.0, t-0.9))
        yield (l1-l2)*3.0 * lfo * env * 0.9

def _g_earth():
    n = int(SR * 0.8)
    for i in range(n):
        t = i / SR
        s = math.sin(2*math.pi*58*t) * math.exp(-9*t) * 0.95
        if t > 0.16:
            s += math.sin(2*math.pi*58*t) * math.exp(-9*(t-0.16)) * 0.7
        if t < 0.012:
            s += random.uniform(-1, 1) * 0.6 * (1 - t/0.012)
        yield s

def _g_light():
    notes = ((0.00, 523), (0.09, 659), (0.18, 784), (0.30, 1047))
    n = int(SR * 1.1)
    for i in range(n):
        t = i / SR
        s = random.uniform(-1, 1) * 0.02
        for t0, f in notes:
            if t >= t0:
                s += math.sin(2*math.pi*f*(t-t0)) * math.exp(-3.5*(t-t0)) * 0.4
        yield s * min(1.0, t/0.01) * math.exp(-0.4*t)

def _g_sound():
    n = int(SR * 1.0)
    for i in range(n):
        t = i / SR
        vm = 0.04 * math.sin(2*math.pi*5*t)
        s = (math.sin(2*math.pi*220*t + vm*0.5)*0.16 + math.sin(2*math.pi*440*t + vm)*0.28
             + math.sin(2*math.pi*554*t + vm*1.26)*0.2 + math.sin(2*math.pi*660*t + vm*1.5)*0.2)
        yield s * min(1.0, t/0.03) * math.exp(-1.3*t)

def _g_time():
    n = int(SR * 1.2); ph = 0.0
    for i in range(n):
        t = i / SR
        f = 900 - (650/0.6)*t if t < 0.6 else 250 + (950/0.6)*(t-0.6)
        ph += 2*math.pi*f/SR
        s = math.sin(ph) * 0.5
        for tk in (0.15, 0.45, 0.75, 1.05):
            if 0 <= t-tk < 0.03:
                s += math.sin(2*math.pi*1500*(t-tk)) * 0.35 * math.exp(-90*(t-tk))
        yield s * min(1.0, t/0.02) * math.exp(-0.5*t)

def _g_repetition():
    starts = ((0.00, 0.5), (0.14, 0.22), (0.28, 0.5), (0.42, 0.22), (0.56, 0.5), (0.70, 0.22))
    n = int(SR * 1.0)
    for i in range(n):
        t = i / SR
        s = 0.0
        for t0, a in starts:
            if t >= t0:
                tau = t - t0
                s += (math.sin(2*math.pi*660*tau) + 0.35*math.sin(2*math.pi*1320*tau)) \
                     * a * math.exp(-7*tau) * 0.4
        yield s * min(1.0, t/0.005)

def _g_forbidden():
    n = int(SR * 1.7); lp = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        lp += 0.05 * (x - lp)
        s = 0.0
        for f in (55.0, 57.5, 110.0, 116.0, 220.0, 233.0):
            s += math.sin(2*math.pi*f*t) * 0.15
        s += math.sin(2*math.pi*36*t) * 0.28
        env = min(1.0, t/0.25)
        if t > 1.05:
            env *= math.exp(-2.2*(t-1.05))
        lfo = 0.85 + 0.15*math.sin(2*math.pi*4*t)
        yield (s + lp*0.5) * env * lfo * 0.75

def _g_sign():
    n = int(SR * 0.09)
    for i in range(n):
        t = i / SR
        yield (math.sin(2*math.pi*950*t)*math.exp(-40*t)
               + random.uniform(-1, 1)*0.2*math.exp(-60*t))

def _g_ring():
    n = int(SR * 0.20); l1 = l2 = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        l1 += 0.35*(x-l1); l2 += 0.08*(x-l2)
        amp = 0.35 + 0.65*abs(math.sin(2*math.pi*21*t))
        env = min(1.0, t/0.01, max(0.0, (0.20-t)/0.05))
        yield (l1-l2)*4.0 * amp * env * 0.6

def _g_success():
    notes = ((0.00, 660, 0.5), (0.13, 880, 0.45))
    n = int(SR * 0.8)
    for i in range(n):
        t = i / SR
        s = 0.0
        for t0, f, a in notes:
            if t >= t0:
                tau = t - t0
                s += (math.sin(2*math.pi*f*tau) + 0.4*math.sin(2*math.pi*2*f*tau)
                      + 0.2*math.sin(2*math.pi*2.99*f*tau)) * a * math.exp(-4*tau)
        yield s * 0.6

def _g_fail():
    n = int(SR * 0.5); ph = 0.0; lp = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        lp += 0.12*(x-lp)
        f = 120*(1 - 0.35*t)
        ph += 2*math.pi*f/SR
        yield (math.sin(ph)*0.6 + lp*0.6) * math.exp(-6*t)

def _g_dissolve():
    n = int(SR * 0.5); l1 = l2 = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        l1 += 0.2*(x-l1); l2 += 0.03*(x-l2)
        env = min(1.0, t/0.05) * math.exp(-3.5*t)
        yield (l1-l2)*2.2 * env * 0.5

SFX_GENS = {
    "fire": _g_fire, "water": _g_water, "wind": _g_wind, "earth": _g_earth,
    "light": _g_light, "sound": _g_sound, "time": _g_time, "repetition": _g_repetition,
    "forbidden": _g_forbidden, "sign": _g_sign, "ring": _g_ring,
    "success": _g_success, "fail": _g_fail, "dissolve": _g_dissolve,
}

class SFX(QObject):
    readyChanged = Signal(bool)
    _synthDone = Signal(dict)

    def __init__(self):
        super().__init__()
        self.ok = False
        self.muted = False
        self.volume = 0.55
        self._pool = {}
        if not HAS_MULTIMEDIA:
            return
        self._synthDone.connect(self._build)
        self._thread = threading.Thread(target=self._synthesize, daemon=True)
        self._thread.start()

    def _synthesize(self):
        try:
            os.makedirs(SFX_DIR, exist_ok=True)
            paths = {}
            for name, gen in SFX_GENS.items():
                p = _save_wav(name, gen)
                if p:
                    paths[name] = p
            self._synthDone.emit(paths)
        except Exception:
            self._synthDone.emit({})

    def _build(self, paths):
        for name, path in paths.items():
            try:
                eff = QSoundEffect()
                eff.setSource(QUrl.fromLocalFile(path))
                eff.setVolume(self.volume)
                self._pool[name] = eff
            except Exception:
                pass
        was = self.ok
        self.ok = len(self._pool) == len(SFX_GENS)
        if self.ok != was:
            self.readyChanged.emit(self.ok)

    def play(self, name):
        if self.ok and not self.muted:
            eff = self._pool.get(name)
            if eff:
                eff.play()

    def set_muted(self, m):
        self.muted = bool(m)

    def set_volume(self, v):
        self.volume = clamp(float(v), 0.0, 1.0)
        for eff in self._pool.values():
            eff.setVolume(self.volume)

# ----------------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------------
@dataclass
class Ring:
    pts: list
    cx: float
    cy: float
    r: float
    prec: float

@dataclass
class Sign:
    kind: str
    u: float
    v: float
    rot: float = 0.0

@dataclass
class Particle:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    g: float = 0.0
    life: float = 1.0
    max_life: float = 1.0
    size: float = 3.0
    color: QColor = None
    kind: str = "dot"
    ang: float = 0.0
    rad: float = 0.0
    w: float = 0.0
    vr: float = 0.0
    cx: float = 0.0
    cy: float = 0.0
    rot: float = 0.0
    vrot: float = 0.0
    grow: float = 0.0
    splash: bool = False
    trail: bool = False
    blend: str = "plus"
    segs: list = None
    hist: list = field(default_factory=list)

# ----------------------------------------------------------------------------
# Sigil glyph paths — built centered at the origin and cached
# ----------------------------------------------------------------------------
_PATH_CACHE = {}

def sigil_path(key, R):
    q = max(4.0, round(R * 2.0) / 2.0)
    ck = (key, q)
    hit = _PATH_CACHE.get(ck)
    if hit is not None:
        return hit
    R = q
    path = QPainterPath()
    if key == "FIRE":
        path.moveTo(0, -R)
        path.cubicTo(0.55*R, -0.45*R, 0.62*R, 0.05*R, 0.30*R, 0.55*R)
        path.cubicTo(0.15*R, 0.78*R, -0.15*R, 0.78*R, -0.30*R, 0.55*R)
        path.cubicTo(-0.62*R, 0.05*R, -0.55*R, -0.45*R, 0, -R)
        path.moveTo(0, -0.15*R)
        path.cubicTo(0.28*R, 0.18*R, 0.22*R, 0.42*R, 0, 0.62*R)
        path.cubicTo(-0.22*R, 0.42*R, -0.28*R, 0.18*R, 0, -0.15*R)
    elif key == "WATER":
        for row in (-0.45, 0.0, 0.45):
            pts = []
            for i in range(25):
                t = i / 24.0
                pts.append(QPointF((t*1.4 - 0.7)*R, row*R + math.sin(t*math.pi*3)*0.12*R))
            path.moveTo(pts[0])
            for p in pts[1:]:
                path.lineTo(p)
    elif key == "EARTH":
        s = 0.75*R
        path.addRect(QRectF(-s, -s, 2*s, 2*s))
        d = s * 0.62
        path.moveTo(0, -d); path.lineTo(d, 0)
        path.lineTo(0, d); path.lineTo(-d, 0); path.closeSubpath()
    elif key == "WIND":
        pts = []
        for i in range(120):
            t = i / 119.0
            ang = t * 3.2 * math.pi
            r = R * (0.08 + 0.9*t)
            pts.append(QPointF(math.cos(ang)*r, math.sin(ang)*r))
        path.moveTo(pts[0])
        for p in pts[1:]:
            path.lineTo(p)
    elif key == "LIGHT":
        path.addEllipse(-0.2*R, -0.2*R, 0.4*R, 0.4*R)
        for k in range(8):
            a = math.radians(k * 45)
            path.moveTo(math.cos(a)*0.45*R, math.sin(a)*0.45*R)
            path.lineTo(math.cos(a)*0.95*R, math.sin(a)*0.95*R)
    elif key == "SOUND":
        path.addEllipse(-0.10*R, -0.10*R, 0.2*R, 0.2*R)
        for rr in (0.38, 0.64, 0.92):
            rect = QRectF(-rr*R, -rr*R, 2*rr*R, 2*rr*R)
            path.arcMoveTo(rect, -55)
            path.arcTo(rect, -55, 110)
    elif key == "TIME":
        path.addEllipse(-0.9*R, -0.9*R, 1.8*R, 1.8*R)
        path.moveTo(0, 0); path.lineTo(0, -0.55*R)
        path.moveTo(0, 0); path.lineTo(0.35*R, 0.12*R)
        path.addEllipse(-0.06*R, -0.06*R, 0.12*R, 0.12*R)
    elif key == "REPETITION":
        for a0 in (30, 210):
            rect = QRectF(-0.65*R, -0.65*R, 1.3*R, 1.3*R)
            path.arcMoveTo(rect, a0)
            path.arcTo(rect, a0, 240)
            a_end = math.radians(a0 + 240)
            tx, ty = math.cos(a_end)*0.65*R, math.sin(a_end)*0.65*R
            for sgn in (-1, 1):
                b = a_end + math.pi + sgn*0.5
                path.moveTo(tx, ty)
                path.lineTo(tx + math.cos(b)*0.22*R, ty + math.sin(b)*0.22*R)
    if len(_PATH_CACHE) > 300:
        _PATH_CACHE.clear()
    _PATH_CACHE[ck] = path
    return path

# ----------------------------------------------------------------------------
# The CPU canvas (scene + logic)
# ----------------------------------------------------------------------------
class SigilCanvas(QWidget):
    stateChanged = Signal()
    logged = Signal(str)
    castFinished = Signal()

    def __init__(self, sfx, parent=None):
        super().__init__(parent)
        self.sfx = sfx
        self.setMinimumSize(460, 460)
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.tool = "ring"
        self.pending_sign = "LEVITATION"
        self.pending_rot = 0.0
        self.rings = []
        self.signs = []
        self.sigil = None
        self.intensity = 0.40
        self.forbidden = False
        self.show_guide = True
        # hover ghost
        self.hover_pos = None
        # practice drill
        self.practice = False
        self.practice_target = None
        self.practice_msg = None
        self.practice_msg_until = 0.0
        self.practice_n = 0
        self.practice_streak = 0
        self.practice_best = 0
        # sign dragging
        self.drag_sign = -1
        # effect toggles (scene)
        self.fx_shake = True
        self.fx_glow = True
        self.fx_trails = True
        self.fx_motes = True
        self.fx_vignette = True
        # GPU post toggles
        self.fx_post = True
        self.fx_bloom = True
        self.fx_distort = True
        self.fx_aberr = True
        self.fx_grain = True
        # gpu per-frame parameters
        self.gpu = {"center": (0.5, 0.5), "heat": 0.0, "ripple": 0.0,
                    "warp": 0.0, "wind": 0.0, "aberr": 0.0}
        self._gpu_pass = False
        # fx state
        self.particles = []
        self.bolts = []
        self.rings_fx = []
        self.flashes = []
        self.motes = []
        self.shake = 0.0
        self.ghost_fit = None
        self.casting = False
        self.cast_elapsed = 0.0
        self._stab = 0.8
        self._drift = QPointF(0, 0)
        self._acc = self._ring_acc = self._rep_acc = self._bolt_acc = self._light_acc = 0.0
        self._rep_echo = False
        self.current_stroke = []
        self.selected_sign_index = -1
        self._undo = []
        # stats
        self.stat_casts = 0
        self.stat_good = 0
        self.stat_forbidden = 0
        self._t = 0.0
        self._clock = QElapsedTimer()
        self._clock.start()
        self._last_busy = time.monotonic()
        self._cur_iv = TICK_MS
        self._seed_motes()
        self.cast_timer = QTimer(self)
        self.cast_timer.setInterval(TICK_MS)
        self.cast_timer.timeout.connect(self._tick)
        self.cast_timer.start()

    # ---- timing / wake ------------------------------------------------------
    def _wake(self):
        self._last_busy = time.monotonic()
        if self._cur_iv != TICK_MS:
            self._cur_iv = TICK_MS
            self.cast_timer.setInterval(TICK_MS)

    # ---- undo ---------------------------------------------------------------
    def push_undo(self):
        self._undo.append(self.serialize())
        if len(self._undo) > 50:
            self._undo.pop(0)

    def undo(self):
        if not self._undo:
            self.logged.emit("Nothing to unbind — the vellum holds no earlier truth.")
            return
        self._apply(self._undo.pop(), rescale=False, quiet=True)
        self.sfx.play("dissolve")
        self.logged.emit("You rewind a stroke of the quill.")
        self.update()
        self.stateChanged.emit()

    # ---- sealing helpers ---------------------------------------------------
    def _inner(self):
        return min(self.rings, key=lambda g: g.r)

    def _kinds(self):
        return {s.kind for s in self.signs}

    def validate(self):
        if not self.rings:
            return "The seal fails — you must draw an enclosing RING before casting."
        if not self.sigil:
            return "The seal is hollow — choose a SIGIL to give the spell purpose."
        return None

    def set_practice(self, on):
        self.practice = bool(on)
        if self.practice:
            c = QPointF(self.width()/2, self.height()/2)
            r = 0.30 * min(self.width(), self.height())
            self.practice_target = (c.x(), c.y(), r)
            self.practice_n = 0
            self.practice_streak = 0
            self.logged.emit("🧪 Coach ring set — trace it true. (Esc ends practice)")
        else:
            self.practice_target = None
            self.practice_msg = None
            self.logged.emit(f"Practice ends. Best streak this session: {self.practice_best}.")
        self._wake()
        self.update()
        self.stateChanged.emit()

    def clear_seal(self, quiet=False):
        had = bool(self.rings or self.signs or self.sigil)
        if had:
            self.push_undo()
        if had and not quiet:
            self._dissolve_ink()
            self.sfx.play("dissolve")
        self.rings = []; self.signs = []; self.sigil = None
        self.current_stroke = []; self.ghost_fit = None
        self.selected_sign_index = -1; self.drag_sign = -1
        if not quiet:
            self.logged.emit("You wipe the vellum clean; the ink scatters like ash.")
            self.update()
            self.stateChanged.emit()

    def _dissolve_ink(self):
        n = 0
        for rg in self.rings:
            for p in rg.pts[::3]:
                if n > 260:
                    break
                self.particles.append(Particle(
                    x=p.x(), y=p.y(), vx=random.uniform(-40, 40),
                    vy=random.uniform(-60, 10), g=90,
                    life=random.uniform(0.5, 0.9), size=random.uniform(1.2, 2.6),
                    color=QColor("#efe4c8"), blend="src"))
                n += 1
        if self.rings:
            inner = self._inner()
            for s in self.signs:
                self.particles.append(Particle(
                    x=inner.cx + s.u*inner.r, y=inner.cy + s.v*inner.r,
                    vx=random.uniform(-30, 30), vy=random.uniform(-40, 0), g=80,
                    life=0.7, size=2.2, color=QColor("#e8dcc0"), blend="src"))

    def undo_ring(self):
        if not self.rings:
            self.logged.emit("No ring to unbind.")
            return
        self.push_undo()
        self.rings.pop()
        if self.rings:
            kept = [s for s in self.signs if math.hypot(s.u, s.v) <= 0.95]
            dropped = len(self.signs) - len(kept)
            self.signs = kept
            if dropped:
                self.logged.emit(f"{dropped} sign(s) fell outside the innermost ring and faded.")
        self.sfx.play("sign")
        self._wake()
        self.update()
        self.logged.emit("You wipe away the outermost ring.")
        self.stateChanged.emit()

    def remove_sign(self, i):
        if 0 <= i < len(self.signs):
            self.push_undo()
            self.signs.pop(i)
            self.selected_sign_index = -1; self.drag_sign = -1
            self.sfx.play("sign")
            self._wake()
            self.update()
            self.logged.emit("You scratch the sign from the vellum.")
            self.stateChanged.emit()

    def _sign_at(self, pos):
        if not self.rings:
            return -1
        inner = self._inner()
        for i, s in enumerate(self.signs):
            px, py = inner.cx + s.u*inner.r, inner.cy + s.v*inner.r
            if math.hypot(pos.x()-px, pos.y()-py) < 16:
                return i
        return -1

    def _place_sign(self, pos):
        if not self.rings:
            self.logged.emit("Signs need a ring to live in — draw the ring first.")
            return
        if len(self.signs) >= 8:
            self.logged.emit("Eight signs — no seal can bear more.")
            return
        inner = self._inner()
        u = (pos.x() - inner.cx) / inner.r
        v = (pos.y() - inner.cy) / inner.r
        if math.hypot(u, v) > 0.92:
            self.logged.emit("The sign must rest within the innermost ring.")
            return
        self.push_undo()
        self.signs.append(Sign(self.pending_sign, u, v, self.pending_rot))
        self.selected_sign_index = len(self.signs) - 1
        self.sfx.play("sign")
        self.rings_fx.append({"c": QPointF(pos), "r": 3.0, "vr": 90.0, "life": 0.8,
                              "color": QColor("#e8dcc0")})
        self._wake()
        self.update()
        self.logged.emit(SIGN_FLAVOR[self.pending_sign] +
                         (f"  (rotated {int(round(self.pending_rot))}°)" if abs(self.pending_rot) >= 1 else ""))
        self.stateChanged.emit()

    def _finalize_ring(self):
        pts, self.current_stroke = self.current_stroke, []
        self.ghost_fit = None
        if len(pts) < 12:
            if pts:
                self.logged.emit("A mere dab of ink — drag to draw a full ring.")
            return
        pts = smooth_pts(pts)                       # steady the hand
        fit = fit_circle(pts)
        if fit is None or fit[2] < 40:
            self.logged.emit("The ring is too small or too crooked to hold ink.")
            return
        ncx, ncy, nr, nprec = fit
        for rg in self.rings:
            d = math.hypot(ncx - rg.cx, ncy - rg.cy)
            inside = d + nr <= rg.r * 0.97
            contains = d + rg.r <= nr * 0.97
            if not (inside or contains):
                self.logged.emit("The rings intersect — the seal collapses into blots. "
                                 "Draw the new ring fully inside or outside the others.")
                return
        if len(self.rings) >= 3:
            self.logged.emit("Three nested rings is the limit of sane witchcraft.")
            return
        if self.practice and self.practice_target:
            tcx, tcy, tr = self.practice_target
            round_s = nprec
            center_s = 1.0 - clamp(math.hypot(ncx-tcx, ncy-tcy) / (tr*0.5), 0, 1)
            radius_s = 1.0 - clamp(abs(nr-tr)/tr * 2.5, 0, 1)
            total = 0.5*round_s + 0.3*center_s + 0.2*radius_s
            self.practice_n += 1
            if total >= 0.75:
                self.practice_streak += 1
                self.practice_best = max(self.practice_best, self.practice_streak)
            else:
                self.practice_streak = 0
            grade = ("Masterful — Qifrey would nod." if total >= 0.9 else
                     "A steady hand." if total >= 0.8 else
                     "Acceptable. Again, smoother." if total >= 0.7 else
                     "The ink forgives… barely." if total >= 0.5 else
                     "Again. Breathe first, then draw.")
            self.practice_msg = (f"Drill {self.practice_n}: {total*100:.0f}% — {grade}   "
                                 f"(streak {self.practice_streak}, best {self.practice_best})")
            self.practice_msg_until = self._t + 3.0
            self.logged.emit("🧪 " + self.practice_msg)
            self.sfx.play("success" if total >= 0.8 else "sign" if total >= 0.5 else "fail")
        self.push_undo()
        self.rings.append(Ring(rdp_points(pts, 0.7), ncx, ncy, nr, nprec))
        self.sfx.play("ring")
        self.rings_fx.append({"c": QPointF(ncx, ncy), "r": nr*0.85, "vr": -nr*0.5,
                              "life": 0.9, "color": QColor("#efe4c8")})
        if nprec < 0.35:
            self.logged.emit("The ring wobbles — a steadier hand would serve the ink better.")
        elif nprec > 0.8 and not self.practice:
            self.logged.emit("A true circle — the ink settles with a satisfied hush.")
        if len(self.rings) > 1:
            mult = min(2.0, 1.0 + 0.25 * (len(self.rings) - 1))
            self.logged.emit(f"Nested seal anchored — power ×{mult:.2f}.")
        kept = [s for s in self.signs if math.hypot(s.u, s.v) <= 0.95]
        dropped = len(self.signs) - len(kept)
        self.signs = kept
        if dropped:
            self.logged.emit(f"{dropped} sign(s) fell outside the innermost ring and faded.")
        self._wake()
        self.update()
        self.stateChanged.emit()

    # ---- analysis -----------------------------------------------------------
    def _eff_angles(self):
        return [(math.atan2(s.v, s.u) + math.radians(s.rot)) % (2*math.pi)
                for s in self.signs]

    def _sign_balance(self):
        n = len(self.signs)
        if n == 0:
            return 1.0, None
        angs = sorted(self._eff_angles())
        if n == 1:
            return 0.45, angs[0]
        gaps = [(angs[(i+1) % n] - angs[i]) % (2*math.pi) for i in range(n)]
        ideal = 2*math.pi / n
        dev = sum(abs(g - ideal) for g in gaps) / (2*math.pi)
        bal = clamp(1.0 - dev * 1.5, 0.0, 1.0)
        sx = sum(math.cos(a) for a in angs)
        sy = sum(math.sin(a) for a in angs)
        dang = math.atan2(sy, sx) if math.hypot(sx, sy) > 1e-6 else None
        return bal, dang

    def _predict(self, stab, drift_word):
        if not self.sigil:
            return "A hollow ring — choose a sigil."
        noun = SIGILS[self.sigil]["noun"]
        kinds = self._kinds()
        form = next((SIGNS[k]["phrase"] for k in FORM_ORDER if k in kinds), "manifestation")
        adj = "steady" if stab >= 0.72 else "flickering" if stab >= 0.45 else "unstable"
        txt = f"A {adj} {form} of {noun}"
        if drift_word:
            txt += f", drifting {drift_word}"
        txt += "."
        if self.forbidden:
            txt = "⚠ Forbidden working — " + txt[0].lower() + txt[1:]
        return txt

    def analyse(self):
        d = {"has_ring": bool(self.rings), "sigil": self.sigil, "forbidden": self.forbidden,
             "nested": len(self.rings), "ring_q": None, "balance": 1.0, "drift_word": None,
             "stability": 0.0, "power": 0.0, "mult": 1.0, "n_signs": len(self.signs),
             "predicted": "—"}
        if not self.rings:
            return d
        ring_q = sum(g.prec for g in self.rings) / len(self.rings)
        bal, dang = self._sign_balance()
        stab = 0.55 * ring_q + 0.45 * bal
        mult = min(2.0, 1.0 + 0.25 * (len(self.rings) - 1))
        power = clamp(self.intensity * 100.0 * mult, 0.0, 100.0)
        word = compass_word(dang) if (self.signs and bal < 0.75 and dang is not None) else None
        d.update(ring_q=ring_q, balance=bal, drift_word=word, stability=stab,
                 power=power, mult=mult, predicted=self._predict(stab, word))
        return d

    # ---- casting -------------------------------------------------------------
    def cast(self):
        if self.casting or self.validate():
            return
        d = self.analyse()
        self._stab = d["stability"]
        angs = self._eff_angles()
        mag = (1.0 - d["balance"]) * (0.9 if d["balance"] < 0.75 else 0.25) * 260.0
        if self.signs:
            vx = sum(math.cos(a) for a in angs)
            vy = sum(math.sin(a) for a in angs)
            ang = math.atan2(vy, vx)
        else:
            ang = None
        self._drift = QPointF(math.cos(ang)*mag, math.sin(ang)*mag) \
            if (ang is not None and d["balance"] < 0.9) else QPointF(0, 0)
        self.particles = []; self.bolts = []; self.rings_fx = []
        self._acc = self._ring_acc = self._rep_acc = self._bolt_acc = self._light_acc = 0.0
        self._rep_echo = False
        self.cast_elapsed = 0.0
        self.casting = True
        inner = self._inner()
        c = QPointF(inner.cx, inner.cy)
        base = QColor("#ff2e55") if self.forbidden else SIGILS[self.sigil]["color"]
        self.flashes.append({"color": QColor(base.red(), base.green(), base.blue()),
                             "a": 0.30 if not self.forbidden else 0.42})
        self.rings_fx.append({"c": c, "r": inner.r*0.2, "vr": inner.r*2.2, "life": 1.0,
                              "color": QColor(base)})
        shake_map = {"EARTH": 7, "WIND": 2.5, "WATER": 1.5, "FIRE": 3}
        self._add_shake(11 if self.forbidden else shake_map.get(self.sigil, 1.5))
        if self.sigil == "WIND" and not self.forbidden:
            for _ in range(4):
                self._add_bolt("WIND", c, inner.r*0.85, inner.r*1.3)
        if self.sigil == "EARTH" and not self.forbidden:
            for _ in range(4):
                self._add_bolt("EARTH", c, inner.r*0.5, inner.r*0.95)
        if self.forbidden:
            for _ in range(6):
                self._add_bolt(None, c, inner.r*0.3, inner.r*1.35)
            self.sfx.play("forbidden")
            self.logged.emit("You trace the forbidden sigil. The ink feels cold. Something answers.")
        else:
            self.sfx.play(self.sigil.lower())
            noun = SIGILS[self.sigil]["noun"]
            self.logged.emit(f"You close the ring and speak the word. {noun.capitalize()} answers!")
        if "TOGGLE" in self._kinds():
            self.logged.emit("The toggle sign shivers — the magic will pulse in waves.")
        self._wake()
        self.stateChanged.emit()

    def _add_shake(self, v):
        if self.fx_shake:
            self.shake = min(14.0, max(self.shake, v))

    def _add_bolt(self, key, c, r0, r1):
        ang = random.uniform(0, 2*math.pi)
        pts = []
        segs = random.randint(6, 9)
        for i in range(segs+1):
            rr = r0 + (r1-r0)*i/segs
            a = ang + (random.uniform(-0.22, 0.22) if 0 < i < segs else 0)
            pts.append(QPointF(c.x()+math.cos(a)*rr, c.y()+math.sin(a)*rr))
        col = {"WIND": QColor("#bff3ea"), "EARTH": QColor("#caa36b")}.get(key, QColor("#b026ff"))
        self.bolts.append({"pts": QPolygonF(pts), "life": 1.0,
                           "decay": random.uniform(2.2, 3.4),
                           "color": col, "w": random.uniform(1.4, 2.4)})

    def _rate(self):
        if self.forbidden:
            return 110
        return {"FIRE": 70, "WATER": 80, "EARTH": 55, "WIND": 60, "LIGHT": 85,
                "SOUND": 30, "TIME": 45, "REPETITION": 40}.get(self.sigil, 60)

    # ---- particle factories ---------------------------------------------------
    def _mk_smoke(self, x, y, col):
        p = Particle(x=x, y=y, vx=random.uniform(-8, 8), vy=-random.uniform(14, 28),
                     life=random.uniform(1.0, 1.5), size=random.uniform(4, 7),
                     grow=random.uniform(16, 30), kind="smoke", blend="src",
                     color=QColor(col))
        p.max_life = p.life
        return p

    def _mk_rune(self, c, R, col):
        a = random.uniform(0, 2*math.pi)
        sp = random.uniform(20, 55)
        p = Particle(x=c.x()+math.cos(a)*R*0.2, y=c.y()+math.sin(a)*R*0.2,
                     vx=math.cos(a)*sp, vy=math.sin(a)*sp - 10,
                     life=random.uniform(0.9, 1.4), size=random.uniform(6, 11),
                     rot=random.uniform(0, 6.28), vrot=random.uniform(-1.6, 1.6),
                     kind="rune", segs=rune_segs(), color=QColor(col))
        p.max_life = p.life
        return p

    def _emit_forbidden(self, c, R):
        a = random.uniform(0, 2*math.pi)
        rr = random.uniform(R*0.9, R*1.6)
        jit = (1.0 - self._stab) * 40
        out = [Particle(
            x=c.x()+math.cos(a)*rr, y=c.y()+math.sin(a)*rr,
            vx=-math.cos(a)*random.uniform(60, 160)+random.uniform(-jit, jit),
            vy=-math.sin(a)*random.uniform(60, 160)+random.uniform(-jit, jit),
            life=random.uniform(0.4, 0.9), size=random.uniform(1.5, 3.5),
            color=QColor(random.choice(("#b026ff", "#ff2e55", "#7a1fa2", "#ff5c8a"))),
            trail=True)]
        if random.random() < 0.10:
            out.append(self._mk_rune(c, R, "#ff2e55"))
        if random.random() < 0.06:
            out.append(self._mk_smoke(c.x()+random.uniform(-0.5, 0.5)*R,
                                      c.y()+random.uniform(-0.5, 0.5)*R,
                                      QColor(40, 18, 60)))
        return out

    def _emit_fire(self, c, R):
        kinds = self._kinds()
        col = QColor(random.choice(("#ffd166", "#ff7a33", "#e63946")))
        if "LEVITATION" in kinds:
            a = random.uniform(0, 2*math.pi)
            rad = random.uniform(R*0.14, R*0.45)
            p = Particle(kind="orbit", cx=c.x(), cy=c.y(), ang=a, rad=rad,
                         w=random.uniform(1.6, 2.8)*random.choice((1, 1, -1)),
                         vr=random.uniform(-8, 8), life=random.uniform(1.0, 1.6),
                         size=random.uniform(2, 4.5), color=col, trail=True)
            p.x, p.y = c.x()+math.cos(a)*rad, c.y()+math.sin(a)*rad
            p.max_life = p.life
            return [p]
        if "COLUMN" in kinds:
            p = Particle(kind="spark", x=c.x()+random.uniform(-4, 4), y=c.y()+R*0.15,
                         vx=random.uniform(-30, 30), vy=-random.uniform(240, 330), g=-30,
                         life=random.uniform(0.6, 1.0), size=random.uniform(2, 4),
                         color=col, trail=True)
            p.max_life = p.life
            return [p]
        p = Particle(x=c.x()+random.uniform(-R*0.25, R*0.25),
                     y=c.y()+random.uniform(-R*0.2, R*0.2),
                     vx=random.uniform(-25, 25), vy=-random.uniform(60, 150), g=-40,
                     life=random.uniform(0.8, 1.4), size=random.uniform(2, 5),
                     color=col, trail=True)
        p.max_life = p.life
        out = [p]
        if random.random() < 0.15:
            out.append(self._mk_smoke(p.x, p.y, QColor(120, 118, 128)))
        return out

    def _emit_water(self, c, R):
        kinds = self._kinds()
        col = QColor(random.choice(("#4fa8ff", "#7cc4ff", "#2f6fd6")))
        if "LEVITATION" in kinds:
            a = random.uniform(0, 2*math.pi)
            rad = random.uniform(R*0.10, R*0.32)
            p = Particle(kind="orbit", cx=c.x(), cy=c.y(), ang=a, rad=rad,
                         w=random.uniform(0.8, 1.6)*random.choice((1, -1)),
                         vr=random.uniform(-4, 4), life=random.uniform(1.0, 1.5),
                         size=random.uniform(2, 4), color=col, trail=True)
            p.x, p.y = c.x()+math.cos(a)*rad, c.y()+math.sin(a)*rad
            p.max_life = p.life
            return [p]
        if "COLUMN" in kinds:
            p = Particle(kind="spark", x=c.x()+random.uniform(-4, 4), y=c.y(),
                         vx=random.uniform(-20, 20), vy=-random.uniform(180, 260), g=240,
                         life=random.uniform(0.8, 1.2), size=random.uniform(1.8, 3.6),
                         color=col, trail=True, splash=True)
            p.max_life = p.life
            return [p]
        p = Particle(kind="dot", x=c.x()+random.uniform(-0.7, 0.7)*R,
                     y=c.y()-R*random.uniform(0.8, 1.2),
                     vx=random.uniform(-10, 10), vy=random.uniform(40, 90), g=160,
                     life=random.uniform(0.9, 1.3), size=random.uniform(1.6, 3),
                     color=col, splash=True)
        p.max_life = p.life
        out = [p]
        if random.random() < 0.2:
            out.append(Particle(x=c.x()+random.uniform(-R*0.5, R*0.5),
                                y=c.y()+random.uniform(0, R*0.5),
                                vy=-random.uniform(15, 30), g=0,
                                life=random.uniform(1.0, 1.5), size=random.uniform(1.2, 2.2),
                                color=QColor("#9fd0ff")))
            out[-1].max_life = out[-1].life
        return out

    def _emit_earth(self, c, R):
        p = Particle(kind="earth", x=c.x()+random.uniform(-R*0.45, R*0.45),
                     y=c.y()-R*random.uniform(0.2, 0.8),
                     vx=random.uniform(-30, 30), vy=random.uniform(-20, 20), g=320,
                     rot=random.uniform(0, 360), vrot=random.uniform(-160, 160),
                     life=random.uniform(0.9, 1.3), size=random.uniform(2, 5),
                     color=QColor(random.choice(("#c8a06a", "#8d774f", "#9aa0a6"))),
                     blend="src")
        p.max_life = p.life
        out = [p]
        if random.random() < 0.15:
            out.append(self._mk_smoke(c.x()+random.uniform(-R*0.4, R*0.4),
                                      c.y()+R*0.45, QColor(150, 132, 104)))
        return out

    def _emit_wind(self, c, R):
        col = QColor(random.choice(("#9be3d8", "#c8f2ec")))
        if random.random() < 0.7:
            a = random.uniform(0, 2*math.pi)
            rad = random.uniform(R*0.25, R*1.0)
            p = Particle(kind="orbit", cx=c.x(), cy=c.y(), ang=a, rad=rad,
                         w=random.uniform(2.4, 4.6), vr=random.uniform(-25, 10),
                         life=random.uniform(1.0, 1.6), size=random.uniform(1.5, 3),
                         color=col, trail=True)
            p.x, p.y = c.x()+math.cos(a)*rad, c.y()+math.sin(a)*rad
        else:
            p = Particle(kind="spark", x=c.x()-R, y=c.y()+random.uniform(-R*0.6, R*0.6),
                         vx=random.uniform(220, 340), vy=random.uniform(-40, 40),
                         life=random.uniform(0.3, 0.45), size=2, color=col, trail=True)
        p.max_life = p.life
        return [p]

    def _emit_light(self, c, R):
        if random.random() < 0.6:
            a = random.uniform(0, 2*math.pi)
            sp = random.uniform(80, 200) * (1.6 if "EXPANSION" in self._kinds() else 1.0)
            p = Particle(kind="spark", x=c.x(), y=c.y(),
                         vx=math.cos(a)*sp, vy=math.sin(a)*sp,
                         life=random.uniform(0.4, 0.9), size=random.uniform(1.5, 3.5),
                         color=QColor(random.choice(("#fff3c4", "#ffe27a", "#ffffff"))),
                         trail=True)
        else:
            a = random.uniform(0, 2*math.pi)
            rr = R * random.uniform(0.25, 0.85)
            p = Particle(kind="star", x=c.x()+math.cos(a)*rr, y=c.y()+math.sin(a)*rr,
                         vx=random.uniform(-10, 10), vy=random.uniform(-16, -4),
                         rot=random.uniform(0, 6.28), vrot=random.uniform(-2.5, 2.5),
                         life=random.uniform(0.8, 1.2), size=random.uniform(3.5, 6),
                         color=QColor(random.choice(("#ffe27a", "#fff3c4"))))
        p.max_life = p.life
        return [p]

    def _emit_sound(self, c, R):
        out = [self._mk_rune(c, R, "#c39bff")]
        if random.random() < 0.5:
            a = random.uniform(0, 2*math.pi)
            out.append(Particle(x=c.x(), y=c.y(),
                                vx=math.cos(a)*random.uniform(30, 70),
                                vy=math.sin(a)*random.uniform(30, 70),
                                life=random.uniform(0.5, 0.9), size=2,
                                color=QColor("#e0c9ff")))
            out[-1].max_life = out[-1].life
        return out

    def _emit_time(self, c, R):
        a = random.uniform(0, 2*math.pi)
        rad = random.uniform(R*0.25, R*0.9)
        p = Particle(kind="orbit", cx=c.x(), cy=c.y(), ang=a, rad=rad,
                     w=-random.uniform(0.9, 1.9), vr=random.uniform(-8, 2),
                     life=random.uniform(1.2, 1.8), size=random.uniform(1.5, 3),
                     color=QColor(random.choice(("#5ce8c8", "#b7fff0"))), trail=True)
        p.x, p.y = c.x()+math.cos(a)*rad, c.y()+math.sin(a)*rad
        p.max_life = p.life
        out = [p]
        if random.random() < 0.18:
            out.append(self._mk_rune(c, R, "#5ce8c8"))
        return out

    def _emit_repetition(self, c, R):
        a = random.uniform(0, 2*math.pi)
        sp = random.uniform(40, 110)
        p = Particle(x=c.x(), y=c.y(), vx=math.cos(a)*sp, vy=math.sin(a)*sp,
                     life=random.uniform(0.4, 0.8), size=random.uniform(1.8, 3.5),
                     color=QColor(random.choice(("#ff8f9c", "#ffc2ca"))))
        p.max_life = p.life
        return [p]

    def _emitter(self):
        if self.forbidden:
            return self._emit_forbidden
        return {"FIRE": self._emit_fire, "WATER": self._emit_water,
                "EARTH": self._emit_earth, "WIND": self._emit_wind,
                "LIGHT": self._emit_light, "SOUND": self._emit_sound,
                "TIME": self._emit_time, "REPETITION": self._emit_repetition,
                }.get(self.sigil, self._emit_light)

    # ---- fx simulation ----------------------------------------------------------
    def _seed_motes(self):
        self.motes = []
        for _ in range(46):
            self.motes.append({
                "x": random.uniform(0, max(1, self.width())),
                "y": random.uniform(0, max(1, self.height())),
                "vx": random.uniform(-6, 6), "vy": random.uniform(-10, -3),
                "s": random.uniform(0.8, 2.2), "ph": random.uniform(0, 6.28)})

    def _update_gpu_fx(self):
        g = self.gpu
        w = max(1.0, float(self.width())); h = max(1.0, float(self.height()))
        if self.rings:
            inner = self._inner()
            g["center"] = (inner.cx / w, inner.cy / h)
        else:
            g["center"] = (0.5, 0.5)
        ramp = 0.0
        live = self.casting and bool(self.rings)
        if live:
            ramp = min(1.0, math.sin(clamp(self.cast_elapsed / CAST_SECONDS, 0.0, 1.0) * math.pi) * 1.7)
        f = self.forbidden
        d = self.fx_distort
        g["heat"] = (0.9 * ramp if (live and self.sigil == "FIRE" and not f) else 0.0) if d else 0.0
        if f and live and d:
            g["heat"] = max(g["heat"], 0.5 + 0.5 * ramp)
        g["ripple"] = (0.85 * ramp if (live and self.sigil == "WATER" and not f) else 0.0) if d else 0.0
        g["warp"]   = (0.75 * ramp if (live and self.sigil == "TIME" and not f) else 0.0) if d else 0.0
        g["wind"]   = (0.90 * ramp if (live and self.sigil == "WIND" and not f) else 0.0) if d else 0.0
        g["aberr"]  = (0.004 + 0.02 * ramp) if (f and self.fx_aberr) else 0.0

    def _spawn(self, dt):
        # spell toggling: emission pulses on/off in waves
        if "TOGGLE" in self._kinds() and \
           math.sin(2*math.pi*self.cast_elapsed*1.8) <= 0:
            return
        inner = self._inner()
        c = QPointF(inner.cx, inner.cy)
        emit = self._emitter()
        self._acc += self._rate() * dt
        while self._acc >= 1:
            self._acc -= 1
            if len(self.particles) < 900:
                for p in emit(c, inner.r):
                    self.particles.append(p)
        if self.sigil == "SOUND" and not self.forbidden:
            self._ring_acc += dt
            if self._ring_acc >= 0.33:
                self._ring_acc = 0.0
                self.rings_fx.append({"c": c, "r": 6.0, "vr": 170.0, "life": 1.0,
                                      "color": QColor("#c39bff")})
        if self.sigil == "LIGHT" and not self.forbidden:
            self._light_acc += dt
            if self._light_acc >= 0.5:
                self._light_acc = 0.0
                self.rings_fx.append({"c": c, "r": inner.r*0.15, "vr": inner.r*0.9,
                                      "life": 1.0, "color": QColor("#ffe27a")})
        if self.sigil == "REPETITION" and not self.forbidden:
            self._rep_acc += dt
            if self._rep_acc >= 0.4:
                self._rep_acc = 0.0
                for k in range(6):
                    a = math.radians(k*60 + self.cast_elapsed*50)
                    p = Particle(x=c.x()+math.cos(a)*inner.r*0.3,
                                 y=c.y()+math.sin(a)*inner.r*0.3,
                                 vx=math.cos(a)*90, vy=math.sin(a)*90,
                                 life=0.6, size=3, color=QColor("#ff8f9c"))
                    p.max_life = p.life
                    if len(self.particles) < 900:
                        self.particles.append(p)
            if not self._rep_echo and self.cast_elapsed > 0.45:
                self._rep_echo = True
                self.rings_fx.append({"c": c, "r": inner.r*0.5, "vr": inner.r*0.6,
                                      "life": 1.0, "color": QColor("#ff8f9c")})
        self._bolt_acc += dt
        if self.forbidden:
            if self._bolt_acc >= 0.20:
                self._bolt_acc = 0.0
                self._add_bolt(None, c, 12 + self.cast_elapsed*26, inner.r*1.35)
                self._add_shake(2.0)
        elif self.sigil == "WIND":
            if self._bolt_acc >= 0.24:
                self._bolt_acc = 0.0
                self._add_bolt("WIND", c, inner.r*0.85, inner.r*1.25)

    def _update_fx(self, dt):
        alive = []
        births = []
        for p in self.particles:
            if p.kind == "orbit":
                p.ang += p.w * dt
                p.rad += p.vr * dt
                p.x = p.cx + math.cos(p.ang) * p.rad
                p.y = p.cy + math.sin(p.ang) * p.rad
            else:
                p.vy += p.g * dt
                p.x += p.vx * dt
                p.y += p.vy * dt
            p.rot += p.vrot * dt
            p.x += self._drift.x() * dt
            p.y += self._drift.y() * dt
            p.life -= dt
            if self.fx_trails and p.trail:
                p.hist.append((p.x, p.y))
                if len(p.hist) > 7:
                    p.hist.pop(0)
            if p.life > 0:
                alive.append(p)
            elif p.splash:
                for _ in range(2):
                    q = Particle(x=p.x, y=p.y, vx=random.uniform(-30, 30),
                                 vy=-random.uniform(40, 90), g=300,
                                 life=random.uniform(0.25, 0.4),
                                 size=random.uniform(1.2, 2.2),
                                 color=QColor(p.color))
                    q.max_life = q.life
                    births.append(q)
        if births:
            alive.extend(births[:60])
        self.particles = alive[:900]
        for b in self.bolts:
            b["life"] -= b["decay"] * dt
        self.bolts = [b for b in self.bolts if b["life"] > 0]
        for fx in self.rings_fx:
            fx["r"] += fx["vr"] * dt
            fx["life"] -= dt * 0.9
        self.rings_fx = [f for f in self.rings_fx if f["life"] > 0]
        for f in self.flashes:
            f["a"] -= dt * 1.4
        self.flashes = [f for f in self.flashes if f["a"] > 0]

    def _end_burst(self):
        inner = self._inner()
        c = QPointF(inner.cx, inner.cy)
        stab = self._stab
        # statistics
        self.stat_casts += 1
        if self.forbidden:
            self.stat_forbidden += 1
        elif stab >= 0.7:
            self.stat_good += 1
        key = self.sigil if self.sigil in SIGILS else None
        base = QColor("#ff2e55") if self.forbidden else \
            (SIGILS[key]["color"] if key else QColor("#efe4c8"))
        if self.forbidden:
            self.flashes.append({"color": QColor(255, 30, 70), "a": 0.5})
            self._add_shake(9)
            for i in range(50):
                a = random.uniform(0, 2*math.pi)
                sp = random.uniform(60, 300)
                self.particles.append(Particle(
                    x=c.x(), y=c.y(), vx=math.cos(a)*sp, vy=math.sin(a)*sp,
                    life=random.uniform(0.4, 1.0), size=random.uniform(1.5, 4),
                    color=QColor(random.choice(("#b026ff", "#ff2e55", "#ff5c8a"))),
                    trail=True))
            self.sfx.play("fail")
            self.logged.emit("The forbidden seal releases. The ink goes quiet. Too quiet.")
            return
        if stab >= 0.7:
            self.flashes.append({"color": QColor(255, 226, 150), "a": 0.38})
            self.rings_fx.append({"c": c, "r": inner.r*0.3, "vr": inner.r*1.6,
                                  "life": 1.0, "color": QColor(base)})
            for i in range(36):
                a = random.uniform(0, 2*math.pi)
                sp = random.uniform(80, 320)
                self.particles.append(Particle(
                    x=c.x(), y=c.y(), vx=math.cos(a)*sp, vy=math.sin(a)*sp,
                    life=random.uniform(0.4, 0.9), size=random.uniform(1.5, 3.5),
                    color=QColor(base), trail=True))
            self.sfx.play("success")
        elif stab >= 0.45:
            self.flashes.append({"color": QColor(220, 210, 200), "a": 0.16})
            self.rings_fx.append({"c": c, "r": inner.r*0.2, "vr": inner.r*0.8,
                                  "life": 0.8, "color": QColor(base)})
            self.sfx.play("sign")
        else:
            self.flashes.append({"color": QColor(120, 40, 50), "a": 0.28})
            self._add_shake(5)
            for _ in range(12):
                self.particles.append(self._mk_smoke(
                    c.x()+random.uniform(-inner.r*0.4, inner.r*0.4),
                    c.y()+random.uniform(-inner.r*0.3, inner.r*0.3),
                    QColor(110, 105, 115)))
            self.sfx.play("fail")

    def _tick(self):
        dt = clamp(self._clock.restart() / 1000.0, 0.001, 0.05)
        self._t += dt
        self._update_gpu_fx()
        if self.casting:
            self.cast_elapsed += dt
            if self.forbidden:
                self._add_shake(2.2)
            if self.rings:
                self._spawn(dt)
            self._update_fx(dt)
            if self.cast_elapsed >= CAST_SECONDS:
                self.casting = False
                self._end_burst()
                d = self.analyse()
                if not self.forbidden:
                    if d["stability"] >= 0.7:
                        self.logged.emit("The seal holds. The magic settles like dust in lamplight.")
                    elif d["stability"] >= 0.45:
                        self.logged.emit("The spell gutters, but holds its shape… mostly.")
                    else:
                        self.logged.emit("The seal sputters apart — the ink was not kind to you.")
                self.castFinished.emit()
        if self.fx_motes:
            w, h = max(1, self.width()), max(1, self.height())
            for m in self.motes:
                m["x"] = (m["x"] + (m["vx"] + 8*math.sin(self._t*0.6 + m["ph"])) * dt) % w
                m["y"] = (m["y"] + m["vy"] * dt) % h
        self.shake *= 0.88
        if self.shake < 0.05:
            self.shake = 0.0
        if self.practice_msg and self._t > self.practice_msg_until:
            self.practice_msg = None
            self.update()
        busy = bool(self.casting or self.particles or self.bolts or self.rings_fx
                    or self.flashes or self.shake > 0.05 or self.ghost_fit
                    or self.drag_sign >= 0)
        if busy:
            self._last_busy = time.monotonic()
        iv = TICK_MS if (time.monotonic() - self._last_busy) < IDLE_AFTER else IDLE_MS
        if iv != self._cur_iv:
            self._cur_iv = iv
            self.cast_timer.setInterval(iv)
        if busy:
            self.update()

    # ---- input ---------------------------------------------------------------
    def mousePressEvent(self, e):
        self._wake()
        if e.button() == Qt.RightButton and self.rings:
            i = self._sign_at(e.position())
            if i >= 0:
                inner = self._inner()
                s = self.signs[i]
                self.rings_fx.append({"c": QPointF(inner.cx + s.u*inner.r,
                                                   inner.cy + s.v*inner.r),
                                      "r": 3.0, "vr": 90.0, "life": 0.7,
                                      "color": QColor("#ff8f9c")})
                self.remove_sign(i)
            return
        if self.casting or e.button() != Qt.LeftButton:
            return
        if self.tool == "ring":
            self.current_stroke = [e.position()]
            self.ghost_fit = None
        else:
            i = self._sign_at(e.position())
            if i >= 0:
                self.push_undo()
                self.drag_sign = i
                self.selected_sign_index = i
            else:
                self._place_sign(e.position())
        self.update()

    def mouseMoveEvent(self, e):
        self.hover_pos = e.position()
        if self.casting:
            self.update()
            return
        if self.drag_sign >= 0 and self.rings:
            inner = self._inner()
            u = (e.position().x() - inner.cx) / inner.r
            v = (e.position().y() - inner.cy) / inner.r
            d = math.hypot(u, v)
            if d > 0.9:
                u, v = u/d*0.9, v/d*0.9
            self.signs[self.drag_sign].u = u
            self.signs[self.drag_sign].v = v
            self._wake()
            self.update()
            return
        if self.tool == "sign":
            self.update()
            return
        if self.tool != "ring" or not self.current_stroke:
            return
        if math.hypot(e.position().x()-self.current_stroke[-1].x(),
                      e.position().y()-self.current_stroke[-1].y()) > 2.5:
            self.current_stroke.append(e.position())
            if len(self.current_stroke) >= 12:
                self.ghost_fit = fit_circle(self.current_stroke)
            self._wake()
            self.update()

    def mouseReleaseEvent(self, e):
        self._wake()
        if self.drag_sign >= 0:
            self.drag_sign = -1
            self.stateChanged.emit()
            self.update()
            return
        if self.casting or self.tool != "ring" or not self.current_stroke:
            return
        self._finalize_ring()
        self.update()

    def leaveEvent(self, e):
        self.hover_pos = None
        self.update()

    def wheelEvent(self, e):
        """Scroll to cycle sigils."""
        if self.current_stroke or self.casting:
            return
        d = 1 if e.angleDelta().y() > 0 else -1
        keys = list(SIGILS)
        i = keys.index(self.sigil) if self.sigil in SIGILS else -d
        self.sigil = keys[(i + d) % len(keys)]
        self.sfx.play("sign")
        if self.rings:
            inner = self._inner()
            self.rings_fx.append({"c": QPointF(inner.cx, inner.cy), "r": inner.r*0.2,
                                  "vr": inner.r*0.8, "life": 0.6,
                                  "color": QColor(SIGILS[self.sigil]["color"])})
        self._wake()
        self.update()
        self.stateChanged.emit()
        self.logged.emit(SIGIL_FLAVOR[self.sigil])

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            if self.practice:
                self.set_practice(False)
            elif self.current_stroke:
                self.current_stroke = []
                self.ghost_fit = None
                self.update()
        else:
            super().keyPressEvent(e)

    # ---- persistence ----------------------------------------------------------
    def serialize(self):
        return {
            "sigil": self.sigil,
            "forbidden": self.forbidden,
            "intensity": self.intensity,
            "rings": [{"cx": g.cx, "cy": g.cy, "r": g.r,
                       "pts": [[(p.x()-g.cx)/g.r, (p.y()-g.cy)/g.r] for p in g.pts]}
                      for g in self.rings],
            "signs": [{"kind": s.kind, "u": s.u, "v": s.v, "rot": s.rot}
                      for s in self.signs],
        }

    def _apply(self, data, rescale=True, quiet=False):
        self.rings = []; self.signs = []; self.sigil = None
        self.current_stroke = []; self.ghost_fit = None
        self.selected_sign_index = -1; self.drag_sign = -1
        self.sigil = data.get("sigil")
        self.forbidden = bool(data.get("forbidden", False))
        self.intensity = float(data.get("intensity", 0.4))
        rings = data.get("rings") or []
        if rings:
            if rescale:
                outer = max(rings, key=lambda g: g["r"])
                f = (0.35 * min(self.width(), self.height())) / max(outer["r"], 1e-6)
                ocx, ocy = outer["cx"], outer["cy"]
                ccx, ccy = self.width()/2, self.height()/2
            for g in rings:
                if rescale:
                    ncx = ccx + (g["cx"]-ocx) * f
                    ncy = ccy + (g["cy"]-ocy) * f
                    nr = g["r"] * f
                else:
                    ncx, ncy, nr = g["cx"], g["cy"], g["r"]
                pts = [QPointF(ncx + px*nr, ncy + py*nr) for px, py in g["pts"]]
                self.rings.append(Ring(pts, ncx, ncy, nr, _precision(pts, ncx, ncy, nr)))
        for s in data.get("signs", []):
            self.signs.append(Sign(s["kind"], float(s["u"]), float(s["v"]),
                                   float(s.get("rot", 0.0))))
        if not quiet:
            self.sfx.play("ring")
            self._wake()
            self.update()
            self.stateChanged.emit()

    def deserialize(self, data, msg=None):
        self.push_undo()
        self._apply(data, rescale=True, quiet=msg is not None)
        if msg:
            self.sfx.play("ring")
            self._wake()
            self.update()
            self.stateChanged.emit()
            self.logged.emit(msg)

    # ---- painting ---------------------------------------------------------------
    def _draw_particle(self, painter, p):
        frac = clamp(p.life / p.max_life, 0, 1)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver if p.blend == "src"
                                   else QPainter.CompositionMode_Plus)
        col = QColor(p.color)
        col.setAlphaF(clamp(col.alphaF() * frac, 0, 1))
        r = p.size * (0.4 + 0.6*frac)
        if p.kind == "smoke":
            r = p.size + p.grow * (1.0 - frac)
            col.setAlphaF(0.16 * frac)
        if p.trail and self.fx_trails and len(p.hist) > 2 and p.kind != "smoke":
            poly = QPolygonF([QPointF(x, y) for x, y in p.hist] + [QPointF(p.x, p.y)])
            tcol = QColor(p.color)
            tcol.setAlphaF(0.30 * frac)
            painter.setPen(QPen(tcol, max(1.0, p.size*0.5)))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolyline(poly)
        painter.setPen(Qt.NoPen)
        painter.setBrush(col)
        if p.kind == "earth":
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.rot)
            painter.drawRect(QRectF(-r, -r, 2*r, 2*r))
            painter.restore()
        elif p.kind == "star":
            pts = []
            for k in range(8):
                rr = r*1.6 if k % 2 == 0 else r*0.66
                a = p.rot + k*math.pi/4
                pts.append(QPointF(p.x+math.cos(a)*rr, p.y+math.sin(a)*rr))
            painter.drawPolygon(QPolygonF(pts))
        elif p.kind == "rune":
            pen = QPen(col, max(1.0, p.size*0.22))
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(math.degrees(p.rot))
            for x1, y1, x2, y2 in p.segs:
                painter.drawLine(QPointF(x1*p.size, y1*p.size), QPointF(x2*p.size, y2*p.size))
            painter.restore()
        elif p.kind == "spark":
            pen = QPen(col, max(1.2, p.size*0.7))
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(QPointF(p.x - p.vx*0.035, p.y - p.vy*0.035), QPointF(p.x, p.y))
        else:
            if self.fx_glow and p.kind != "smoke":
                halo = QColor(col)
                halo.setAlphaF(col.alphaF() * 0.30)
                painter.setBrush(halo)
                painter.drawEllipse(QPointF(p.x, p.y), r*2.4, r*2.4)
                painter.setBrush(col)
            painter.drawEllipse(QPointF(p.x, p.y), r, r)

    def _draw_sign(self, painter, sign, center, ring_r, selected):
        p = QPointF(center.x() + sign.u*ring_r, center.y() + sign.v*ring_r)
        ang = math.degrees(math.atan2(sign.v, sign.u)) + sign.rot
        s = clamp(ring_r * 0.14, 9, 22)
        painter.save()
        painter.translate(p)
        painter.rotate(ang)
        if selected:
            painter.setPen(QPen(QColor(255, 215, 0, 110), 5))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(0, 0), s*1.7, s*1.7)
        color = QColor("#ff5c7a") if self.forbidden else QColor("#e8dcc0")
        pen = QPen(color, 2.4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        k = sign.kind
        if k == "LEVITATION":
            painter.drawLine(QPointF(-s, 0.5*s), QPointF(0, -0.6*s))
            painter.drawLine(QPointF(0, -0.6*s), QPointF(s, 0.5*s))
            painter.drawLine(QPointF(-s, 1.2*s), QPointF(0, 0.1*s))
            painter.drawLine(QPointF(0, 0.1*s), QPointF(s, 1.2*s))
        elif k == "COLUMN":
            for dx in (-0.5*s, 0.0, 0.5*s):
                painter.drawLine(QPointF(dx, -s), QPointF(dx, 1.2*s))
        elif k == "EXPANSION":
            for ox in (0.0, 0.9*s):
                painter.drawLine(QPointF(ox-0.4*s, -0.7*s), QPointF(ox+0.5*s, 0))
                painter.drawLine(QPointF(ox+0.5*s, 0), QPointF(ox-0.4*s, 0.7*s))
        elif k == "ROTATION":
            painter.drawArc(QRectF(-s, -s, 2*s, 2*s), 30*16, 270*16)
            start = QPointF(math.cos(math.radians(30))*s, -math.sin(math.radians(30))*s)
            painter.drawLine(start, start + QPointF(-s*0.35, -s*0.25))
            painter.drawLine(start, start + QPointF(s*0.10, -s*0.45))
        elif k == "INVERSION":
            painter.drawLine(QPointF(0, -s), QPointF(0, s))
            painter.drawLine(QPointF(-0.45*s, -0.5*s), QPointF(0, -s))
            painter.drawLine(QPointF(0.45*s, -0.5*s), QPointF(0, -s))
            painter.drawLine(QPointF(-0.45*s, 0.5*s), QPointF(0, s))
            painter.drawLine(QPointF(0.45*s, 0.5*s), QPointF(0, s))
        elif k == "TOGGLE":
            painter.drawRoundedRect(QRectF(-0.9*s, -0.6*s, 1.8*s, 1.2*s), 3, 3)
            painter.drawLine(QPointF(-0.5*s, 0.3*s), QPointF(0.45*s, -0.3*s))
            painter.drawEllipse(QPointF(-0.55*s, 0.3*s), 0.14*s, 0.14*s)
            painter.drawEllipse(QPointF(0.55*s, -0.3*s), 0.14*s, 0.14*s)
        painter.restore()

    def paintEvent(self, ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), QColor("#131022"))
        painter.setPen(QPen(QColor(255, 255, 255, 14), 1))
        step = 28
        for gx in range(step, w, step):
            painter.drawLine(gx, 0, gx, h)
        for gy in range(step, h, step):
            painter.drawLine(0, gy, w, gy)

        gpu = bool(getattr(self, "_gpu_pass", False))
        shaking = (not gpu) and self.shake > 0.3 and self.fx_shake
        painter.save()
        if shaking:
            painter.translate(random.uniform(-1, 1)*self.shake,
                              random.uniform(-1, 1)*self.shake)

        if self.show_guide and not self.casting:
            c = QPointF(w/2, h/2)
            r = 0.35 * min(w, h)
            painter.setPen(QPen(QColor(255, 255, 255, 30), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(c, r, r)
            painter.drawEllipse(c, 2.2, 2.2)

        if self.practice and self.practice_target and not self.casting:
            tcx, tcy, tr = self.practice_target
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(212, 176, 106, 170), 2, Qt.DashLine))
            painter.drawEllipse(QPointF(tcx, tcy), tr, tr)
            painter.setPen(QPen(QColor(212, 176, 106, 80), 1))
            painter.drawEllipse(QPointF(tcx, tcy), tr*0.94, tr*0.94)
            painter.drawEllipse(QPointF(tcx, tcy), tr*1.06, tr*1.06)
            painter.setPen(QPen(QColor(212, 176, 106, 170), 1))
            painter.drawEllipse(QPointF(tcx, tcy), 2.2, 2.2)

        ink = QColor("#c04df0") if self.forbidden else QColor("#efe4c8")
        casting = self.casting

        for rg in self.rings:
            if len(rg.pts) >= 2:
                if casting and self.fx_glow:
                    painter.setCompositionMode(QPainter.CompositionMode_Plus)
                    painter.setPen(QPen(QColor(ink.red(), ink.green(), ink.blue(), 46), 8))
                    painter.drawPolyline(QPolygonF(rg.pts))
                    painter.setPen(QPen(QColor(ink.red(), ink.green(), ink.blue(), 90), 4))
                    painter.drawPolyline(QPolygonF(rg.pts))
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                painter.setPen(QPen(ink, 3.0))
                painter.drawPolyline(QPolygonF(rg.pts))
            faint = QColor(ink); faint.setAlpha(48)
            painter.setPen(QPen(faint, 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(rg.cx, rg.cy), rg.r, rg.r)

        if len(self.current_stroke) >= 2:
            painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
            painter.drawPolyline(QPolygonF(self.current_stroke))
        if self.ghost_fit:
            gcx, gcy, gr, gq = self.ghost_fit
            col = lerp_color(QColor(200, 70, 90), QColor(220, 180, 110), gq)
            painter.setPen(QPen(col, 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(gcx, gcy), gr, gr)

        if self.rings:
            inner = self._inner()
            center = QPointF(inner.cx, inner.cy)
            if casting and self.fx_glow:
                painter.setCompositionMode(QPainter.CompositionMode_Plus)
                base = QColor("#ff2e55") if self.forbidden else \
                    (SIGILS[self.sigil]["color"] if self.sigil else QColor("#efe4c8"))
                aura = QColor(base)
                aura.setAlphaF(0.10 + 0.05*math.sin(self.cast_elapsed*8))
                grad = QRadialGradient(center, inner.r*2.4)
                grad.setColorAt(0.0, aura)
                grad.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.setPen(Qt.NoPen)
                painter.setBrush(grad)
                painter.drawRect(self.rect())
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            if self.sigil:
                col = QColor("#ff4d6d") if self.forbidden else SIGILS[self.sigil]["color"]
                R = inner.r * self.intensity
                path = sigil_path(self.sigil, R)
                painter.save()
                painter.translate(center)
                if casting:
                    painter.rotate(math.sin(self.cast_elapsed*3)*4)
                    s = 1 + 0.05*math.sin(self.cast_elapsed*8)
                    painter.scale(s, s)
                if self.forbidden:
                    painter.setCompositionMode(QPainter.CompositionMode_Plus)
                    painter.setPen(QPen(QColor(255, 60, 90, 60), clamp(R*0.22, 4, 10)))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawPath(path)
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                if self.fx_glow:
                    painter.setCompositionMode(QPainter.CompositionMode_Plus)
                    alpha = 150 if casting else 60
                    if casting and "TOGGLE" in self._kinds():
                        alpha = int(alpha * (0.3 + 0.7*max(0.0, math.sin(2*math.pi*self.cast_elapsed*1.8))))
                    gpen = QPen(QColor(col.red(), col.green(), col.blue(), alpha),
                                clamp(R*0.30, 4, 12))
                    gpen.setCapStyle(Qt.RoundCap); gpen.setJoinStyle(Qt.RoundJoin)
                    painter.setPen(gpen); painter.setBrush(Qt.NoBrush)
                    painter.drawPath(path)
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                pen = QPen(col, clamp(R*0.10, 2.0, 5.0))
                pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(pen); painter.setBrush(Qt.NoBrush)
                painter.drawPath(path)
                painter.restore()
            for idx, sgn in enumerate(self.signs):
                self._draw_sign(painter, sgn, center, inner.r, idx == self.selected_sign_index)
            # ghost sign preview at the cursor
            if (self.tool == "sign" and not casting and self.hover_pos
                    and not self.current_stroke):
                u = (self.hover_pos.x() - center.x()) / inner.r
                v = (self.hover_pos.y() - center.y()) / inner.r
                if math.hypot(u, v) <= 0.92:
                    painter.setOpacity(0.45)
                    self._draw_sign(painter, Sign(self.pending_sign, u, v, self.pending_rot),
                                    center, inner.r, False)
                    painter.setOpacity(1.0)

        for p in self.particles:
            self._draw_particle(painter, p)
        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        for b in self.bolts:
            a = clamp(b["life"], 0, 1)
            glow = QColor(b["color"]); glow.setAlphaF(0.35*a)
            painter.setPen(QPen(glow, b["w"]*3.2))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolyline(b["pts"])
            core = QColor(235, 235, 255); core.setAlphaF(0.9*a)
            painter.setPen(QPen(core, b["w"]))
            painter.drawPolyline(b["pts"])
        for fx in self.rings_fx:
            fcol = QColor(fx["color"]); fcol.setAlphaF(0.5 * clamp(fx["life"], 0, 1))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(fcol, 2.5))
            painter.drawEllipse(fx["c"], max(0.5, fx["r"]), max(0.5, fx["r"]))
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        if casting and self.rings:
            inner = self._inner()
            c = QPointF(inner.cx, inner.cy)
            if self.sigil == "TIME" and not self.forbidden:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(92, 232, 200, 180), 2.5))
                a = math.radians(self.cast_elapsed * 140)
                painter.drawEllipse(c, inner.r*0.5, inner.r*0.5)
                painter.drawLine(c, QPointF(c.x()+math.cos(a)*inner.r*0.5,
                                            c.y()+math.sin(a)*inner.r*0.5))
            if self.forbidden:
                rr = (12 + self.cast_elapsed*26) * (1 + 0.06*math.sin(self.cast_elapsed*12))
                painter.setCompositionMode(QPainter.CompositionMode_Plus)
                ogr = QRadialGradient(c, rr*2.0)
                ogr.setColorAt(0.0, QColor(255, 46, 85, 110))
                ogr.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.setPen(Qt.NoPen); painter.setBrush(ogr)
                painter.drawEllipse(c, rr*2.0, rr*2.0)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                painter.setPen(QPen(QColor("#ff2e55"), 2))
                painter.setBrush(QColor(24, 6, 34, 235))
                painter.drawEllipse(c, rr, rr)

        painter.restore()  # end shake

        if self.fx_motes and self.motes:
            painter.setCompositionMode(QPainter.CompositionMode_Plus)
            tint = SIGILS[self.sigil]["color"] if self.sigil else QColor(232, 224, 200)
            painter.setPen(Qt.NoPen)
            for m in self.motes:
                a = 0.10 + 0.10*math.sin(self._t*2 + m["ph"])
                col = QColor(tint.red(), tint.green(), tint.blue(), int(a*255))
                painter.setBrush(col)
                painter.drawEllipse(QPointF(m["x"], m["y"]), m["s"], m["s"])
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        if not gpu:
            for f in self.flashes:
                col = QColor(f["color"])
                col.setAlphaF(clamp(f["a"], 0, 1))
                painter.fillRect(self.rect(), col)
            if self.fx_vignette:
                vg = QRadialGradient(QPointF(w/2, h/2), math.hypot(w, h)*0.6)
                vg.setColorAt(0.55, QColor(0, 0, 0, 0))
                vg.setColorAt(1.0, QColor(5, 3, 12, 120))
                painter.setPen(Qt.NoPen)
                painter.setBrush(vg)
                painter.drawRect(self.rect())

        fam = app_font_family()
        if self.ghost_fit:
            gq = self.ghost_fit[3]
            col = lerp_color(QColor(220, 100, 115), QColor(235, 195, 125), gq)
            painter.setPen(QPen(col))
            painter.setFont(QFont(fam, 11, QFont.Bold))
            painter.drawText(QRectF(14, 10, w-28, 24), Qt.AlignLeft,
                             f"Ring quality {gq*100:.0f}%")
        if self.practice_msg:
            painter.setPen(QPen(QColor(235, 215, 160)))
            painter.setFont(QFont(fam, 11, QFont.Bold))
            painter.drawText(QRectF(0, 34, w, 24), Qt.AlignCenter, self.practice_msg)
        if self.practice:
            painter.setPen(QPen(QColor(160, 150, 190)))
            painter.setFont(QFont(fam, 9))
            painter.drawText(QRectF(0, h-26, w, 20), Qt.AlignCenter,
                             f"Practice  ·  drills {self.practice_n}  ·  "
                             f"streak {self.practice_streak}  ·  best {self.practice_best}")
        painter.end()

# ----------------------------------------------------------------------------
# GLSL shaders
# ----------------------------------------------------------------------------
VS_SRC = """
attribute vec2 aPos;
varying vec2 vUv;
void main(){
    vUv = aPos * 0.5 + vec2(0.5);
    gl_Position = vec4(aPos, 0.0, 1.0);
}
"""

FS_BRIGHT = """
#ifdef GL_ES
precision highp float;
#endif
uniform sampler2D uTex;
uniform float uThresh;
varying vec2 vUv;
void main(){
    vec2 uv = vec2(vUv.x, 1.0 - vUv.y);
    vec3 c = texture2D(uTex, uv).rgb;
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    float k = smoothstep(uThresh, uThresh + 0.28, l);
    gl_FragColor = vec4(c * k, 1.0);
}
"""

FS_BLUR = """
#ifdef GL_ES
precision highp float;
#endif
uniform sampler2D uTex;
uniform vec2 uDir;
varying vec2 vUv;
void main(){
    vec3 s = texture2D(uTex, vUv).rgb * 0.2270270;
    s += (texture2D(uTex, vUv + uDir * 1.3846154).rgb +
          texture2D(uTex, vUv - uDir * 1.3846154).rgb) * 0.3162162;
    s += (texture2D(uTex, vUv + uDir * 3.2307692).rgb +
          texture2D(uTex, vUv - uDir * 3.2307692).rgb) * 0.0702703;
    gl_FragColor = vec4(s, 1.0);
}
"""

FS_COMP = """
#ifdef GL_ES
precision highp float;
#endif
uniform sampler2D uScene;
uniform sampler2D uBloom;
uniform float uTime;
uniform float uBloomAmt;
uniform vec2  uCenter;
uniform float uHeat;
uniform float uRipple;
uniform float uWarp;
uniform float uWind;
uniform float uAberr;
uniform float uGrain;
uniform float uVignette;
uniform vec2  uShake;
uniform vec3  uFlash;
uniform float uFlashA;
varying vec2 vUv;

float hash(vec2 p){
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main(){
    vec2 uv = vUv;
    vec2 suv = vec2(uv.x, 1.0 - uv.y);
    vec2 c = vec2(uCenter.x, 1.0 - uCenter.y);
    vec2 d = suv - c;
    float dist = length(d);
    vec2 dir = dist > 0.0001 ? d / dist : vec2(0.0);
    vec2 off = vec2(0.0);
    float hm = uHeat * smoothstep(0.55, 0.05, dist);
    off += hm * 0.013 * vec2(
        sin(suv.y * 47.0 + uTime * 7.0) + 0.6 * sin(suv.y * 23.0 - uTime * 11.0),
        sin(suv.x * 41.0 - uTime * 6.0) + 0.6 * sin(suv.x * 19.0 + uTime * 9.0));
    float w = sin(dist * 60.0 - uTime * 9.0) * exp(-dist * 3.5);
    off += uRipple * 0.013 * dir * w;
    off += uWarp * 0.010 * vec2(sin(suv.y * 11.0 + uTime * 2.2),
                                cos(suv.x * 9.0 - uTime * 1.7));
    off += uWind * 0.009 * vec2(sin(suv.y * 35.0 + uTime * 14.0), 0.0);
    suv += off + uShake;

    vec3 col;
    if (uAberr > 0.001) {
        vec2 rdir = (suv - vec2(0.5)) * uAberr * 4.0;
        col.r = texture2D(uScene, suv + rdir).r;
        col.g = texture2D(uScene, suv).g;
        col.b = texture2D(uScene, suv - rdir).b;
    } else {
        col = texture2D(uScene, suv).rgb;
    }
    col += texture2D(uBloom, vUv).rgb * uBloomAmt;
    float vd = distance(uv, vec2(0.5));
    col *= 1.0 - uVignette * smoothstep(0.42, 0.95, vd);
    float g = hash(gl_FragCoord.xy + vec2(fract(uTime) * 97.0));
    col += (g - 0.5) * uGrain;
    col = mix(col, uFlash, uFlashA);
    gl_FragColor = vec4(col, 1.0);
}
"""

# ----------------------------------------------------------------------------
# OpenGL probe + canvas factory
# ----------------------------------------------------------------------------
def probe_opengl():
    try:
        ctx = QOpenGLContext()
        fmt = QSurfaceFormat.defaultFormat()
        ctx.setFormat(fmt)
        if not ctx.create() or not ctx.isValid():
            return False
        surf = QOffscreenSurface()
        surf.setFormat(fmt)
        surf.create()
        if not ctx.makeCurrent(surf):
            return False
        ctx.doneCurrent()
        return True
    except Exception:
        return False

def create_canvas(sfx):
    if HAS_GL_MODULES and probe_opengl():
        try:
            return GLSigilCanvas(sfx)
        except Exception:
            pass
    return SigilCanvas(sfx)

if HAS_GL_MODULES:

    class GLSigilCanvas(QOpenGLWidget):
        """GPU post-processing wrapper around a hidden SigilCanvas."""

        _DIRECT = {"scene", "ok", "gl_mode", "gpu_info", "gl", "_img", "_tex",
                   "_f_bright", "_f_a", "_f_b", "_rebuild", "_quad", "_progs"}

        def __init__(self, sfx, parent=None):
            super().__init__(parent)
            self.scene = SigilCanvas(sfx)
            self.scene.update = self.update
            self.scene.setMinimumSize(460, 460)
            self.setMinimumSize(460, 460)
            self.setMouseTracking(True)
            self.setFocusPolicy(Qt.StrongFocus)
            self.ok = True
            self.gl_mode = "gpu"
            self.gpu_info = ""
            self.gl = None
            self._img = None
            self._tex = None
            self._f_bright = None
            self._f_a = None
            self._f_b = None
            self._rebuild = True
            self._quad = struct.pack("8f", -1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0)
            self._progs = {}

        def __getattr__(self, name):
            if name == "scene":
                raise AttributeError(name)
            scene = self.__dict__.get("scene")
            if scene is None:
                raise AttributeError(name)
            return getattr(scene, name)

        def __setattr__(self, name, value):
            if name in GLSigilCanvas._DIRECT or hasattr(GLSigilCanvas, name):
                object.__setattr__(self, name, value)
            else:
                scene = self.__dict__.get("scene")
                if scene is not None:
                    setattr(scene, name, value)
                else:
                    object.__setattr__(self, name, value)

        def mousePressEvent(self, e):
            self.scene.mousePressEvent(e)
            self.update()

        def mouseMoveEvent(self, e):
            self.scene.mouseMoveEvent(e)

        def mouseReleaseEvent(self, e):
            self.scene.mouseReleaseEvent(e)
            self.update()

        def wheelEvent(self, e):
            self.scene.wheelEvent(e)
            self.update()

        def keyPressEvent(self, e):
            self.scene.keyPressEvent(e)

        def resizeEvent(self, e):
            super().resizeEvent(e)
            self.scene.resize(e.size())
            self._img = None
            self._rebuild = True

        def _mkprog(self, vs, fs):
            p = QOpenGLShaderProgram(self)
            okv = p.addShaderFromSourceCode(QOpenGLShader.Vertex, vs)
            okf = p.addShaderFromSourceCode(QOpenGLShader.Fragment, fs)
            okl = p.link()
            if not (okv and okf and okl):
                raise RuntimeError(p.log()[:220])
            return p

        def initializeGL(self):
            try:
                self.gl = self.context().functions()
                self.gl.initializeOpenGLFunctions()
                try:
                    ren = self.gl.glGetString(GLC.RENDERER)
                    if isinstance(ren, bytes):
                        ren = ren.decode("utf-8", "replace")
                except Exception:
                    ren = ""
                try:
                    maj, mnr = self.context().format().version()
                    ver = f"GL {maj}.{mnr}"
                except Exception:
                    ver = "GL"
                self.gpu_info = f"{(ren or 'OpenGL').strip()} · {ver}"
                self._progs = {
                    "bright": self._mkprog(VS_SRC, FS_BRIGHT),
                    "blur":   self._mkprog(VS_SRC, FS_BLUR),
                    "comp":   self._mkprog(VS_SRC, FS_COMP),
                }
                self.gl_mode = "gpu"
            except Exception as exc:
                self.gl = None
                self.gl_mode = "fallback"
                self.gpu_info = f"shaders unavailable — {exc}"

        def _ensure_img_only(self):
            dpr = self.devicePixelRatioF()
            w = max(2, int(self.width() * dpr))
            h = max(2, int(self.height() * dpr))
            if self._img is None or self._img.width() != w or self._img.height() != h:
                self._img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
                self._img.setDevicePixelRatio(dpr)
                self._rebuild = True

        def _ensure_targets(self):
            self._ensure_img_only()
            W, H = self._img.width(), self._img.height()
            if self._tex is None or self._tex.width() != W or self._tex.height() != H:
                if self._tex is not None:
                    try:
                        self._tex.destroy()
                    except Exception:
                        pass
                tex = QOpenGLTexture(QOpenGLTexture.Target2D)
                tex.setSize(W, H)
                tex.setFormat(QOpenGLTexture.RGBA8_UNorm)
                tex.setMinificationFilter(QOpenGLTexture.Linear)
                tex.setMagnificationFilter(QOpenGLTexture.Linear)
                tex.setWrapMode(QOpenGLTexture.ClampToEdge)
                tex.allocateStorage()
                self._tex = tex
                self._rebuild = True
            if self._rebuild:
                bw, bh = max(1, W // 2), max(1, H // 2)
                self._f_bright = QOpenGLFramebufferObject(bw, bh)
                self._f_a = QOpenGLFramebufferObject(bw, bh)
                self._f_b = QOpenGLFramebufferObject(bw, bh)
                for f in (self._f_bright, self._f_a, self._f_b):
                    self.gl.glBindTexture(GLC.TEXTURE_2D, f.texture())
                    self.gl.glTexParameteri(GLC.TEXTURE_2D, GLC.TEXTURE_MIN_FILTER, GLC.LINEAR)
                    self.gl.glTexParameteri(GLC.TEXTURE_2D, GLC.TEXTURE_MAG_FILTER, GLC.LINEAR)
                    self.gl.glTexParameteri(GLC.TEXTURE_2D, GLC.TEXTURE_WRAP_S, GLC.CLAMP_TO_EDGE)
                    self.gl.glTexParameteri(GLC.TEXTURE_2D, GLC.TEXTURE_WRAP_T, GLC.CLAMP_TO_EDGE)
                self.gl.glBindTexture(GLC.TEXTURE_2D, 0)
                self._rebuild = False

        def _u(self, prog, name, *vals):
            loc = prog.uniformLocation(name)
            if loc < 0:
                return
            if len(vals) == 1:
                self.gl.glUniform1f(loc, float(vals[0]))
            elif len(vals) == 2:
                self.gl.glUniform2f(loc, float(vals[0]), float(vals[1]))
            elif len(vals) == 3:
                self.gl.glUniform3f(loc, float(vals[0]), float(vals[1]), float(vals[2]))

        def _draw_quad(self, prog, setup):
            g = self.gl
            prog.bind()
            setup()
            g.glEnableVertexAttribArray(0)
            g.glVertexAttribPointer(0, 2, GLC.FLOAT, False, 0, self._quad)
            g.glDrawArrays(GLC.TRIANGLE_STRIP, 0, 4)
            g.glDisableVertexAttribArray(0)
            prog.release()

        def paintGL(self):
            if self.gl_mode == "gpu":
                try:
                    self._paint_gpu()
                    return
                except Exception:
                    self.gl_mode = "fallback"
            self._paint_fallback()

        def _paint_fallback(self):
            self._ensure_img_only()
            self.scene.render(self._img)
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            painter.drawImage(self.rect(), self._img)
            painter.end()

        def _paint_gpu(self):
            self._ensure_targets()
            img = self._img
            sc = self.scene
            g = self.gl
            img.fill(0)
            sc._gpu_pass = True
            sc.render(img)
            sc._gpu_pass = False
            g.glDisable(GLC.BLEND)
            self._tex.setData(img)
            W, H = img.width(), img.height()
            fbr = self._f_bright
            bw, bh = fbr.width(), fbr.height()

            fbr.bind()
            g.glViewport(0, 0, bw, bh)
            prog = self._progs["bright"]
            def bright_setup():
                self._tex.bind()
                prog.setUniformValue("uTex", 0)
                self._u(prog, "uThresh", 0.55)
            self._draw_quad(prog, bright_setup)

            prog = self._progs["blur"]
            src = fbr.texture()
            for rad in (1.0, 1.9):
                for fbo, dx, dy in ((self._f_a, rad / bw, 0.0),
                                    (self._f_b, 0.0, rad / bh)):
                    fbo.bind()
                    g.glViewport(0, 0, bw, bh)
                    def blur_setup(tex=src, dx=dx, dy=dy):
                        g.glActiveTexture(GLC.TEXTURE0)
                        g.glBindTexture(GLC.TEXTURE_2D, tex)
                        prog.setUniformValue("uTex", 0)
                        self._u(prog, "uDir", dx, dy)
                    self._draw_quad(prog, blur_setup)
                    src = fbo.texture()

            g.glBindFramebuffer(GLC.FRAMEBUFFER, 0)
            g.glViewport(0, 0, W, H)
            prog = self._progs["comp"]
            ramp = 0.0
            if sc.casting and sc.rings:
                ramp = min(1.0, math.sin(
                    clamp(sc.cast_elapsed / CAST_SECONDS, 0.0, 1.0) * math.pi) * 1.7)
            post = getattr(sc, "fx_post", True)
            bloom = 0.0
            if post and sc.fx_bloom:
                bloom = 0.85 + 0.35 * ramp + (0.35 if sc.forbidden else 0.0)
                if "TOGGLE" in sc._kinds() and sc.casting:
                    bloom *= (0.4 + 0.6*max(0.0, math.sin(2*math.pi*sc.cast_elapsed*1.8)))
            heat = sc.gpu["heat"] if post else 0.0
            ripple = sc.gpu["ripple"] if post else 0.0
            warp = sc.gpu["warp"] if post else 0.0
            wind = sc.gpu["wind"] if post else 0.0
            ab = sc.gpu["aberr"] if post else 0.0
            grain = (0.045 + (0.02 if sc.forbidden else 0.0)) if (post and sc.fx_grain) else 0.0
            vig = 0.85 if sc.fx_vignette else 0.0
            if post and sc.forbidden:
                vig += 0.08 + 0.05 * math.sin(sc._t * 4.0)
            fr = fg = fb = 0.0
            fa = 0.0
            if sc.flashes:
                fl = sc.flashes[0]
                c0 = fl["color"]
                fr, fg, fb = c0.red() / 255.0, c0.green() / 255.0, c0.blue() / 255.0
                fa = clamp(fl["a"], 0.0, 1.0)
            sx = sy = 0.0
            if sc.shake > 0.3 and sc.fx_shake:
                sx = random.uniform(-1, 1) * sc.shake / max(1, W)
                sy = random.uniform(-1, 1) * sc.shake / max(1, H)
            cx, cy = sc.gpu["center"]
            def comp_setup():
                self._tex.bind()
                g.glActiveTexture(GLC.TEXTURE1)
                g.glBindTexture(GLC.TEXTURE_2D, src)
                prog.setUniformValue("uScene", 0)
                prog.setUniformValue("uBloom", 1)
                self._u(prog, "uTime", sc._t)
                self._u(prog, "uBloomAmt", bloom)
                self._u(prog, "uCenter", cx, cy)
                self._u(prog, "uHeat", heat)
                self._u(prog, "uRipple", ripple)
                self._u(prog, "uWarp", warp)
                self._u(prog, "uWind", wind)
                self._u(prog, "uAberr", ab)
                self._u(prog, "uGrain", grain)
                self._u(prog, "uVignette", min(1.2, vig))
                self._u(prog, "uShake", sx, sy)
                self._u(prog, "uFlash", fr, fg, fb)
                self._u(prog, "uFlashA", fa)
            g.glClearColor(0.0, 0.0, 0.0, 1.0)
            g.glClear(GLC.COLOR_BUFFER_BIT)
            self._draw_quad(prog, comp_setup)

# ----------------------------------------------------------------------------
# Demo grimoire
# ----------------------------------------------------------------------------
def build_demo_grimoire():
    def ring(cx, cy, r, prec, n=160):
        pts = []
        for i in range(n):
            a = 2*math.pi*i/n
            jit = (1.0-prec)*r*(0.10*math.sin(7*a+1.3) + 0.05*math.sin(13*a))
            rr = (r + jit) / r
            pts.append([math.cos(a)*rr, math.sin(a)*rr])
        return pts
    C = 300.0
    return {
        "Hearthlight": {
            "sigil": "FIRE", "forbidden": False, "intensity": 0.5,
            "rings": [{"cx": C, "cy": C, "r": 150.0, "pts": ring(C, C, 150, 0.95)}],
            "signs": [{"kind": "LEVITATION", "u": 0.0, "v": -0.62, "rot": 0.0}],
        },
        "Tidecall": {
            "sigil": "WATER", "forbidden": False, "intensity": 0.45,
            "rings": [{"cx": C, "cy": C, "r": 150.0, "pts": ring(C, C, 150, 0.93)}],
            "signs": [{"kind": "COLUMN", "u": 0.0, "v": -0.60, "rot": 22.0}],
        },
        "Gale Spiral": {
            "sigil": "WIND", "forbidden": False, "intensity": 0.55,
            "rings": [{"cx": C, "cy": C, "r": 165.0, "pts": ring(C, C, 165, 0.90)},
                      {"cx": C, "cy": C, "r": 75.0, "pts": ring(C, C, 75, 0.88)}],
            "signs": [{"kind": "ROTATION",
                       "u": 0.60*math.cos(math.radians(a)),
                       "v": 0.60*math.sin(math.radians(a)), "rot": 15.0}
                      for a in (0, 120, 240)],
        },
        "The Sealed Page": {
            "sigil": "FIRE", "forbidden": True, "intensity": 0.7,
            "rings": [{"cx": C, "cy": C, "r": 150.0, "pts": ring(C, C, 150, 0.97)},
                      {"cx": C, "cy": C, "r": 85.0, "pts": ring(C, C, 85, 0.96)}],
            "signs": [{"kind": "EXPANSION",
                       "u": 0.5*math.cos(math.radians(a)),
                       "v": 0.5*math.sin(math.radians(a)), "rot": 0.0}
                      for a in (45, 135, 225, 315)],
        },
    }

# ----------------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------------
FX_TOGGLES = [
    ("fx/shake",   "fx_shake"),
    ("fx/glow",    "fx_glow"),
    ("fx/trails",  "fx_trails"),
    ("fx/motes",   "fx_motes"),
    ("fx/vignette","fx_vignette"),
    ("fx/post",    "fx_post"),
    ("fx/bloom",   "fx_bloom"),
    ("fx/distort", "fx_distort"),
    ("fx/aberr",   "fx_aberr"),
    ("fx/grain",   "fx_grain"),
]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sigil Atelier — Witch Hat Atelier Spellcraft")
        self.resize(1300, 860)
        self.sfx = SFX()
        self.canvas = create_canvas(self.sfx)
        self.grimoire = {}
        self.glaives = [None, None, None, None]
        self.chain_list = []
        self._chain_timer = QTimer(self)
        self._chain_timer.setSingleShot(True)
        self._chain_timer.setInterval(700)
        self._chain_timer.timeout.connect(self._chain_fire)
        self._glaive_cd = QTimer(self)
        self._glaive_cd.setSingleShot(True)
        self._glaive_cd.setInterval(GLAIVE_COOLDOWN_MS)
        self._glaive_cd.timeout.connect(lambda: self.glaive_bar.setEnabled(True))
        self.fx_menu = None
        self.act_gpu = None
        self.gpu_lbl = QLabel("")
        self.stats_lbl = QLabel("")
        self._load_settings()
        self._build_ui()
        self._build_menus()
        self._build_glaive_shortcuts()
        self._load_grimoire_file()
        self.canvas.stateChanged.connect(self._sync)
        self.canvas.logged.connect(self._log)
        self.canvas.castFinished.connect(self._on_cast_finished)
        self.sfx.readyChanged.connect(self._on_sound_ready)
        self.statusBar().showMessage(
            "1/2 tools · wheel = sigils · drag signs · right-click erases · "
            "Ctrl+Z undo · Ctrl+1–4 glaives · Ctrl+Return casts.")
        self.statusBar().addPermanentWidget(self.stats_lbl)
        self.statusBar().addPermanentWidget(self.gpu_lbl)
        self._log("Welcome to the atelier. Every spell begins with a single, honest circle.")
        if HAS_MULTIMEDIA and not self.sfx.ok:
            self._log("(The ink is being tuned — sounds will arrive in a moment.)")
        if not HAS_MULTIMEDIA:
            self._log("(Sound unavailable — the atelier hums in silence.)")
        QTimer.singleShot(150, self._log_gpu)
        self._sync()
        self._refresh_stats()
        self._refresh_glaives()

    # ---- settings ------------------------------------------------------------
    def _load_settings(self):
        s = QSettings()
        geo = s.value("win/geometry", "")
        if geo:
            try:
                self.restoreGeometry(QByteArray.fromBase64(geo.encode("ascii")))
            except Exception:
                pass
        self.sfx.set_volume(float(s.value("audio/volume", 0.55, float)))
        self.sfx.set_muted(s.value("audio/muted", False, bool))
        for key, attr in FX_TOGGLES:
            setattr(self.canvas, attr, s.value(key, True, bool))
        self.canvas.show_guide = s.value("view/guide", True, bool)
        self.canvas.practice_best = int(s.value("practice/best", 0))
        self.canvas.stat_casts = int(s.value("stats/casts", 0))
        self.canvas.stat_good = int(s.value("stats/good", 0))
        self.canvas.stat_forbidden = int(s.value("stats/forbidden", 0))
        try:
            arr = json.loads(s.value("glaives", "[]"))
            if isinstance(arr, list):
                self.glaives = (list(arr) + [None]*4)[:4]
        except Exception:
            pass

    def _save_settings(self):
        s = QSettings()
        s.setValue("win/geometry", bytes(self.saveGeometry().toBase64()).decode("ascii"))
        s.setValue("audio/volume", self.sfx.volume)
        s.setValue("audio/muted", self.sfx.muted)
        for key, attr in FX_TOGGLES:
            s.setValue(key, getattr(self.canvas, attr))
        s.setValue("view/guide", self.canvas.show_guide)
        s.setValue("practice/best", int(self.canvas.practice_best))
        s.setValue("stats/casts", int(self.canvas.stat_casts))
        s.setValue("stats/good", int(self.canvas.stat_good))
        s.setValue("stats/forbidden", int(self.canvas.stat_forbidden))
        s.setValue("glaives", json.dumps(self.glaives))
        s.sync()

    def closeEvent(self, e):
        self._save_settings()
        e.accept()

    def _log_gpu(self):
        info = getattr(self.canvas, "gpu_info", "")
        mode = getattr(self.canvas, "gl_mode", "")
        short = (info[:44] + "…") if len(info) > 45 else info
        self.gpu_lbl.setText(f"GPU: {short}" if info else "")
        if hasattr(self, "act_gpu") and self.act_gpu is not None:
            self.act_gpu.setText(f"Renderer: {info or 'unknown'}")
        if mode == "gpu" and info:
            self._log(f"✦ GPU pipeline online — {info}. "
                      "Bloom, shimmer and aberration run on your graphics card.")
        elif info:
            self._log(f"GPU shaders unavailable ({info}) — the CPU veil carries the spell.")

    def _on_sound_ready(self, ok):
        if ok:
            self._log("♪ The ink sings — sound engine ready.")
        else:
            self._log("(Sound could not be initialized — the atelier hums in silence.)")

    # ---- UI construction -------------------------------------------------------
    def _build_ui(self):
        title = QLabel("✦  Sigil Atelier  ✦")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("draw the ring · anchor the sigil · set your signs · cast")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color:#a89cc8;")

        gb_grim = QGroupBox("📖 Grimoire")
        lv = QVBoxLayout(gb_grim)
        self.spell_list = QListWidget()
        self.spell_list.itemDoubleClicked.connect(lambda _: self._load_spell())
        lv.addWidget(self.spell_list)
        row = QHBoxLayout()
        b_save = QPushButton("Save")
        b_load = QPushButton("Load")
        b_del = QPushButton("Delete")
        b_save.clicked.connect(self._save_spell)
        b_load.clicked.connect(self._load_spell)
        b_del.clicked.connect(self._delete_spell)
        for b in (b_save, b_load, b_del):
            row.addWidget(b)
        lv.addLayout(row)
        row2 = QHBoxLayout()
        b_chain = QPushButton("🔗 Toggle Chain")
        b_chain.setToolTip("Mark/unmark this seal for linked casting — chained seals "
                           "auto-load and cast after the previous cast finishes.")
        b_chain.clicked.connect(self._toggle_chain)
        row2.addWidget(b_chain)
        lv.addLayout(row2)
        hint = QLabel("Double-click loads · grimoire.json")
        hint.setStyleSheet("color:#7d739c; font-size:11px;")
        hint.setWordWrap(True)
        lv.addWidget(hint)

        center_w = QWidget()
        cv = QVBoxLayout(center_w)
        cv.setContentsMargins(0, 0, 0, 0)
        tools = QHBoxLayout()
        self.btn_ring = QToolButton(); self.btn_ring.setText("✏ Draw Ring (1)")
        self.btn_ring.setCheckable(True); self.btn_ring.setChecked(True)
        self.btn_sign = QToolButton(); self.btn_sign.setText("⊕ Place Sign (2)")
        self.btn_sign.setCheckable(True)
        grp = QButtonGroup(self); grp.setExclusive(True)
        grp.addButton(self.btn_ring); grp.addButton(self.btn_sign)
        self.btn_ring.clicked.connect(lambda: self.set_tool("ring"))
        self.btn_sign.clicked.connect(lambda: self.set_tool("sign"))
        tools.addWidget(self.btn_ring); tools.addWidget(self.btn_sign)
        tools.addSpacing(10)
        b_undo = QPushButton("Undo (Ctrl+Z)")
        b_clear = QPushButton("Clear Seal")
        b_undo.clicked.connect(self.canvas.undo)
        b_clear.clicked.connect(self.canvas.clear_seal)
        tools.addWidget(b_undo); tools.addWidget(b_clear)
        tools.addSpacing(10)
        self.btn_practice = QToolButton()
        self.btn_practice.setText("🎯 Practice")
        self.btn_practice.setCheckable(True)
        self.btn_practice.setToolTip("Coco's circle drill — trace the coach ring and be graded.")
        self.btn_practice.toggled.connect(self._toggle_practice)
        tools.addWidget(self.btn_practice)
        tools.addStretch(1)
        self.btn_fx = QToolButton()
        self.btn_fx.setText("✧ Effects")
        self.btn_fx.setPopupMode(QToolButton.InstantPopup)
        tools.addWidget(self.btn_fx)
        self.guide_check = QCheckBox("Tracing guide")
        self.guide_check.setChecked(self.canvas.show_guide)
        self.guide_check.toggled.connect(self._toggle_guide)
        tools.addWidget(self.guide_check)
        cv.addLayout(tools)

        # ---- glaives bar ------------------------------------------------------
        self.glaive_bar = QWidget()
        gl = QHBoxLayout(self.glaive_bar)
        gl.setContentsMargins(0, 2, 0, 2)
        lbl = QLabel("⚔ Glaives")
        lbl.setStyleSheet("color:#d4b06a; font-weight:600;")
        gl.addWidget(lbl)
        self.glaive_slots = []
        for i in range(4):
            b = QToolButton()
            b.setText("—")
            b.setMinimumWidth(64)
            b.setToolTip(f"Glaive {i+1} — empty. Bind a seal here, then cast with Ctrl+{i+1}.")
            b.clicked.connect(lambda _=False, k=i: self._cast_glaive(k))
            b.setContextMenuPolicy(Qt.CustomContextMenu)
            b.customContextMenuRequested.connect(
                lambda pos, k=i, btn=b: self._glaive_menu(btn, k))
            self.glaive_slots.append(b)
            gl.addWidget(b)
        b_bind = QPushButton("⚔ Bind")
        b_bind.setToolTip("Bind the current seal to the first empty glaive slot.")
        b_bind.clicked.connect(self._bind_glaive)
        gl.addWidget(b_bind)
        gl.addStretch(1)
        cv.addWidget(self.glaive_bar)

        cv.addWidget(self.canvas, 1)
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(110)
        self.log_box.setPlaceholderText("Atelier log…")
        cv.addWidget(self.log_box)

        right = QWidget()
        right.setFixedWidth(300)
        rv = QVBoxLayout(right)

        gb_sig = QGroupBox("Sigils")
        sv = QVBoxLayout(gb_sig)
        grid = QGridLayout()
        grid.setSpacing(6)
        self.sigil_buttons = []
        tips = {
            "FIRE": "Primary Tetrad. Embers, smoke, heat shimmer.",
            "WATER": "Primary Tetrad. Rain, jets — the page ripples like water.",
            "EARTH": "Primary Tetrad. Falling stones, dust — and the table shakes.",
            "WIND": "Primary Tetrad. Gales, lightning sparks, streaking air.",
            "LIGHT": "A phenomena sigil — radiant sparks and golden stars.",
            "SOUND": "A phenomena sigil — resonance rings and drifting notes.",
            "TIME": "A phenomena sigil — slow orbits and a warping of the page.",
            "REPETITION": "A phenomena sigil — echoing pulses, twice.",
        }
        for i, (k, v) in enumerate(SIGILS.items()):
            b = QPushButton(v["label"])
            b.setCheckable(True)
            b.setProperty("sigil_key", k)
            b.setToolTip(tips[k])
            b.clicked.connect(lambda _=False, key=k: self._pick_sigil(key))
            self.sigil_buttons.append(b)
            grid.addWidget(b, i // 2, i % 2)
        sv.addLayout(grid)
        irow = QHBoxLayout()
        irow.addWidget(QLabel("Intensity"))
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setRange(10, 75)
        self.intensity_slider.setValue(int(self.canvas.intensity * 100))
        self.intensity_slider.setToolTip("Sigil size relative to the ring — bigger sigils, stronger spells.")
        self.lbl_intensity = QLabel(f"{int(self.canvas.intensity*100)}%")
        self.intensity_slider.valueChanged.connect(self._intensity_changed)
        irow.addWidget(self.intensity_slider, 1)
        irow.addWidget(self.lbl_intensity)
        sv.addLayout(irow)
        rv.addWidget(gb_sig)

        gb_sign = QGroupBox("Signs")
        nv = QVBoxLayout(gb_sign)
        self.sign_combo = QComboBox()
        for k, v in SIGNS.items():
            self.sign_combo.addItem(v["label"], k)
        self.sign_combo.currentIndexChanged.connect(self._sign_kind_changed)
        nv.addWidget(self.sign_combo)
        rrow = QHBoxLayout()
        rrow.addWidget(QLabel("Sign rotation"))
        self.rot_slider = QSlider(Qt.Horizontal)
        self.rot_slider.setRange(-180, 180)
        self.rot_slider.setValue(0)
        self.rot_slider.setToolTip("Sign rotation shifts a sign's effective angle — "
                                   "the glyph points where the spell will drift.")
        self.lbl_rot = QLabel("0°")
        self.rot_slider.valueChanged.connect(self._rot_changed)
        rrow.addWidget(self.rot_slider, 1)
        rrow.addWidget(self.lbl_rot)
        nv.addLayout(rrow)
        self.sign_list = QListWidget()
        self.sign_list.setMaximumHeight(110)
        self.sign_list.currentRowChanged.connect(self._sign_selected)
        nv.addWidget(self.sign_list)
        b_rm = QPushButton("Remove Selected Sign")
        b_rm.clicked.connect(self._remove_sign)
        nv.addWidget(b_rm)
        tip = QLabel("A ghost preview follows your cursor. Drag to move; right-click "
                     "to erase. Spread signs evenly — or rotate them — or the spell drifts. "
                     "The toggle sign makes the spell pulse.")
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#7d739c; font-size:11px;")
        nv.addWidget(tip)
        rv.addWidget(gb_sign)

        gb_an = QGroupBox("Seal Analysis")
        av = QGridLayout(gb_an)
        self.lbl_ring = QLabel("—"); self.lbl_bal = QLabel("—")
        self.lbl_power = QLabel("—"); self.lbl_stab = QLabel("—")
        for row_i, (name, wname) in enumerate((("Ring Quality", "lbl_ring"),
                                               ("Sign Balance", "lbl_bal"),
                                               ("Power", "lbl_power"),
                                               ("Stability", "lbl_stab"))):
            av.addWidget(QLabel(name), row_i, 0)
            av.addWidget(getattr(self, wname), row_i, 1)
        self.lbl_pred = QLabel("—")
        self.lbl_pred.setWordWrap(True)
        self.lbl_pred.setMinimumHeight(52)
        av.addWidget(self.lbl_pred, 4, 0, 1, 2)
        self.forbidden_check = QCheckBox("Draw forbidden magic")
        self.forbidden_check.setObjectName("forbiddenCheck")
        self.forbidden_check.setToolTip("Certain sigils must never be drawn. The atelier will only watch.")
        self.forbidden_check.toggled.connect(self._toggle_forbidden)
        av.addWidget(self.forbidden_check, 5, 0, 1, 2)
        rv.addWidget(gb_an)

        self.cast_btn = QPushButton("✦ Cast Spell ✦")
        self.cast_btn.setObjectName("castButton")
        self.cast_btn.clicked.connect(self._cast)
        rv.addWidget(self.cast_btn)
        rv.addStretch(1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(gb_grim)
        splitter.addWidget(center_w)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)

        root = QVBoxLayout()
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(splitter, 1)
        wrap = QWidget()
        wrap.setLayout(root)
        self.setCentralWidget(wrap)

    def _build_glaive_shortcuts(self):
        for i in range(4):
            sc = QShortcut(QKeySequence(f"Ctrl+{i+1}"), self)
            sc.activated.connect(lambda k=i: self._cast_glaive(k))

    def _build_menus(self):
        self.fx_menu = QMenu("Effects", self)

        def add_fx(text, getter, setter):
            act = QAction(text, self)
            act.setCheckable(True)
            act.setChecked(getter())
            def on_toggle(on, st=setter):
                st(on)
                self._save_settings()
            act.toggled.connect(on_toggle)
            self.fx_menu.addAction(act)
            return act

        def vol_setter(on):
            self.sfx.set_muted(not on)
            self._save_settings()
        add_fx("Sound effects", lambda: not self.sfx.muted, vol_setter)
        for text, attr in (("Screen shake", "fx_shake"),
                           ("Ink glow (scene)", "fx_glow"),
                           ("Particle trails", "fx_trails"),
                           ("Ambient motes", "fx_motes")):
            add_fx(text, lambda a=attr: getattr(self.canvas, a),
                   lambda on, a=attr: (setattr(self.canvas, a, on),
                                       self.canvas.update()))
        self.fx_menu.addSeparator()
        for text, attr in (("GPU post-processing", "fx_post"),
                           ("GPU screen bloom", "fx_bloom"),
                           ("Spell distortion (heat · ripple · warp)", "fx_distort"),
                           ("Chromatic aberration (forbidden)", "fx_aberr"),
                           ("Film grain", "fx_grain")):
            add_fx(text, lambda a=attr: getattr(self.canvas, a),
                   lambda on, a=attr: setattr(self.canvas, a, on))
        volw = QWidget()
        hl = QHBoxLayout(volw)
        hl.setContentsMargins(8, 2, 8, 2)
        hl.addWidget(QLabel("🔊"))
        vs = QSlider(Qt.Horizontal)
        vs.setRange(0, 100)
        vs.setValue(int(self.sfx.volume * 100))
        def vol_changed(v):
            self.sfx.set_volume(v / 100.0)
            self._save_settings()
        vs.valueChanged.connect(vol_changed)
        hl.addWidget(vs)
        wact = QWidgetAction(self.fx_menu)
        wact.setDefaultWidget(volw)
        self.fx_menu.addAction(wact)
        self.fx_menu.addSeparator()
        self.act_gpu = QAction("Renderer: probing…", self)
        self.act_gpu.setEnabled(False)
        self.fx_menu.addAction(self.act_gpu)
        self.btn_fx.setMenu(self.fx_menu)

        m_file = self.menuBar().addMenu("&File")
        act_new = QAction("New Seal", self)
        act_new.setShortcut(QKeySequence("Ctrl+N"))
        act_new.triggered.connect(self.canvas.clear_seal)
        act_save = QAction("Save to Grimoire", self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self._save_spell)
        act_export = QAction("Export Grimoire As…", self)
        act_export.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_export.triggered.connect(self._export_grimoire)
        act_img = QAction("Export Seal as Image…", self)
        act_img.setShortcut(QKeySequence("Ctrl+E"))
        act_img.triggered.connect(self._export_image)
        act_quit = QAction("Quit", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        for a in (act_new, act_save, act_export, act_img, act_quit):
            m_file.addAction(a)

        m_edit = self.menuBar().addMenu("&Edit")
        act_undo = QAction("Undo", self)
        act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        act_undo.triggered.connect(self.canvas.undo)
        m_edit.addAction(act_undo)

        m_seal = self.menuBar().addMenu("&Seal")
        a1 = QAction("Ring Tool", self); a1.setShortcut(QKeySequence("1"))
        a1.triggered.connect(lambda: self.set_tool("ring"))
        a2 = QAction("Sign Tool", self); a2.setShortcut(QKeySequence("2"))
        a2.triggered.connect(lambda: self.set_tool("sign"))
        a3 = QAction("Cast Spell", self); a3.setShortcut(QKeySequence("Ctrl+Return"))
        a3.triggered.connect(self._cast)
        for a in (a1, a2, a3):
            m_seal.addAction(a)

        m_fx = self.menuBar().addMenu("✧ &Effects")
        for act in self.fx_menu.actions():
            if not isinstance(act, QWidgetAction):
                m_fx.addAction(act)

        m_help = self.menuBar().addMenu("&Help")
        a_help = QAction("How Seals Work…", self)
        a_help.setShortcut(QKeySequence("F1"))
        a_help.triggered.connect(lambda: QMessageBox.information(self, "How Seals Work", HELP_TEXT))
        a_about = QAction("About", self)
        a_about.triggered.connect(lambda: QMessageBox.about(
            self, "About Sigil Atelier",
            "A fan-made spellcraft toy inspired by <b>Witch Hat Atelier</b><br>"
            "(<i>Tongari Bōshi no Atelier</i>) by Kamome Shirahama.<br><br>"
            "Rings, sigils and signs — rotated, toggled, chained and<br>"
            "kept sheathed in glaives, all bloomed in GLSL."))
        m_help.addAction(a_help)
        m_help.addAction(a_about)

    # ---- glaives ---------------------------------------------------------------
    def _glaive_menu(self, btn, i):
        m = QMenu(self)
        a_bind = m.addAction("⚔ Bind current seal here")
        a_clear = m.addAction("Clear this slot")
        a_clear.setEnabled(self.glaives[i] is not None)
        chosen = m.exec(btn.mapToGlobal(btn.rect().topLeft() + btn.pos()*0).topLeft()
                        if False else btn.mapToGlobal(btn.rect().topLeft()))
        if chosen == a_bind:
            self._bind_glaive(i)
        elif chosen == a_clear:
            self.glaives[i] = None
            self._refresh_glaives()
            self._save_settings()
            self._log(f"Glaive {i+1} is emptied.")

    def _bind_glaive(self, slot=None):
        if self.canvas.validate():
            QMessageBox.warning(self, "Bind Glaive",
                                "The seal is incomplete — bind a full seal (ring + sigil).")
            return
        if slot is None:
            slot = next((i for i, g in enumerate(self.glaives) if g is None), None)
            if slot is None:
                self._log("All four glaives are laden — clear one first (right-click a slot).")
                return
        self.glaives[slot] = self.canvas.serialize()
        self._refresh_glaives()
        self._save_settings()
        self.sfx.play("ring")
        self._log(f"⚔ The seal is pressed into glaive {slot+1} — cast it any time "
                  f"with Ctrl+{slot+1}.")

    def _cast_glaive(self, i):
        if self.canvas.casting:
            return
        data = self.glaives[i]
        if not data:
            self._log(f"Glaive {i+1} is an empty sheath.")
            return
        self._break_chain()
        self.canvas.deserialize(data, msg=f"⚔ You level glaive {i+1} — its seal springs to ink.")
        if self.canvas.validate() is None:
            self.canvas.cast()
            self.glaive_bar.setEnabled(False)
            self._glaive_cd.start()

    def _refresh_glaives(self):
        for i, b in enumerate(self.glaive_slots):
            g = self.glaives[i]
            if g:
                sig = g.get("sigil")
                sym = SIGILS[sig]["label"].split(" ")[0] if sig in SIGILS else "✦"
                b.setText(sym)
                n = len(g.get("signs", []))
                b.setToolTip(
                    f"Glaive {i+1}: {sig or '—'} · {len(g.get('rings', []))} ring(s) · "
                    f"{n} sign(s){' · ⚠ FORBIDDEN' if g.get('forbidden') else ''}\n"
                    f"Click or Ctrl+{i+1} to cast. Right-click to bind/clear.")
            else:
                b.setText("—")
                b.setToolTip(f"Glaive {i+1} — empty. Bind a seal here (⚔ Bind, or "
                             f"right-click), then cast with Ctrl+{i+1}.")

    def _refresh_stats(self):
        c = self.canvas
        self.stats_lbl.setText(f"casts {c.stat_casts} · ✦ {c.stat_good} · ⚠ {c.stat_forbidden}")

    # ---- handlers -----------------------------------------------------------------
    def _break_chain(self):
        if self._chain_timer.isActive():
            self._chain_timer.stop()
            self._log("You break the chain — casting of your own will.")

    def set_tool(self, tool):
        self.canvas.tool = tool
        self.canvas._wake()
        self.canvas.update()
        self.btn_ring.setChecked(tool == "ring")
        self.btn_sign.setChecked(tool == "sign")

    def _pick_sigil(self, key):
        self.canvas.sigil = key
        self.sfx.play("sign")
        if self.canvas.rings:
            inner = self.canvas._inner()
            self.canvas.rings_fx.append({
                "c": QPointF(inner.cx, inner.cy), "r": inner.r*0.2,
                "vr": inner.r*0.8, "life": 0.7,
                "color": QColor(SIGILS[key]["color"])})
        self.canvas.update()
        self.canvas._wake()
        self._log(SIGIL_FLAVOR[key])
        self.canvas.stateChanged.emit()

    def _sign_kind_changed(self, i):
        self.canvas.pending_sign = self.sign_combo.itemData(i)
        self.canvas.update()

    def _rot_changed(self, v):
        self.canvas.pending_rot = float(v)
        self.lbl_rot.setText(f"{v}°")
        row = self.sign_list.currentRow()
        if 0 <= row < len(self.canvas.signs):
            self.canvas.signs[row].rot = float(v)
            self.canvas.update()
            self.sign_list.item(row).setText(self._sign_item_text(self.canvas.signs[row]))

    def _sign_item_text(self, s):
        rot = int(round(s.rot))
        base = SIGNS[s.kind]["label"]
        return f"{base}  ({rot}°)" if rot else base

    def _sign_selected(self, row):
        if not (0 <= row < len(self.canvas.signs)):
            return
        s = self.canvas.signs[row]
        self.sign_combo.blockSignals(True)
        idx = self.sign_combo.findData(s.kind)
        if idx >= 0:
            self.sign_combo.setCurrentIndex(idx)
        self.sign_combo.blockSignals(False)
        self.rot_slider.blockSignals(True)
        self.rot_slider.setValue(int(round(s.rot)))
        self.lbl_rot.setText(f"{int(round(s.rot))}°")
        self.rot_slider.blockSignals(False)
        self.canvas.pending_sign = s.kind
        self.canvas.pending_rot = s.rot
        self.canvas.selected_sign_index = row
        self.canvas.update()

    def _intensity_changed(self, v):
        self.canvas.intensity = v / 100.0
        self.lbl_intensity.setText(f"{v}%")
        self.canvas.stateChanged.emit()

    def _remove_sign(self):
        self.canvas.remove_sign(self.sign_list.currentRow())

    def _toggle_guide(self, on):
        self.canvas.show_guide = on
        self.canvas._wake()
        self.canvas.update()
        self._save_settings()

    def _toggle_practice(self, on):
        self.canvas.set_practice(bool(on))
        self._save_settings()

    def _toggle_forbidden(self, on):
        self.canvas.forbidden = bool(on)
        if on:
            self._log("You open the book you were told not to open. "
                      "(Forbidden magic: unstable, unwise, available — and it bends the light.)")
        else:
            self._log("You close the forbidden book. Wise.")
        self.canvas.update()
        self.canvas._wake()
        self.canvas.stateChanged.emit()

    def _cast(self):
        self._break_chain()
        err = self.canvas.validate()
        if err:
            self._log(err)
            QMessageBox.warning(self, "The Seal Fails", err)
            return
        self.canvas.cast()

    def _on_cast_finished(self):
        self._refresh_stats()
        self._save_settings()
        if not self.chain_list:
            return
        name = self.chain_list.pop(0)
        data = self.grimoire.get(name)
        self._refresh_chain_marks()
        if not data:
            return
        self._log(f"🔗 Linked seal — “{name}” unfurls as the first fades.")
        self.canvas.deserialize(data)
        self._chain_timer.start()

    def _chain_fire(self):
        if self.canvas.validate() is None:
            self.canvas.cast()
        else:
            self._log("The linked seal is incomplete — the chain fizzles.")

    def _toggle_chain(self):
        it = self.spell_list.currentItem()
        if not it:
            QMessageBox.information(self, "Chain Casting",
                                    "Select a seal in the grimoire first.")
            return
        name = it.data(Qt.UserRole)
        if name in self.chain_list:
            self.chain_list.remove(name)
            self._log(f"🔗 “{name}” is released from the chain.")
        else:
            self.chain_list.append(name)
            self._log(f"🔗 “{name}” is bound into the chain ({len(self.chain_list)} linked).")
        self._refresh_chain_marks()

    def _item_text(self, name):
        sig = self.grimoire.get(name, {}).get("sigil")
        label = SIGILS[sig]["label"] if sig in SIGILS else "—"
        link = "🔗 " if name in self.chain_list else ""
        return f"{link}{name}   ·   {label}"

    def _refresh_chain_marks(self):
        for i in range(self.spell_list.count()):
            it = self.spell_list.item(i)
            it.setText(self._item_text(it.data(Qt.UserRole)))

    # ---- grimoire -------------------------------------------------------------------
    def _load_grimoire_file(self):
        seeded = False
        if not os.path.exists(GRIMOIRE_FILE):
            self.grimoire = build_demo_grimoire()
            seeded = True
            try:
                with open(GRIMOIRE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.grimoire, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
        else:
            try:
                with open(GRIMOIRE_FILE, "r", encoding="utf-8") as f:
                    self.grimoire = json.load(f)
            except Exception:
                self.grimoire = {}
        for name in self.grimoire:
            it = QListWidgetItem(self._item_text(name))
            it.setData(Qt.UserRole, name)
            self.spell_list.addItem(it)
        if seeded:
            self._log("A starter grimoire has been pressed into your hands — four seals, "
                      "one of which you should not cast. Double-click to load, then Cast. "
                      "Bind your favorites to the glaives (⚔).")

    def _save_grimoire_file(self):
        try:
            with open(GRIMOIRE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.grimoire, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Grimoire", f"Could not save grimoire:\n{e}")

    def _save_spell(self):
        name, ok = QInputDialog.getText(self, "Save to Grimoire", "Name this seal:")
        if not ok:
            return
        name = name.strip() or f"Untitled Seal {len(self.grimoire)+1}"
        self.grimoire[name] = self.canvas.serialize()
        for i in range(self.spell_list.count()):
            if self.spell_list.item(i).data(Qt.UserRole) == name:
                self.spell_list.takeItem(i)
                break
        it = QListWidgetItem(self._item_text(name))
        it.setData(Qt.UserRole, name)
        self.spell_list.addItem(it)
        self._save_grimoire_file()
        self.sfx.play("sign")
        self._log(f"“{name}” pressed between the pages of your grimoire.")

    def _load_spell(self):
        it = self.spell_list.currentItem()
        if not it:
            QMessageBox.information(self, "Grimoire", "Choose a seal from the grimoire first.")
            return
        self.canvas.deserialize(self.grimoire[it.data(Qt.UserRole)])

    def _delete_spell(self):
        it = self.spell_list.currentItem()
        if not it:
            return
        name = it.data(Qt.UserRole)
        self.grimoire.pop(name, None)
        if name in self.chain_list:
            self.chain_list.remove(name)
            self._refresh_chain_marks()
        self.spell_list.takeItem(self.spell_list.row(it))
        self._save_grimoire_file()
        self._log(f"“{name}” is struck from the record.")

    def _export_grimoire(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Grimoire",
                                              GRIMOIRE_FILE, "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.grimoire, f, indent=2, ensure_ascii=False)
            self._log("The grimoire is copied for a fellow witch.")
        except Exception as e:
            QMessageBox.critical(self, "Grimoire", f"Could not export:\n{e}")

    def _export_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Seal as Image",
                                              "seal.png", "PNG (*.png)")
        if not path:
            return
        try:
            w, h = self.canvas.width(), self.canvas.height()
            img = QImage(w*2, h*2, QImage.Format_ARGB32_Premultiplied)
            img.setDevicePixelRatio(2.0)
            img.fill(QColor("#131022"))
            self.canvas.render(img)
            if img.save(path):
                self._log("The seal is pressed onto parchment (PNG, 2×).")
            else:
                raise IOError("save failed")
        except Exception as e:
            QMessageBox.critical(self, "Export", f"Could not export image:\n{e}")

    # ---- sync / log ------------------------------------------------------------------
    def _log(self, msg):
        self.log_box.appendPlainText(msg)

    def _sync(self):
        self.canvas._wake()
        for b in self.sigil_buttons:
            b.setChecked(b.property("sigil_key") == self.canvas.sigil)
        self.intensity_slider.blockSignals(True)
        self.intensity_slider.setValue(int(self.canvas.intensity * 100))
        self.lbl_intensity.setText(f"{int(self.canvas.intensity*100)}%")
        self.intensity_slider.blockSignals(False)
        self.sign_list.blockSignals(True)
        self.sign_list.clear()
        for i, s in enumerate(self.canvas.signs):
            self.sign_list.addItem(QListWidgetItem(f"{i+1}.  {self._sign_item_text(s)}"))
        self.sign_list.blockSignals(False)
        self.forbidden_check.blockSignals(True)
        self.forbidden_check.setChecked(self.canvas.forbidden)
        self.forbidden_check.blockSignals(False)
        if hasattr(self, "btn_practice"):
            self.btn_practice.blockSignals(True)
            self.btn_practice.setChecked(self.canvas.practice)
            self.btn_practice.blockSignals(False)
        d = self.canvas.analyse()
        if d["has_ring"]:
            self.lbl_ring.setText(f"{d['ring_q']*100:.0f}%")
            self.lbl_bal.setText(
                "No signs — pure sigil seal." if d["n_signs"] == 0 else
                "Balanced — the spell holds true." if d["balance"] >= 0.75 else
                f"Uneven — it will drift {d['drift_word']}.")
            self.lbl_power.setText(f"{d['power']:.0f}%" +
                                   (f"  (nested ×{d['mult']:.2f})" if d["mult"] > 1 else ""))
            self.lbl_stab.setText(f"{d['stability']*100:.0f}%")
        else:
            for wname in ("lbl_ring", "lbl_bal", "lbl_power", "lbl_stab"):
                getattr(self, wname).setText("—")
        self.lbl_pred.setText(d["predicted"])
        self.lbl_pred.setStyleSheet("color:#ff7a90;" if d["forbidden"] else "")

# ----------------------------------------------------------------------------
# Styles & entry point
# ----------------------------------------------------------------------------
QSS = """
QWidget { background-color: #17132a; color: #e8e0f0; font-size: 13px; }
QGroupBox { border: 1px solid #3c3357; border-radius: 8px; margin-top: 14px;
            padding: 10px 8px 8px 8px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #d4b06a; }
QPushButton, QToolButton { background: #2b2440; border: 1px solid #4a3f6b;
    border-radius: 6px; padding: 6px 10px; }
QPushButton:hover, QToolButton:hover { background: #373054; border-color: #6b5a9e; }
QPushButton:checked, QToolButton:checked { background: #4a3f6b; border-color: #d4b06a; color: #ffe9b8; }
QToolButton::menu-indicator { image: none; }
QListWidget, QPlainTextEdit, QComboBox { background: #1f1a33; border: 1px solid #3c3357;
    border-radius: 6px; padding: 2px; }
QSlider::groove:horizontal { height: 6px; background: #2b2440; border-radius: 3px; }
QSlider::handle:horizontal { background: #d4b06a; width: 14px; margin: -5px 0; border-radius: 7px; }
QCheckBox::indicator { width: 15px; height: 15px; }
#castButton { background: #d4b06a; color: #241d3a; font-weight: 700; font-size: 15px; padding: 10px; }
#castButton:hover { background: #e6c47e; }
#forbiddenCheck { color: #ff7a90; font-weight: 600; }
#titleLabel { font-size: 20px; font-weight: 700; color: #f0e6d2; }
QMenuBar { background: #17132a; }
QMenuBar::item:selected, QMenu::item:selected { background: #373054; }
QMenu { background: #221c3a; border: 1px solid #4a3f6b; }
QStatusBar { color: #a89cc8; }
"""

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    if HAS_GL_MODULES:
        fmt = QSurfaceFormat()
        fmt.setProfile(QSurfaceFormat.CompatibilityProfile)
        fmt.setVersion(2, 1)
        QSurfaceFormat.setDefaultFormat(fmt)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()