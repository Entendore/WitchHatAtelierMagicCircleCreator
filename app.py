#!/usr/bin/env python3
"""
Witch Hat Atelier - Magic Circle Creator & Magic System Reference
Enhanced with Freehand Drawing, Undo/Redo, Vector Export, Alignment Tools,
Live Spell Monitoring, and Detailed Circle Description.

Install: pip install PySide6
Run:     python witch_hat_magic_circle.py
"""

import sys
import math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QGroupBox, QFormLayout, QLabel,
    QPushButton, QDoubleSpinBox, QSpinBox, QCheckBox, QColorDialog,
    QComboBox, QTextBrowser, QLineEdit, QMenu, QToolBar, QFileDialog,
    QStatusBar, QMessageBox, QScrollArea, QInputDialog, QSlider
)
from PySide6.QtCore import Qt, QRectF, QPointF, QSize, Signal, QTimer
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath, QFont,
    QAction, QPixmap, QTransform, QRadialGradient, QFontMetrics,
    QUndoStack, QUndoCommand, QCursor
)
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QGraphicsItem
)

try:
    from PySide6.QtSvg import QSvgGenerator
    HAS_SVG = True
except ImportError:
    HAS_SVG = False

# ═══════════════════════════════════════════════════════════════
# CONSTANTS & COLOR SCHEME
# ═══════════════════════════════════════════════════════════════

GOLDEN       = QColor(210, 175, 55)
GOLDEN_LIGHT = QColor(255, 220, 100)
CANVAS_BG    = QColor(15, 15, 25)
ACCENT       = QColor(100, 180, 255)

MODE_SELECT = 0
MODE_DRAW   = 1

GLYPH_NAMES = {
    "fire": "Fire (火)", "water": "Water (水)", "earth": "Earth (土)",
    "wind": "Wind (風)", "light": "Light (光)", "dark": "Dark (闇)",
    "healing": "Healing (治癒)", "creation": "Creation (創造)",
    "destruction": "Destruction (破壊)", "movement": "Movement (移動)",
    "transformation": "Transform (変化)", "sound": "Sound (音)",
    "binding": "Binding (拘束)", "barrier": "Barrier (結界)",
    "summon": "Summon (召喚)",
}

GLYPH_DESCRIPTIONS = {
    "fire": "Controls flame and heat. Basic offensive and utility magic.",
    "water": "Manipulates water and liquids. Healing support and flow control.",
    "earth": "Commands stone, soil, and minerals. Structural and defensive magic.",
    "wind": "Governs air currents and pressure. Speed and ranged attacks.",
    "light": "Produces illumination and radiant energy. Revelation and purification.",
    "dark": "Governs shadow and void. Concealment and negation.",
    "healing": "Mends wounds and restores vitality. The most regulated magic.",
    "creation": "Brings new forms into existence. Close to forbidden territory.",
    "destruction": "Unmakes and dissolves matter. Dangerous and closely watched.",
    "movement": "Controls displacement and velocity. Teleportation and kinetic force.",
    "transformation": "Alters the form of objects. Body modification is FORBIDDEN.",
    "sound": "Commands vibrations and acoustic phenomena. Communication magic.",
    "binding": "Restricts and constrains. Contracts and seals.",
    "barrier": "Creates protective wards and shields. Defensive circles.",
    "summon": "Calls forth entities and objects. Requires precise circle geometry.",
}

GLYPH_COLORS = {
    "fire": "#ff8844", "water": "#4488ff", "earth": "#44aa44",
    "wind": "#88ddff", "light": "#ffee88", "dark": "#aa88dd",
    "healing": "#66ddaa", "creation": "#88ff88", "destruction": "#ff4444",
    "movement": "#88ccff", "transformation": "#cc88ff", "sound": "#88ffcc",
    "binding": "#ff88aa", "barrier": "#aaddff", "summon": "#ffaa88",
}

# ═══════════════════════════════════════════════════════════════
# DETAILED SPELL / CIRCLE DESCRIPTION DATA
# ═══════════════════════════════════════════════════════════════

SPELL_EFFECTS = {
    "fire": {
        "primary": "Creates and controls flame and heat",
        "effects": ["Fire projection", "Heat generation", "Ignition", "Fire resistance"],
        "classification": "Offensive / Utility",
        "power_base": 7,
        "narrative": "Flames erupt at the caster's command, dancing along the circle's rings. "
                     "Heat distorts the air as the glyph pulses with orange light.",
    },
    "water": {
        "primary": "Manipulates water and liquids",
        "effects": ["Water manipulation", "Minor healing", "Flow control", "Ice formation"],
        "classification": "Support / Healing",
        "power_base": 5,
        "narrative": "Water flows along the inscribed paths, rising and falling with the caster's will. "
                     "The circle hums with a cool, soothing resonance.",
    },
    "earth": {
        "primary": "Commands stone, soil, and minerals",
        "effects": ["Stone shaping", "Barrier creation", "Terrain alteration", "Mineral detection"],
        "classification": "Defensive / Structural",
        "power_base": 6,
        "narrative": "The ground trembles as earthen power channels through the circle. "
                     "Stone and soil answer the call, rising into predetermined forms.",
    },
    "wind": {
        "primary": "Governs air currents and pressure",
        "effects": ["Wind control", "Flight assistance", "Pressure manipulation", "Sound carrying"],
        "classification": "Utility / Ranged",
        "power_base": 5,
        "narrative": "Air spirals inward, bending to the circle's geometry. "
                     "Gusts and breezes become weapons and shields at the caster's direction.",
    },
    "light": {
        "primary": "Produces illumination and radiant energy",
        "effects": ["Illumination", "Purification", "Revelation", "Radiant damage"],
        "classification": "Utility / Purification",
        "power_base": 6,
        "narrative": "Brilliant radiance pours from the circle, banishing shadow and revealing hidden truths. "
                     "The light is warm, absolute, and unwavering.",
    },
    "dark": {
        "primary": "Governs shadow and void",
        "effects": ["Shadow manipulation", "Concealment", "Negation", "Void pockets"],
        "classification": "Stealth / Negation",
        "power_base": 6,
        "narrative": "Darkness pools within the circle's bounds, drinking in light. "
                     "Shadows deepen and move with purpose, whispering secrets of the void.",
    },
    "healing": {
        "primary": "Mends wounds and restores vitality",
        "effects": ["Wound closure", "Pain relief", "Vitality restoration", "Disease resistance"],
        "classification": "Healing (Regulated)",
        "power_base": 4,
        "narrative": "Warm restorative energy flows outward from the circle, knitting flesh and soothing pain. "
                     "The most closely monitored of all magics — for good reason.",
    },
    "creation": {
        "primary": "Brings new forms into existence",
        "effects": ["Material creation", "Form synthesis", "Object conjuration", "Structure building"],
        "classification": "Creation (Dangerous)",
        "power_base": 9,
        "narrative": "Reality shudders as something from nothing takes shape within the circle. "
                     "Creation magic borders on the forbidden — the Brimmed Caps watch for this.",
    },
    "destruction": {
        "primary": "Unmakes and dissolves matter",
        "effects": ["Material dissolution", "Structure weakening", "Disintegration", "Entropy acceleration"],
        "classification": "Destruction (Dangerous)",
        "power_base": 9,
        "narrative": "The circle's energy eats away at whatever it touches, unraveling the very fabric of matter. "
                     "A dangerous art, swiftly punished if used without sanction.",
    },
    "movement": {
        "primary": "Controls displacement and velocity",
        "effects": ["Teleportation", "Kinetic force", "Speed enhancement", "Object propulsion"],
        "classification": "Utility / Transportation",
        "power_base": 6,
        "narrative": "Space folds within the circle's bounds. Distance becomes suggestion, "
                     "velocity becomes will. The caster moves between heartbeats.",
    },
    "transformation": {
        "primary": "Alters the form of objects",
        "effects": ["Shape alteration", "Material transmutation", "Size change", "State shift"],
        "classification": "Transmutation (Body Mod FORBIDDEN)",
        "power_base": 8,
        "narrative": "The circle reshapes what enters its domain, bending form to the caster's intent. "
                     "But NEVER on living flesh — that is the absolute prohibition.",
    },
    "sound": {
        "primary": "Commands vibrations and acoustic phenomena",
        "effects": ["Sound projection", "Silence creation", "Vibration control", "Communication"],
        "classification": "Communication / Utility",
        "power_base": 4,
        "narrative": "The circle sings with controlled resonance, carrying voice across vast distances "
                     "or silencing all sound within its domain.",
    },
    "binding": {
        "primary": "Restricts and constrains",
        "effects": ["Magical contracts", "Seals", "Restraint", "Oath enforcement"],
        "classification": "Binding / Contractual",
        "power_base": 5,
        "narrative": "Invisible chains manifest within the circle's geometry. "
                     "What is bound here cannot break free without equal or greater magic.",
    },
    "barrier": {
        "primary": "Creates protective wards and shields",
        "effects": ["Shield creation", "Ward inscription", "Defensive zones", "Reflection"],
        "classification": "Defensive / Warding",
        "power_base": 6,
        "narrative": "The circle projects an impenetrable barrier, deflecting harm from those within. "
                     "A shield-maiden's art, steadfast and true.",
    },
    "summon": {
        "primary": "Calls forth entities and objects",
        "effects": ["Entity summoning", "Object retrieval", "Familiar calling", "Spirit conjuration"],
        "classification": "Summoning (Requires precise geometry)",
        "power_base": 7,
        "narrative": "The circle opens a conduit, calling something from elsewhere into presence. "
                     "Precision is paramount — a flawed summoning circle invites catastrophe.",
    },
}

