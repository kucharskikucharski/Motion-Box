"""Motion Box - core: constants, helpers, data model, icon drawing.

Layout grid: everything is positioned on a 4px / 8px grid (see GRID below).
"""
import colorsys
import copy
import math
import os
import re
import sys

import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FROZEN = getattr(sys, "frozen", False)                   # True inside a packaged app
RES_DIR = getattr(sys, "_MEIPASS", BASE_DIR)             # read-only resources (icons, splash)
DATA_DIR = os.path.join(os.path.expanduser("~"), "MotionBox") if FROZEN else BASE_DIR   # user data
PROJECTS_DIR = os.path.join(DATA_DIR, "projects")
SCRIPTS_DIR = os.path.join(DATA_DIR, "scripts")
ICONS_DIR = os.path.join(RES_DIR, "icons")       # put your PNG icons here, e.g. icons/select.png
ASSETS_DIR = os.path.join(RES_DIR, "assets")     # assets/splash.png
LIBRARY_FILE = os.path.join(DATA_DIR, "library.json")
for _d in (PROJECTS_DIR, SCRIPTS_DIR):
    os.makedirs(_d, exist_ok=True)

EXAMPLE_SCRIPT = '''# Example Motion Box script (File > Import Script...)
# Available: app.add_box(name, x, y, color)   app.add_null(name, x, y)   app.link(child, parent)
#            app.set_key(obj, prop, frame, value)   app.find(name)   app.msg("text")
# prop: "x" "y" "scale" "rotation" "opacity"
null = app.add_null("Script Null", 500, 800)
box = app.add_box("Script Box", 500, 800, color=(230, 120, 40))
app.link(box, null)
for f, x in ((1, 400), (36, 1300), (72, 400)):
    app.set_key(null, "x", f, x)
for f, r in ((1, 0), (72, 360)):
    app.set_key(null, "rotation", f, r)
'''
_ex = os.path.join(SCRIPTS_DIR, "example.py")
if not os.path.exists(_ex):
    with open(_ex, "w", encoding="utf-8") as _fh:
        _fh.write(EXAMPLE_SCRIPT)

GRID = 8
COLOR_ACCENT = (22, 49, 167)        # #1631A7
COLOR_ACCENT_L = (36, 66, 200)          # navy - sliders, buttons, checkboxes
COLOR_NAVY = (40, 72, 205)          # hover outline
COLOR_BG = (34, 34, 34)
COLOR_PANEL = (38, 38, 38)
COLOR_VIEWPORT = (28, 28, 28)
COLOR_ARTBOARD = (20, 20, 20)
COLOR_BTN = (48, 48, 48)
COLOR_HOVER = (62, 62, 62)
COLOR_TEXT = (234, 234, 234)
COLOR_MUTED = (150, 150, 150)
COLOR_LINE = (58, 58, 58)
COLOR_TEAL = (0, 170, 160)
COLOR_PLAYHEAD = (44, 80, 225)      # navy playhead
COLOR_THUMB = (79, 79, 79)          # #4F4F4F scrollbar thumb
COLOR_YELLOW = (240, 190, 60)
COLOR_HEAD = (28, 28, 28)           # panel header strip, inactive tabs
COLOR_FIELD = (26, 26, 26)          # text fields, unchecked boxes
COLOR_TL = (30, 31, 35)             # timeline and bottom bars
LABEL_PURPLE = (126, 87, 194)
# label colours per element type (editable: click the dot on a layer or Edit > Preferences > Labels)
# 16 label colours + names (like After Effects > Settings > Labels); palette chosen by the user
LABEL_DEFAULT_LIST = [("Deep Lilac", (131, 86, 193)), ("Bubblegum Pink", (255, 107, 125)), ("Porcelain", (255, 251, 246)),
                      ("Icy Aqua", (173, 236, 230)), ("Night Bordeaux", (67, 7, 20)), ("Tomato", (255, 74, 79)),
                      ("Mustard", (255, 215, 111)), ("Blue Sail", (42, 157, 240)), ("Midnight Violet", (36, 12, 48)),
                      ("Cinnamon Wood", (180, 123, 101)), ("Blush Pop", (239, 171, 200)), ("Amber Flame", (255, 188, 63)),
                      ("Deep Mocha", (64, 40, 40)), ("Deep Teal", (0, 133, 122)), ("Dark Plum", (75, 38, 110)),
                      ("Slate", (96, 110, 130))]
# which label each element type uses by default (index into the list above)
TYPE_LABEL_DEFAULT = {"vector": 0, "brush": 3, "null": 7, "controller": 11, "image": 1, "comp": 5, "text": 6, "peg": 10}
LABEL_NAMES = {"vector": "Vectors", "brush": "Brush / raster", "null": "Nulls", "controller": "Controllers",
               "image": "Images", "comp": "Compositions", "text": "Text", "peg": "Pegs"}

PROPS = ("x", "y", "scale", "rotation", "opacity")
PROP_LABEL = {"x": "Position X", "y": "Position Y", "scale": "Scale", "rotation": "Rotation",
              "opacity": "Opacity"}
PROP_RANGE = {"x": (0, 1920), "y": (0, 1080), "scale": (0.1, 4.0), "rotation": (-360, 360),
              "opacity": (0, 100)}