COMBINATION_EFFECTS = {
    frozenset(["fire", "water"]): {
        "name": "Steam / Pressure Magic",
        "desc": "Superheated steam and pressure explosions. Combines fluidity with destructive heat.",
        "danger": "Medium-High",
    },
    frozenset(["fire", "wind"]): {
        "name": "Flamestorm",
        "desc": "Devastating fire tornadoes and ranged flame attacks. Wind feeds the fire into an inferno.",
        "danger": "Very High",
    },
    frozenset(["fire", "earth"]): {
        "name": "Magma Control",
        "desc": "Commands molten rock and creates volcanic barriers. Earth channels fire's destructive force.",
        "danger": "High",
    },
    frozenset(["fire", "light"]): {
        "name": "Solar Fire",
        "desc": "Purifying flame that burns away darkness and evil. Radiant conflagration.",
        "danger": "High",
    },
    frozenset(["fire", "dark"]): {
        "name": "Hellfire",
        "desc": "Consuming dark flame that burns without light. Unnatural fire that feeds on shadow.",
        "danger": "Extreme",
    },
    frozenset(["water", "earth"]): {
        "name": "Swamp / Mud Magic",
        "desc": "Terrain control through mud and swamp. Entrapping and transformative.",
        "danger": "Low-Medium",
    },
    frozenset(["water", "wind"]): {
        "name": "Storm Magic",
        "desc": "Summons rainstorms, hurricanes, and lightning. Nature's fury unleashed.",
        "danger": "High",
    },
    frozenset(["water", "light"]): {
        "name": "Purification Waters",
        "desc": "Cleansing waters that purify poison, curse, and corruption. Holy rain.",
        "danger": "Low",
    },
    frozenset(["water", "dark"]): {
        "name": "Drowning Void",
        "desc": "Suffocating darkness carried by water. Abyssal depths given form.",
        "danger": "Very High",
    },
    frozenset(["earth", "wind"]): {
        "name": "Sandstorm / Erosion",
        "desc": "Abrasive wind carrying stone dust. Erosion magic that grinds anything away.",
        "danger": "Medium",
    },
    frozenset(["earth", "light"]): {
        "name": "Crystal Magic",
        "desc": "Precious stone creation and crystal growth. Prismatic barriers and refracted light.",
        "danger": "Low-Medium",
    },
    frozenset(["earth", "dark"]): {
        "name": "Seismic Dark",
        "desc": "Destructive earth tremors cloaked in shadow. Earthquakes from the abyss.",
        "danger": "High",
    },
    frozenset(["wind", "light"]): {
        "name": "Holy Wind",
        "desc": "Divine guidance and supernatural speed. Blessed gales that carry revelation.",
        "danger": "Low",
    },
    frozenset(["wind", "dark"]): {
        "name": "Void Wind",
        "desc": "Cutting vacuum blades and absolute silence. Wind from the space between worlds.",
        "danger": "Very High",
    },
    frozenset(["light", "dark"]): {
        "name": "Twilight Magic",
        "desc": "Balance of opposites. Dawn and dusk given magical form. Paradox made real.",
        "danger": "Extreme",
    },
    frozenset(["healing", "transformation"]): {
        "name": "⚠ FORBIDDEN: Body Modification",
        "desc": "Transformation applied to living flesh. The absolute prohibition of the Great Hall.",
        "danger": "FORBIDDEN",
    },
    frozenset(["creation", "summon"]): {
        "name": "⚠ FORBIDDEN: Creating Life",
        "desc": "Summoning combined with creation to bring sentient life into existence. FORBIDDEN.",
        "danger": "FORBIDDEN",
    },
    frozenset(["healing", "water"]): {
        "name": "Restorative Springs",
        "desc": "Enhanced healing through water channeling. Powerful curative magic.",
        "danger": "Low",
    },
    frozenset(["barrier", "light"]): {
        "name": "Holy Ward",
        "desc": "Radiant protective barrier that repels dark magic and evil entities.",
        "danger": "Low",
    },
    frozenset(["barrier", "earth"]): {
        "name": "Fortress Ward",
        "desc": "Impenetrable stone barrier. The strongest defensive circle short of a keystone seal.",
        "danger": "Low",
    },
    frozenset(["binding", "dark"]): {
        "name": "Dark Seal",
        "desc": "Shadow-binding contracts. Oaths enforced by darkness itself. Difficult to break.",
        "danger": "High",
    },
    frozenset(["destruction", "fire"]): {
        "name": "Annihilation Flame",
        "desc": "Fire that unmakes rather than burns. Matter itself is consumed and erased.",
        "danger": "Extreme",
    },
    frozenset(["movement", "wind"]): {
        "name": "Swift Passage",
        "desc": "Rapid teleportation powered by wind. Movement between heartbeats across vast distances.",
        "danger": "Medium",
    },
    frozenset(["summon", "binding"]): {
        "name": "Controlled Summoning",
        "desc": "Summoned entities are bound by contract. Safer summoning with enforced compliance.",
        "danger": "Medium",
    },
    frozenset(["sound", "wind"]): {
        "name": "Voice of the World",
        "desc": "Sound carried across any distance by wind. Perfect long-range communication magic.",
        "danger": "Low",
    },
    frozenset(["transformation", "creation"]): {
        "name": "Genesis Weaving",
        "desc": "Creation of fully transformed materials. Brings into existence objects of complex design.",
        "danger": "Very High",
    },
}


# ═══════════════════════════════════════════════════════════════
# CUSTOM UNDO/REDO COMMANDS
# ═══════════════════════════════════════════════════════════════

class AddItemCommand(QUndoCommand):
    def __init__(self, scene, item):
        super().__init__("Add Item")
        self._scene = scene
        self._item = item

    def undo(self):
        self._scene.removeItem(self._item)

    def redo(self):
        self._scene.addItem(self._item)


class DeleteItemsCommand(QUndoCommand):
    def __init__(self, scene, items):
        super().__init__("Delete Items")
        self._scene = scene
        self._items = items

    def undo(self):
        for item in self._items:
            self._scene.addItem(item)

    def redo(self):
        for item in self._items:
            self._scene.removeItem(item)


# ═══════════════════════════════════════════════════════════════
# CUSTOM GRAPHICS ITEMS
# ═══════════════════════════════════════════════════════════════

class BaseMagicItem(QGraphicsItem):
    def __init__(self):
        super().__init__()
        self._color = QColor(GOLDEN)
        self._line_width = 2.0
        self._glow = True
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.update()
        elif change == QGraphicsItem.ItemPositionHasChanged:
            if self.scene():
                self.scene().circleChanged.emit()
        return super().itemChange(change, value)

    def get_color(self): return self._color
    def set_color(self, color): self._color = QColor(color); self.update()
    def get_line_width(self): return self._line_width
    def set_line_width(self, w): self._line_width = w; self.update()
    def get_glow(self): return self._glow
    def set_glow(self, v): self._glow = v; self.update()
    def item_type_name(self): return "Base Item"


class FreehandPathItem(BaseMagicItem):
    """Freehand drawn path — can be drawn, selected, and moved alongside shapes."""
    def __init__(self):
        super().__init__()
        self._path = QPainterPath()
        self._min_distance = 3.0

    def item_type_name(self): return "✏ Freehand Drawing"
    def boundingRect(self):
        extra = self._line_width + 12
        br = self._path.boundingRect()
        if br.isEmpty():
            return QRectF(-10, -10, 20, 20)
        return br.adjusted(-extra, -extra, extra, extra)

    def paint(self, painter, option, widget):
        if self._path.elementCount() < 2:
            return
        painter.setRenderHint(QPainter.Antialiasing)
        color = GOLDEN_LIGHT if self.isSelected() else self._color

        if self._glow:
            gc = QColor(color.red(), color.green(), color.blue(), 30)
            painter.setPen(QPen(gc, self._line_width + 6))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(self._path)

        painter.setPen(QPen(color, self._line_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self._path)

    # ---- drawing helpers (called while the user drags) ----
    def start_drawing(self, point):
        self._path = QPainterPath()
        self._path.moveTo(point)

    def continue_drawing(self, point):
        if self._path.elementCount() == 0:
            self._path.moveTo(point)
            return
        last = self._path.currentPosition()
        dx = point.x() - last.x()
        dy = point.y() - last.y()
        if dx * dx + dy * dy >= self._min_distance ** 2:
            self._path.lineTo(point)
            self.prepareGeometryChange()
            self.update()

    def finish_drawing(self):
        self.update()

    def smooth_path(self):
        """Chaikin's corner-cutting smoothing."""
        n = self._path.elementCount()
        if n < 4:
            return
        points = []
        for i in range(n):
            e = self._path.elementAt(i)
            points.append(QPointF(e.x, e.y))
        new_pts = [points[0]]
        for i in range(len(points) - 1):
            p0, p1 = points[i], points[i + 1]
            new_pts.append(QPointF(0.75 * p0.x() + 0.25 * p1.x(),
                                   0.75 * p0.y() + 0.25 * p1.y()))
            new_pts.append(QPointF(0.25 * p0.x() + 0.75 * p1.x(),
                                   0.25 * p0.y() + 0.75 * p1.y()))
        new_pts.append(points[-1])
        np = QPainterPath()
        np.moveTo(new_pts[0])
        for p in new_pts[1:]:
            np.lineTo(p)
        self.prepareGeometryChange()
        self._path = np
        self.update()

    def get_point_count(self): return self._path.elementCount()
    def get_path(self): return self._path


class CircleRingItem(BaseMagicItem):
    def __init__(self, radius=100, ring_type="outer"):
        super().__init__()
        self._radius = max(5, radius)
        self._ring_type = ring_type
        self._dashed = False
        self._double_line = False

    def item_type_name(self): return f"Circle Ring ({self._ring_type})"
    def boundingRect(self):
        r = self._radius + self._line_width + 8
        return QRectF(-r, -r, 2 * r, 2 * r)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        color = GOLDEN_LIGHT if self.isSelected() else self._color
        if self._glow:
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 30), self._line_width + 6))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(0, 0), self._radius, self._radius)
        pen = QPen(color, self._line_width)
        if self._dashed: pen.setDashPattern([6, 4])
        painter.setPen(pen); painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(0, 0), self._radius, self._radius)
        if self._double_line:
            pen2 = QPen(color, self._line_width * 0.6)
            if self._dashed: pen2.setDashPattern([3, 5])
            painter.setPen(pen2)
            painter.drawEllipse(QPointF(0, 0), max(self._radius - 6, 3), max(self._radius - 6, 3))

    def get_radius(self): return self._radius
    def set_radius(self, r): self.prepareGeometryChange(); self._radius = max(5, r); self.update()
    def get_ring_type(self): return self._ring_type
    def get_dashed(self): return self._dashed
    def set_dashed(self, v): self._dashed = v; self.update()
    def get_double_line(self): return self._double_line
    def set_double_line(self, v): self._double_line = v; self.update()


class ConcentricPolygonItem(BaseMagicItem):
    def __init__(self, radius=80, sides=6, step=2, inner_radius_ratio=0.5):
        super().__init__()
        self._radius = max(5, radius); self._sides = max(3, sides)
        self._step = max(1, step)
        self._inner_radius_ratio = max(0.1, min(1.0, inner_radius_ratio))
        self._is_star = (step > 1 and step < sides // 2)

    def item_type_name(self): return "Star/Polygon"
    def boundingRect(self):
        r = self._radius + self._line_width + 8; return QRectF(-r, -r, 2 * r, 2 * r)

    def _build_path(self):
        path = QPainterPath(); r = self._radius; ir = r * self._inner_radius_ratio
        if self._is_star:
            pts = []
            for i in range(self._sides * 2):
                a = math.pi * i / self._sides - math.pi / 2
                rad = ir if i % 2 else r
                pts.append(QPointF(rad * math.cos(a), rad * math.sin(a)))
            path.moveTo(pts[0])
            for p in pts[1:]: path.lineTo(p)
            path.closeSubpath()
        else:
            path.moveTo(r * math.cos(-math.pi / 2), r * math.sin(-math.pi / 2))
            for i in range(1, self._sides):
                a = 2 * math.pi * i / self._sides - math.pi / 2
                path.lineTo(r * math.cos(a), r * math.sin(a))
            path.closeSubpath()
        return path

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        color = GOLDEN_LIGHT if self.isSelected() else self._color
        path = self._build_path()
        if self._glow:
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 30), self._line_width + 6))
            painter.setBrush(Qt.NoBrush); painter.drawPath(path)
        painter.setPen(QPen(color, self._line_width))
        fill = QColor(color); fill.setAlpha(25); painter.setBrush(QBrush(fill)); painter.drawPath(path)

    def get_radius(self): return self._radius
    def set_radius(self, r): self.prepareGeometryChange(); self._radius = max(5, r); self.update()
    def get_sides(self): return self._sides
    def set_sides(self, s): self.prepareGeometryChange(); self._sides = max(3, s); self.update()
    def get_is_star(self): return self._is_star
    def set_is_star(self, v): self._is_star = v; self.update()
    def get_inner_ratio(self): return self._inner_radius_ratio
    def set_inner_ratio(self, r): self.prepareGeometryChange(); self._inner_radius_ratio = r; self.update()


class TextLabelItem(BaseMagicItem):
    def __init__(self, text="Arcane", font_size=16):
        super().__init__(); self._text = text; self._font_size = font_size
        self.setFont(QFont("Segoe UI", font_size))

    def item_type_name(self): return "Text Label"
    def boundingRect(self):
        fm = QFontMetrics(self.font()); r = fm.boundingRect(self._text)
        return QRectF(r.adjusted(-5, -5, 5, 5))

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        color = GOLDEN_LIGHT if self.isSelected() else self._color
        painter.setPen(QPen(color)); painter.setFont(self.font())
        painter.drawText(self.boundingRect().adjusted(5, 5, -5, -5), Qt.AlignCenter, self._text)

    def get_text(self): return self._text
    def set_text(self, t): self._text = t; self.update()
    def get_font_size(self): return self._font_size
    def set_font_size(self, s): self._font_size = s; self.setFont(QFont("Segoe UI", s)); self.prepareGeometryChange(); self.update()


class GlyphItem(BaseMagicItem):
    def __init__(self, glyph_type="fire", size=60):
        super().__init__(); self._glyph_type = glyph_type; self._size = max(10, size)

    def item_type_name(self): return f"Glyph: {GLYPH_NAMES.get(self._glyph_type, self._glyph_type)}"
    def boundingRect(self):
        s = self._size / 2 + self._line_width + 10; return QRectF(-s, -s, 2 * s, 2 * s)

    def _build_path(self):
        path = QPainterPath(); s = self._size / 2; gt = self._glyph_type
        if gt == "fire":
            path.moveTo(0, -s); path.lineTo(s*0.866, s*0.5); path.lineTo(-s*0.866, s*0.5); path.closeSubpath()
            inner = QPainterPath(); inner.moveTo(0, -s*0.35); inner.lineTo(s*0.3, s*0.2); inner.lineTo(-s*0.3, s*0.2); inner.closeSubpath(); path.addPath(inner)
        elif gt == "water":
            path.moveTo(0, s); path.lineTo(s*0.866, -s*0.5); path.lineTo(-s*0.866, -s*0.5); path.closeSubpath()
        elif gt == "earth":
            path.moveTo(0, -s); path.lineTo(s, 0); path.lineTo(0, s); path.lineTo(-s, 0); path.closeSubpath()
        elif gt == "wind":
            for i in range(3):
                y = -s*0.5 + i*s*0.5; arc = QPainterPath(); arc.moveTo(-s*0.7, y)
                arc.cubicTo(-s*0.2, y-s*0.35, s*0.2, y+s*0.35, s*0.7, y); path.addPath(arc)
        elif gt == "light":
            pts_out, pts_in = [], []
            for i in range(8):
                a = i*math.pi/4 - math.pi/2; ia = a + math.pi/8
                pts_out.append(QPointF(s*math.cos(a), s*math.sin(a)))
                pts_in.append(QPointF(s*0.38*math.cos(ia), s*0.38*math.sin(ia)))
            path.moveTo(pts_out[0])
            for i in range(8): path.lineTo(pts_out[i]); path.lineTo(pts_in[i])
            path.closeSubpath()
        elif gt == "dark":
            path.addEllipse(QPointF(0,0), s*0.85, s*0.85); inner = QPainterPath()
            inner.addEllipse(QPointF(s*0.25,0), s*0.55, s*0.55); path.addPath(inner)
        elif gt == "healing":
            w = s*0.22; arm = QPainterPath()
            arm.addRect(-w, -s*0.8, w*2, s*1.6); arm.addRect(-s*0.8, -w, s*1.6, w*2); path.addPath(arm)
        elif gt == "creation":
            for off in [0, math.pi]:
                tri = QPainterPath()
                for i in range(3):
                    a = i*2*math.pi/3 - math.pi/2 + off; x, y = s*0.85*math.cos(a), s*0.85*math.sin(a)
                    if i == 0: tri.moveTo(x, y)
                    else: tri.lineTo(x, y)
                tri.closeSubpath(); path.addPath(tri)
        elif gt == "destruction":
            pts_out, pts_in = [], []
            for i in range(5):
                a = i*2*math.pi/5 - math.pi/2; ia = a + math.pi/5
                pts_out.append(QPointF(s*math.cos(a), s*math.sin(a)))
                pts_in.append(QPointF(s*0.35*math.cos(ia), s*0.35*math.sin(ia)))
            path.moveTo(pts_out[0])
            for i in range(5): path.lineTo(pts_out[i]); path.lineTo(pts_in[i])
            path.closeSubpath()
        elif gt == "movement":
            arr = QPainterPath(); arr.moveTo(s,0); arr.lineTo(s*0.35,-s*0.55); arr.lineTo(s*0.35,-s*0.22)
            arr.lineTo(-s*0.8,-s*0.22); arr.lineTo(-s*0.8,s*0.22); arr.lineTo(s*0.35,s*0.22)
            arr.lineTo(s*0.35,s*0.55); arr.closeSubpath(); path.addPath(arr)
        elif gt == "transformation":
            for sc, rot in [(1.0,0),(0.55,math.pi/4)]:
                d = QPainterPath(); r = s*0.85*sc; d.moveTo(0,-r); d.lineTo(r,0); d.lineTo(0,r); d.lineTo(-r,0)
                d.closeSubpath(); t = QTransform(); t.rotateRadians(rot); path.addPath(t.map(d))
        elif gt == "sound":
            path.addEllipse(QPointF(0,0), s*0.85, s*0.85); path.addEllipse(QPointF(0,0), s*0.5, s*0.5)
        elif gt == "binding":
            for i in range(3):
                c = QPainterPath(); x = -s*0.5 + i*s*0.5; c.addEllipse(QPointF(x,0), s*0.22, s*0.3); path.addPath(c)
        elif gt == "barrier":
            sh = QPainterPath(); sh.moveTo(0,-s); sh.lineTo(s*0.8,-s*0.45); sh.lineTo(s*0.75,s*0.15)
            sh.cubicTo(s*0.55,s*0.55,s*0.2,s*0.85,0,s)
            sh.cubicTo(-s*0.2,s*0.85,-s*0.55,s*0.55,-s*0.75,s*0.15)
            sh.lineTo(-s*0.8,-s*0.45); sh.closeSubpath(); path.addPath(sh)
        elif gt == "summon":
            path.addEllipse(QPointF(0,0), s*0.85, s*0.85); path.addEllipse(QPointF(0,0), s*0.5, s*0.5)
            arr = QPainterPath(); arr.moveTo(0,-s*0.9); arr.lineTo(s*0.25,-s*0.5); arr.lineTo(s*0.08,-s*0.5)
            arr.lineTo(s*0.08,s*0.4); arr.lineTo(-s*0.08,s*0.4); arr.lineTo(-s*0.08,-s*0.5)
            arr.lineTo(-s*0.25,-s*0.5); arr.closeSubpath(); path.addPath(arr)
        return path

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        color = GOLDEN_LIGHT if self.isSelected() else self._color
        gp = self._build_path()
        if self._glow:
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 25), self._line_width + 6))
            painter.setBrush(Qt.NoBrush); painter.drawPath(gp)
        painter.setPen(QPen(color, self._line_width)); fill = QColor(color); fill.setAlpha(35)
        painter.setBrush(QBrush(fill)); painter.drawPath(gp)

    def get_glyph_type(self): return self._glyph_type
    def set_glyph_type(self, t): self._glyph_type = t; self.update()
    def get_size(self): return self._size
    def set_size(self, v): self.prepareGeometryChange(); self._size = max(10, v); self.update()


class RuneTextItem(BaseMagicItem):
    def __init__(self, radius=90, text="ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉ"):
        super().__init__(); self._radius = max(10, radius); self._text = text; self._spacing = 12.0

    def item_type_name(self): return "Rune Text Ring"
    def boundingRect(self): r = self._radius + 28; return QRectF(-r, -r, 2*r, 2*r)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        color = GOLDEN_LIGHT if self.isSelected() else self._color
        font = QFont("Segoe UI Symbol", 11); painter.setFont(font)
        for i, ch in enumerate(self._text):
            a = math.radians(i * self._spacing - 90)
            x = self._radius * math.cos(a); y = self._radius * math.sin(a)
            if self._glow:
                painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 25), 4))
                painter.drawText(QRectF(x-8, y-8, 16, 16), Qt.AlignCenter, ch)
            painter.save(); painter.translate(x, y); painter.rotate(math.degrees(a) + 90)
            painter.setPen(QPen(color, 1)); painter.drawText(QRectF(-8,-8,16,16), Qt.AlignCenter, ch); painter.restore()

    def get_radius(self): return self._radius
    def set_radius(self, r): self.prepareGeometryChange(); self._radius = max(10, r); self.update()
    def get_text(self): return self._text
    def set_text(self, t): self._text = t; self.update()
    def get_spacing(self): return self._spacing
    def set_spacing(self, s): self._spacing = s; self.update()


class DotRingItem(BaseMagicItem):
    def __init__(self, radius=80, count=12, dot_size=3.0):
        super().__init__(); self._radius = max(10, radius); self._count = max(3, count); self._dot_size = max(1, dot_size)

    def item_type_name(self): return "Dot Ring"
    def boundingRect(self): r = self._radius + self._dot_size + 6; return QRectF(-r, -r, 2*r, 2*r)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        color = GOLDEN_LIGHT if self.isSelected() else self._color; painter.setPen(Qt.NoPen)
        for i in range(self._count):
            a = i * 2 * math.pi / self._count; x = self._radius * math.cos(a); y = self._radius * math.sin(a)
            if self._glow:
                painter.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 40)))
                painter.drawEllipse(QPointF(x,y), self._dot_size+2, self._dot_size+2)
            painter.setBrush(QBrush(color)); painter.drawEllipse(QPointF(x,y), self._dot_size, self._dot_size)

    def get_radius(self): return self._radius
    def set_radius(self, r): self.prepareGeometryChange(); self._radius = max(10, r); self.update()
    def get_count(self): return self._count
    def set_count(self, c): self._count = max(3, c); self.update()
    def get_dot_size(self): return self._dot_size
    def set_dot_size(self, s): self.prepareGeometryChange(); self._dot_size = max(1, s); self.update()


class ArcSegmentItem(BaseMagicItem):
    def __init__(self, radius=95, start_angle=0, span_angle=60):
        super().__init__(); self._radius = max(10, radius); self._start_angle = start_angle; self._span_angle = span_angle

    def item_type_name(self): return "Arc Segment"
    def boundingRect(self): r = self._radius + self._line_width + 8; return QRectF(-r, -r, 2*r, 2*r)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        color = GOLDEN_LIGHT if self.isSelected() else self._color
        rect = QRectF(-self._radius, -self._radius, 2*self._radius, 2*self._radius)
        if self._glow:
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 25), self._line_width + 4))
            painter.setBrush(Qt.NoBrush); painter.drawArc(rect, int(self._start_angle*16), int(self._span_angle*16))
        painter.setPen(QPen(color, self._line_width)); painter.setBrush(Qt.NoBrush)
        painter.drawArc(rect, int(self._start_angle*16), int(self._span_angle*16))

    def get_radius(self): return self._radius
    def set_radius(self, r): self.prepareGeometryChange(); self._radius = max(10, r); self.update()
    def get_start_angle(self): return self._start_angle
    def set_start_angle(self, a): self._start_angle = a; self.update()
    def get_span_angle(self): return self._span_angle
    def set_span_angle(self, a): self._span_angle = a; self.update()