SHIFT_STEP = {"x": 10, "y": 10, "scale": 0.1, "rotation": 10, "opacity": 10}
IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tga")
VID_EXT = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")
AUD_EXT = (".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a")
VECTOR_KINDS = ("rect", "ellipse", "polygon", "line", "brush", "bone")

# ---------------------------------------------------------------- tools
TOOL_INFO = {
    "select": ("Select", "V", "Click to select, drag to move (Shift = one axis). Shift+click adds to selection. "
                              "Drag a handle to resize, just outside a corner to rotate."),
    "transform": ("Transform", "T", "Free transform (uses the same handles as Select)."),
    "rect": ("Rectangle", "R", "Drag to draw a rectangle (Shift = square). Hold the tool for more shapes."),
    "ellipse": ("Ellipse", "", "Drag to draw an ellipse (Shift = circle)."),
    "polygon": ("Polygon", "", "Drag to draw a polygon (Shift = regular)."),
    "line": ("Line", "", "Drag to draw a line (Shift = 45 degree steps)."),
    "brush": ("Brush", "B", "Drag to paint a vector stroke. Options (auto close / group / fill, draw under) appear at the top of the viewport."),
    "fill": ("Fill Bucket", "F", "Click a shape or closed stroke to fill it with the current fill colour."),
    "eraser": ("Eraser", "E", "Erases pixels on a raster layer (select or create a raster layer first)."),
    "pen": ("Pen", "P", "Coming soon: bezier paths."),
    "null": ("Null", "N", "Click to place a null object (a target to link other objects to)."),
    "ctrl": ("Position Controller", "", "Click to place a controller that only moves (scale and rotation are locked)."),
    "ctrl_rot": ("Rotation Controller", "", "Click to place a controller that only rotates (everything else is locked)."),
    "ctrl_posrot": ("Position + Rotation Controller", "", "Click to place a controller that moves and rotates (scale is locked)."),
    "peg": ("Peg", "", "Click to place a peg: a transform-only parent you can drive with an expression or script."),
    "select_level": ("Select Whole Level", "", "Click a shape to select every shape of its layer."),
    "multiline": ("Multiline", "", "Coming soon: multi-segment lines."),
    "text": ("Text", "", "Coming soon: text layers."),
    "eyedropper": ("Eyedropper", "", "Click anywhere in the viewport to pick that colour as the fill colour."),
    "scissors": ("Cut", "C", "Click a layer to cut it in two at the playhead."),
    "taper": ("Taper / Join", "", "Coming soon: join segments and patch shapes (Tahoma's Taper tool)."),
    "lipsync": ("Lipsync", "", "Coming soon: map phonemes to the drawings of a mouth layer."),
    "bone_anim": ("Animate Bones", "", "Drag a bone to rotate it around its joint. Only rotation is animated; length and position stay as you built them."),
    "bone_edit": ("Edit Skeleton", "", "Drag the ball at the end of a bone to bend / lengthen it, drag the joint at its start to move it. A joint dropped on the end of another bone snaps to it and becomes its child."),
    "bone_ik": ("Create IK", "", "Click the LOWER bone of a two-bone chain: an IK controller appears at its tip - move it and the chain follows."),
    "animate": ("Animate", "A", "Select and move only pegs or only controllers (choose in the bar at the top); everything else is protected."),
    "zoom": ("Zoom", "Z", "Click to zoom in, Alt+click to zoom out."),
    "view_rotate": ("Rotate View", "", "Coming soon: rotate the artboard view."),
    "joy_x": ("Joystick X", "", "Click to place a joystick limited to the X axis."),
    "joy_y": ("Joystick Y", "", "Click to place a joystick limited to the Y axis."),
    "joy_xy": ("Joystick XY", "", "Click to place a joystick that moves on both axes."),
    "bone": ("Create Bones", "J", "Drag to draw a bone. Start the next bone on the end of the last one to chain them."),
    "anchor": ("Anchor Point", "Y", "Drag to move the pivot of the selected object (it rotates and scales around it). Hold Ctrl to snap to the box corners, edges, centre and the artboard centre."),
    "hand": ("Hand", "H", "Drag to pan the view. Scroll to zoom. Home = fit."),
}
SLOTS = [["select", "select_level", "transform", "anchor", "animate"], None,
         ["rect", "ellipse", "polygon", "line"], ["pen", "multiline"], ["brush", "eraser"], ["fill"], ["text"], ["eyedropper"], None,
         ["scissors"], ["taper"], ["lipsync"], None,
         ["joy_x", "joy_y", "joy_xy"], ["ctrl", "ctrl_rot", "ctrl_posrot", "null", "peg"], ["bone", "bone_edit", "bone_anim", "bone_ik"], None,
         ["hand", "zoom", "view_rotate"]]
KEYMAP = {pygame.K_v: "select", pygame.K_t: "transform", pygame.K_r: "rect", pygame.K_b: "brush",
          pygame.K_e: "eraser", pygame.K_a: "animate", pygame.K_c: "scissors", pygame.K_z: "zoom", pygame.K_y: "anchor", pygame.K_f: "fill", pygame.K_p: "pen", pygame.K_n: "null", pygame.K_j: "bone",
          pygame.K_h: "hand"}
WORKSPACES = ["Drawing", "Animate", "Schematic", "Fx", "Expressions", "Script"]
MENU_NAMES = ["File", "Edit", "Object", "Type", "Effects", "View", "Tools", "Panels"]
FORMATS = [("HD 1920 x 1080", 1920, 1080), ("4K UHD 3840 x 2160", 3840, 2160),
           ("Square 1080 x 1080", 1080, 1080), ("Vertical 1080 x 1920", 1080, 1920),
           ("Custom", None, None)]