class RadialLineItem(BaseMagicItem):
    def __init__(self, angle=0, inner_radius=30, outer_radius=140):
        super().__init__(); self._angle = angle; self._inner_radius = max(0, inner_radius); self._outer_radius = max(5, outer_radius)

    def item_type_name(self): return "Radial Line"
    def boundingRect(self): r = self._outer_radius + self._line_width + 8; return QRectF(-r, -r, 2*r, 2*r)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        color = GOLDEN_LIGHT if self.isSelected() else self._color
        a = math.radians(self._angle)
        p1 = QPointF(self._inner_radius*math.cos(a), self._inner_radius*math.sin(a))
        p2 = QPointF(self._outer_radius*math.cos(a), self._outer_radius*math.sin(a))
        if self._glow:
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 25), self._line_width + 4)); painter.drawLine(p1, p2)
        painter.setPen(QPen(color, self._line_width)); painter.drawLine(p1, p2)

    def get_angle(self): return self._angle
    def set_angle(self, a): self._angle = a; self.update()
    def get_inner_radius(self): return self._inner_radius
    def set_inner_radius(self, r): self._inner_radius = max(0, r); self.update()
    def get_outer_radius(self): return self._outer_radius
    def set_outer_radius(self, r): self.prepareGeometryChange(); self._outer_radius = max(5, r); self.update()


class KeystoneItem(BaseMagicItem):
    def __init__(self, size=45): super().__init__(); self._size = max(10, size)
    def item_type_name(self): return "Keystone"
    def boundingRect(self): s = self._size/2 + self._line_width + 10; return QRectF(-s, -s, 2*s, 2*s)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing); color = GOLDEN_LIGHT if self.isSelected() else self._color; s = self._size/2
        if self._glow:
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 25), self._line_width + 8))
            painter.setBrush(Qt.NoBrush); painter.drawEllipse(QPointF(0,0), s, s)
        painter.setPen(QPen(color, self._line_width)); fill = QColor(color); fill.setAlpha(40)
        painter.setBrush(QBrush(fill)); painter.drawEllipse(QPointF(0,0), s, s)
        painter.setBrush(Qt.NoBrush); painter.setPen(QPen(color, self._line_width*0.7))
        for off in [0, math.pi]:
            path = QPainterPath()
            for i in range(3):
                a = i*2*math.pi/3 - math.pi/2 + off; x = s*0.55*math.cos(a); y = s*0.55*math.sin(a)
                if i == 0: path.moveTo(x, y)
                else: path.lineTo(x, y)
            path.closeSubpath(); painter.drawPath(path)
        painter.setPen(Qt.NoPen); painter.setBrush(QBrush(color)); painter.drawEllipse(QPointF(0,0), 3, 3)

    def get_size(self): return self._size
    def set_size(self, s): self.prepareGeometryChange(); self._size = max(10, s); self.update()


# ═══════════════════════════════════════════════════════════════
# CUSTOM SCENE WITH SIGNALS
# ═══════════════════════════════════════════════════════════════

class MagicCircleScene(QGraphicsScene):
    circleChanged = Signal()

    def addItem(self, item):
        super().addItem(item); self.circleChanged.emit()

    def removeItem(self, item):
        super().removeItem(item); self.circleChanged.emit()


# ═══════════════════════════════════════════════════════════════
# COMPONENT PALETTE
# ═══════════════════════════════════════════════════════════════

class ComponentPalette(QWidget):
    item_requested = Signal(str, dict)
    draw_mode_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(210); self.setMaximumWidth(260); self._build_ui()

    def _make_btn(self, label, callback):
        btn = QPushButton(label); btn.setCursor(Qt.PointingHandCursor); btn.clicked.connect(callback); return btn

    def _build_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(4, 4, 4, 4); layout.setSpacing(4)
        title = QLabel("✦ Components"); title.setStyleSheet("font-size:15px; font-weight:bold; color:#d0af3f; padding:4px;")
        layout.addWidget(title)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget(); inner_layout = QVBoxLayout(inner); inner_layout.setSpacing(8)

        # ---- Drawing Section ----
        draw_grp = QGroupBox("✏ Drawing"); draw_lay = QVBoxLayout(); draw_lay.setSpacing(3)
        draw_btn = self._make_btn("✏ Freehand Draw", lambda: self.draw_mode_requested.emit())
        draw_btn.setStyleSheet("background:#2a3a22; color:#88dd88; font-weight:bold; padding:6px; border:2px solid #446633; border-radius:4px;")
        draw_lay.addWidget(draw_btn)
        hint = QLabel("Click & drag on canvas\nto draw freehand lines.\nSwitch back to Select\nmode to move shapes.")
        hint.setStyleSheet("color:#888; font-size:10px; padding:2px 6px;"); hint.setWordWrap(True)
        draw_lay.addWidget(hint)
        draw_grp.setLayout(draw_lay); inner_layout.addWidget(draw_grp)

        # Circles
        circ_grp = QGroupBox("◯ Circle Rings"); circ_lay = QVBoxLayout(); circ_lay.setSpacing(3)
        for label, rtype in [("Outer Ring","outer"),("Inner Ring","inner"),("Third Ring","third"),("Decorative Ring","decorative")]:
            circ_lay.addWidget(self._make_btn(label, lambda _, t=rtype: self.item_requested.emit("circle", {"ring_type": t})))
        circ_grp.setLayout(circ_lay); inner_layout.addWidget(circ_grp)

        # Shapes
        shape_grp = QGroupBox("⬡ Shapes"); shape_lay = QVBoxLayout(); shape_lay.setSpacing(3)
        for label, sides, star in [("Triangle",3,False),("Square",4,False),("Pentagram",5,True),("Hexagram",6,True),("Octagon",8,False)]:
            shape_lay.addWidget(self._make_btn(label, lambda _, s=sides, st=star: self.item_requested.emit("shape", {"sides": s, "is_star": st})))
        shape_grp.setLayout(shape_lay); inner_layout.addWidget(shape_grp)

        # Glyphs
        glyph_grp = QGroupBox("✧ Glyphs"); glyph_lay = QVBoxLayout(); glyph_lay.setSpacing(3)
        for gtype, gname in GLYPH_NAMES.items():
            color = GLYPH_COLORS.get(gtype, "#ccc")
            btn = self._make_btn(gname, lambda _, t=gtype: self.item_requested.emit("glyph", {"glyph_type": t}))
            btn.setStyleSheet(btn.styleSheet() + f"border-left: 3px solid {color};")
            glyph_lay.addWidget(btn)
        glyph_grp.setLayout(glyph_lay); inner_layout.addWidget(glyph_grp)

        # Decorations
        deco_grp = QGroupBox("❖ Decorations"); deco_lay = QVBoxLayout(); deco_lay.setSpacing(3)
        for label, dtype in [("Rune Text Ring","rune_text"),("Dot Ring","dot_ring"),("Arc Segment","arc"),("Radial Line","radial_line"),("Keystone","keystone"),("Text Label","text")]:
            deco_lay.addWidget(self._make_btn(label, lambda _, t=dtype: self.item_requested.emit("decoration", {"deco_type": t})))
        deco_grp.setLayout(deco_lay); inner_layout.addWidget(deco_grp)

        inner_layout.addStretch(); scroll.setWidget(inner); layout.addWidget(scroll)


# ═══════════════════════════════════════════════════════════════
# PROPERTIES PANEL
# ═══════════════════════════════════════════════════════════════

class PropertiesPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(260); self.setMaximumWidth(320)
        self._current_item = None; self._building = False; self._build_ui()

    def _build_ui(self):
        self._main_layout = QVBoxLayout(self); self._main_layout.setContentsMargins(4, 4, 4, 4)
        self._title = QLabel("✦ Properties"); self._title.setStyleSheet("font-size:15px; font-weight:bold; color:#d0af3f; padding:4px;")
        self._main_layout.addWidget(self._title)
        self._info_label = QLabel("Select an item to edit."); self._info_label.setWordWrap(True); self._info_label.setStyleSheet("color:#999; padding:8px;")
        self._main_layout.addWidget(self._info_label)
        self._scroll = QScrollArea(); self._scroll.setWidgetResizable(True); self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._form_widget = QWidget(); self._form_layout = QFormLayout(self._form_widget); self._form_layout.setContentsMargins(4, 4, 4, 4); self._form_layout.setSpacing(6)
        self._scroll.setWidget(self._form_widget); self._scroll.hide()
        self._main_layout.addWidget(self._scroll); self._main_layout.addStretch()

    def set_item(self, item): self._current_item = item; self._rebuild_form()

    def _add_spin(self, label, value, min_v, max_v, step=1.0, callback=None):
        spin = QDoubleSpinBox(); spin.setRange(min_v, max_v); spin.setSingleStep(step); spin.setValue(value)
        if callback: spin.valueChanged.connect(lambda v: callback(v) if not self._building else None)
        self._form_layout.addRow(label, spin); return spin

    def _add_int_spin(self, label, value, min_v, max_v, callback=None):
        spin = QSpinBox(); spin.setRange(min_v, max_v); spin.setValue(value)
        if callback: spin.valueChanged.connect(lambda v: callback(v) if not self._building else None)
        self._form_layout.addRow(label, spin); return spin

    def _add_check(self, label, value, callback=None):
        cb = QCheckBox(); cb.setChecked(value)
        if callback: cb.toggled.connect(lambda v: callback(v) if not self._building else None)
        self._form_layout.addRow(label, cb); return cb

    def _add_color_btn(self, item):
        color_btn = QPushButton(); color_btn.setFixedSize(60, 24)
        color_btn.setStyleSheet(f"background-color:{item.get_color().name()}; border:1px solid #666; border-radius:3px;")
        def pick():
            c = QColorDialog.getColor(item.get_color(), self, "Item Color")
            if c.isValid(): item.set_color(c); color_btn.setStyleSheet(f"background-color:{c.name()}; border:1px solid #666; border-radius:3px;")
        color_btn.clicked.connect(pick); self._form_layout.addRow("Color:", color_btn)

    def _rebuild_form(self):
        self._building = True
        while self._form_layout.count():
            child = self._form_layout.takeAt(0); w = child.widget()
            if w: w.setParent(None); w.deleteLater()

        item = self._current_item
        if item is None:
            self._scroll.hide(); self._info_label.show(); self._building = False; return

        self._info_label.hide(); self._scroll.show()
        type_label = QLabel(item.item_type_name()); type_label.setStyleSheet("font-weight:bold; color:#d0af3f;")
        self._form_layout.addRow("Type:", type_label)
        self._add_spin("X:", item.pos().x(), -2000, 2000, 1.0, lambda v: item.setX(v))
        self._add_spin("Y:", item.pos().y(), -2000, 2000, 1.0, lambda v: item.setY(v))
        self._add_spin("Rotation:", item.rotation(), -360, 360, 5.0, lambda v: item.setRotation(v))
        self._add_spin("Line Width:", item.get_line_width(), 0.5, 10, 0.5, item.set_line_width)
        self._add_check("Glow:", item.get_glow(), item.set_glow)
        self._add_color_btn(item)

        sep = QLabel("─" * 30); sep.setStyleSheet("color:#444; font-size:10px;"); self._form_layout.addRow(sep)

        if isinstance(item, FreehandPathItem):
            self._add_spin("Draw Width:", item.get_line_width(), 0.5, 12, 0.5, item.set_line_width)
            pt_label = QLabel(str(item.get_point_count())); pt_label.setStyleSheet("color:#aaa;")
            self._form_layout.addRow("Points:", pt_label)
            smooth_btn = QPushButton("〰 Smooth Path")
            smooth_btn.setStyleSheet("padding:5px; font-weight:bold; background:#223344; color:#88ccff; border-radius:4px;")
            smooth_btn.clicked.connect(item.smooth_path)
            self._form_layout.addRow(smooth_btn)
        elif isinstance(item, CircleRingItem):
            self._add_spin("Radius:", item.get_radius(), 5, 500, 1.0, item.set_radius)
            self._add_check("Dashed:", item.get_dashed(), item.set_dashed)
            self._add_check("Double Line:", item.get_double_line(), item.set_double_line)
        elif isinstance(item, ConcentricPolygonItem):
            self._add_spin("Radius:", item.get_radius(), 5, 500, 1.0, item.set_radius)
            self._add_int_spin("Sides:", item.get_sides(), 3, 20, item.set_sides)
            self._add_check("Is Star:", item.get_is_star(), item.set_is_star)
            self._add_spin("Inner Ratio:", item.get_inner_ratio(), 0.1, 1.0, 0.05, item.set_inner_ratio)
        elif isinstance(item, GlyphItem):
            self._add_spin("Size:", item.get_size(), 10, 200, 1.0, item.set_size)
            type_combo = QComboBox()
            for k, v in GLYPH_NAMES.items(): type_combo.addItem(v, k)
            keys = list(GLYPH_NAMES.keys())
            if item.get_glyph_type() in keys: type_combo.setCurrentIndex(keys.index(item.get_glyph_type()))
            type_combo.currentIndexChanged.connect(lambda i: item.set_glyph_type(type_combo.itemData(i)) if not self._building else None)
            self._form_layout.addRow("Glyph:", type_combo)
        elif isinstance(item, TextLabelItem):
            text_edit = QLineEdit(item.get_text()); text_edit.textChanged.connect(lambda v: item.set_text(v) if not self._building else None)
            self._form_layout.addRow("Text:", text_edit)
            self._add_int_spin("Font Size:", item.get_font_size(), 8, 72, item.set_font_size)
        elif isinstance(item, RuneTextItem):
            self._add_spin("Radius:", item.get_radius(), 10, 500, 1.0, item.set_radius)
            text_edit = QLineEdit(item.get_text()); text_edit.textChanged.connect(lambda v: item.set_text(v) if not self._building else None)
            self._form_layout.addRow("Text:", text_edit)
            self._add_spin("Spacing:", item.get_spacing(), 3, 40, 0.5, item.set_spacing)
        elif isinstance(item, DotRingItem):
            self._add_spin("Radius:", item.get_radius(), 10, 500, 1.0, item.set_radius)
            self._add_int_spin("Count:", item.get_count(), 3, 60, item.set_count)
            self._add_spin("Dot Size:", item.get_dot_size(), 1, 15, 0.5, item.set_dot_size)
        elif isinstance(item, ArcSegmentItem):
            self._add_spin("Radius:", item.get_radius(), 10, 500, 1.0, item.set_radius)
            self._add_spin("Start Angle:", item.get_start_angle(), 0, 360, 5.0, item.set_start_angle)
            self._add_spin("Span Angle:", item.get_span_angle(), 1, 360, 5.0, item.set_span_angle)
        elif isinstance(item, RadialLineItem):
            self._add_spin("Angle:", item.get_angle(), 0, 360, 5.0, item.set_angle)
            self._add_spin("Inner R:", item.get_inner_radius(), 0, 500, 1.0, item.set_inner_radius)
            self._add_spin("Outer R:", item.get_outer_radius(), 5, 500, 1.0, item.set_outer_radius)
        elif isinstance(item, KeystoneItem):
            self._add_spin("Size:", item.get_size(), 10, 200, 1.0, item.set_size)

        snap_btn = QPushButton("⊕ Snap to Center")
        snap_btn.setStyleSheet("padding:6px; font-weight:bold; background:#223355; color:#88bbff; border-radius:4px;")
        snap_btn.clicked.connect(lambda: item.setPos(0, 0)); self._form_layout.addRow(snap_btn)

        del_btn = QPushButton("🗑 Delete Item")
        del_btn.setStyleSheet("background-color:#552222; color:#ffaaaa; padding:8px; font-weight:bold; border-radius:4px;")
        del_btn.clicked.connect(self._delete_item); self._form_layout.addRow(del_btn)
        self._building = False

    def _delete_item(self):
        if self._current_item and self._current_item.scene():
            self._current_item.scene().removeItem(self._current_item)
            self._current_item = None; self._rebuild_form()


# ═══════════════════════════════════════════════════════════════
# REFERENCE & SPELL ANALYSIS
# ═══════════════════════════════════════════════════════════════

class ReferencePanel(QWidget):
    def __init__(self):
        super().__init__(); self._build_ui()
    def _build_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(2, 2, 2, 2); tabs = QTabWidget()
        overview = QTextBrowser(); overview.setHtml("<h2 style='color:#d0af3f;'>🔮 Magic System</h2><p>Magic is drawn. The circle must be closed. Glyphs define the spell. Body mod is forbidden.</p>")
        anatomy = QTextBrowser(); anatomy.setHtml("<h2 style='color:#d0af3f;'>⭕ Anatomy</h2><p>Outer Ring, Inner Rings, Glyphs, Keystone, Lines, Runes.</p>")
        elements = QTextBrowser(); elem_html = "<h2 style='color:#d0af3f;'>✧ Elements</h2>"
        for gtype, gname in GLYPH_NAMES.items():
            desc = GLYPH_DESCRIPTIONS.get(gtype, ""); color = GLYPH_COLORS.get(gtype, "#ccc")
            elem_html += f"<h3 style='color:{color};'>{gname}</h3><p>{desc}</p>"
        elements.setHtml(elem_html)
        forbidden = QTextBrowser(); forbidden.setHtml("<h2 style='color:#ff4444;'>⚠ Forbidden</h2><p>Body Modification, Memory Manipulation, Resurrection, Creating Life, Time Manipulation.</p>")
        tabs.addTab(overview, "Overview"); tabs.addTab(anatomy, "Anatomy"); tabs.addTab(elements, "Elements"); tabs.addTab(forbidden, "⚠ Forbidden")
        layout.addWidget(tabs)