# ---------------------------------------------------------------- helpers


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def shade(c, k):
    return tuple(int(clamp(v * k, 0, 255)) for v in c[:3])


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hex_to_rgb(s):
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return None
    try:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def rgb_to_hex(c):
    return "%02X%02X%02X" % tuple(int(v) for v in c[:3])


def rgb_to_hsv(c):
    return colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)


def hsv_to_rgb(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255 + .5), int(g * 255 + .5), int(b * 255 + .5))


def rpoly(surf, color, pts, r=2):
    """Filled polygon with rounded corners (no sharp angles anywhere)."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    ins = []
    for x, y in pts:
        d = math.hypot(cx - x, cy - y) or 1
        t = min(0.45, r * 1.6 / d)
        ins.append((x + (cx - x) * t, y + (cy - y) * t))
    pygame.draw.polygon(surf, color, ins)
    if r >= 1:
        pygame.draw.polygon(surf, color, ins, max(1, int(r * 2)))
        for p in ins:
            pygame.draw.circle(surf, color, (int(p[0]), int(p[1])), int(r))


def rdiamond(surf, c, size, col, filled=True):
    cx, cy = c
    pts = [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)]
    if filled:
        rpoly(surf, col, pts, 2)
    else:
        ins = [(cx, cy - size + 2), (cx + size - 2, cy), (cx, cy + size - 2), (cx - size + 2, cy)]
        pygame.draw.lines(surf, col, True, ins, 2)
        for p in ins:
            pygame.draw.circle(surf, col, (int(p[0]), int(p[1])), 1)


_icon_cache = {}
_icon_index = None
_icon_unmatched = []
ICON_ALIASES = {"bone_animation": "bone_anim", "slider_x": "joy_x", "slider_y": "joy_y", "psition_rotation_controller": "ctrl_posrot",
                "edit_skeleton": "bone_edit", "color_picker": "eyedropper", "control_point_editor": "pen", "fill_bucket": "fill", "paint_bucket": "fill", "bucket": "fill", "controller": "ctrl", "position_controller": "ctrl",
                "rotation_controller": "ctrl_rot", "position_rotation_controller": "ctrl_posrot", "pos_rot_controller": "ctrl_posrot",
                "position_and_rotation_controller": "ctrl_posrot", "joystick_x": "joy_x", "joystick_y": "joy_y", "joystick_xy": "joy_xy",
                "joystick": "joy_xy", "cut": "scissors", "scissor": "scissors", "taper_join": "taper", "taper_tool": "taper",
                "paperclip": "taper", "paper_clip": "taper", "animate_bones": "bone_anim", "pose_bones": "bone_anim", "bones": "bone",
                "create_bones": "bone", "edit_bones": "bone_edit", "create_ik": "bone_ik", "ik": "bone_ik", "rotate_view": "view_rotate",
                "rotate_artboard": "view_rotate", "hand_tool": "hand", "pan": "hand", "select_whole_level": "select_level",
                "whole_level": "select_level", "free_transform": "transform", "anchor_point": "anchor", "multi_line": "multiline",
                "rectangle": "rect", "square": "rect", "circle": "ellipse", "oval": "ellipse", "lasso": "lipsync", "speech": "lipsync",
                "text_tool": "text", "pen_tool": "pen", "brush_tool": "brush", "eraser_tool": "eraser", "zoom_tool": "zoom",
                "magnifier": "zoom", "color_picker": "eyedropper", "picker": "eyedropper", "animate_tool": "animate", "move": "select",
                "arrow": "select", "pointer": "select", "line_tool": "line", "triangle": "polygon"}


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def tool_id_for(name):
    """icons/ file names may use the tool id (ctrl_rot) or its on-screen name (Rotation Controller / rotation_controller)."""
    n = _norm(name)
    if n in TOOL_INFO:
        return n
    for tid, (title, _, _) in TOOL_INFO.items():
        if _norm(title) == n:
            return tid
    return ICON_ALIASES.get(n)


def icon_report():
    """(tools without any icon, files that matched no tool)"""
    global _icon_index
    if _icon_index is None:
        _icon_index = _build_icon_index()
    have = {k[0] for k in _icon_index}
    return [t for t in TOOL_INFO if t not in have], list(_icon_unmatched)
STATE_WORDS = {"default": "default", "idle": "default", "inactive": "default", "normal": "default", "off": "default",
               "hover": "hover", "over": "hover", "active": "active", "selected": "active", "pressed": "active", "on": "active"}


def _build_icon_index():
    """Finds icons/<tool>.png and also <tool>_default / _hover / _active (any separator, any case, sub-folders allowed)."""
    idx = {}
    for root, _, files in os.walk(ICONS_DIR):
        dirs = [d for d in os.path.relpath(root, ICONS_DIR).lower().replace("\\", "/").split("/") if d not in (".", "")]
        for fn in sorted(files):
            if not fn.lower().endswith(".png"):
                continue
            tokens = [t for t in re.split(r"[\s_\-.]+", os.path.splitext(fn)[0].lower()) if t]
            state = next((STATE_WORDS[t] for t in reversed(tokens + dirs) if t in STATE_WORDS), "any")
            tid = "_".join(t for t in tokens if t not in STATE_WORDS)
            real = tool_id_for(tid)
            if real is None:
                _icon_unmatched.append(fn)
                continue
            idx.setdefault((real, state), os.path.join(root, fn))
    if _icon_unmatched:
        print("Motion Box: icon files that match no tool:", ", ".join(_icon_unmatched[:20]))
    return idx


def reset_icon_cache():
    global _icon_index
    _icon_cache.clear()
    _icon_unmatched.clear()
    _icon_index = None


def load_icon_state(name, size=30, state="default"):
    """(surface, state_specific). 30x30 PNGs are used 1:1, other sizes are scaled."""
    global _icon_index
    if _icon_index is None:
        _icon_unmatched.clear()
        _icon_index = _build_icon_index()
    key = (name, size, state)
    if key in _icon_cache:
        return _icon_cache[key]
    path = _icon_index.get((name, state))
    specific = path is not None
    if path is None:
        path = _icon_index.get((name, "any")) or _icon_index.get((name, "default"))
    surf = None
    if path:
        try:
            img = pygame.image.load(path).convert_alpha()
            surf = img if img.get_size() == (size, size) else pygame.transform.smoothscale(img, (size, size))
        except Exception:  # noqa
            surf = None
    _icon_cache[key] = (surf, specific)
    return _icon_cache[key]


def cursor_png(kind):
    """Your own cursor artwork: icons/cursors/<kind>.png or icons/cursor_<kind>.png (resize_v, resize_h, resize_d1, resize_d2, rotate)."""
    key = ("cursor", kind)
    if key not in _icon_cache:
        sf = None
        for p in (os.path.join(ICONS_DIR, "cursors", kind + ".png"), os.path.join(ICONS_DIR, "cursor_" + kind + ".png")):
            if os.path.exists(p):
                try:
                    sf = pygame.image.load(p).convert_alpha()
                except Exception:  # noqa
                    sf = None
                break
        _icon_cache[key] = (sf, True)
    return _icon_cache[key][0]


def load_icon(name, size=30):
    return load_icon_state(name, size, "default")[0]


def draw_icon(surf, kind, r, col):
    """Transport / small UI icons - all with rounded corners."""
    cx, cy = r.center
    s = 6
    d = pygame.draw
    if kind == "play":
        rpoly(surf, col, [(cx - s + 1, cy - s), (cx - s + 1, cy + s), (cx + s + 1, cy)], 2)
    elif kind == "pause":
        d.rect(surf, col, (cx - s, cy - s, 5, 2 * s), border_radius=2)
        d.rect(surf, col, (cx + 2, cy - s, 5, 2 * s), border_radius=2)
    elif kind == "stop":
        d.rect(surf, col, (cx - s, cy - s, 2 * s, 2 * s), border_radius=3)
    elif kind in ("first", "last"):
        sg = -1 if kind == "first" else 1
        d.rect(surf, col, (cx - sg * s - 1, cy - s, 3, 2 * s), border_radius=1)
        rpoly(surf, col, [(cx - sg * 4 + sg * 8, cy), (cx - sg * 4, cy - s), (cx - sg * 4, cy + s)], 2)
    elif kind in ("prev", "next"):
        sg = -1 if kind == "prev" else 1
        for o in (-4, 4):
            rpoly(surf, col, [(cx + o + sg * 4, cy), (cx + o - sg * 3, cy - s + 1), (cx + o - sg * 3, cy + s - 1)], 2)
    elif kind == "key":
        rdiamond(surf, (cx, cy), 7, col, False)
    elif kind == "key_f":
        rdiamond(surf, (cx, cy), 7, col, True)
    elif kind == "key_auto":                    # auto keyframe: record dot
        d.circle(surf, col, (cx, cy), 10, 2)
        d.circle(surf, col, (cx, cy), 4)
    elif kind == "key_g":                      # global keyframe: every layer
        rdiamond(surf, (cx, cy), 6, col, False)
        d.circle(surf, col, (cx, cy), 11, 1)
        d.line(surf, col, (cx - 11, cy), (cx + 11, cy), 1)
    elif kind == "key_x":                      # delete keyframes at the playhead
        rdiamond(surf, (cx - 2, cy - 2), 6, col, False)
        d.line(surf, col, (cx + 3, cy + 3), (cx + 9, cy + 9), 2)
        d.line(surf, col, (cx + 9, cy + 3), (cx + 3, cy + 9), 2)
    elif kind == "key_all":                    # select all keyframes at the playhead
        rdiamond(surf, (cx, cy), 7, col, True)
        d.circle(surf, col, (cx, cy), 11, 1)
    elif kind == "loop":
        d.arc(surf, col, (cx - 8, cy - 6, 16, 12), 0.5, 2.9, 2)
        d.arc(surf, col, (cx - 8, cy - 6, 16, 12), 3.64, 6.04, 2)
        rpoly(surf, col, [(cx - 9, cy + 1), (cx - 5, cy - 2), (cx - 5, cy + 4)], 1)
        rpoly(surf, col, [(cx + 9, cy - 1), (cx + 5, cy + 2), (cx + 5, cy - 4)], 1)
    elif kind in ("chev_l", "chev_r"):
        sg = -1 if kind == "chev_l" else 1
        d.lines(surf, col, False, [(cx - sg * 3, cy - 6), (cx + sg * 3, cy), (cx - sg * 3, cy + 6)], 2)
    elif kind == "mtn_s":
        rpoly(surf, col, [(cx - 7, cy + 4), (cx, cy - 4), (cx + 7, cy + 4)], 2)
    elif kind == "mtn_l":
        rpoly(surf, col, [(cx - 9, cy + 6), (cx, cy - 7), (cx + 9, cy + 6)], 2)
    elif kind == "tri_r":
        rpoly(surf, col, [(cx - 3, cy - 4), (cx + 4, cy), (cx - 3, cy + 4)], 1.5)
    elif kind == "tri_d":
        rpoly(surf, col, [(cx - 4, cy - 3), (cx + 4, cy - 3), (cx, cy + 4)], 1.5)


def draw_tool_icon(surf, tid, r, col):
    """Fallback tool glyphs used until you drop your own PNGs into icons/."""
    cx, cy = r.center
    d = pygame.draw
    if tid in ("select", "transform"):
        if tid == "select":
            rpoly(surf, col, [(cx - 6, cy - 9), (cx - 6, cy + 8), (cx - 1, cy + 3), (cx + 6, cy + 3)], 2)
        else:
            d.rect(surf, col, (cx - 8, cy - 8, 16, 16), 2, border_radius=3)
            for ox, oy in ((-8, -8), (8, -8), (8, 8), (-8, 8)):
                d.circle(surf, col, (cx + ox, cy + oy), 3)
    elif tid == "rect":
        d.rect(surf, col, (cx - 9, cy - 8, 18, 16), 2, border_radius=4)
    elif tid == "ellipse":
        d.ellipse(surf, col, (cx - 9, cy - 8, 18, 16), 2)
    elif tid == "polygon":
        pts = [(cx + 9 * math.sin(i * math.tau / 6), cy - 9 * math.cos(i * math.tau / 6)) for i in range(6)]
        d.lines(surf, col, True, pts, 2)
    elif tid == "line":
        d.line(surf, col, (cx - 8, cy + 8), (cx + 8, cy - 8), 2)
        d.circle(surf, col, (cx - 8, cy + 8), 3)
        d.circle(surf, col, (cx + 8, cy - 8), 3)
    elif tid == "brush":
        d.line(surf, col, (cx + 8, cy - 8), (cx - 3, cy + 3), 4)
        d.circle(surf, col, (cx - 6, cy + 6), 4)
    elif tid == "eraser":
        rpoly(surf, col, [(cx - 8, cy + 2), (cx + 1, cy - 8), (cx + 9, cy), (cx, cy + 9)], 2)
    elif tid == "pen":
        rpoly(surf, col, [(cx, cy + 9), (cx - 6, cy - 2), (cx, cy - 9), (cx + 6, cy - 2)], 2)
    elif tid == "null":
        d.rect(surf, col, (cx - 9, cy - 9, 18, 18), 2, border_radius=4)
        d.circle(surf, col, (cx, cy), 3)
    elif tid == "ctrl":
        rpoly(surf, col, [(cx + x * 10, cy + y * 10) for x, y in CTRL_SHAPE], 1)
    elif tid == "peg":
        d.circle(surf, col, (cx, cy), 8, 2)
        d.line(surf, col, (cx - 11, cy), (cx + 11, cy), 1)
        d.line(surf, col, (cx, cy - 11), (cx, cy + 11), 1)
    elif tid in ("bone_anim", "bone_edit", "bone_ik"):
        d.line(surf, col, (cx - 8, cy + 8), (cx + 2, cy - 2), 3)
        d.circle(surf, col, (cx - 9, cy + 9), 3)
        d.circle(surf, col, (cx + 3, cy - 3), 3)
        if tid == "bone_ik":
            d.line(surf, col, (cx + 3, cy - 3), (cx + 9, cy + 3), 3)
            d.circle(surf, col, (cx + 10, cy + 4), 3, 1)
        elif tid == "bone_anim":
            d.arc(surf, col, (cx - 3, cy - 12, 20, 20), 0.2, 1.6, 2)
        else:
            d.rect(surf, col, (cx + 5, cy - 10, 6, 6), 1)
    elif tid == "taper":
        d.arc(surf, col, (cx - 8, cy - 9, 14, 18), 1.6, 4.9, 2)
        d.arc(surf, col, (cx - 4, cy - 6, 14, 18), 4.7, 1.6 + 6.28, 2)
    elif tid == "eyedropper":
        d.line(surf, col, (cx - 8, cy + 8), (cx + 2, cy - 2), 3)
        d.circle(surf, col, (cx + 6, cy - 6), 5, 2)
    elif tid == "scissors":
        d.line(surf, col, (cx - 8, cy - 8), (cx + 8, cy + 8), 2)
        d.line(surf, col, (cx - 8, cy + 8), (cx + 8, cy - 8), 2)
        d.circle(surf, col, (cx - 7, cy + 7), 3, 1)
        d.circle(surf, col, (cx + 7, cy + 7), 3, 1)
    elif tid == "zoom":
        d.circle(surf, col, (cx - 2, cy - 2), 7, 2)
        d.line(surf, col, (cx + 3, cy + 3), (cx + 9, cy + 9), 3)
    elif tid == "lipsync":
        d.ellipse(surf, col, (cx - 9, cy - 8, 18, 14), 2)
        d.polygon(surf, col, [(cx - 5, cy + 5), (cx - 8, cy + 10), (cx, cy + 6)])
    elif tid == "select_level":
        d.rect(surf, col, (cx - 9, cy - 9, 12, 12), 2, border_radius=3)
        d.rect(surf, col, (cx - 3, cy - 3, 12, 12), 2, border_radius=3)
    elif tid == "artboard":
        d.rect(surf, col, (cx - 8, cy - 8, 16, 16), 2, border_radius=3)
    elif tid in ("ctrl_rot", "ctrl_posrot"):
        d.arc(surf, col, (cx - 9, cy - 9, 18, 18), 0.4, 5.4, 2)
        rpoly(surf, col, [(cx + 6, cy - 8), (cx + 11, cy - 2), (cx + 3, cy - 3)], 1)
    elif tid.startswith("joy"):
        d.rect(surf, col, (cx - 9, cy - 9, 18, 18), 2, border_radius=6)
        d.circle(surf, col, (cx + (3 if "x" in tid else 0), cy + (3 if "y" in tid else 0)), 4)
    elif tid == "bone":
        d.line(surf, col, (cx - 7, cy + 7), (cx + 7, cy - 7), 4)
        d.circle(surf, col, (cx - 8, cy + 8), 4)
        d.circle(surf, col, (cx + 8, cy - 8), 4)
    elif tid == "hand":
        d.rect(surf, col, (cx - 7, cy - 2, 14, 11), 2, border_radius=5)
        for ox in (-5, -1, 3):
            d.line(surf, col, (cx + ox, cy - 2), (cx + ox, cy - 8), 2)


EXPR_WORDS = ["layer(\"", "world(\"", "wiggle(", "value", "time", "t", "sin(", "cos(", "tan(", "abs(", "min(", "max(", "clamp(", "sqrt(", "pi"]
FPS_LIST = [12, 15, 24, 25, 30, 48, 60]

# four-way arrow controller outline (unit coordinates)
CTRL_SHAPE = [(0, -1), (.3, -.6), (.1, -.6), (.1, -.1), (.6, -.1), (.6, -.3), (1, 0), (.6, .3), (.6, .1),
              (.1, .1), (.1, .6), (.3, .6), (0, 1), (-.3, .6), (-.1, .6), (-.1, .1), (-.6, .1), (-.6, .3),
              (-1, 0), (-.6, -.3), (-.6, -.1), (-.1, -.1), (-.1, -.6), (-.3, -.6)]

# ---------------------------------------------------------------- easing
DEFAULT_EASE = (1 / 3, 1 / 3, False)   # identical to the old smoothstep
EASE_PRESETS = [("Linear", (0.0, 0.0, False)), ("Ease In (slow start)", (0.66, 0.0, False)),
                ("Ease Out (slow end)", (0.0, 0.66, False)), ("Ease In / Out", (0.5, 0.5, False)),
                ("Hold", (0.0, 0.0, True))]


def ease_t(t, e):
    o, i = e[0], e[1]
    hold = e[2] if len(e) > 2 else False
    if hold:
        return 0.0 if t < 1 else 1.0
    lo, hi = 0.0, 1.0
    for _ in range(14):
        s = (lo + hi) / 2
        x = 3 * (1 - s) ** 2 * s * o + 3 * (1 - s) * s * s * (1 - i) + s ** 3
        if x < t:
            lo = s
        else:
            hi = s
    s = (lo + hi) / 2
    return 3 * (1 - s) * s * s + s ** 3


# ---------------------------------------------------------------- model
FIELDS = ("name", "kind", "w", "h", "pts", "fill", "fill_on", "fill_a", "stroke_on", "stroke", "stroke_a",
          "stroke_w", "base", "expr", "visible", "locked", "render", "expanded", "label", "node", "phases",
          "limit", "t_in", "t_out", "closed", "fold_id", "src", "anchor", "png", "matte", "matte_inv", "caption", "ik", "caption_color", "matte_show", "collapsed", "rot_limit", "sides", "drivers", "pin")


class Obj:
    """Scene object. kind: rect ellipse polygon line brush null ctrl joy"""

    def __init__(self, name, kind, x, y, w=200, h=200):
        self.name, self.kind, self.w, self.h = name, kind, float(w), float(h)
        self.pts = [(-.5, -.5), (.5, .5)] if kind == "line" else []   # unit points (brush/line)
        self.fill, self.fill_on, self.fill_a = (140, 70, 200), True, 100.0
        self.stroke, self.stroke_on, self.stroke_a, self.stroke_w = (15, 15, 15), False, 100.0, 2.0
        self.base = {"x": float(x), "y": float(y), "scale": 1.0, "rotation": 0.0, "opacity": 100.0}
        self.keys = {p: {} for p in PROPS}
        self.ease = {}            # segment start frame -> (out, in, hold)
        self.expr = {}            # prop -> python expression
        self.parent = None
        self.visible, self.locked, self.render, self.expanded = True, False, True, False
        self.label = None          # None = use the colour of the element type
        self.node = None
        self.phases = []          # frames where a new drawing phase starts
        self.phase_pts = {}
        self.limit = None         # (minx, maxx, miny, maxy) for joystick knobs
        self.t_in, self.t_out = 1, None     # layer in / out frame (trim); keyframes are independent of it
        self.closed = False       # closed brush stroke (can be filled)
        self.fold_id = None       # layers sharing a fold id are shown as one bar in the timeline
        self.u_mode, self.node_open, self.u_props = False, False, None
        self.src = None           # footage id this layer was made from (image / sequence / solid)
        self.anchor = (0.0, 0.0)  # pivot, relative to the shape centre; the object's position is the anchor point
        self.items = []           # shapes drawn inside a vector layer ("vlayer")
        self.owner = None         # the vector layer this shape belongs to
        self.surf, self.png = None, None      # raster layer pixels / saved png (assets/...)
        self.ik = None            # two-bone IK: {role, other, target, flip}
        self.caption_color = None
        self.matte_show = False   # keep the matte layer visible as well
        self.collapsed = False    # a group (parent) whose children are folded away in the timeline
        self.rot_limit = None     # bones: (min, max) bend angle in degrees relative to the parent
        self.sides = 6            # polygon: number of corners
        self.drivers = []         # controllers this object follows: [{src, k, lag}]
        self.pin = False          # bones: the joint is locked (rotation cannot be changed)
        self.matte, self.matte_inv, self.caption = None, False, ""   # alpha matte layer (name), inverted?, text shown above sliders

    def value(self, prop, f):
        k = self.keys[prop]
        if not k:
            return self.base[prop]
        fr = sorted(k)
        if f <= fr[0]:
            return k[fr[0]]
        if f >= fr[-1]:
            return k[fr[-1]]
        for a, b in zip(fr, fr[1:]):
            if a <= f <= b:
                t = ease_t((f - a) / (b - a), self.ease.get(a, DEFAULT_EASE))
                return k[a] + (k[b] - k[a]) * t
        return self.base[prop]

    def set_value(self, prop, frame, v):
        if self.keys[prop]:
            self.keys[prop][int(frame)] = float(v)
        else:
            self.base[prop] = float(v)

    def key_frames(self, prop=None):
        if prop:
            return sorted(self.keys[prop])
        return sorted({f for p in PROPS for f in self.keys[p]})

    def pts_at(self, f):
        if self.phase_pts:
            ks = [k for k in self.phase_pts if k <= f]
            if ks:
                return self.phase_pts[max(ks)]
        return self.pts

    def to_dict(self):
        d = {k: getattr(self, k) for k in FIELDS}
        d["items"] = [it.to_dict() for it in self.items]
        d["keys"] = {p: {str(f): v for f, v in self.keys[p].items()} for p in PROPS}
        d["ease"] = {str(f): list(e) for f, e in self.ease.items()}
        d["phase_pts"] = {str(f): p for f, p in self.phase_pts.items()}
        d["parent"] = self.parent.name if self.parent else None
        return copy.deepcopy(d)                              # a real copy: never shares dicts / lists with the object

    @staticmethod
    def from_dict(d):
        o = Obj(d["name"], d["kind"], 0, 0)
        for k in FIELDS:
            if k in d:
                setattr(o, k, copy.deepcopy(d[k]))
        for k in ("fill", "stroke"):
            setattr(o, k, tuple(getattr(o, k)))
        o.label = tuple(o.label) if o.label and tuple(o.label) != LABEL_PURPLE else None
        o.limit = tuple(o.limit) if o.limit else None
        o.anchor = tuple(o.anchor)
        o.caption_color = tuple(o.caption_color) if o.caption_color else None
        o.items = [Obj.from_dict(x) for x in d.get("items", [])]
        for it in o.items:
            it.parent = it.owner = o
        o.pts = [tuple(p) for p in o.pts]
        o.keys = {p: {int(f): v for f, v in d.get("keys", {}).get(p, {}).items()} for p in PROPS}
        o.ease = {int(f): tuple(e) for f, e in d.get("ease", {}).items()}
        o.phase_pts = {int(f): [tuple(q) for q in p] for f, p in d.get("phase_pts", {}).items()}
        return o


def rrect_pts(hw, hh, r, seg=8):
    r = min(r, hw, hh)
    pts = []
    for cx, cy, a0 in ((hw - r, -(hh - r), -90), (hw - r, hh - r, 0), (-(hw - r), hh - r, 90), (-(hw - r), -(hh - r), 180)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _raw_pts(o, frame=1):
    """Local outline points of an object (before transform) and whether the outline is closed."""
    hw, hh = o.w / 2, o.h / 2
    k = o.kind
    if k == "pill":                       # single-axis joystick rail: full pill
        return rrect_pts(hw, hh, min(hw, hh)), True
    if k == "rsquare":                    # XY joystick: rounded square
        return rrect_pts(hw, hh, 0.22 * min(o.w, o.h)), True
    if k == "bone":
        return [(-hw, 0), (-hw * 0.55, -hh), (hw, 0), (-hw * 0.55, hh)], True
    if k == "ellipse":
        return [(hw * math.cos(i * math.tau / 40), hh * math.sin(i * math.tau / 40)) for i in range(40)], True
    if k == "polygon":
        n = max(3, int(o.sides))
        return [(hw * math.sin(i * math.tau / n), -hh * math.cos(i * math.tau / n)) for i in range(n)], True
    if k in ("line", "brush"):
        return [(px * o.w, py * o.h) for px, py in o.pts_at(frame)], bool(o.closed and k == "brush")
    if k == "ctrl":
        return [(x * hw, y * hh) for x, y in CTRL_SHAPE], True
    return [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)], True


def draw_arrange_icon(surf, kind, r, col):
    cx, cy = r.center
    d = pygame.draw
    if kind == "left":
        d.line(surf, col, (cx - 9, cy - 9), (cx - 9, cy + 9), 2)
        d.rect(surf, col, (cx - 6, cy - 6, 14, 4), border_radius=2)
        d.rect(surf, col, (cx - 6, cy + 2, 9, 4), border_radius=2)
    elif kind == "bottom":
        d.line(surf, col, (cx - 9, cy + 9), (cx + 9, cy + 9), 2)
        d.rect(surf, col, (cx - 6, cy - 6, 4, 13), border_radius=2)
        d.rect(surf, col, (cx + 2, cy - 1, 4, 8), border_radius=2)
    elif kind == "top":
        d.line(surf, col, (cx - 9, cy - 9), (cx + 9, cy - 9), 2)
        d.rect(surf, col, (cx - 6, cy - 6, 4, 13), border_radius=2)
        d.rect(surf, col, (cx + 2, cy - 6, 4, 8), border_radius=2)
    elif kind == "right":
        d.line(surf, col, (cx + 9, cy - 9), (cx + 9, cy + 9), 2)
        d.rect(surf, col, (cx - 8, cy - 6, 14, 4), border_radius=2)
        d.rect(surf, col, (cx - 3, cy + 2, 9, 4), border_radius=2)


def draw_pathfinder_icon(surf, kind, r):
    cx, cy = r.center
    a = pygame.Rect(cx - 10, cy - 10, 13, 13)
    b = pygame.Rect(cx - 3, cy - 3, 13, 13)
    light, dark = (215, 215, 215), (110, 110, 110)
    d = pygame.draw
    if kind == "Unite":
        d.rect(surf, light, a, border_radius=3)
        d.rect(surf, light, b, border_radius=3)
    elif kind == "Minus Front":
        d.rect(surf, light, a, border_radius=3)
        d.rect(surf, dark, b, border_radius=3)
        d.rect(surf, light, b, 1, border_radius=3)
    elif kind == "Intersect":
        d.rect(surf, light, a, 1, border_radius=3)
        d.rect(surf, light, b, 1, border_radius=3)
        d.rect(surf, light, a.clip(b))
    else:
        d.rect(surf, light, a, border_radius=3)
        d.rect(surf, light, b, border_radius=3)
        d.rect(surf, (40, 40, 40), a.clip(b))


def round_surf(surf, r):
    """Copy of a surface with rounded corners."""
    mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=r)
    out = surf.convert_alpha()
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def shape_pts(o, frame=1):
    """Outline in local coordinates relative to the object's anchor point."""
    pts, closed = _raw_pts(o, frame)
    ax, ay = o.anchor
    if ax or ay:
        pts = [(x - ax, y - ay) for x, y in pts]
    return pts, closed