class SpellAnalysisWidget(QWidget):
    """Enhanced spell analysis with detailed 'What does this circle do?' descriptions."""

    def __init__(self):
        super().__init__(); self._scene = None; self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(4, 4, 4, 4)
        title = QLabel("✦ Circle Analysis & Description"); title.setStyleSheet("font-size:14px; font-weight:bold; color:#d0af3f; padding:4px;")
        layout.addWidget(title)

        btn_row = QHBoxLayout()
        analyze_btn = QPushButton("🔍 Analyze"); analyze_btn.setStyleSheet("padding:6px; font-weight:bold;"); analyze_btn.setCursor(Qt.PointingHandCursor); analyze_btn.clicked.connect(self._do_analysis)
        desc_btn = QPushButton("📖 What Does It Do?"); desc_btn.setStyleSheet("padding:6px; font-weight:bold; background:#2a2a44; color:#ffcc44; border:1px solid #555; border-radius:4px;"); desc_btn.setCursor(Qt.PointingHandCursor); desc_btn.clicked.connect(self._do_detailed_description)
        btn_row.addWidget(analyze_btn); btn_row.addWidget(desc_btn)
        layout.addLayout(btn_row)

        self._analysis_text = QTextBrowser(); self._analysis_text.setMaximumHeight(200)
        self._analysis_text.setHtml("<p style='color:#999;'>Build your circle to see analysis.</p>")
        layout.addWidget(self._analysis_text)

        self._description_text = QTextBrowser(); self._description_text.setMinimumHeight(220)
        self._description_text.setHtml("<p style='color:#999;'>Click <b>📖 What Does It Do?</b> for a detailed description of your magic circle.</p>")
        layout.addWidget(self._description_text)

    def set_scene(self, scene): self._scene = scene

    def _scan_scene(self):
        """Scan the scene and return categorized items."""
        glyphs, rings, has_keystone, rune_count, arc_count, radial_count, drawings = [], [], False, 0, 0, 0, 0
        shapes, dot_rings, texts = [], [], []
        for item in self._scene.items():
            if isinstance(item, GlyphItem): glyphs.append(item.get_glyph_type())
            elif isinstance(item, CircleRingItem): rings.append(item.get_ring_type())
            elif isinstance(item, KeystoneItem): has_keystone = True
            elif isinstance(item, RuneTextItem): rune_count += 1
            elif isinstance(item, ArcSegmentItem): arc_count += 1
            elif isinstance(item, RadialLineItem): radial_count += 1
            elif isinstance(item, FreehandPathItem): drawings += 1
            elif isinstance(item, ConcentricPolygonItem): shapes.append(item)
            elif isinstance(item, DotRingItem): dot_rings.append(item)
            elif isinstance(item, TextLabelItem): texts.append(item)
        return {
            "glyphs": glyphs, "rings": rings, "has_keystone": has_keystone,
            "rune_count": rune_count, "arc_count": arc_count, "radial_count": radial_count,
            "drawings": drawings, "shapes": shapes, "dot_rings": dot_rings, "texts": texts,
        }

    def _do_analysis(self):
        if not self._scene: return
        d = self._scan_scene()
        glyphs, rings, has_keystone = d["glyphs"], d["rings"], d["has_keystone"]

        if not glyphs and not rings:
            self._analysis_text.setHtml("<p style='color:#999;'>The circle is empty.</p>"); return

        html = "<h3 style='color:#d0af3f;'>Analysis</h3>"
        forbidden, glyph_set = False, set(glyphs)
        for combo_set, name, desc in [
            ({"transformation","healing"}, "Body Mod", "Transformation + Healing is FORBIDDEN."),
            ({"creation","summon"}, "Creating Life", "Creation + Summon is FORBIDDEN."),
        ]:
            if combo_set.issubset(glyph_set):
                forbidden = True; html += f"<div style='background:#3a1111; border:1px solid #ff4444; padding:6px; border-radius:4px;'><b style='color:#ff4444;'>⚠ FORBIDDEN: {name}</b><br><span style='color:#ffaaaa;'>{desc}</span></div>"

        element_names = [GLYPH_NAMES.get(g, g) for g in glyphs]
        html += f"<p><b>Elements:</b> {', '.join(element_names) if element_names else 'None'}</p>"
        stability, stab_color = "Unstable", "#ff4444"
        if has_keystone and len(rings) >= 2 and len(glyphs) >= 1: stability, stab_color = "Stable", "#44ff44"
        elif len(rings) >= 1 and len(glyphs) >= 1: stability, stab_color = "Partial", "#ffaa44"
        html += f"<p><b>Stability:</b> <span style='color:{stab_color};'>{stability}</span></p>"
        html += f"<p><b>Structure:</b> {len(rings)} ring(s), {d['arc_count']} arc(s), {d['radial_count']} line(s), {d['rune_count']} rune(s)"
        if d['drawings']: html += f", {d['drawings']} freehand stroke(s)"
        html += "</p>"

        if glyphs:
            prefixes = {"fire":"Ignis","water":"Aqua","earth":"Terra","wind":"Ventus","light":"Lux","dark":"Umbra","healing":"Vita","creation":"Genesis","destruction":"Ruin","movement":"Celerity","transformation":"Mutare","sound":"Echonus","binding":"Vinculum","barrier":"Aegis","summon":"Evocare"}
            name = prefixes.get(glyphs[0], "Arcane") + (" Ritual" if has_keystone else " Circle")
            name_color = "#ff4444" if forbidden else "#d0af3f"
            html += f"<p><b style='color:{name_color};'>Spell: {name}</b></p>"
        self._analysis_text.setHtml(html)

    # ──────────────────────────────────────────────────────
    #  DETAILED "What Does It Do?" DESCRIPTION
    # ──────────────────────────────────────────────────────
    def _do_detailed_description(self):
        if not self._scene: return
        d = self._scan_scene()
        glyphs, rings, has_keystone = d["glyphs"], d["rings"], d["has_keystone"]

        if not glyphs and not rings:
            self._description_text.setHtml(
                "<div style='padding:10px;'><h3 style='color:#888;'>Empty Circle</h3>"
                "<p style='color:#999;'>This circle has no glyphs or rings yet. Add components "
                "to define what the magic circle does.</p></div>")
            return

        glyph_set = set(glyphs)
        html = '<div style="padding:6px;">'

        # ── Header ──
        html += "<h3 style='color:#d0af3f;'>🔮 What Does This Magic Circle Do?</h3>"

        # ── Forbidden check ──
        forbidden_combos = []
        for combo_set, info in COMBINATION_EFFECTS.items():
            if "FORBIDDEN" in info.get("name", "") and combo_set.issubset(glyph_set):
                forbidden_combos.append(info)
        direct_forbidden = {"transformation"} if "transformation" in glyph_set else set()

        if forbidden_combos or direct_forbidden:
            html += "<div style='background:#3a1111; border:2px solid #ff4444; padding:8px; border-radius:6px; margin-bottom:8px;'>"
            html += "<h4 style='color:#ff4444; margin:0;'>⚠ FORBIDDEN MAGIC DETECTED</h4>"
            for fc in forbidden_combos:
                html += f"<p style='color:#ffaaaa;'><b>{fc['name']}</b>: {fc['desc']}</p>"
            if "transformation" in glyph_set:
                html += "<p style='color:#ffaaaa;'><b>Transformation Glyph</b>: Using this on living beings is absolutely FORBIDDEN by the Great Hall.</p>"
            html += "<p style='color:#ff8888; font-style:italic;'>The Brimmed Caps would take great interest in this circle...</p>"
            html += "</div>"

        # ── Primary Spell Type ──
        primary = glyphs[0] if glyphs else None
        if primary and primary in SPELL_EFFECTS:
            se = SPELL_EFFECTS[primary]
            html += f"<h4 style='color:{GLYPH_COLORS.get(primary, '#ccc')};'>Primary Effect: {se['primary']}</h4>"
            html += f"<p><b>Classification:</b> {se['classification']}</p>"
            html += "<p><b>Capabilities:</b></p><ul>"
            for eff in se["effects"]:
                html += f"<li style='color:#ccc;'>{eff}</li>"
            html += "</ul>"

        # ── Multiple glyphs ──
        if len(glyphs) > 1:
            html += "<h4 style='color:#ddaa44;'>Combined Elements</h4>"
            unique = list(dict.fromkeys(glyphs))  # preserve order, remove dupes
            found_combo = False
            for i in range(len(unique)):
                for j in range(i + 1, len(unique)):
                    key = frozenset([unique[i], unique[j]])
                    if key in COMBINATION_EFFECTS:
                        ce = COMBINATION_EFFECTS[key]
                        danger_color = "#ff4444" if "FORBIDDEN" in ce.get("danger", "") else \
                                       "#ff8844" if "Extreme" in ce.get("danger", "") else \
                                       "#ffaa44" if "High" in ce.get("danger", "") else "#88cc88"
                        html += f"<div style='background:#1a1a2e; border-left:3px solid {danger_color}; padding:6px; margin:4px 0; border-radius:3px;'>"
                        html += f"<b style='color:{danger_color};'>{ce['name']}</b><br>"
                        html += f"<span style='color:#bbb;'>{ce['desc']}</span><br>"
                        html += f"<span style='color:{danger_color}; font-size:11px;'>Danger: {ce['danger']}</span>"
                        html += "</div>"
                        found_combo = True
            if not found_combo:
                html += "<p style='color:#999; font-style:italic;'>No known combination effects for these element pairs. "
                html += "The interaction is unpredictable — experiment with caution.</p>"
            if len(unique) > 2:
                html += f"<p style='color:#ddaa88;'>⚠ This circle weaves <b>{len(unique)} elements</b> together. "
                html += "Multi-element circles require precise geometry to prevent magical backlash.</p>"

        # ── All glyph descriptions ──
        if len(glyphs) > 1:
            html += "<h4 style='color:#aaa;'>Element Breakdown</h4>"
            for g in dict.fromkeys(glyphs):
                se = SPELL_EFFECTS.get(g)
                if se:
                    gc = GLYPH_COLORS.get(g, "#ccc")
                    html += f"<p style='color:{gc};'><b>{GLYPH_NAMES.get(g, g)}</b>: {se['primary']}</p>"

        # ── Structural assessment ──
        html += "<h4 style='color:#88aacc;'>Structural Assessment</h4>"

        # Stability
        if has_keystone and len(rings) >= 2:
            stability = "Stable"; stab_color = "#44ff44"; stab_desc = "The keystone anchors the spell and the multiple rings contain the magical flow properly."
        elif len(rings) >= 2:
            stability = "Moderately Stable"; stab_color = "#aadd44"; stab_desc = "Multiple rings provide containment, but without a keystone the spell may waver."
        elif len(rings) >= 1:
            stability = "Partially Stable"; stab_color = "#ffaa44"; stab_desc = "A single ring provides minimal containment. Add more rings or a keystone for safety."
        else:
            stability = "Unstable"; stab_color = "#ff6644"; stab_desc = "No containment rings! The spell energy has no defined boundary. DANGEROUS."

        html += f"<p><b>Stability:</b> <span style='color:{stab_color};'>{stability}</span></p>"
        html += f"<p style='color:#999; font-size:11px;'>{stab_desc}</p>"

        # Power level
        power = sum(SPELL_EFFECTS.get(g, {}).get("power_base", 5) for g in dict.fromkeys(glyphs))
        if has_keystone: power += 3
        power += len(rings) * 2
        power += d["rune_count"] * 1
        power += d["radial_count"] * 0.5
        power = min(power, 50)

        if power >= 30: plevel, pcolor = "Extremely Powerful", "#ff4444"
        elif power >= 20: plevel, pcolor = "Very Powerful", "#ff8844"
        elif power >= 14: plevel, pcolor = "Powerful", "#ffaa44"
        elif power >= 8: plevel, pcolor = "Moderate", "#88cc88"
        else: plevel, pcolor = "Weak", "#88aacc"
        bar_len = min(int(power / 50 * 20), 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        html += f"<p><b>Power Level:</b> <span style='color:{pcolor};'>{plevel}</span> ({power:.0f})</p>"
        html += f"<p style='font-family:monospace; color:{pcolor}; font-size:11px;'>[{bar}]</p>"

        # Components breakdown
        html += "<p style='color:#999; font-size:11px;'>"
        html += f"Rings: {len(rings)}"
        if rings: html += f" ({', '.join(rings)})"
        html += f" | Keystone: {'Yes ✦' if has_keystone else 'No ✧'}"
        html += f" | Runes: {d['rune_count']}"
        html += f" | Arcs: {d['arc_count']}"
        html += f" | Radials: {d['radial_count']}"
        html += f" | Shapes: {len(d['shapes'])}"
        html += f" | Drawings: {d['drawings']}"
        html += "</p>"

        # ── Activation requirements ──
        html += "<h4 style='color:#aa88cc;'>Activation Requirements</h4>"
        reqs = []
        if not has_keystone:
            reqs.append("⚠ No keystone — the spell lacks a focal point. Add a keystone for reliable activation.")
        if len(rings) < 2 and glyphs:
            reqs.append("⚠ Fewer than 2 containment rings — magical energy may leak or backlash.")
        if d["rune_count"] == 0 and glyphs:
            reqs.append("Consider adding rune text to specify spell parameters and duration.")
        if d["radial_count"] == 0 and len(glyphs) > 1:
            reqs.append("Radial lines between glyphs would help channel combined elemental energy.")
        if not reqs:
            reqs.append("✓ The circle appears structurally complete. The spell should activate reliably when drawn with ink and intent.")
        for r in reqs:
            color = "#ff8844" if r.startswith("⚠") else "#88cc88"
            html += f"<p style='color:{color}; font-size:11px;'>• {r}</p>"

        # ── Narrative description ──
        html += "<h4 style='color:#d0af3f;'>📖 Narrative</h4>"
        narrative = self._generate_narrative(d)
        html += f"<p style='color:#ccc; font-style:italic; line-height:1.5;'>{narrative}</p>"

        html += '</div>'
        self._description_text.setHtml(html)

    def _generate_narrative(self, d):
        """Generate a narrative description of what happens when the circle is activated."""
        glyphs = d["glyphs"]
        rings = d["rings"]
        has_keystone = d["has_keystone"]
        glyph_set = set(glyphs)

        if not glyphs and not rings:
            return "An empty circle — ink without intent. Nothing would happen if activated."

        # Check for forbidden
        for combo_set, info in COMBINATION_EFFECTS.items():
            if "FORBIDDEN" in info.get("name", "") and combo_set.issubset(glyph_set):
                return (f"This is a forbidden circle. {info['desc']} "
                        f"If activated, the Brimmed Caps would surely take notice. "
                        f"The Great Hall strictly prohibits such magic — for good reason. "
                        f"The ink would shimmer with an ominous dark light, and reality itself would protest.")

        parts = []

        # Opening based on primary glyph
        if glyphs:
            primary = glyphs[0]
            se = SPELL_EFFECTS.get(primary)
            if se:
                parts.append(se["narrative"])

        # Additional elements
        unique = list(dict.fromkeys(glyphs))
        if len(unique) > 1:
            # Find combination
            combo_found = False
            for i in range(len(unique)):
                for j in range(i + 1, len(unique)):
                    key = frozenset([unique[i], unique[j]])
                    if key in COMBINATION_EFFECTS:
                        ce = COMBINATION_EFFECTS[key]
                        if "FORBIDDEN" not in ce.get("name", ""):
                            parts.append(f" The interplay with {GLYPH_NAMES.get(unique[j], '')} creates {ce['name'].lower()} — {ce['desc'].lower()}.")
                            combo_found = True
            if not combo_found and len(unique) > 1:
                others = [GLYPH_NAMES.get(g, g) for g in unique[1:]]
                parts.append(f" Secondary elements ({', '.join(others)}) add their own resonance to the spell, though their interaction is not a well-documented combination.")

        # Structure
        if has_keystone:
            parts.append(" The keystone at the circle's heart anchors the spell with unwavering stability, ensuring the magic holds its form.")
        if len(rings) >= 3:
            parts.append(" Three or more containment rings create a powerful magical circuit, allowing complex energy flows.")
        elif len(rings) >= 2:
            parts.append(" The dual containment rings channel the magical energy in a controlled circuit.")
        elif len(rings) == 1:
            parts.append(" A single ring barely contains the magical energy — the spell would be unstable without additional structure.")

        if d["rune_count"] > 0:
            parts.append(" Inscribed runes specify the spell's parameters, giving it precision and duration.")

        if d["drawings"] > 0:
            parts.append(f" The freehand inscriptions ({d['drawings']} stroke(s)) add a personal touch to the circle — the caster's own sigils woven into the design.")

        # Conclusion
        if has_keystone and len(rings) >= 2:
            parts.append(" When activated with ink and intent, this circle would cast its spell reliably and powerfully — a well-crafted work of magic.")
        elif len(rings) >= 1:
            parts.append(" When activated, the spell would function but may require the caster's concentration to maintain stability.")
        else:
            parts.append(" Activating this circle would be risky — the lack of containment could cause the spell to spiral out of control.")

        return "".join(parts)


# ═══════════════════════════════════════════════════════════════
# CANVAS  (with freehand drawing support)
# ═══════════════════════════════════════════════════════════════

class MagicCircleCanvas(QGraphicsView):
    drawModeChanged = Signal(bool)

    def __init__(self, scene):
        super().__init__(scene)
        self._zoom = 1.0
        self._panning = False; self._pan_start = QPointF()
        self._draw_mode = False
        self._current_draw_item = None
        self._draw_color = QColor(GOLDEN)
        self._draw_line_width = 2.0
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setMinimumSize(500, 500); self.setMouseTracking(True); self.centerOn(0, 0)

    # ── draw mode ──
    def set_draw_mode(self, enabled):
        self._draw_mode = enabled
        if enabled:
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(Qt.CrossCursor)
        else:
            self.setDragMode(QGraphicsView.RubberBandDrag)
            self.setCursor(Qt.ArrowCursor)
            if self._current_draw_item:
                self._current_draw_item.finish_drawing()
                self._current_draw_item = None
        self.drawModeChanged.emit(enabled)

    def get_draw_mode(self): return self._draw_mode
    def set_draw_color(self, color): self._draw_color = QColor(color)
    def get_draw_color(self): return self._draw_color
    def set_draw_line_width(self, w): self._draw_line_width = w
    def get_draw_line_width(self): return self._draw_line_width

    # ── background ──
    def drawBackground(self, painter, rect):
        painter.fillRect(rect, CANVAS_BG)
        pen = QPen(QColor(30, 30, 50), 0.5); painter.setPen(pen)
        gridSize = 50; left = int(rect.left()) - (int(rect.left()) % gridSize); top = int(rect.top()) - (int(rect.top()) % gridSize)
        for x in range(left, int(rect.right()) + 1, gridSize): painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
        for y in range(top, int(rect.bottom()) + 1, gridSize): painter.drawLine(int(rect.left()), y, int(rect.right()), y)
        painter.setPen(QPen(QColor(60, 60, 90), 1, Qt.DashLine))
        painter.drawLine(int(rect.left()), 0, int(rect.right()), 0)
        painter.drawLine(0, int(rect.top()), 0, int(rect.bottom()))

    # ── mouse events ──
    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom = max(0.1, min(5.0, self._zoom * factor))
        self.setTransform(QTransform().scale(self._zoom, self._zoom))

    def mousePressEvent(self, event):
        if self._draw_mode and event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            self._current_draw_item = FreehandPathItem()
            self._current_draw_item.set_color(self._draw_color)
            self._current_draw_item.set_line_width(self._draw_line_width)
            self._current_draw_item.start_drawing(scene_pos)
            self.scene().addItem(self._current_draw_item)
            event.accept()
        elif event.button() == Qt.MiddleButton:
            self._panning = True; self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor); event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._draw_mode and self._current_draw_item and event.buttons() & Qt.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            self._current_draw_item.continue_drawing(scene_pos)
            event.accept()
        elif self._panning:
            delta = event.position() - self._pan_start; self._pan_start = event.position()
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._draw_mode and event.button() == Qt.LeftButton and self._current_draw_item:
            self._current_draw_item.finish_drawing()
            # Discard if too small (just a click)
            if self._current_draw_item.get_point_count() < 2:
                self.scene().removeItem(self._current_draw_item)
            self._current_draw_item = None
            event.accept()
        elif event.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CrossCursor if self._draw_mode else Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self._draw_mode:
            self.set_draw_mode(False)
        else:
            super().keyPressEvent(event)

    def get_zoom(self): return self._zoom
    def reset_zoom(self): self._zoom = 1.0; self.setTransform(QTransform().scale(1.0, 1.0)); self.centerOn(0, 0)