# interface themes (all keep light text; pick one in Edit > Preferences)
THEMES = {
    "Dark": dict(COLOR_BG=(34, 34, 34), COLOR_PANEL=(38, 38, 38), COLOR_VIEWPORT=(28, 28, 28), COLOR_BTN=(48, 48, 48),
                 COLOR_HOVER=(62, 62, 62), COLOR_LINE=(58, 58, 58), COLOR_TEXT=(234, 234, 234), COLOR_MUTED=(150, 150, 150),
                 COLOR_HEAD=(28, 28, 28), COLOR_FIELD=(26, 26, 26), COLOR_TL=(30, 31, 35)),
    "Graphite": dict(COLOR_BG=(50, 51, 54), COLOR_PANEL=(60, 61, 65), COLOR_VIEWPORT=(42, 43, 46), COLOR_BTN=(74, 75, 80),
                     COLOR_HOVER=(92, 93, 99), COLOR_LINE=(82, 83, 88), COLOR_TEXT=(240, 240, 242), COLOR_MUTED=(170, 170, 176),
                     COLOR_HEAD=(44, 45, 48), COLOR_FIELD=(40, 41, 44), COLOR_TL=(46, 47, 50)),
    "Slate": dict(COLOR_BG=(58, 64, 76), COLOR_PANEL=(70, 77, 91), COLOR_VIEWPORT=(50, 55, 66), COLOR_BTN=(84, 92, 108),
                  COLOR_HOVER=(104, 113, 131), COLOR_LINE=(94, 102, 118), COLOR_TEXT=(242, 244, 248), COLOR_MUTED=(176, 184, 198),
                  COLOR_HEAD=(52, 58, 69), COLOR_FIELD=(46, 51, 61), COLOR_TL=(54, 60, 72)),
    "Steel": dict(COLOR_BG=(84, 88, 96), COLOR_PANEL=(98, 103, 112), COLOR_VIEWPORT=(72, 76, 84), COLOR_BTN=(114, 120, 131),
                  COLOR_HOVER=(136, 143, 156), COLOR_LINE=(124, 130, 142), COLOR_TEXT=(248, 248, 250), COLOR_MUTED=(200, 204, 212),
                  COLOR_HEAD=(76, 80, 88), COLOR_FIELD=(66, 70, 78), COLOR_TL=(78, 82, 90)),
}


def apply_theme(name):
    """Colours are module-level names, so a theme is applied by rewriting them in every module."""
    t = THEMES.get(name, THEMES["Dark"])
    for modname in ("mb_core", "mb_app", "mb_canvas", "mb_panels", "mb_timeline", "mb_start"):
        m = sys.modules.get(modname)
        if m:
            m.__dict__.update(t)