# ═══════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("✦ Witch Hat Atelier — Magic Circle Creator")
        self.setMinimumSize(1200, 750); self.resize(1400, 850)

        self._scene = MagicCircleScene()
        self._scene.setSceneRect(-800, -800, 1600, 1600)
        self._scene.selectionChanged.connect(self._on_selection_changed)
        self._scene.circleChanged.connect(self._update_live_status)

        self._undo_stack = QUndoStack()
        self._undo_stack.canUndoChanged.connect(lambda _: self._update_statusbar())
        self._undo_stack.canRedoChanged.connect(lambda _: self._update_statusbar())

        self._build_ui(); self._build_toolbar(); self._build_menubar(); self._build_statusbar(); self._apply_stylesheet()

    # ── UI ──
    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        main_layout = QHBoxLayout(central); main_layout.setContentsMargins(4, 4, 4, 4); main_layout.setSpacing(4)
        splitter = QSplitter(Qt.Horizontal)

        self._palette = ComponentPalette()
        self._palette.item_requested.connect(self._add_item)
        self._palette.draw_mode_requested.connect(self._toggle_draw_mode)
        splitter.addWidget(self._palette)

        center_widget = QWidget(); center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0); center_layout.setSpacing(4)
        self._canvas = MagicCircleCanvas(self._scene)
        self._canvas.drawModeChanged.connect(self._on_draw_mode_changed)
        center_layout.addWidget(self._canvas, stretch=1)
        self._analysis = SpellAnalysisWidget(); self._analysis.set_scene(self._scene)
        center_layout.addWidget(self._analysis)
        splitter.addWidget(center_widget)

        right_widget = QWidget(); right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0); right_layout.setSpacing(4)
        self._right_tabs = QTabWidget()
        self._properties = PropertiesPanel(); self._reference = ReferencePanel()
        self._right_tabs.addTab(self._properties, "✦ Properties")
        self._right_tabs.addTab(self._reference, "📖 Reference")
        right_layout.addWidget(self._right_tabs); splitter.addWidget(right_widget)

        splitter.setSizes([220, 700, 300]); main_layout.addWidget(splitter)

    def _build_toolbar(self):
        toolbar = QToolBar("Main"); toolbar.setIconSize(QSize(20, 20)); toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Select mode
        self._select_action = QAction("☝ Select", self)
        self._select_action.setCheckable(True); self._select_action.setChecked(True)
        self._select_action.triggered.connect(lambda: self._canvas.set_draw_mode(False))
        toolbar.addAction(self._select_action)

        # Draw mode
        self._draw_action = QAction("✏ Draw", self)
        self._draw_action.setCheckable(True); self._draw_action.setChecked(False)
        self._draw_action.triggered.connect(lambda: self._canvas.set_draw_mode(True))
        toolbar.addAction(self._draw_action)

        toolbar.addSeparator()

        # Draw color button
        self._draw_color_btn = QPushButton(); self._draw_color_btn.setFixedSize(32, 24)
        self._draw_color_btn.setStyleSheet(f"background-color:{GOLDEN.name()}; border:1px solid #888; border-radius:3px;")
        self._draw_color_btn.setToolTip("Drawing Color")
        self._draw_color_btn.clicked.connect(self._pick_draw_color)
        toolbar.addWidget(self._draw_color_btn)

        # Draw width
        toolbar.addWidget(QLabel(" Width:"))
        self._draw_width_spin = QDoubleSpinBox(); self._draw_width_spin.setRange(0.5, 12); self._draw_width_spin.setValue(2.0); self._draw_width_spin.setSingleStep(0.5)
        self._draw_width_spin.setFixedWidth(65)
        self._draw_width_spin.valueChanged.connect(self._canvas.set_draw_line_width)
        toolbar.addWidget(self._draw_width_spin)

        toolbar.addSeparator()

        toolbar.addAction(QAction("📄 New", self, triggered=self._new_canvas))
        toolbar.addAction(QAction("💾 Export PNG", self, triggered=self._export_image))
        if HAS_SVG: toolbar.addAction(QAction("📐 Export SVG", self, triggered=self._export_svg))
        toolbar.addSeparator()
        toolbar.addAction(QAction("↩ Undo", self, triggered=self._undo_stack.undo))
        toolbar.addAction(QAction("↪ Redo", self, triggered=self._undo_stack.redo))
        toolbar.addSeparator()
        toolbar.addAction(QAction("🔍+", self, triggered=lambda: self._zoom(1.2)))
        toolbar.addAction(QAction("🔍-", self, triggered=lambda: self._zoom(1 / 1.2)))
        toolbar.addAction(QAction("⤓ Fit", self, triggered=self._canvas.reset_zoom))
        toolbar.addSeparator()
        toolbar.addAction(QAction("⊕ Arrange", self, triggered=self._arrange_selected))

        preset_menu = QMenu("Presets", self)
        for name, key in [("🔥 Fire","fire"),("💧 Healing","healing"),("🛡 Barrier","barrier"),("✦ Summon","summon"),("☀ Light","light"),("🌪 Wind","wind")]:
            preset_menu.addAction(name, lambda k=key: self._load_preset(k))
        preset_btn = QPushButton("✦ Presets"); preset_btn.setMenu(preset_menu)
        preset_btn.setStyleSheet("padding:4px 10px; font-weight:bold; background:#2a2a42; color:#d0af3f; border:1px solid #555; border-radius:4px;")
        toolbar.addWidget(preset_btn)

    def _build_menubar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New", self._new_canvas, "Ctrl+N")
        file_menu.addAction("Export PNG...", self._export_image, "Ctrl+E")
        if HAS_SVG: file_menu.addAction("Export SVG...", self._export_svg, "Ctrl+Shift+E")
        file_menu.addSeparator(); file_menu.addAction("Exit", self.close, "Ctrl+Q")
        edit_menu = menubar.addMenu("Edit")
        edit_menu.addAction("Undo", self._undo_stack.undo, "Ctrl+Z")
        edit_menu.addAction("Redo", self._undo_stack.redo, "Ctrl+Y")
        edit_menu.addSeparator()
        edit_menu.addAction("Delete", self._delete_selected, "Delete")
        edit_menu.addAction("Select All", self._select_all, "Ctrl+A")
        edit_menu.addAction("Arrange in Circle", self._arrange_selected, "Ctrl+L")
        mode_menu = menubar.addMenu("Mode")
        mode_menu.addAction("Select Mode", lambda: self._canvas.set_draw_mode(False), "S")
        mode_menu.addAction("Draw Mode", lambda: self._canvas.set_draw_mode(True), "D")

    def _build_statusbar(self):
        self._statusbar = QStatusBar(); self.setStatusBar(self._statusbar)
        self._live_status_label = QLabel("Status: Empty")
        self._live_status_label.setStyleSheet("padding: 0 10px; font-weight: bold; color: #888;")
        self._statusbar.addPermanentWidget(self._live_status_label)
        self._mode_label = QLabel("Mode: Select")
        self._mode_label.setStyleSheet("padding: 0 10px; font-weight: bold; color: #88bbff;")
        self._statusbar.addPermanentWidget(self._mode_label)
        self._statusbar.showMessage("Ready")

    # ── draw mode ──
    def _toggle_draw_mode(self):
        self._canvas.set_draw_mode(not self._canvas.get_draw_mode())

    def _on_draw_mode_changed(self, enabled):
        self._draw_action.setChecked(enabled)
        self._select_action.setChecked(not enabled)
        if enabled:
            self._mode_label.setText("Mode: ✏ Draw"); self._mode_label.setStyleSheet("padding: 0 10px; font-weight: bold; color: #88dd88;")
        else:
            self._mode_label.setText("Mode: ☝ Select"); self._mode_label.setStyleSheet("padding: 0 10px; font-weight: bold; color: #88bbff;")

    def _pick_draw_color(self):
        c = QColorDialog.getColor(self._canvas.get_draw_color(), self, "Drawing Color")
        if c.isValid():
            self._canvas.set_draw_color(c)
            self._draw_color_btn.setStyleSheet(f"background-color:{c.name()}; border:1px solid #888; border-radius:3px;")

    # ── selection / properties ──
    def _on_selection_changed(self):
        selected = self._scene.selectedItems()
        if len(selected) == 1:
            self._properties.set_item(selected[0])
            self._right_tabs.setCurrentIndex(0)
        else:
            self._properties.set_item(None)
        self._update_statusbar()

    # ── live status ──
    def _update_live_status(self):
        glyphs, has_keystone, rings = [], False, []
        for item in self._scene.items():
            if isinstance(item, GlyphItem): glyphs.append(item.get_glyph_type())
            elif isinstance(item, KeystoneItem): has_keystone = True
            elif isinstance(item, CircleRingItem): rings.append(item.get_ring_type())

        glyph_set = set(glyphs); forbidden = False
        for combo_set in [{"transformation","healing"}, {"creation","summon"}]:
            if combo_set.issubset(glyph_set): forbidden = True

        if forbidden:
            self._live_status_label.setText("⚠️ FORBIDDEN MAGIC DETECTED")
            self._live_status_label.setStyleSheet("padding: 0 10px; font-weight: bold; color: #ff4444;")
        elif glyphs:
            stability = "Stable" if has_keystone and len(rings) >= 2 else "Partial" if rings else "Unstable"
            color = "#44ff44" if stability == "Stable" else "#ffaa44" if stability == "Partial" else "#ff8844"
            elem = ", ".join(GLYPH_NAMES.get(g, g) for g in dict.fromkeys(glyphs))
            self._live_status_label.setText(f"Status: {stability} | {elem}")
            self._live_status_label.setStyleSheet(f"padding: 0 10px; font-weight: bold; color: {color};")
        else:
            self._live_status_label.setText("Status: Empty")
            self._live_status_label.setStyleSheet("padding: 0 10px; font-weight: bold; color: #888;")

    def _update_statusbar(self):
        items = self._scene.items(); selected = self._scene.selectedItems(); zoom = self._canvas.get_zoom()
        self._statusbar.showMessage(f"Items: {len(items)} | Selected: {len(selected)} | Zoom: {zoom:.0%} | Undo: {self._undo_stack.count()}")

    # ── add items ──
    def _add_item(self, item_type, params):
        item = None
        if item_type == "circle":
            r = {"outer": 140, "inner": 100, "third": 70, "decorative": 50}.get(params.get("ring_type", "outer"), 100)
            item = CircleRingItem(radius=r, ring_type=params.get("ring_type", "outer"))
        elif item_type == "shape":
            item = ConcentricPolygonItem(sides=params.get("sides", 6),
                                         step=2 if params.get("is_star", False) else 1)
        elif item_type == "glyph":
            item = GlyphItem(glyph_type=params.get("glyph_type", "fire"))
            item.set_color(QColor(GLYPH_COLORS.get(params["glyph_type"], GOLDEN.name())))
        elif item_type == "decoration":
            dt = params.get("deco_type")
            if dt == "rune_text": item = RuneTextItem()
            elif dt == "dot_ring": item = DotRingItem()
            elif dt == "arc": item = ArcSegmentItem()
            elif dt == "radial_line": item = RadialLineItem()
            elif dt == "keystone": item = KeystoneItem()
            elif dt == "text": item = TextLabelItem()

        if item:
            item.setPos(0, 0)
            self._undo_stack.push(AddItemCommand(self._scene, item))
            self._scene.clearSelection()
            item.setSelected(True)
            # Automatically switch back to select mode after adding an item
            self._canvas.set_draw_mode(False)

    # ── canvas actions ──
    def _new_canvas(self):
        self._scene.clear()
        self._undo_stack.clear()
        self._properties.set_item(None)
        self._update_live_status()
        self._statusbar.showMessage("Canvas cleared", 2000)

    def _export_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Magic Circle as PNG", "", "PNG Files (*.png);;All Files (*)")
        if path:
            rect = self._scene.itemsBoundingRect().adjusted(-30, -30, 30, 30)
            pixmap = QPixmap(rect.size().toSize())
            pixmap.fill(CANVAS_BG)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            self._scene.render(painter, QRectF(pixmap.rect()), rect)
            painter.end()
            if pixmap.save(path, "PNG"):
                self._statusbar.showMessage(f"Exported to {path}", 3000)
            else:
                QMessageBox.warning(self, "Export Error", "Failed to save PNG file.")

    def _export_svg(self):
        if not HAS_SVG:
            QMessageBox.information(self, "SVG Not Available", "PySide6.QtSvg is not installed.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Magic Circle as SVG", "", "SVG Files (*.svg);;All Files (*)")
        if path:
            rect = self._scene.itemsBoundingRect().adjusted(-30, -30, 30, 30)
            generator = QSvgGenerator()
            generator.setFileName(path)
            generator.setSize(rect.size().toSize())
            generator.setViewBox(rect)
            generator.setTitle("Witch Hat Atelier - Magic Circle")
            generator.setDescription("Created with Magic Circle Creator")
            painter = QPainter(generator)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillRect(rect, CANVAS_BG)
            self._scene.render(painter, QRectF(), rect)
            painter.end()
            self._statusbar.showMessage(f"Exported SVG to {path}", 3000)

    def _zoom(self, factor):
        self._canvas._zoom = max(0.1, min(5.0, self._canvas._zoom * factor))
        self._canvas.setTransform(QTransform().scale(self._canvas._zoom, self._canvas._zoom))
        self._update_statusbar()

    def _arrange_selected(self):
        selected = self._scene.selectedItems()
        if len(selected) < 2:
            self._statusbar.showMessage("Select at least 2 items to arrange", 2000)
            return
        # Arrange selected items in a circle around the center of their bounding rect
        center = QPointF(0, 0)
        for item in selected:
            center += item.pos()
        center /= len(selected)
        
        radius = 120
        for i, item in enumerate(selected):
            angle = 2 * math.pi * i / len(selected) - math.pi / 2
            item.setPos(center.x() + radius * math.cos(angle), center.y() + radius * math.sin(angle))
        self._statusbar.showMessage(f"Arranged {len(selected)} items in a circle", 2000)

    def _delete_selected(self):
        selected = self._scene.selectedItems()
        if selected:
            self._undo_stack.push(DeleteItemsCommand(self._scene, selected))
            self._properties.set_item(None)

    def _select_all(self):
        for item in self._scene.items():
            if isinstance(item, BaseMagicItem):
                item.setSelected(True)

    # ── presets ──
    def _load_preset(self, key):
        self._new_canvas()
        self._add_item("circle", {"ring_type": "outer"})
        self._add_item("circle", {"ring_type": "inner"})
        self._add_item("decoration", {"deco_type": "keystone"})
        
        if key == "fire":
            self._add_item("glyph", {"glyph_type": "fire"})
            self._add_item("shape", {"sides": 3, "is_star": False})
            self._add_item("decoration", {"deco_type": "radial_line"})
        elif key == "healing":
            self._add_item("glyph", {"glyph_type": "healing"})
            self._add_item("decoration", {"deco_type": "dot_ring"})
        elif key == "barrier":
            self._add_item("glyph", {"glyph_type": "barrier"})
            self._add_item("shape", {"sides": 8, "is_star": False})
        elif key == "summon":
            self._add_item("glyph", {"glyph_type": "summon"})
            self._add_item("circle", {"ring_type": "third"})
            self._add_item("shape", {"sides": 5, "is_star": True})
        elif key == "light":
            self._add_item("glyph", {"glyph_type": "light"})
            self._add_item("decoration", {"deco_type": "rune_text"})
        elif key == "wind":
            self._add_item("glyph", {"glyph_type": "wind"})
            self._add_item("shape", {"sides": 6, "is_star": True})
            
        self._scene.clearSelection()
        self._statusbar.showMessage(f"Loaded preset: {key.capitalize()}", 3000)

    # ── styling ──
    def _apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a2e; }
            QWidget { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; font-size: 12px; }
            QGroupBox { 
                border: 1px solid #3a3a5e; border-radius: 4px; 
                margin-top: 10px; padding-top: 14px; 
                font-weight: bold; color: #a0a0d0; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; left: 8px; padding: 0 4px; 
            }
            QPushButton { 
                background-color: #2a2a42; border: 1px solid #4a4a6e; 
                border-radius: 3px; padding: 5px 10px; color: #d0d0e0; 
                text-align: center;
            }
            QPushButton:hover { background-color: #3a3a5e; border: 1px solid #6a6a9e; }
            QPushButton:pressed { background-color: #4a4a6e; }
            QPushButton:checked { background-color: #44447a; border: 2px solid #8888cc; }
            
            QTabWidget::pane { border: 1px solid #3a3a5e; background: #1e1e32; border-radius: 2px; }
            QTabBar::tab { 
                background: #2a2a42; border: 1px solid #3a3a5e; 
                padding: 6px 12px; border-top-left-radius: 4px; border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected { background: #3a3a5e; border-bottom-color: #3a3a5e; color: #d0af3f; }
            
            QToolBar { 
                background: #16162a; border-bottom: 1px solid #3a3a5e; 
                spacing: 4px; padding: 3px; 
            }
            QToolBar QAbstractButton { margin: 2px; font-weight: bold; } 
            
            QStatusBar { background: #16162a; color: #808090; border-top: 1px solid #3a3a5e; }
            
            QDoubleSpinBox, QSpinBox, QLineEdit, QComboBox { 
                background: #2a2a42; border: 1px solid #4a4a6e; 
                border-radius: 3px; padding: 3px; color: #e0e0e0; 
            }
            QComboBox::drop-down { border: none; background: #3a3a5e; width: 20px; border-top-right-radius: 3px; border-bottom-right-radius: 3px; }
            QComboBox QAbstractItemView { background: #2a2a42; border: 1px solid #4a4a6e; color: #e0e0e0; selection-background-color: #4a4a8e; }
            
            QTextBrowser { 
                background: #1e1e32; border: 1px solid #3a3a5e; color: #c0c0d0; 
                border-radius: 3px;
            }
            
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: #1e1e32; width: 10px; margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3a3a5e; min-height: 20px; border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            
            QMenuBar { background: #16162a; color: #c0c0d0; border-bottom: 1px solid #3a3a5e; }
            QMenuBar::item:selected { background: #3a3a5e; }
            QMenu { background: #2a2a42; border: 1px solid #4a4a6e; color: #c0c0d0; }
            QMenu::item:selected { background: #3a3a5e; }
            
            QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #4a4a6e; border-radius: 2px; background: #2a2a42; }
            QCheckBox::indicator:checked { background: #5588cc; border-color: #77aaee; }
            
            QSplitter::handle { background: #3a3a5e; width: 2px; }
        """)


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())