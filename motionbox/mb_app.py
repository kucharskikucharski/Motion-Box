"""Motion Box - application base: scene operations, projects, layout, UI primitives, event loop."""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import traceback

import pygame

from mb_core import *            # noqa
from mb_canvas import CanvasMixin
from mb_panels import PanelsMixin
from mb_timeline import TimelineMixin
from mb_start import StartMixin

os.environ.setdefault("SDL_VIDEO_CENTERED", "1")      # splash, start window and main window open centred

KIND_DEF = {"ctrl_rot": ("Rotation Controller", 120, 120), "ctrl_posrot": ("Position + Rotation Controller", 120, 120), "vlayer": ("Vector Layer", 100, 100), "rlayer": ("Raster Layer", 100, 100), "peg": ("Peg", 40, 40), "image": ("Image", 100, 100), "bone": ("Bone", 100, 16), "rsquare": ("Joystick", 200, 200), "rect": ("Box Object", 200, 200), "ellipse": ("Circle Object", 200, 200),
            "polygon": ("Polygon Object", 200, 200), "line": ("Line Object", 200, 1),
            "brush": ("Brush Stroke", 10, 10), "pill": ("Joystick", 200, 40), "null": ("Null Control", 100, 100),
            "ctrl": ("Position Controller", 120, 120), "joy": ("Joystick", 200, 200)}


class AppBase:
    def __init__(self, quick=False):
        pygame.init()
        pygame.font.init()
        self.make_fonts()
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((640, 360))
        self.W, self.H = 640, 360
        self.running, self.mode = True, "splash"
        # document
        self.fps, self.total, self.frame = 24, 72, 1
        self.aw, self.ah = 1920, 1080
        self.project_name, self.project_dir = "Untitled", None
        self.objs, self.sel, self.hover = [], [], None
        # playback
        self.playing, self.loop, self.play_acc = False, True, 0.0
        # tools / ui state
        self.tool, self.slot_tool = "select", {}
        self.flyout, self.press_slot = None, None
        self.workspace, self.left_tab, self.right_tab = "Animate", "Edit", "Properties"
        self.link_mode, self.link_drag, self.link_mouse = False, None, (0, 0)
        self.drag, self.drag_end, self.btn = None, None, 1
        self.hits, self.row_rects, self.hover_hint = [], [], None
        self.dialog, self.edit, self.picker, self.eyedrop = None, None, None, False
        self.menu_open, self.maxi = None, None
        self.toast = ("", 0)
        self.view_fit, self.zoom, self.ox, self.oy = True, 0.3, 0.0, 0.0
        self.view = {"safe": False, "grid3": False, "gray": False, "onion": False, "render": False, "camera": False}
        self.def_fill, self.def_stroke = (140, 70, 200), (15, 15, 15)
        self.brush_pts, self.marquee, self.cursor_kind = None, None, None
        self.library, self.lib_scroll = [], 0
        self.tl_zoom, self.tl_off, self.tl_vy = 1.0, 0.0, 0.0
        self.tl_cw, self.tl_area, self.tl_max, self.tl_vmax = 1.0, 1.0, 0.0, 0.0
        self.expr_bad, self._expr_depth = set(), 0
        self.ctx, self.rotating, self.slot_pos, self.flyout_rects = None, False, {}, []
        self.start_scroll, self.start_sel, self.start_click, self.np_dd = 0, None, (None, 0), False
        self.start_tab, self.tl_cx0 = "load", 0
        self.auto_phase = False
        self.r_view = pygame.Rect(0, 0, 100, 100)
        self.r_aux = None
        self.w_left, self.w_right, self.h_tl = 208, 264, 176          # resizable panels
        self.reorder, self.quit_dlg, self.saved_sig, self.last_autosave = None, None, None, 0
        self.autosave = {"on": True, "min": 5}
        self.theme, self.idle_icons, self._ik_depth = "Dark", {}, 0
        self.replace_target, self.seq_dlg, self.clipboard, self.paste_n, self.br_start, self.br_last = None, None, [], 0, {}, 0
        self.animate_filter, self.split_frac, self.sel_wire, self.hit_clip, self.aux_scroll = "both", 0.5, None, None, 0
        self.focus_area, self.clip_cut, self.ar_start, self.ar_last, self.rename_dlg = "view", False, {}, 0, None
        self.prefs_tab, self.pref_q = "General", ""
        self.global_key, self.rig_bones, self.auto_key, self.rest_layer, self.parent_drop, self.autoscroll = False, {}, False, None, None, None
        self.drop_wire, self.kf_clip, self._last_sel, self.prop_rects = None, [], (), []
        self.sel_prop, self._ws_prev, self._ft_t, self.tl_marquee, self.kf_rects = None, None, 0, None, []
        self.ph_sel, self.ph_play, self.ph_prev = set(), False, None
        self.right_scroll, self.right_max, self._content_end, self.align_to = 0, 0, 0, "artboard"
        self.wrap_ok, self.wrap_off, self.dock_picker, self.drawing_tab, self.eyedrop_p = False, 0, {"field": "fill", "h": 0.0, "s": 0.0, "v": 1.0, "a": 100, "sv_h": None}, "Colors", None
        self.onion, self.markers, self.marker_dlg = {"before": 1, "after": 1}, [], None
        self.fill_opts, self.foot_view, self.foot_q, self.sugg_rects, self.sugg_i = {"target": "fill", "mode": "click"}, "list", "", [], 0
        self.cursor_cache, self.tool_cols = {}, 1
        self.split_active, self.splitters = None, []
        self.undo_stack, self.redo_stack, self.kf_sel = [], [], []
        self.prefs_open, self.thumb_cache = False, {}
        self.label_list = [[n, c] for n, c in LABEL_DEFAULT_LIST]
        self.type_label = dict(TYPE_LABEL_DEFAULT)
        self.labels = {}
        self.labels_sync()
        self.nd_zoom, self.nd_ox, self.nd_oy = 1.0, 0.0, 0.0           # node panel view
        self.art_color, self.hidden, self.sel_anchor = COLOR_ARTBOARD, {"right"}, None       # the right dock starts closed (Panels menu opens it)
        self.brush_opts = {"auto_close": False, "auto_group": False, "auto_fill": False, "draw_under": False}
        self.palette = [{"c": tuple(c), "name": "", "folder": None} for _, c in LABEL_DEFAULT_LIST[:8]]
        self.pal_folders, self.pal_view, self.pal_open = [], "circles", None
        self.lib_sel, self.lib_folder, self._lib_cache, self._lib_click, self._lib_visible = set(), None, {}, (None, 0), []
        self.foot_multi = set()
        self.ex_multi, self.ex_seq = set(), True
        self.hint_since, self._last_hint, self.nd_marquee, self.bone_last = 0, None, None, None
        self.link_start, self.tl_edges = (0, 0), []
        self.bone_chain, self.active_layer, self.layer_dlg = False, None, False
        self.render_dlg, self.rend_prog, self._nd_seen, self.brush_px = None, None, -1, 8
        self.footage, self.foot_sel, self.foot_click, self.foot_scroll = [], None, (None, 0), 0
        self.lib_mode, self.ex_dir, self.ex_sel, self.ex_click, self.ex_scroll, self.ex_n = "Objects", os.path.expanduser("~"), None, (None, 0), 0, 0
        self.img_cache, self.scaled_cache, self.ex_thumbs = {}, {}, {}
        self.work_in = self.work_out = None                          # work area (I / O)
        self.load_prefs()
        try:
            pygame.display.set_icon(pygame.image.load(os.path.join(ASSETS_DIR, "icon.png")))
        except Exception:  # noqa
            pass
        self.load_library()
        self.new_scene()
        self.enter_splash()
        if quick:
            self.project_dir = os.path.join(PROJECTS_DIR, "Untitled")
            os.makedirs(self.project_dir, exist_ok=True)
            self.enter_main()

    # ------------------------------------------------------------------ scene
    def new_scene(self):
        null = Obj("Null Control 1", "null", 760, 540, 100, 100)
        null.fill = (61, 121, 230)
        for f, x, y in ((1, 760, 540), (36, 1150, 380), (72, 760, 540)):
            null.keys["x"][f], null.keys["y"][f] = x, y
        box = Obj("Box Object", "rect", 1010, 490, 200, 200)
        self.objs, self.sel, self.frame = [null, box], [box], 1

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, v):
        self._frame = v
        Obj.CUR[0] = int(v)
        sel = getattr(self, "sel", None)
        if sel:                                              # shapes of another phase are not on the screen any more
            keep = [s for s in sel if not s.owner or s in s.owner.items]
            if len(keep) != len(sel):
                self.sel = keep

    @property
    def psel(self):
        return self.sel[-1] if self.sel else None

    def select_relative(self, children=False):
        o = self.psel
        if o is None:
            return
        lyr = o.owner or o
        if children:
            kids = [c for c in self.objs if c.parent is lyr]
            if not kids:
                self.msg(f"{lyr.name} has no children")
                return
            lyr.collapsed = False
            self.sel = kids
        else:
            p = lyr.parent
            if p is None or p not in self.objs:
                self.msg(f"{lyr.name} has no parent")
                return
            self.sel = [p]
        self.reveal_in_timeline(self.sel[0])
        self.msg("Selected " + ("children of " + lyr.name if children else "parent " + self.sel[0].name))

    def nd_center_on(self, o):
        if o is None or not self.r_aux:
            self.msg("Select something first")
            return
        nr, r = self.node_rect(o), self.r_aux
        self.nd_ox += r.centerx - nr.centerx
        self.nd_oy += r.centery - nr.centery

    def reveal_in_timeline(self, o, center=False):
        lyr = o.owner or o
        p = lyr.parent
        while p is not None:                                   # open the parents on the way
            p.collapsed = False
            p = p.parent
        for i, (kind, ob, _) in enumerate(self.tl_rows()):
            if ob is lyr and kind == "o":
                reg_h = max(24, self.r_tl.h - 48)
                if center or i * 24 < self.tl_vy or i * 24 + 24 > self.tl_vy + reg_h:
                    self.tl_vy = max(0, i * 24 - reg_h // 2)
                return

    def select(self, o, add=False):
        if o is None:
            if not add:
                self.sel = []
        elif add:
            if o in self.sel:
                self.sel.remove(o)
            else:
                self.sel.append(o)
        else:
            self.sel = [o]

    def unique_name(self, base, numbered=False):
        names = {o.name for o in self.objs}
        if numbered:
            n = 1
            while f"{base} {n}" in names:
                n += 1
            return f"{base} {n}"
        if base not in names:
            return base
        n = 2
        while f"{base} {n}" in names:
            n += 1
        return f"{base} {n}"

    def new_obj(self, kind, x, y, w=None, h=None, select=True, insert=True):
        base, dw, dh = KIND_DEF[kind]
        o = Obj(self.unique_name(base, numbered=kind in ("null", "ctrl", "ctrl_rot", "ctrl_posrot", "peg")), kind, x, y, w or dw, h or dh)
        if kind in ("rect", "ellipse", "polygon"):
            o.fill, o.stroke = self.def_fill, self.def_stroke
        elif kind in ("line", "brush"):
            o.fill_on, o.stroke_on = False, True
            o.stroke_w = 4 if kind == "brush" else 3
            o.stroke = self.def_fill                            # lines and strokes use the front colour swatch
        elif kind == "null":
            o.fill = (61, 121, 230)
        elif kind.startswith("ctrl"):
            o.fill = (240, 160, 40)
        elif kind == "bone":
            o.fill, o.fill_a, o.stroke_on, o.stroke, o.stroke_w = (239, 171, 200), 22.0, True, (239, 171, 200), 2.0   # outline bones, own colour
        elif kind == "peg":
            o.fill = (160, 160, 170)
        if insert:
            self.objs.insert(0, o)
        if select:
            self.sel = [o]
        return o

    def add_box(self, name="Box Object", x=960, y=540, color=(140, 70, 200)):   # used by scripts
        o = self.new_obj("rect", x, y)
        o.name, o.fill = self.unique_name(name), tuple(color)
        return o

    def add_null(self, name=None, x=960, y=540):
        o = self.new_obj("null", x, y)
        if name:
            o.name = self.unique_name(name)
        return o

    def add_joystick(self, mode, x, y):
        name = {"x": "Slider X", "y": "Slider Y", "xy": "Joystick XY"}[mode]
        w = 200 if "x" in mode else 40
        h = 200 if "y" in mode else 40
        fr = Obj(self.unique_name(name), "rsquare" if mode == "xy" else "pill", x, y, w, h)
        fr.fill, fr.stroke, fr.stroke_on = (40, 40, 46), (110, 110, 125), True
        kn = Obj(self.unique_name(fr.name + " Knob"), "ellipse", 0, 0, 36, 36)
        kn.fill, kn.parent = (61, 121, 230), fr
        lx = (w - 36) / 2 if "x" in mode else 0        # the knob never leaves the frame
        ly = (h - 36) / 2 if "y" in mode else 0
        kn.limit = (-lx, lx, -ly, ly)
        self.objs[0:0] = [kn, fr]
        self.sel = [kn]
        self.msg(f"{fr.name} created - move the knob")

    # ------------------------------------------------------------------ layers
    def new_layer(self, kind):
        base = "Vector Layer" if kind == "vlayer" else "Raster Layer"
        o = Obj(self.unique_name(base, numbered=True), kind, self.aw // 2, self.ah // 2, self.aw, self.ah)
        if kind == "rlayer":
            o.surf = pygame.Surface((self.aw, self.ah), pygame.SRCALPHA)
        self.objs.insert(0, o)
        self.sel, self.active_layer, self.layer_dlg = [o], o, False
        self.msg(f"{o.name} created - shape tools and the brush now draw into it")
        return o

    def target_layer(self, kind):
        for c in ((self.psel.owner or self.psel) if self.psel else None, self.active_layer):
            if c and c.kind == kind and c in self.objs and not c.locked:
                return c
        return None

    def new_item(self, kind, x, y, w=1, h=1):
        """A shape inside the active vector layer (one is created when there is none)."""
        layer = self.target_layer("vlayer") or self.new_layer("vlayer")
        o = self.new_obj(kind, x, y, w=w, h=h, insert=False)
        o.parent = o.owner = layer
        self.put_base(o, x, y)
        layer.items.insert(0, o)
        self.sel, self.active_layer = [o], layer
        return o

    def put_base(self, o, ax, ay):
        if o.owner:
            ax, ay = self.to_local(o.owner, ax, ay)
        o.base["x"], o.base["y"] = round(ax, 1), round(ay, 1)

    def art_to_layer(self, layer, ax, ay):
        x, y, s, r = self.world(layer, self.frame)
        a = math.radians(-r)
        dx, dy = ax - x, ay - y
        return ((dx * math.cos(a) - dy * math.sin(a)) / s + layer.w / 2, (dx * math.sin(a) + dy * math.cos(a)) / s + layer.h / 2)

    def toggle_flag(self, o, flag):
        v = not getattr(o, flag)
        for t in (self.sel if o in self.sel else [o]):
            setattr(t, flag, v)

    def layer_menu(self, o, pos):
        if o not in self.sel:
            self.sel = [o]
        self.ctx = {"pos": pos, "items": [("Group  (Ctrl+G)", self.group_selected), ("Fold layers (pack)", self.fold_selected),
                                          ("Lock / unlock", lambda: self.toggle_flag(o, "locked")),
                                          ("Hide / show", lambda: self.toggle_flag(o, "visible")),
                                          ("Rename...  (Ctrl+R)", self.open_rename),
                                          ("Parent to...", lambda: self.parent_menu(o, pos)),
                                          ("Trim start to playhead", lambda: self.trim_to_playhead("in")),
                                          ("Trim end to playhead", lambda: self.trim_to_playhead("out")),
                                          ("Cut at playhead", lambda: self.cut_layer(o.owner or o, self.frame)),
                                          ("Remove trim", lambda: self.trim_to_playhead("reset")),
                                          ("New layer...", lambda: setattr(self, "layer_dlg", True)),
                                          ("Delete", self.delete_selected)] + ([("Show in footage", lambda: self.show_in_footage(o))] if o.src is not None else [])}

    def reset_anchor(self):
        for o in self.sel:
            ax, ay = o.anchor
            if ax or ay:
                x, y, s, r = self.world(o, self.frame)
                a = math.radians(r)
                o.anchor = (0.0, 0.0)
                self.set_world_pos(o, x + (-ax * math.cos(a) + ay * math.sin(a)) * s, y + (-ax * math.sin(a) - ay * math.cos(a)) * s)
        self.msg("Anchor point moved back to the centre")

    # ------------------------------------------------------- clipboard (copy / cut / paste)
    def copy_sel(self, cut=False):
        if not self.sel:
            self.msg("Nothing selected")
            return False
        self.clipboard = []
        for o in self.sel:
            x, y = self.world(o, self.frame)[:2]
            self.clipboard.append({"d": o.to_dict(), "pos": (x, y), "item": bool(o.owner), "layer": o.owner.name if o.owner else None,
                                   "surf": o.surf.copy() if o.surf is not None else None})
        self.paste_n, self.clip_cut = 0, cut
        self.msg(f"Copied {len(self.sel)} object(s)" if not cut else f"Cut {len(self.sel)} object(s)")
        return True

    def cut_sel(self):
        if self.copy_sel(cut=True):
            self.delete_selected()
            self.msg("Cut - select a layer in the timeline and press Ctrl+V")

    def paste(self, at=None):
        """Pasting into the same layer puts the copy 10 px beside the original; into another layer it lands on the same spot.
        The copy is always a separate object."""
        if not self.clipboard:
            self.msg("The clipboard is empty")
            return
        self.paste_n += 1
        p = self.psel
        lyr = (p.owner or p) if p else None
        target = lyr if (lyr and lyr.kind == "vlayer" and not lyr.locked and lyr in self.objs) else None
        src = {c["layer"] for c in self.clipboard if c["item"]}
        if target is None and src:                                 # nothing selected: back into the layer it came from
            target = next((o for o in self.objs if o.kind == "vlayer" and o.name in src and not o.locked), None)
        same = target is not None and target.name in src
        step = self.paste_n - (1 if self.clip_cut else 0)             # a cut original is gone, so the first paste is in place
        off = 10 * step if (same or any(not c["item"] for c in self.clipboard)) else 0
        new = []
        for c in self.clipboard:
            o = Obj.from_dict(c["d"])
            o.parent = None
            o.owner = None
            wx, wy = c["pos"]
            if o.kind not in ("vlayer", "rlayer"):
                wx, wy = wx + off, wy + off
            if c["item"] or o.kind in ("rect", "ellipse", "polygon", "line", "brush"):
                target = target or self.new_layer("vlayer")
                o.parent = o.owner = target
                target.items.insert(0, o)
                self.put_base(o, wx, wy)
            else:
                o.name = self.unique_name(o.name)
                o.base["x"], o.base["y"] = round(wx, 1), round(wy, 1)
                if c["surf"] is not None:
                    o.surf = c["surf"].copy()
                self.objs.insert(0, o)
            new.append(o)
        self.sel = new
        if target:
            self.active_layer = target
        self.msg(f"Pasted {len(new)} object(s)" + (f" into {target.name}" if target else ""))

    def move_to_new_layer(self):
        its = [o for o in self.sel if o.owner]
        if not its:
            self.msg("Select shapes that are drawn inside a vector layer")
            return
        pos = [self.world(o, self.frame)[:2] for o in its]
        for o in its:
            o.owner.items.remove(o)
        layer = self.new_layer("vlayer")
        for o, (x, y) in zip(its, pos):
            o.parent = o.owner = layer
            layer.items.append(o)
            self.put_base(o, x, y)
        self.sel = its

    def trim_to_playhead(self, which):
        f = self.frame
        for o in self.sel:
            lyr = o.owner or o
            if which == "in" and f <= (lyr.t_out or self.total):
                lyr.t_in = f
            elif which == "out" and f >= lyr.t_in:
                lyr.t_out = None if f >= self.total else f
            elif which == "reset":
                lyr.t_in, lyr.t_out = 1, None
        self.msg("Layer trimmed" if which != "reset" else "Trim removed")

    def arrow_key(self, k, mods):
        step = 10 if mods & pygame.KMOD_SHIFT else 1
        movable = [o for o in self.sel if not o.locked]
        if self.focus_area == "view" and movable:                       # nudge the selection: 1 px, Shift = 10 px
            dx = step * ((k == pygame.K_RIGHT) - (k == pygame.K_LEFT))
            dy = step * ((k == pygame.K_DOWN) - (k == pygame.K_UP))
            for o in movable:
                x, y = self.world(o, self.frame)[:2]
                self.set_world_pos(o, x + dx, y + dy)
        elif k in (pygame.K_LEFT, pygame.K_RIGHT):                      # after clicking the timeline: step the playhead
            self.goto(self.frame + (step if k == pygame.K_RIGHT else -step))

    def open_rename(self, mx=0, my=0):
        targets = [o for o in self.sel if not o.owner]
        if not targets:
            self.msg("Select one or more layers in the timeline first")
            return
        self.rename_dlg = {"find": "", "repl": "", "suffix_on": True, "suffix": "", "targets": targets}

    def rename_preview(self, d):
        out = []
        for n, o in enumerate(d["targets"], 1):
            new = o.name.replace(d["find"], d["repl"]) if d["find"] else o.name
            if d["suffix_on"] and d["suffix"]:
                new += d["suffix"].replace("#", str(n))
            out.append((o, new))
        return out

    def apply_rename(self):
        d, self.rename_dlg = self.rename_dlg, None
        for o, new in self.rename_preview(d):
            self.rename_obj(o, new)

    def layer_double_click(self, o):
        now = pygame.time.get_ticks()
        last = getattr(self, "_lp_last", (None, 0))
        self._lp_last = (o, now)
        if last[0] is o and now - last[1] < 400:                     # double-click on a layer = rename it
            self.begin_edit(f"rename_{id(o)}", o.name, lambda s, o=o: self.rename_obj(o, s))

    def set_doc(self, attr, v, lo, hi):
        v = int(clamp(v, lo, hi))
        if attr == "total" and v > self.total:
            for o in self.objs:                              # layers keep their length when the scene gets longer
                if o.t_out is None:
                    o.t_out = self.total
        setattr(self, attr, v)

    def parent_menu(self, o, pos):
        names = [x for x in self.objs if x not in self.sel][:14]
        self.ctx = {"pos": pos, "items": [("None (unparent)", lambda: [self.unlink(c) for c in self.sel])] +
                    [(x.name, (lambda x=x: [self.link(c, x) for c in self.sel])) for x in names]}

    def rename_obj(self, o, new):
        new = new.strip()
        old = o.name
        if not new or new == old:
            return
        if any(x is not o and x.name == new for x in self.objs):
            new = self.unique_name(new)
        o.name = new
        for x in self.objs:                                          # keep everything that points at the old name working
            for d in x.drivers:
                if d["src"] == old:
                    d["src"] = new
            if x.matte == old:
                x.matte = new
            if x.ik:
                for k in ("other", "target"):
                    if x.ik.get(k) == old:
                        x.ik[k] = new
            for p, ex in list(x.expr.items()):
                x.expr[p] = ex.replace(f'("{old}"', f'("{new}"')
        self.msg(f"Renamed to {new}")

    def find(self, name):
        return next((o for o in self.objs if o.name == name), None)

    def set_key(self, obj, prop, frame, value):
        obj.keys[prop][int(frame)] = float(value)

    def delete_selected(self):
        for o in list(self.sel):
            if o.owner:                                      # a shape inside a vector layer
                if o in o.owner.items:
                    o.owner.items.remove(o)
                continue
            for c in [c for c in self.objs if c.parent is o]:
                self.unlink(c, quiet=True)
            if o in self.objs:
                self.objs.remove(o)
        if self.sel:
            self.msg("Deleted " + (self.sel[0].name if len(self.sel) == 1 else f"{len(self.sel)} objects"))
        self.sel = []

    def duplicate_selected(self):
        new = []
        for o in self.sel:
            if o.owner:
                n = Obj.from_dict(o.to_dict())
                n.parent = n.owner = o.owner
                n.base["x"] += 10
                n.base["y"] += 10
                o.owner.items.insert(0, n)
                new.append(n)
                continue
            n = Obj.from_dict(o.to_dict())
            n.name, n.parent = self.unique_name(o.name), o.parent
            n.base["x"] += 10
            n.base["y"] += 10
            self.objs.insert(0, n)
            new.append(n)
        if new:
            self.sel = new
            self.msg(f"Duplicated {len(new)} object(s)")

    def group_selected(self):
        if len(self.sel) < 2:
            self.msg("Select two or more objects to group")
            return
        pts = [self.world(o, self.frame) for o in self.sel]
        g = self.new_obj("null", sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), select=False)
        g.name = self.unique_name("Group")
        for o in list(self.sel):
            if not o.parent:
                self.link(o, g, quiet=True)
        self.sel = [g]
        self.msg(f"Grouped into {g.name} (a null parent)")

    def ungroup_selected(self):
        for o in list(self.sel):
            kids = [c for c in self.objs if c.parent is o]
            if o.kind == "null" and kids:
                for c in kids:
                    self.unlink(c, quiet=True)
                self.objs.remove(o)
                self.sel = kids
                self.msg(f"Ungrouped {o.name}")

    # ---------------------------------------------------- transforms / values
    def val(self, o, p, f):
        if self.rest_layer is not None:                          # drawing view: everything at its rest values (no rig, no animation)
            return o.base[p]
        v = o.value(p, f)
        if p == "rotation" and o.ik and self._ik_depth < 1:
            v = self.ik_rotation(o, f, v)
        ex = o.expr.get(p)
        if ex and self._expr_depth < 4:
            self._expr_depth += 1

            def _world(name):
                ob = self.find(name)
                if not ob:
                    raise ValueError("no object " + name)
                return self.world(ob, f)
            class _L:
                def __init__(s, w):
                    s.x, s.y, s.sc, s.rot = w
            def _layer(n):                                    # layer("Name").x .y (world) and .lx .ly (local, e.g. a joystick knob)
                ob = self.find(n)
                if not ob:
                    raise ValueError("no object " + n)
                L = _L(self.world(ob, f))
                L.lx, L.ly = self.val(ob, "x", f), self.val(ob, "y", f)
                return L
            def _layer2(n, lag=0):                            # layer("Name", delay_in_frames).lx .ly .x .y
                ob = self.find(n)
                if not ob:
                    raise ValueError("no object " + n)
                ff = max(1, f - int(lag))
                L = _L(self.world(ob, ff))
                L.lx, L.ly = self.val(ob, "x", ff), self.val(ob, "y", ff)
                return L
            ns = {"layer": _layer2, "t": f, "time": f / self.fps, "value": v, "pi": math.pi, "sin": math.sin, "cos": math.cos,
                  "tan": math.tan, "abs": abs, "min": min, "max": max, "sqrt": math.sqrt, "clamp": clamp,
                  "world": _world,
                  "wiggle": lambda fr, am: am * (math.sin(f * fr * .37) + math.sin(f * fr * .91 + 1.3)) / 2}
            try:
                v = float(eval(ex, {"__builtins__": {}}, ns))
            except Exception as e:  # noqa
                if (o.name, p) not in self.expr_bad:
                    self.expr_bad.add((o.name, p))
                    self.msg(f"Expression error ({o.name}.{p}): {e}")
            finally:
                self._expr_depth -= 1
        return v

    # ------------------------------------------------------------- two-bone IK
    def world_pos(self, o, f):
        x, y = self.val(o, "x", f), self.val(o, "y", f)
        if not o.parent:
            return x, y
        px, py, ps, pr = self.world(o.parent, f)
        a = math.radians(pr)
        return px + x * ps * math.cos(a) - y * ps * math.sin(a), py + x * ps * math.sin(a) + y * ps * math.cos(a)

    def world_scale(self, o, f):
        return self.val(o, "scale", f) * (self.world_scale(o.parent, f) if o.parent else 1.0)

    def ik_rotation(self, o, f, default):
        """Law of cosines: the two bones reach for the controller (Duik-style IK)."""
        d = o.ik
        other, tgt = self.find(d.get("other", "")), self.find(d.get("target", ""))
        if not other or not tgt:
            return default
        upper, lower = (o, other) if d["role"] == "upper" else (other, o)
        if lower.parent is not upper:
            return default
        self._ik_depth += 1
        try:
            P, T = self.world_pos(upper, f), self.world(tgt, f)[:2]
            L1, L2 = upper.w * self.world_scale(upper, f), lower.w * self.world_scale(lower, f)
            dx, dy = T[0] - P[0], T[1] - P[1]
            dist = clamp(math.hypot(dx, dy), abs(L1 - L2) + 1e-3, L1 + L2 - 1e-3)
            c1 = clamp((L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist), -1, 1)
            c2 = clamp((L1 * L1 + L2 * L2 - dist * dist) / (2 * L1 * L2), -1, 1)
            sg = -1 if d.get("flip") else 1
            if d["role"] == "upper":
                pr = self.world(upper.parent, f)[3] if upper.parent else 0.0
                return math.degrees(math.atan2(dy, dx) - sg * math.acos(c1)) - pr
            return math.degrees(sg * (math.pi - math.acos(c2)))
        finally:
            self._ik_depth -= 1

    def create_ik(self, lower):
        upper = lower.parent
        if lower.kind != "bone" or not upper or upper.kind != "bone":
            self.msg("Click the LOWER bone of a chain made of two bones")
            return
        c = self.new_obj("ctrl", *self.bone_end(lower))
        c.name = self.unique_name("IK " + lower.name)
        lower.ik = {"role": "lower", "other": upper.name, "target": c.name, "flip": False}
        upper.ik = {"role": "upper", "other": lower.name, "target": c.name, "flip": False}
        self.msg(f"IK created: move '{c.name}' and the chain follows")

    def flip_ik(self, o):
        for b in (o, self.find((o.ik or {}).get("other", ""))):
            if b and b.ik:
                b.ik["flip"] = not b.ik.get("flip", False)

    def remove_ik(self, o):
        other = self.find((o.ik or {}).get("other", ""))
        o.ik = None
        if other:
            other.ik = None

    def world(self, o, f, depth=0):
        x, y, s, r = (self.val(o, p, f) for p in ("x", "y", "scale", "rotation"))
        if o.parent and depth < 32:
            px, py, ps, pr = self.world(o.parent, f, depth + 1)
            a = math.radians(pr)
            lx, ly = x * ps, y * ps
            x = px + lx * math.cos(a) - ly * math.sin(a)
            y = py + lx * math.sin(a) + ly * math.cos(a)
            s *= ps
            r += pr
        return x, y, s, r

    def to_local(self, parent, wx, wy):
        px, py, ps, pr = self.world(parent, self.frame)
        a = math.radians(pr)
        dx, dy = wx - px, wy - py
        return ((dx * math.cos(a) + dy * math.sin(a)) / ps, (-dx * math.sin(a) + dy * math.cos(a)) / ps)

    def set_world_pos(self, o, wx, wy):
        if o.locked or {"x", "y"} <= self.locked_props(o):
            return
        lx, ly = self.to_local(o.parent, wx, wy) if o.parent else (wx, wy)
        if o.limit:
            lx, ly = clamp(lx, o.limit[0], o.limit[1]), clamp(ly, o.limit[2], o.limit[3])
        o.set_value("x", self.frame, round(lx, 1))
        o.set_value("y", self.frame, round(ly, 1))

    def locked_props(self, o):
        """Properties that cannot be changed for this object (controllers and joysticks are restricted on purpose)."""
        k = o.kind
        if o.pin:
            return {"rotation"}                          # a pinned joint
        if o.ik:
            return {"rotation"}                          # driven by the IK solver
        if k == "ctrl":
            return {"scale", "rotation"}
        if k == "ctrl_rot":
            return {"x", "y", "scale"}
        if k == "ctrl_posrot":
            return {"scale"}
        if k in ("pill", "rsquare"):
            return {"rotation"}
        if o.limit:
            return {"rotation", "scale"}
        return set()

    def is_joy(self, o):
        return o.kind in ("pill", "rsquare") or bool(o.limit)

    def joy_parts(self, o):
        """(frame, knob) if o belongs to a joystick, else None."""
        if o.kind in ("pill", "rsquare"):
            kn = next((c for c in self.objs if c.parent is o and c.limit), None)
            return (o, kn) if kn else None
        if o.limit and o.parent and o.parent.kind in ("pill", "rsquare"):
            return (o.parent, o)
        return None

    def in_range(self, o, f=None):
        f = f or self.frame
        return o.t_in <= f <= (o.t_out or self.total)

    def layer_click(self, o):
        """After Effects selection: Shift = range, Ctrl/Cmd = toggle only the clicked layer."""
        m = pygame.key.get_mods()
        if m & pygame.KMOD_SHIFT and self.sel_anchor in self.objs:
            a, b = self.objs.index(self.sel_anchor), self.objs.index(o)
            rng = self.objs[min(a, b):max(a, b) + 1]
            self.sel = rng if not m & (pygame.KMOD_CTRL | pygame.KMOD_META) else self.sel + [x for x in rng if x not in self.sel]
        elif m & (pygame.KMOD_CTRL | pygame.KMOD_META):
            self.select(o, True)
            self.sel_anchor = o
        else:
            self.sel, self.sel_anchor = [o], o

    def fold_selected(self):
        if len(self.sel) < 2:
            self.msg("Select two or more layers to fold")
            return
        fid = max([o.fold_id for o in self.objs if o.fold_id is not None] or [0]) + 1
        for o in self.sel:
            o.fold_id = fid
        self.sel = []
        self.msg("Layers folded - click the bar in the timeline to unfold")

    def unfold(self, fid):
        for o in self.objs:
            if o.fold_id == fid:
                o.fold_id = None

    def toggle_u(self):
        if not self.sel:
            self.msg("Select a layer, then press U to show only its animated properties")
        for o in self.sel:
            if o.expanded and o.u_mode:
                o.expanded = o.u_mode = False
            else:
                o.expanded = o.u_mode = True
                o.u_props = None

    def open_right(self, tab):
        self.hidden.discard("right")
        self.right_tab = tab

    def is_controller(self, o):
        if o.kind.startswith("ctrl") or o.limit:
            return True
        return o.kind in ("pill", "rsquare") and any(c.parent is o and c.limit for c in self.objs)      # the frame of a joystick / slider

    def trim_at_playhead(self, keep_left):
        n = 0
        for o in [x for x in self.sel if not x.owner]:
            end = o.t_out or self.total
            if keep_left and self.frame < o.t_in:
                continue
            if not keep_left and self.frame > end:
                continue
            if keep_left:                                    # Alt+]  keeps the part before the playhead (or stretches the layer to it)
                o.t_out = None if self.frame >= self.total else self.frame
            else:                                            # Alt+[  keeps the part after the playhead (or stretches the layer back to it)
                o.t_in = self.frame
            n += 1
        self.msg(f"Trimmed {n} layer(s): kept the part {'before' if keep_left else 'after'} the playhead" if n else "Select a layer under the playhead")

    def toggle_dock(self, name):
        self.hidden ^= {name}

    def set_prop(self, o, p, v):
        if p in self.locked_props(o):
            return
        if not o.locked:
            if self.auto_key and p in PROPS and self.watched(o, p):   # Auto Key: every edit of a stopwatch-on value becomes a keyframe
                o.keys[p][int(self.frame)] = float(v)
            else:
                o.set_value(p, self.frame, v)

    def link(self, child, parent, quiet=False):
        p = parent
        while p:
            if p is child:
                self.msg("Cannot link: it would create a parent loop")
                return False
            p = p.parent
        wx, wy, ws, wr = self.world(child, self.frame)
        child.parent = parent
        lx, ly = self.to_local(parent, wx, wy)
        _, _, ps, pr = self.world(parent, self.frame)
        child.keys["x"].clear()
        child.keys["y"].clear()
        child.base["x"], child.base["y"] = round(lx, 1), round(ly, 1)
        if not child.keys["rotation"]:
            child.base["rotation"] = wr - pr
        if not child.keys["scale"]:
            child.base["scale"] = ws / ps
        if not quiet:
            self.msg(f"{child.name} is now a child of {parent.name} (its X/Y keys were cleared)")
        return True

    def unlink(self, o, quiet=False):
        if not o.parent:
            return
        wx, wy, ws, wr = self.world(o, self.frame)
        o.parent = None
        o.keys["x"].clear()
        o.keys["y"].clear()
        o.base["x"], o.base["y"] = round(wx, 1), round(wy, 1)
        if not o.keys["rotation"]:
            o.base["rotation"] = wr
        if not o.keys["scale"]:
            o.base["scale"] = ws
        if not quiet:
            self.msg(f"Unlinked {o.name}")

    def toggle_key(self, o, f=None):
        f = f or self.frame
        if f in o.key_frames():
            for p in PROPS:
                o.keys[p].pop(f, None)
            self.msg(f"Removed keyframe {f}")
        else:
            ps = [p for p in PROPS if self.watched(o, p)]
            if not ps:
                self.msg("No stopwatch is on for this layer: press P / R / S / T to show a value and click its stopwatch")
                return
            for p in ps:
                o.keys[p][f] = o.value(p, f)
            self.msg(f"Keyframe {f} on {o.name}: {', '.join(PROP_LABEL[p] for p in ps)}")

    def toggle_prop_key(self, o, p):
        if self.frame in o.keys[p]:
            del o.keys[p][self.frame]
        else:
            o.keys[p][self.frame] = o.value(p, self.frame)

    def kf_copy(self):
        base = min(f for _, _, f in self.kf_sel)
        self.kf_clip = []
        for o, p, f in self.kf_sel:
            props = [(pp, o.keys[pp][f]) for pp in (PROPS if p is None else (p,)) if f in o.keys[pp]]
            if props:
                self.kf_clip.append((o, p, f - base, props, o.ease.get(f) if p is None else None))
        self.msg(f"Copied {len(self.kf_clip)} keyframe(s) - Ctrl+V pastes them at the playhead")

    def kf_paste(self):
        srcs = []
        for c in self.kf_clip:
            if c[0] not in srcs:
                srcs.append(c[0])
        targets = [o for o in self.sel if not o.owner]
        mapping = {id(srcs[0]): targets} if (len(srcs) == 1 and targets) else {}      # one source layer -> every selected layer
        new = []
        for o, p, rel, props, ease in self.kf_clip:
            for t in mapping.get(id(o), [o]):
                f = int(clamp(self.frame + rel, 1, self.total))
                for pp, v in props:
                    t.keys[pp][f] = v
                if ease is not None:
                    t.ease[f] = ease
                new.append((t, p, f))
        self.kf_sel = new
        self.msg(f"Pasted {len(new)} keyframe(s) at frame {self.frame}")

    def toggle_auto_key(self, mx=0, my=0):
        self.auto_key = not self.auto_key
        self.msg("Auto Key ON: every change of position, rotation, scale or opacity makes a keyframe" if self.auto_key else "Auto Key off")

    def enter_rest_edit(self, o=None):
        o = o or self.psel
        lyr = (o.owner or o) if o else None
        if not lyr or lyr.kind not in ("vlayer", "rlayer"):
            self.msg("Select a drawing layer first")
            return
        self.rest_layer, self.active_layer, self.sel = lyr, lyr, [lyr]
        self.msg(f"Drawing view: {lyr.name} without the rig and animation. Esc leaves it")

    def watched(self, o, p):
        return p in o.watch or bool(o.keys[p])

    def set_watch(self, o, p):
        if p in o.watch or o.keys[p]:                              # switching a stopwatch off removes that value's keyframes
            if o.keys[p]:
                self.push_undo()
                o.keys[p] = {}
                self.msg(f"{PROP_LABEL[p]}: keyframes removed, the value stays as it is now")
            if p in o.watch:
                o.watch.remove(p)
        else:
            o.watch.append(p)

    def descendants(self, o):
        out, stack = [], [o]
        while stack:
            cur = stack.pop()
            for c in self.objs:
                if c.parent is cur and c not in out:
                    out.append(c)
                    stack.append(c)
        return out

    def key_prop(self, o, p):
        if p not in o.watch:
            o.watch.append(p)
        if self.frame in o.keys[p]:
            del o.keys[p][self.frame]
            self.msg(f"{PROP_LABEL[p]}: keyframe {self.frame} removed")
        else:
            o.keys[p][self.frame] = o.value(p, self.frame)
            self.msg(f"{PROP_LABEL[p]}: keyframe {self.frame} on {o.name}")

    def toggle_global_key(self, mx=0, my=0):
        self.global_key = not self.global_key
        self.msg("Global keyframe ON: K sets a key on every layer" if self.global_key else "Global keyframe off")

    def key_here(self, mx=0, my=0):
        """One layer: toggle a keyframe. Several layers: set a keyframe on all of them at once. Global key: every layer."""
        if self.global_key:
            for o in self.objs:
                self.add_key_at(o, None, self.frame)
            self.msg(f"Global keyframe {self.frame} set on {len(self.objs)} layers")
            return
        pos_ = pygame.mouse.get_pos()                                  # the mouse is over a value row: key only that value
        for rc, o_, p_ in getattr(self, "prop_rects", []):
            if rc.collidepoint(pos_):
                self.key_prop(o_, p_)
                return
        sp = self.sel_prop
        if sp and sp[0] in self.sel:                                  # the value highlighted in the timeline
            self.key_prop(sp[0], sp[1])
            return
        if any(o.owner for o in self.sel):
            self.msg("Keyframes live on layers - select the layer in the timeline")
            return
        if len(self.sel) == 1:
            self.toggle_key(self.sel[0])
        elif self.sel:
            for o in self.sel:
                self.add_key_at(o, None, self.frame)
            self.msg(f"Keyframe {self.frame} set on {len(self.sel)} layers")

    def delete_keys_here(self, mx=0, my=0):
        n = 0
        for o in self.sel:
            if self.frame in o.key_frames():
                n += 1
                for p in PROPS:
                    o.keys[p].pop(self.frame, None)
                o.ease.pop(self.frame, None)
        self.msg(f"Deleted keyframes at frame {self.frame} on {n} layer(s)")

    def select_keys_frame(self, mx=0, my=0):
        self.kf_sel = [(o, None, self.frame) for o in self.objs if self.frame in o.key_frames()]
        self.msg(f"Selected {len(self.kf_sel)} keyframe(s) at frame {self.frame}")

    def jump_key(self, d):
        o = self.psel
        if not o:
            return
        ks = o.key_frames()
        c = [k for k in ks if (k > self.frame if d > 0 else k < self.frame)]
        if c:
            self.goto(min(c) if d > 0 else max(c))

    def add_phase(self, o=None):
        o = o or self.psel
        o = (o.owner or o) if o else None
        if not o or o.kind not in ("vlayer", "rlayer"):                 # phases belong to a drawing layer
            self.msg("Phases live inside a drawing layer - select a vector / raster layer")
            return
        f = self.frame
        if f in o.phases:
            self.msg(f"Frame {f} already starts a drawing")
            return
        o.phases.append(f)
        o.phases.sort()
        o._pitems[f] = []                                    # a blank drawing of its own: it does not change the other ones
        self.sel = []
        self.msg(f"New blank drawing starts at frame {f}")

    def clone_items(self, o, items):
        out = [Obj.from_dict(it.to_dict()) for it in items]
        for it in out:
            it.parent = it.owner = o
        return out

    def phase_set(self, o, f, items):
        if f not in o.phases and f > 1 or (f == 1 and f not in o.phases):
            o.phases.append(f)
            o.phases.sort()
        o._pitems[f] = items

    def phase_duplicate(self, o, key):
        f = self.frame if self.frame not in o.phases else self.frame + 1
        f = int(clamp(f, 1, self.total))
        self.phase_set(o, f, self.clone_items(o, o._pitems.get(key, [])))
        self.goto(f)
        self.msg(f"Drawing duplicated to frame {f}")

    def phase_delete(self, o, keys):
        for k in keys:
            if k == 0:
                o._pitems[0] = []
            elif k in o.phases:
                o.phases.remove(k)
                o._pitems.pop(k, None)
        self.sel = []
        self.ph_sel = set()
        self.msg("Drawing deleted")

    def jump_phase(self, d):
        o = self.psel
        if not o or not o.phases:
            self.msg("No phases on this layer (Drawing > Level Strip > New Phase)")
            return
        c = [k for k in o.phases if (k > self.frame if d > 0 else k < self.frame)]
        if c:
            self.goto(min(c) if d > 0 else max(c))

    def goto(self, f):
        self.frame = int(clamp(f, 1, self.total))

    def toggle_play(self, mx=0, my=0):
        self.playing = not self.playing
        self.play_acc = 0.0
        if self.playing and not self.loop and self.frame >= self.total:
            self.frame = 1

    def stop(self, mx=0, my=0):
        self.playing, self.frame = False, 1

    def toggle_loop(self, mx=0, my=0):
        self.loop = not self.loop
        self.msg("Loop playback " + ("on" if self.loop else "off"))

    # --------------------------------------------------------------- projects
    def project_file(self):
        return os.path.join(self.project_dir, "project.json") if self.project_dir else None

    def create_project(self, name, w, h, base, fps=24):
        d = os.path.join(base, name)
        os.makedirs(d, exist_ok=True)
        for sub in ("assets", "graphics", "palettes", "scenes", "scripts", "renders", "library"):
            os.makedirs(os.path.join(d, sub), exist_ok=True)
        self.project_dir, self.project_name, self.aw, self.ah = d, name, w, h
        self.fps, self.total, self.art_color, self.markers = fps, 72, COLOR_ARTBOARD, []
        self.footage, self.foot_sel, self.img_cache, self.scaled_cache = [], None, {}, {}
        self.new_scene()
        self.save_project(quiet=True)
        self.enter_main()

    def save_project(self, quiet=False, mx=0, my=0):
        if not self.project_dir:
            self.msg("No project folder")
            return
        self.save_rasters()
        data = {"name": self.project_name, "width": self.aw, "height": self.ah, "fps": self.fps,
                "total": self.total, "art_color": list(self.art_color), "footage": self.footage, "markers": self.markers, "objects": [o.to_dict() for o in self.objs]}
        with open(self.project_file(), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1)
        try:
            pygame.image.save(self.render_thumbnail(), os.path.join(self.project_dir, "thumb.png"))
        except Exception:  # noqa
            pass
        self.saved_sig = self.doc_sig()
        if not quiet:
            self.msg(f"Saved {self.project_name}/project.json")

    # ------------------------------------------------------------------ footage
    def footage_by_id(self, fid):
        return next((f for f in self.footage if f["id"] == fid), None)

    def footage_abs(self, fo, fn=None):
        base = fo["path"]
        if not os.path.isabs(base):
            base = os.path.join(self.project_dir or "", base)
        return os.path.join(base, fn) if fn else base

    def load_img(self, path):
        if path not in self.img_cache:
            if len(self.img_cache) > 150:
                self.img_cache.clear()
            try:
                self.img_cache[path] = pygame.image.load(path).convert_alpha()
            except Exception:  # noqa
                self.img_cache[path] = None
        return self.img_cache[path]

    def footage_surface(self, o, f):
        fo = self.footage_by_id(o.src)
        if not fo:
            return None
        if fo["type"] == "image":
            return self.load_img(self.footage_abs(fo))
        if fo["type"] == "sequence" and fo.get("files"):
            return self.load_img(self.footage_abs(fo, fo["files"][(f - o.t_in) % len(fo["files"])]))
        return None

    def small_thumb(self, path, size):
        key = (path, size)
        if key not in self.ex_thumbs:
            sf = None
            try:
                if os.path.getsize(path) < 12_000_000:
                    img = pygame.image.load(path).convert_alpha()
                    w, h = img.get_size()
                    k = min(size[0] / w, size[1] / h)
                    sf = pygame.transform.smoothscale(img, (max(1, int(w * k)), max(1, int(h * k))))
            except Exception:  # noqa
                sf = None
            if len(self.ex_thumbs) > 400:
                self.ex_thumbs.clear()
            self.ex_thumbs[key] = sf
        return self.ex_thumbs[key]

    def import_footage(self, path, as_seq=None):
        """Images and image sequences are copied into the project's assets/ folder; video / audio are linked."""
        if not self.project_dir:
            self.msg("Open a project first")
            return
        name = os.path.basename(path)
        stem, ext = os.path.splitext(name)
        low = ext.lower()
        adir = os.path.join(self.project_dir, "assets")
        os.makedirs(adir, exist_ok=True)
        fid = max([f["id"] for f in self.footage] or [0]) + 1
        try:
            if low in IMG_EXT:
                src_dir = os.path.dirname(path)
                m = re.match(r"^(.*?)(\d+)$", stem)
                sibs = []
                if m:
                    pre, digits = m.group(1), len(m.group(2))
                    for fn in sorted(os.listdir(src_dir)):
                        s2, e2 = os.path.splitext(fn)
                        m2 = re.match(r"^(.*?)(\d+)$", s2)
                        if e2.lower() == low and m2 and m2.group(1) == pre and len(m2.group(2)) == digits:
                            sibs.append(fn)
                if len(sibs) >= 2 and as_seq is None:               # ask: sequence or single image?
                    self.seq_dlg = {"path": path, "n": len(sibs), "as_seq": True}
                    return
                if len(sibs) >= 2 and as_seq:                       # numbered files = image sequence
                    sub = (pre.rstrip("_- .") or "sequence") + "_seq"
                    dest = os.path.join(adir, sub)
                    os.makedirs(dest, exist_ok=True)
                    for fn in sibs:
                        if os.path.abspath(os.path.join(src_dir, fn)) != os.path.abspath(os.path.join(dest, fn)):
                            shutil.copy2(os.path.join(src_dir, fn), dest)
                    img = self.load_img(os.path.join(dest, sibs[0]))
                    fo = {"id": fid, "name": sub, "type": "sequence", "path": os.path.join("assets", sub), "files": sibs,
                          "w": img.get_width() if img else 100, "h": img.get_height() if img else 100}
                    self.msg(f"Imported image sequence '{sub}' ({len(sibs)} frames)")
                else:
                    dest = os.path.join(adir, name)
                    if os.path.abspath(dest) != os.path.abspath(path):
                        shutil.copy2(path, dest)
                    img = self.load_img(dest)
                    fo = {"id": fid, "name": stem, "type": "image", "path": os.path.join("assets", name),
                          "w": img.get_width() if img else 100, "h": img.get_height() if img else 100}
                    self.msg(f"Imported {name}")
            elif low in VID_EXT or low in AUD_EXT:
                fo = {"id": fid, "name": stem, "type": "video" if low in VID_EXT else "audio", "path": path, "w": 0, "h": 0}
                self.msg(f"Linked {name} (playback is not supported yet)")
            else:
                self.msg(f"Unsupported file type: {ext or name}")
                return
        except Exception as e:  # noqa
            self.msg(f"Import failed: {e}")
            return
        if self.replace_target is not None:                      # Replace (Ctrl+H): keep the id, so every layer follows
            old = self.footage_by_id(self.replace_target)
            fo["id"], fo["name"] = self.replace_target, old["name"] if old else fo["name"]
            self.footage = [fo if f["id"] == fo["id"] else f for f in self.footage]
            self.img_cache.clear()
            self.scaled_cache.clear()
            self.replace_target = None
            self.msg(f"Replaced the footage with {name}")
        else:
            self.footage.append(fo)
        self.foot_sel = fo["id"]
        self.left_tab = "Footage"

    def new_solid(self, mx=0, my=0):
        n = 1
        while any(f["name"] == f"Solid {n}" for f in self.footage):
            n += 1
        fid = max([f["id"] for f in self.footage] or [0]) + 1
        self.footage.append({"id": fid, "name": f"Solid {n}", "type": "solid", "path": "", "color": list(self.def_fill),
                             "w": self.aw, "h": self.ah})
        self.foot_sel = fid
        self.msg(f"Created Solid {n} - Add to Scene puts it at the bottom of the layer stack")

    def add_footage(self, fid=None):
        fo = self.footage_by_id(fid if fid is not None else self.foot_sel)
        if not fo:
            self.msg("Select a footage item first")
            return
        if fo["type"] == "solid":
            o = self.new_obj("rect", self.aw // 2, self.ah // 2, w=self.aw, h=self.ah)
            o.fill = tuple(fo["color"])
            self.objs.remove(o)
            self.objs.append(o)                                  # solids go to the bottom
        elif fo["type"] in ("image", "sequence"):
            k = min(1.0, self.aw * 0.9 / max(1, fo["w"]), self.ah * 0.9 / max(1, fo["h"]))
            o = self.new_obj("image", self.aw // 2, self.ah // 2, w=fo["w"] * k, h=fo["h"] * k)
        else:
            self.msg("Video / audio playback is not supported yet - the file stays in the project footage")
            return
        o.name, o.src = self.unique_name(fo["name"]), fo["id"]
        self.sel = [o]
        self.msg(f"Added {o.name} to the scene")

    def delete_footage(self, fid):
        self.footage = [f for f in self.footage if f["id"] != fid]
        if self.foot_sel == fid:
            self.foot_sel = None

    def delete_unused_footage(self):
        used = {o.src for o in self.objs if o.src is not None}
        n = len(self.footage)
        self.footage = [f for f in self.footage if f["id"] in used]
        self.msg(f"Removed {n - len(self.footage)} unused footage item(s)")

    def ex_seq_key(self, path):
        stem, ext = os.path.splitext(os.path.basename(path))
        m = re.match(r"^(.*?)(\d+)$", stem)
        return (os.path.dirname(path), m.group(1), len(m.group(2)), ext.lower()) if m else None

    def import_selected(self):
        entries = self.ex_entries()
        idxs = sorted(self.ex_multi | ({self.ex_sel} if self.ex_sel is not None else set()))
        files = [os.path.join(self.ex_dir, entries[i][0]) for i in idxs if i < len(entries) and entries[i][1] == "file"]
        if not files:
            self.msg("Select one or more files in the list first")
            return
        seen, n = set(), 0
        for p in files:
            k = self.ex_seq_key(p)
            if self.ex_seq and k:                                # numbered files that belong together become ONE sequence
                if k in seen:
                    continue
                seen.add(k)
            self.import_footage(p, self.ex_seq)
            n += 1
        self.msg(f"Imported {n} item(s)")

    def add_footage_selected(self):
        ids = [f["id"] for f in self.footage if f["id"] in self.foot_multi or f["id"] == self.foot_sel]
        before = len(self.objs)
        for fid in ids:
            self.add_footage(fid)
        made = self.objs[:max(0, len(self.objs) - before)] if len(self.objs) > before else []
        if len(made) > 1:
            self.sel = made

    def footage_click(self, fid, mx=0, my=0):
        now = pygame.time.get_ticks()
        dbl = self.foot_click[0] == fid and now - self.foot_click[1] < 400
        mods = pygame.key.get_mods()
        if mods & pygame.KMOD_CTRL:
            self.foot_multi ^= {fid}
        elif mods & pygame.KMOD_SHIFT and self.foot_sel is not None:
            ids = [f["id"] for f in self.footage]
            if self.foot_sel in ids and fid in ids:
                a, b = sorted((ids.index(self.foot_sel), ids.index(fid)))
                self.foot_multi = set(ids[a:b + 1])
        else:
            self.foot_multi = {fid}
        self.foot_sel, self.foot_click = fid, (fid, now)
        if dbl:
            self.add_footage_selected()                          # double-click = add to scene
            return None
        x0, y0 = mx, my

        def drag(mx, my):
            pass

        def end():                                               # dragged onto the viewer or the timeline: added to the scene
            mp = pygame.mouse.get_pos()
            if math.hypot(mp[0] - x0, mp[1] - y0) > 12 and (self.r_view.collidepoint(mp) or self.r_tl.collidepoint(mp)):
                self.add_footage_selected()
        self.drag_end = end
        return drag

    def footage_menu(self, fid, pos):
        self.foot_sel = fid
        fo = self.footage_by_id(fid)
        extra = [] if not fo or fo["type"] == "solid" else [("Show in file explorer", lambda: self.show_in_explorer(self.footage_abs(fo)))]
        self.ctx = {"pos": pos, "items": [("Import element to scene", lambda: self.add_footage(fid)), ("Replace...  (Ctrl+H)", lambda: self.start_replace(fid))] + extra + [("Delete from project", lambda: self.delete_footage(fid)), ("Delete all unused footage", self.delete_unused_footage)]}
        return
        self.ctx = {"pos": pos, "items": [("Import element to scene", lambda: self.add_footage(fid)),
                                         ("Delete from project", lambda: self.delete_footage(fid)),
                                         ("Delete all unused footage", self.delete_unused_footage)]}

    def show_in_explorer(self, path):
        folder = path if os.path.isdir(path) else os.path.dirname(path)
        try:
            if sys.platform.startswith("linux"):
                subprocess.Popen(["xdg-open", folder])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                os.startfile(folder)                       # noqa (Windows)
        except Exception as e:  # noqa
            self.msg(f"Cannot open the folder: {e}")

    def start_replace(self, fid):
        self.replace_target = fid
        self.show_explorer()
        self.msg("Replace: double-click the new file in Library > Explorer (Esc cancels)")

    def show_in_footage(self, o):
        self.foot_sel, self.left_tab = o.src, "Footage"
        self.hidden.discard("left")

    def clean_cache(self, mx=0, my=0):
        n = len(self.img_cache) + len(self.scaled_cache) + len(self.ex_thumbs) + len(self.thumb_cache) + len(self.cursor_cache)
        for d in (self.img_cache, self.scaled_cache, self.ex_thumbs, self.thumb_cache, self.cursor_cache, self.idle_icons):
            d.clear()
        reset_icon_cache()
        self.msg(f"Cache cleaned ({n} items)")

    # ------------------------------------------------- rigging helpers (Tahoma / Duik style)
    def rebuild_drive(self, o):
        for a in ("x", "y"):
            if o.drivers:
                o.expr[a] = "value" + "".join(f' + layer("{d["src"]}", {d["lag"]}).l{a} * {d["k"]:g}' for d in o.drivers)
            else:
                o.expr.pop(a, None)
            self.expr_bad.discard((o.name, a))

    def drive_by(self, o, src, k, lag=0):
        """An object may follow several controllers at once; the offsets add up. lag = delay in frames."""
        d = next((d for d in o.drivers if d["src"] == src), None)
        if d:
            d["k"], d["lag"] = k, lag
        else:
            o.drivers.append({"src": src, "k": k, "lag": lag})
        self.rebuild_drive(o)
        self.msg(f"{o.name} follows {src}: x {k:g}, {lag} frame delay ({len(o.drivers)} controller(s))")

    def drive_menu(self, o, pos):
        srcs = [x for x in self.objs if x is not o and (x.limit or x.kind.startswith("ctrl") or x.kind in ("null", "peg"))][:14]
        if not srcs:
            self.msg("Create a joystick, controller, null or peg first")
            return
        cur = {d["src"]: d for d in o.drivers}

        def pick_lag(src, k):
            have = cur.get(src.name)
            self.ctx = {"pos": pos, "items": [(f"delay {n} frames", (lambda n=n: self.drive_by(o, src.name, k, n)), None,
                                              bool(have) and have["lag"] == n and have["k"] == k) for n in (0, 2, 4, 6, 8, 12)]}

        def pick_k(src):
            have = cur.get(src.name)
            self.ctx = {"pos": pos, "items": [(f"{src.name}  x {k:g}", (lambda k=k: pick_lag(src, k)), None, bool(have) and have["k"] == k)
                                              for k in (1, 0.75, 0.5, 0.25, -0.25, -0.5, -1)]}
        self.ctx = {"pos": pos, "items": [(x.name + (f"   x {cur[x.name]['k']:g}, {cur[x.name]['lag']}f" if x.name in cur else ""),
                                          (lambda x=x: pick_k(x)), None, x.name in cur) for x in srcs] +
                    [("Stop following (all)", lambda: (o.drivers.clear(), self.rebuild_drive(o)))]}

    def make_bone(self, start, end, name):
        o = self.new_obj("bone", start[0], start[1], w=1, h=8, select=False)
        dx, dy = end[0] - start[0], end[1] - start[1]
        L = max(8.0, math.hypot(dx, dy))
        o.w, o.h, o.anchor = L, clamp(L * 0.16, 8, 20), (-L / 2, 0.0)
        o.base["rotation"] = round(math.degrees(math.atan2(dy, dx)), 1)
        o.name = self.unique_name(name)
        return o

    def skeleton_from_selection(self):
        """Tahoma style: body parts parented in a hierarchy, anchors on the joints -> bones are built for you."""
        layers = [o for o in self.sel if not o.owner and o.kind not in ("bone", "null", "peg") and not o.kind.startswith("ctrl")]
        if len(layers) < 2:
            self.msg("Select the body-part layers (parented in a hierarchy, anchors placed on the joints)")
            return
        ids = {id(l) for l in layers}
        pos = {id(l): self.world(l, self.frame)[:2] for l in layers}
        par = {id(l): (l.parent if l.parent and id(l.parent) in ids else None) for l in layers}

        def depth(l):
            d = 0
            while par[id(l)] is not None and d < 50:
                l, d = par[id(l)], d + 1
            return d
        for l in layers:
            if par[id(l)] is not None:
                self.unlink(l, quiet=True)
        incoming, own, made = {}, {}, []
        for l in sorted(layers, key=depth):
            kids = [c for c in layers if par[id(c)] is l]
            pb = incoming.get(id(l))
            if kids:
                for c in kids:
                    b = self.make_bone(pos[id(l)], pos[id(c)], f"{l.name} > {c.name}")
                    if pb:
                        self.link(b, pb, quiet=True)
                    incoming[id(c)] = b
                    own.setdefault(id(l), b)
                    made.append(b)
            else:                                                # leaf layer: a short bone that continues the direction
                px, py = pos[id(l)]
                ang = math.radians(pb.value("rotation", self.frame) + (self.world(pb.parent, self.frame)[3] if pb.parent else 0)) if pb else math.pi / 2
                b = self.make_bone((px, py), (px + math.cos(ang) * 40, py + math.sin(ang) * 40), f"{l.name} end")
                if pb:
                    self.link(b, pb, quiet=True)
                own[id(l)] = b
                made.append(b)
        for l in layers:
            self.link(l, own[id(l)], quiet=True)                 # every layer follows the bone that starts at its anchor
        self.rig_bones = {}
        for l in layers:                                     # the bone that starts at a layer's anchor carries the layer's name
            b = own[id(l)]
            b.name = self.unique_name(f"{l.name}_bone")
            self.rig_bones[l.name] = b
        self.sel = made
        self.msg(f"Skeleton created: {len(made)} bones. Rotate a bone to pose the character")

    BODY_RIG = [  # name, parent, pivot (joint) relative to the middle of the artboard
        ("Hips", None, (0, -10)), ("Body_1", "Hips", (0, -45)), ("Body_2", "Body_1", (0, -120)), ("Neck", "Body_2", (0, -200)),
        ("Head", "Neck", (0, -240)),
        ("Arm_R", "Body_2", (-40, -185)), ("Forearm_R", "Arm_R", (-120, -85)), ("Hand_R", "Forearm_R", (-170, 10)),
        ("Arm_L", "Body_2", (40, -185)), ("Forearm_L", "Arm_L", (120, -85)), ("Hand_L", "Forearm_L", (170, 10)),
        ("Thigh_R", "Hips", (-30, -5)), ("Tibia_R", "Thigh_R", (-40, 155)), ("Foot_R1", "Tibia_R", (-40, 315)), ("Foot_R2", "Foot_R1", (0, 345)),
        ("Thigh_L", "Hips", (30, -5)), ("Tibia_L", "Thigh_L", (40, 155)), ("Foot_L1", "Tibia_L", (40, 315)), ("Foot_L2", "Foot_L1", (0, 345))]

    def generate_body_layers(self):
        """Duik style: empty drawing layers with the usual body-part names, parented and with the anchor on the joint."""
        made = {}
        cx, cy = self.aw / 2, self.ah / 2
        for name, par, (jx, jy) in self.BODY_RIG:
            px, py = cx + jx, cy + jy
            o = Obj(self.unique_name(name), "vlayer", px, py, self.aw, self.ah)
            o.anchor = (px - cx, py - cy)                    # the pivot sits on the joint, the drawing area stays on the artboard
            self.objs.insert(0, o)
            made[name] = o
        for name, par, _ in self.BODY_RIG:
            if par:
                self.link(made[name], made[par], quiet=True)
        self.sel = list(made.values())
        self.active_layer = made["Head"]
        self.msg("Body layers created and parented. Draw each part in its layer, move the anchors onto the joints, then use Do the Rig")

    def do_rig(self):
        """Build the bones from the body layers (names, anchors, hierarchy) and put two-bone IK on arms and legs."""
        names = {n for n, _, _ in self.BODY_RIG}
        layers = [o for o in self.objs if not o.owner and o.kind == "vlayer" and (o.name in names or o in self.sel)]
        if len(layers) < 2:
            self.msg("Create the body layers first (Object > Generate Body Layers) or select your own parented layers")
            return
        self.sel = layers
        self.skeleton_from_selection()
        n = 0
        for lower in ("Forearm_R", "Forearm_L", "Tibia_R", "Tibia_L"):
            b = self.rig_bones.get(lower)
            if b and b.parent is not None and b.parent.kind == "bone":
                try:
                    self.create_ik(b)
                    n += 1
                except Exception:  # noqa
                    pass
        self.msg(f"Rig done: {len(self.rig_bones)} bones, IK on {n} limbs. Use the Animate Bones tool to pose it")

    def toggle_props(self, props, add=False):
        """P / R / T / S on the timeline show only those properties of the selected layers (like After Effects)."""
        if not self.sel:
            self.msg("Select a layer first")
            return
        for o in self.sel:
            if o.owner:
                continue
            if o.expanded and o.u_props == set(props) and not add:
                o.expanded, o.u_props = False, None
            else:
                o.u_props = (set(o.u_props or ()) | set(props)) if add else set(props)
                o.expanded, o.u_mode = True, False

    def show_explorer(self, mx=0, my=0):
        self.hidden.discard("right")
        self.right_tab, self.lib_mode = "Library", "Explorer"
        if self.ex_dir == os.path.expanduser("~") and self.project_dir:
            self.ex_dir = self.project_dir
        self.msg("Library > Explorer: double-click a file to import it as footage")

    def save_rasters(self):
        adir = os.path.join(self.project_dir, "assets")
        os.makedirs(adir, exist_ok=True)
        for o in self.objs:
            if o.kind == "rlayer" and o.surf is not None:
                name = re.sub(r"[^A-Za-z0-9_-]+", "_", o.name) + ".png"
                pygame.image.save(o.surf, os.path.join(adir, name))
                o.png = os.path.join("assets", name)

    def load_rasters(self):
        for o in self.objs:
            if o.kind == "rlayer":
                sf = None
                if o.png:
                    try:
                        sf = pygame.image.load(os.path.join(self.project_dir, o.png)).convert_alpha()
                    except Exception:  # noqa
                        sf = None
                o.surf = sf or pygame.Surface((self.aw, self.ah), pygame.SRCALPHA)

    # --------------------------------------------------------------- rendering
    def ffmpeg_path(self):
        p = shutil.which("ffmpeg")
        if p:
            return p
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:  # noqa
            return None

    def open_render(self, mx=0, my=0):
        self.render_dlg = {"name": self.project_name, "fmt": 0, "range": 0,
                           "path": os.path.join(self.project_dir or "", "renders")}

    def render_surface(self, f):
        surf = pygame.Surface((self.aw, self.ah))
        surf.fill(self.art_color)
        saved = (self.screen, self.zoom, self.ox, self.oy, self.frame)
        try:
            self.screen, self.zoom, self.ox, self.oy, self.frame = surf, 1.0, 0.0, 0.0, f
            src = self.matte_sources()
            for o in reversed(self.objs):
                if o.visible and o.render and not o.kind.startswith("ctrl") and o.kind not in ("null", "peg", "bone", "pill", "rsquare") \
                        and not o.limit and o.name not in src and self.in_range(o, f):
                    self.draw_layer(o, f)
        finally:
            self.screen, self.zoom, self.ox, self.oy, self.frame = saved
        return surf

    def run_render(self, mx=0, my=0):
        d = self.render_dlg
        lo, hi = (1, self.total) if d["range"] == 0 else (self.work_in or 1, min(self.work_out or self.total, self.total))
        name = re.sub(r'[\\/:*?"<>|]+', "_", d["name"].strip()) or "render"
        out_dir = d["path"].strip() or os.path.join(self.project_dir or ".", "renders")
        os.makedirs(out_dir, exist_ok=True)
        ff = self.ffmpeg_path() if d["fmt"] == 0 else None
        if d["fmt"] == 0 and not ff:
            self.msg("ffmpeg not found (install: sudo apt install ffmpeg) - rendering a PNG sequence instead")
            d["fmt"] = 1
        proc, n, seq = None, hi - lo + 1, None
        if d["fmt"] == 0:
            out = os.path.join(out_dir, name + ".mp4")
            proc = subprocess.Popen([ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{self.aw}x{self.ah}", "-r", str(self.fps),
                                     "-i", "-", "-an", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264",
                                     "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        else:
            seq = os.path.join(out_dir, name + "_seq")
            os.makedirs(seq, exist_ok=True)
        try:
            for i, f in enumerate(range(lo, hi + 1)):
                pygame.event.pump()
                self.rend_prog = (i, n)
                surf = self.render_surface(f)
                if proc:
                    proc.stdin.write(pygame.image.tostring(surf, "RGB"))
                else:
                    pygame.image.save(surf, os.path.join(seq, f"{name}_{f:04d}.png"))
                self.draw_frame()
            if proc:
                proc.stdin.close()
                proc.wait()
            self.msg(f"Rendered {n} frames -> {out if proc else seq}")
        except Exception as e:  # noqa
            self.msg(f"Render failed: {e}")
        finally:
            self.rend_prog, self.render_dlg = None, None

    # ----------------------------------------------------------- quit / dirty
    def doc_sig(self):
        return json.dumps([self.snapshot(), self.footage, list(self.art_color), self.aw, self.ah, self.fps, self.total,
                           self.markers], sort_keys=True, default=str)

    def guard(self, action):
        """Run action, but first ask what to do with unsaved changes."""
        if self.mode == "main" and self.project_dir and self.doc_sig() != self.saved_sig:
            self.quit_dlg = {"after": action}
        else:
            action()

    def request_quit(self, mx=0, my=0):
        self.guard(lambda: setattr(self, "running", False))

    # ------------------------------------------------- expression suggestions
    def expr_suggestions(self):
        ed = self.edit
        if not ed or not str(ed["id"]).startswith(("expr_", "tlexpr_")):
            return []
        t = ed["text"]
        m = re.search(r'(?:layer|world)\("([^"]*)$', t)
        if m:
            part = m.group(1).lower()
            return [(o.name, len(m.group(1)), o.name + '")') for o in self.objs if o.name.lower().startswith(part)][:8]
        tok = re.search(r"[A-Za-z_]*$", t).group(0)
        if not tok:
            return []
        out = [(w, len(tok), w) for w in EXPR_WORDS if w.lower().startswith(tok.lower()) and w.lower() != tok.lower()]
        out += [(o.name, len(tok), f'layer("{o.name}")') for o in self.objs if o.name.lower().startswith(tok.lower())]   # object names
        return out[:8]

    def apply_suggestion(self, i):
        sg = self.expr_suggestions()
        if 0 <= i < len(sg):
            _, rep, ins = sg[i]
            self.edit["text"] = self.edit["text"][:len(self.edit["text"]) - rep] + ins
            self.edit["fresh"], self.sugg_i = False, 0

    def render_thumbnail(self, size=(192, 96)):
        """Draw frame 1 of the scene into a small image (shown on the start screen)."""
        surf = pygame.Surface(size)
        surf.fill(self.art_color)
        saved = (self.screen, self.zoom, self.ox, self.oy)
        try:
            self.screen = surf
            self.zoom = min(size[0] / self.aw, size[1] / self.ah)
            self.ox, self.oy = (size[0] - self.aw * self.zoom) / 2, (size[1] - self.ah * self.zoom) / 2
            for o in reversed(self.objs):
                if o.visible:
                    self.draw_obj(o, 1)
        finally:
            self.screen, self.zoom, self.ox, self.oy = saved
        return surf

    def labels_sync(self):
        self.labels = {k: tuple(self.label_list[self.type_label[k]][1]) for k in TYPE_LABEL_DEFAULT}

    def load_prefs(self):
        try:
            with open(os.path.join(DATA_DIR, "prefs.json"), encoding="utf-8") as fh:
                d = json.load(fh)
            if len(d.get("label_list", [])) == len(self.label_list):
                self.label_list = [[n, tuple(c)] for n, c in d["label_list"]]
            self.type_label.update({k: v for k, v in d.get("type_label", {}).items() if k in self.type_label})
            self.autosave.update(d.get("autosave", {}))
            self.theme = d.get("theme", "Dark") if d.get("theme", "Dark") in THEMES else "Dark"
            apply_theme(self.theme)
            if d.get("palette"):
                self.palette = [{"c": tuple(c), "name": "", "folder": None} if isinstance(c, (list, tuple))
                                else {"c": tuple(c["c"]), "name": c.get("name", ""), "folder": c.get("folder")} for c in d["palette"]]
            self.pal_folders = list(d.get("pal_folders", []))
            self.pal_view = d.get("pal_view", "circles") if d.get("pal_view") in ("circles", "tiles", "list") else "circles"
            self.labels_sync()
        except Exception:  # noqa
            pass

    def save_prefs(self):
        try:
            with open(os.path.join(DATA_DIR, "prefs.json"), "w", encoding="utf-8") as fh:
                json.dump({"label_list": self.label_list, "type_label": self.type_label, "palette": self.palette,
                           "pal_folders": self.pal_folders, "pal_view": self.pal_view,
                           "autosave": self.autosave, "theme": self.theme}, fh, indent=1)
        except OSError:
            pass

    def set_theme(self, name):
        self.theme = name
        apply_theme(name)
        self.save_prefs()

    def idle_icon(self, ic):
        """Tool icons rest slightly grey; they turn white when active or hovered."""
        if id(ic) not in self.idle_icons:
            t = ic.copy()
            t.fill((178, 178, 182, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.idle_icons[id(ic)] = t
        return self.idle_icons[id(ic)]

    def reset_labels(self, mx=0, my=0):
        self.label_list = [[n, c] for n, c in LABEL_DEFAULT_LIST]
        self.type_label = dict(TYPE_LABEL_DEFAULT)
        self.labels_sync()
        self.save_prefs()

    def set_label_name(self, i, s):
        if s.strip():
            self.label_list[i][0] = s.strip()
            self.save_prefs()

    def cycle_type_label(self, key):
        self.type_label[key] = (self.type_label[key] + 1) % len(self.label_list)
        self.labels_sync()
        self.save_prefs()

    @staticmethod
    def label_key(o):
        if o.kind in ("brush", "rlayer"):
            return "brush"
        if o.kind == "null":
            return "null"
        if o.kind in ("bone", "peg"):
            return "peg"
        if o.kind == "image":
            return "image"
        if o.kind.startswith("ctrl") or o.kind in ("pill", "rsquare") or o.limit:
            return "controller"
        return "vector"

    def label_color(self, o):
        o = o.owner or o
        return o.label or self.labels[self.label_key(o)]

    # ------------------------------------------------------------- undo / redo
    def snapshot(self):
        return json.dumps({"o": [o.to_dict() for o in self.objs], "s": [o.name for o in self.sel]}, sort_keys=True)

    def push_undo(self):
        s = self.snapshot()
        if not self.undo_stack or self.undo_stack[-1] != s:
            self.undo_stack.append(s)
            del self.undo_stack[:-100]
            self.redo_stack = []

    def sel_keys(self):
        ks = []
        for o in self.sel:
            if o.owner and o.owner in self.objs and o in o.owner.items:
                ks.append(("i", o.owner.name, o.owner.items.index(o)))
            else:
                ks.append(("o", o.name))
        return ks

    def resolve_sel(self, keys, objs):
        out = []
        for k in keys:
            if k[0] == "o":
                out += [o for o in objs if o.name == k[1]][:1]
            else:
                ly = next((o for o in objs if o.name == k[1]), None)
                if ly and k[2] < len(ly.items):
                    out.append(ly.items[k[2]])
        return out

    def restore(self, s):
        keys = self.sel_keys()                                # the selection survives Undo / Redo
        d = json.loads(s)
        objs = [Obj.from_dict(x) for x in d["o"]]
        by = {o.name: o for o in objs}
        for o, x in zip(objs, d["o"]):
            o.parent = by.get(x.get("parent"))
        ui = {o.name: (o.node, o.node_open, o.u_mode, o.u_props, o.expanded) for o in self.objs}
        for o in objs:
            if o.name in ui:
                o.node, o.node_open, o.u_mode, o.u_props, o.expanded = ui[o.name]
        old = {o.name: o.surf for o in self.objs if o.kind == "rlayer"}
        for o in objs:
            if o.kind == "rlayer":
                o.surf = old.get(o.name) or pygame.Surface((self.aw, self.ah), pygame.SRCALPHA)
        self.objs, self.sel, self.kf_sel, self.hover = objs, self.resolve_sel(keys, objs) or [by[n] for n in d["s"] if n in by], [], None
        self.drag = self.drag_end = None

    def undo(self, mx=0, my=0):
        cur = self.snapshot()
        while self.undo_stack and self.undo_stack[-1] == cur:
            self.undo_stack.pop()
        if not self.undo_stack:
            self.msg("Nothing to undo")
            return
        self.redo_stack.append(cur)
        self.restore(self.undo_stack.pop())
        self.msg("Undo")

    def redo(self, mx=0, my=0):
        if not self.redo_stack:
            self.msg("Nothing to redo")
            return
        self.undo_stack.append(self.snapshot())
        self.restore(self.redo_stack.pop())
        self.msg("Redo")

    # ----------------------------------------------------- keyframe selection
    def delete_keys(self):
        for o, p, f in self.kf_sel:
            for pp in (PROPS if p is None else (p,)):
                o.keys[pp].pop(f, None)
            if p is None:
                o.ease.pop(f, None)
        self.msg(f"Deleted {len(self.kf_sel)} keyframe(s)")
        self.kf_sel = []

    def reverse_keys(self):
        groups = {}
        for o, p, f in self.kf_sel:
            groups.setdefault((id(o), p), (o, p, []))[2].append(f)
        for o, p, frames in groups.values():
            frames = sorted(set(frames))
            for pp in (PROPS if p is None else (p,)):
                vals = [o.keys[pp].get(f) for f in frames]
                for f, v in zip(frames, reversed(vals)):
                    if v is None:
                        o.keys[pp].pop(f, None)
                    else:
                        o.keys[pp][f] = v
        self.msg("Reversed the order of the selected keyframes")

    def add_key_at(self, o, p, f):
        for pp in (PROPS if p is None else (p,)):
            if p is None and not self.watched(o, pp):
                continue
            o.keys[pp][f] = o.value(pp, f)

    def read_project(self, path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        objs = [Obj.from_dict(d) for d in data["objects"]]
        by = {o.name: o for o in objs}
        for o, d in zip(objs, data["objects"]):
            o.parent = by.get(d.get("parent"))
        return data, objs

    def open_project(self, d):
        try:
            data, objs = self.read_project(os.path.join(d, "project.json"))
        except Exception as e:  # noqa
            self.msg(f"Cannot open project: {e}")
            return False
        self.project_dir, self.project_name = d, data.get("name", os.path.basename(d))
        self.aw, self.ah = data.get("width", 1920), data.get("height", 1080)
        self.fps, self.total = data.get("fps", 24), data.get("total", 72)
        self.art_color = tuple(data.get("art_color", COLOR_ARTBOARD))
        self.markers = data.get("markers", [])
        self.footage, self.foot_sel, self.img_cache, self.scaled_cache = data.get("footage", []), None, {}, {}
        self.objs, self.sel, self.frame = objs, [], 1
        self.load_rasters()
        self.enter_main()
        return True

    def list_projects(self):
        out = []
        for n in sorted(os.listdir(PROJECTS_DIR)):
            f = os.path.join(PROJECTS_DIR, n, "project.json")
            if os.path.isfile(f):
                try:
                    with open(f, encoding="utf-8") as fh:
                        dd = json.load(fh)
                    out.append((n, os.path.join(PROJECTS_DIR, n), os.path.getmtime(f),
                                dd.get("width", 1920), dd.get("height", 1080)))
                except Exception:  # noqa
                    pass
        return sorted(out, key=lambda t: -t[2])

    def import_to_library(self, path):
        try:
            _, objs = self.read_project(path)
        except Exception as e:  # noqa
            self.msg(f"Error: {e}")
            return
        for o in objs:
            d = o.to_dict()
            d["parent"] = None
            self.library.append(d)
        self.save_library()
        self.msg(f"Added {len(objs)} object(s) to the library")

    def load_library(self):
        try:
            with open(LIBRARY_FILE, encoding="utf-8") as fh:
                self.library = json.load(fh)
        except Exception:  # noqa
            self.library = []

    def save_library(self):
        with open(LIBRARY_FILE, "w", encoding="utf-8") as fh:
            json.dump(self.library, fh, indent=1)

    def lib_save_objs(self, objs):
        n = 0
        for o in objs:
            o = o.owner or o
            d = o.to_dict()
            d["parent"] = None
            d["lib_folder"] = self.lib_folder
            self.library.append(d)
            n += 1
        self.save_library()
        self.msg(f"Saved {n} object(s) in the library")

    def lib_save_selected(self, mx=0, my=0):
        if not self.sel:
            self.msg("Select an object to save it in the library")
            return
        self.lib_save_objs(self.sel)

    def lib_obj(self, idx):
        d = self.library[idx]
        o = self._lib_cache.get(id(d))
        if o is None:
            try:
                o = Obj.from_dict(d)
            except Exception:  # noqa
                o = False
            self._lib_cache[id(d)] = o
        return o or None

    def lib_insert(self, i, at=None):
        o = Obj.from_dict(self.library[i])
        o.name, o.node = self.unique_name(o.name), None
        if at is not None and not o.keys["x"] and not o.keys["y"]:           # dropped in the viewer: where the mouse let go
            o.base["x"], o.base["y"] = float(at[0]), float(at[1])
        self.objs.insert(0, o)
        return o

    def lib_insert_selected(self, at=None):
        made = [self.lib_insert(i, at) for i in sorted(self.lib_sel) if i < len(self.library) and "_folder" not in self.library[i]]
        if made:
            self.sel = made
            self.msg(f"Inserted {len(made)} object(s)")

    def lib_delete(self, i):
        self.library.pop(i)
        self.lib_sel = set()
        self._lib_cache.clear()
        self.save_library()

    def lib_delete_selected(self):
        for i in sorted(self.lib_sel, reverse=True):
            if i < len(self.library):
                self.library.pop(i)
        self.lib_sel = set()
        self._lib_cache.clear()
        self.save_library()

    def lib_add_folder(self, name):
        name = name.strip()
        if name and not any(e.get("_folder") == name for e in self.library):
            self.library.append({"_folder": name})
            self.lib_folder = name
            self.save_library()

    def lib_move(self, idxs, folder):
        for i in idxs:
            if i < len(self.library) and "_folder" not in self.library[i]:
                self.library[i]["lib_folder"] = folder
        self.save_library()

    def lib_folder_menu(self, f, pos):
        def delete():
            self.library = [e for e in self.library if e.get("_folder") != f]
            for e in self.library:
                if e.get("lib_folder") == f:
                    e["lib_folder"] = None
            if self.lib_folder == f:
                self.lib_folder = None
            self.save_library()
        self.ctx = {"pos": pos, "items": [("Delete folder (objects stay in the library)", delete)]}

    def lib_click(self, idx, mx, my):
        now = pygame.time.get_ticks()
        dbl = self._lib_click[0] == idx and now - self._lib_click[1] < 400
        self._lib_click = (idx, now)
        mods = pygame.key.get_mods()
        if mods & pygame.KMOD_CTRL:
            self.lib_sel ^= {idx}
        elif mods & pygame.KMOD_SHIFT and self.lib_sel and idx in self._lib_visible:
            near = min(self.lib_sel, key=lambda q: abs(q - idx))
            if near in self._lib_visible:
                a, b = sorted((self._lib_visible.index(near), self._lib_visible.index(idx)))
                self.lib_sel = set(self._lib_visible[a:b + 1])
        else:
            self.lib_sel = {idx}
        if dbl:
            self.lib_insert_selected()
            return None
        x0, y0 = mx, my

        def drag(mx, my):
            pass

        def end():                                                     # dragged out of the panel: dropped in the viewer or on the timeline
            mp = pygame.mouse.get_pos()
            if math.hypot(mp[0] - x0, mp[1] - y0) < 12:
                return
            if self.r_view.collidepoint(mp):
                self.lib_insert_selected(self.s2a(*mp))
            elif self.r_tl.collidepoint(mp):
                self.lib_insert_selected()
        self.drag_end = end
        return drag

    def lib_card_menu(self, idx, pos):
        if idx not in self.lib_sel:
            self.lib_sel = {idx}
        folders = [e["_folder"] for e in self.library if "_folder" in e]
        self.ctx = {"pos": pos, "items": [("Insert", self.lib_insert_selected)] +
                    [(f"Move to folder: {f}", (lambda f=f: self.lib_move(list(self.lib_sel), f))) for f in folders] +
                    [("Move out of its folder", lambda: self.lib_move(list(self.lib_sel), None)), ("Delete", self.lib_delete_selected)]}

    # ---- palette
    def pal_add_folder(self, name):
        name = name.strip()
        if name and name not in self.pal_folders:
            self.pal_folders.append(name)
            self.pal_open = name
            self.save_prefs()

    def pal_menu(self, i, pos):
        e = self.palette[i]
        items = [("Rename", lambda: self.begin_edit(f"palname_{i}", e["name"], lambda s, e=e: (e.update(name=s.strip()), self.save_prefs())))]
        items += [(f"Move to folder: {f}", (lambda f=f: (e.update(folder=f), self.save_prefs()))) for f in self.pal_folders]
        items += [("Move out of its folder", lambda: (e.update(folder=None), self.save_prefs())),
                  ("Delete colour", lambda: (self.palette.pop(i), self.save_prefs()))]
        self.ctx = {"pos": pos, "items": items}

    def pal_folder_menu(self, f, pos):
        def delete():
            self.pal_folders.remove(f)
            for e in self.palette:
                if e["folder"] == f:
                    e["folder"] = None
            if self.pal_open == f:
                self.pal_open = None
            self.save_prefs()
        self.ctx = {"pos": pos, "items": [("Delete folder (colours stay in the palette)", delete)]}

    def run_script(self, path):
        try:
            with open(path, encoding="utf-8") as fh:
                code = fh.read()
            exec(compile(code, path, "exec"), {"app": self, "__name__": "motionbox_script"})
            self.msg(f"Script imported: {os.path.basename(path)}")
        except Exception as e:  # noqa
            self.msg(f"Script error: {e}")

    def open_script_dialog(self, mx=0, my=0):
        self.open_dialog("IMPORT SCRIPT", "Import a Python script (.py)", SCRIPTS_DIR, ".py", "Import",
                         self.run_script)

    # ----------------------------------------------------------------- layout
    def make_fonts(self):
        """Put the Inter files anywhere inside fonts/ (sub-folders are fine); otherwise a clean system font is used."""
        fd = os.path.join(RES_DIR, "fonts")
        found = []
        for root, _, files in os.walk(fd):
            found += [os.path.join(root, f) for f in sorted(files) if f.lower().endswith((".ttf", ".otf"))]

        def pick(*words):
            for w in words:
                for p in found:
                    n = os.path.basename(p).lower()
                    if w in n and "italic" not in n:
                        return p
            return None
        reg = pick("regular") or pick("inter") or (found[0] if found else None)
        semi = pick("semibold", "bold", "medium") or reg
        names = "inter,notosans,dejavusans,ubuntu,liberationsans,arial,helvetica"

        def mk(size, bold=False):
            path = semi if bold else reg
            if path:
                try:
                    return pygame.font.Font(path, size)
                except Exception:  # noqa
                    pass
            return pygame.font.SysFont(names, size, bold=bold)
        self.f11, self.f12, self.fb, self.fb2, self.f20 = mk(12), mk(13), mk(13, True), mk(15, True), mk(22, True)

    def compute_layout(self):
        W, H = self.screen.get_size()
        self.W, self.H = W, H
        hid = self.hidden
        TOP, BAR = 40, 24
        TL = 0 if "timeline" in hid else int(clamp(self.h_tl, 96, 400))
        tl_top = H - BAR - TL
        self.r_menu = pygame.Rect(0, 0, W, 32)
        self.r_bar = pygame.Rect(0, H - BAR, W, BAR)
        self.r_tl = pygame.Rect(0, tl_top, W, TL)
        ph = max(160, tl_top - (8 if TL else 0) - 32 - 8 - TOP)
        tw = 0 if "toolbox" in hid else 56
        self.r_tool = pygame.Rect(0, TOP, tw, max(0, tl_top - TOP))
        lw = 0 if "left" in hid else int(clamp(self.w_left, 160, 400))
        self.r_left = pygame.Rect(tw + 8 if tw else 8, TOP, lw, ph)
        wr = 0 if "right" in hid else int(clamp(self.w_right, 200, 480))
        self.r_right = pygame.Rect(W - 8 - wr, TOP, wr, ph)
        mx = self.r_left.right + (8 if lw else 0)
        main = pygame.Rect(mx, TOP, max(200, self.r_right.x - (8 if wr else 0) - mx), ph)
        self.r_trans = pygame.Rect(mx, TOP + ph + 8, main.w, 32)
        self.r_aux = None
        if self.workspace == "Animate":
            self.r_view = main
        else:
            half = int(clamp(int((main.w - 8) * self.split_frac) // 8 * 8, 160, max(160, main.w - 8 - 160)))
            self.r_view = pygame.Rect(main.x, TOP, half, ph)
            self.r_aux = pygame.Rect(self.r_view.right + 8, TOP, main.w - half - 8, ph)
        if self.maxi == "timeline" and TL:
            self.r_tl = pygame.Rect(0, TOP, W, H - BAR - TOP)
        elif self.maxi == "viewport":
            self.r_view, self.r_aux = pygame.Rect(0, TOP, W, H - BAR - TOP), None
        elif self.maxi == "aux" and self.r_aux:
            self.r_aux, self.r_view = pygame.Rect(0, TOP, W, H - BAR - TOP), pygame.Rect(0, 0, 0, 0)
        elif self.maxi:
            self.maxi = None
        if self.view_fit:
            v = self.r_view
            self.zoom = max(0.02, min((v.w - 48) / self.aw, (v.h - 72) / self.ah))
            self.ox = v.centerx - self.aw * self.zoom / 2
            self.oy = v.centery - self.ah * self.zoom / 2

    def draw_tooltip(self):
        h, now = self.hover_hint, pygame.time.get_ticks()
        if h != self._last_hint:
            self._last_hint, self.hint_since = h, now
        if not h or now - self.hint_since < 450 or self.dialog or self.drag:
            return
        tip = h.split(": ")[0] if (": " in h and len(h) > 60) else h
        tip = tip if len(tip) <= 90 else tip[:87] + "..."
        mx, my = pygame.mouse.get_pos()
        rc = pygame.Rect(0, 0, self.f11.size(tip)[0] + 20, 24)
        rc.topleft = (min(mx + 14, self.W - rc.w - 8), min(my + 20, self.H - 32))
        self.rrect(rc, (20, 20, 24), 8)
        self.rrect(rc, (90, 90, 104), 8, 1)
        self.txt(tip, rc.x + 10, rc.y + 5, self.f11, (240, 240, 245))

    # ------------------------------------------------------------ UI primitives
    def hit(self, rect, fn, buttons=(1,)):
        rect = pygame.Rect(rect)
        if self.hit_clip is not None:
            rect = rect.clip(self.hit_clip)
        self.hits.append((rect, fn, buttons))

    def push_clip(self, rect):
        prev = self.screen.get_clip()
        self.screen.set_clip(prev.clip(pygame.Rect(rect)))
        return prev

    def pop_clip(self, prev):
        self.screen.set_clip(prev)

    def txt(self, s, x, y, font=None, color=None, center=False, right=False):
        if color is None:
            color = COLOR_TEXT
        if str(s) == "":
            return 0
        sf = (font or self.f12).render(str(s), True, color)
        if center:
            x, y = x - sf.get_width() // 2, y - sf.get_height() // 2
        elif right:
            x -= sf.get_width()
        self.screen.blit(sf, (int(x), int(y)))
        return sf.get_width()

    def rrect(self, rect, color, r=8, width=0):
        pygame.draw.rect(self.screen, color, rect, width, border_radius=r)

    def hovering(self, rect):
        return pygame.Rect(rect).collidepoint(pygame.mouse.get_pos()) and not self.dialog

    def button(self, rect, label, fn, active=False, color=None, radius=8, font=None, hint=None):
        rect = pygame.Rect(rect)
        hov = self.hovering(rect)
        if color:
            col = shade(color, 1.15) if hov else color
        else:
            col = COLOR_ACCENT if active else (COLOR_HOVER if hov else COLOR_BTN)
        self.rrect(rect, col, rect.h // 2 if label else radius)       # labelled buttons are full pills
        if label:
            self.txt(label, rect.centerx, rect.centery, font or self.f12,
                     (255, 255, 255) if (active or color) else COLOR_TEXT, center=True)
        if hov and hint:
            self.hover_hint = hint
        self.hit(rect, fn)
        return rect

    def flat_button(self, rect, fn, hint=None, active=False, hover=True):
        """No background when idle (same colour as the panel); lighter on hover."""
        rect = pygame.Rect(rect)
        hov = self.hovering(rect)
        if active or (hov and hover):
            self.rrect(rect, COLOR_ACCENT if active else COLOR_HOVER, 8)
        if hov and hint:
            self.hover_hint = hint
        self.hit(rect, fn)
        return rect

    def icon_button(self, rect, icon, fn, active=False, hint=None, col=(235, 235, 235)):
        rc = self.flat_button(rect, fn, hint, active)
        draw_icon(self.screen, icon, rc, col)
        return rc

    def checkbox(self, x, y, on, fn, hint=None):
        rc = pygame.Rect(x, y, 16, 16)
        self.rrect(rc, COLOR_ACCENT_L if on else COLOR_FIELD, 4)
        self.rrect(rc, COLOR_ACCENT_L if on else (110, 110, 110), 4, 2)
        if on:
            pygame.draw.lines(self.screen, (255, 255, 255), False,
                              [(x + 4, y + 8), (x + 7, y + 11), (x + 12, y + 5)], 2)
        if self.hovering(rc.inflate(8, 8)) and hint:
            self.hover_hint = hint
        self.hit(rc.inflate(8, 8), fn)
        return rc

    def field(self, rect, text, cb, fid, numeric=False, center=False, hint=None):
        rect = pygame.Rect(rect)
        editing = bool(self.edit and self.edit["id"] == fid)
        self.rrect(rect, COLOR_FIELD, rect.h // 2)
        if editing:
            self.edit["rect"] = rect
            self.rrect(rect, COLOR_ACCENT_L, rect.h // 2, 1)
        s = self.edit["text"] if editing else str(text)
        prev = self.push_clip(rect.inflate(-8, 0))
        w = self.f12.size(s)[0]
        x = rect.centerx - w // 2 if center else rect.x + 8
        if editing:
            self.edit["tx"] = x
            if self.edit.get("fresh") and s:                        # whole value selected
                self.rrect((x - 2, rect.centery - 9, w + 4, 18), COLOR_ACCENT, 9)
        self.txt(s, x, rect.centery - 8, self.f12, COLOR_TEXT)
        if editing and int(time.time() * 2) % 2 == 0 and not self.edit.get("fresh"):
            cx = x + self.f12.size(s[:self.edit.get("cur", len(s))])[0]
            pygame.draw.line(self.screen, COLOR_TEXT, (cx, rect.centery - 8), (cx, rect.centery + 8), 1)
        self.pop_clip(prev)
        if self.hovering(rect) and hint:
            self.hover_hint = hint + (" (drag sideways to change the value)" if numeric else "")
        elif self.hovering(rect) and numeric:
            self.hover_hint = "Click to type, drag sideways to change the value (Shift = x10)"
        if numeric:
            self.hit(rect, lambda mx, my: self.field_press(fid, str(text), cb, mx))
        else:
            self.hit(rect, lambda mx, my: self.begin_edit(fid, str(text), cb, numeric))
        return rect

    def field_press(self, fid, text, cb, mx0):
        """Figma-style number field: click = type, press and drag sideways = scrub the value."""
        try:
            v0 = float(text.replace(",", "."))
        except ValueError:
            self.begin_edit(fid, text, cb, True)
            return None
        dec, moved = "." in text, [False]
        self.wrap_ok = True

        def drag(mx, my):
            dx = mx - mx0
            if not moved[0] and abs(dx) < 4:
                return
            moved[0] = True
            step = (0.01 if dec else 1) * (10 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1)
            cb(round(v0 + dx * step, 2 if dec else 0))

        def end():
            if not moved[0]:
                self.begin_edit(fid, text, cb, True)
        self.drag_end = end
        return drag

    def begin_edit(self, fid, text, cb, numeric=False):
        self.edit = {"id": fid, "text": text, "cb": cb, "numeric": numeric, "fresh": True, "cur": len(text)}

    def commit_edit(self):
        if not self.edit:
            return
        ed, self.edit = self.edit, None
        if ed["numeric"]:
            try:
                v = float(ed["text"].replace(",", "."))
            except ValueError:
                return
            ed["cb"](v)
        else:
            ed["cb"](ed["text"])

    def tabs(self, x, y, items, active, setter):
        for name, w in items:
            rect = pygame.Rect(x, y, w, 24)
            act = name == active
            col = COLOR_PANEL if act else (COLOR_HOVER if self.hovering(rect) else COLOR_HEAD)
            pygame.draw.rect(self.screen, col, rect, border_top_left_radius=8, border_top_right_radius=8)
            self.txt(name, rect.centerx, rect.centery, self.fb if act else self.f12,
                     COLOR_TEXT if act else COLOR_MUTED, center=True)
            self.hit(rect, lambda mx, my, n=name: setter(n))
            x += w

    def panel(self, r, name=None):
        pygame.draw.rect(self.screen, COLOR_HEAD, (r.x, r.y, r.w, 24), border_top_left_radius=8,
                         border_top_right_radius=8)
        if name:                                    # X closes the dock (Panels menu brings it back)
            xr = pygame.Rect(r.right - 24, r.y, 24, 24)
            if self.hovering(xr):
                self.hover_hint = "Close this dock (Panels menu shows it again)"
            cx, cy = xr.center
            for a, b in (((-4, -4), (4, 4)), ((-4, 4), (4, -4))):
                pygame.draw.line(self.screen, (170, 170, 170), (cx + a[0], cy + a[1]), (cx + b[0], cy + b[1]), 2)
            self.hit(xr, lambda mx, my, n=name: self.toggle_dock(n))
        pygame.draw.rect(self.screen, COLOR_PANEL, (r.x, r.y + 24, r.w, r.h - 24),
                         border_bottom_left_radius=8, border_bottom_right_radius=8)

    def divider(self, x, y, w):
        pygame.draw.line(self.screen, COLOR_LINE, (x, y), (x + w, y))

    def heading(self, x, y, title, sub=None):
        w = self.txt(title, x, y, self.fb)
        if sub:
            self.txt(f" ({sub})", x + w, y, self.f12, COLOR_MUTED)

    def msg(self, s):
        self.toast = (s, pygame.time.get_ticks())

    def draw_toast(self, area):
        s, t = self.toast
        age = pygame.time.get_ticks() - t
        if not s or age > 3200:
            return
        w = min(area.w - 16, self.f12.size(s)[0] + 32)
        rc = pygame.Rect(0, 0, w, 32)
        rc.midbottom = (area.centerx, area.bottom - 16)
        self.rrect(rc, (24, 24, 28), 12)
        self.rrect(rc, (80, 80, 92), 12, 1)
        prev = self.push_clip(rc.inflate(-12, 0))
        self.txt(s, rc.x + 16, rc.centery - 7, self.f12, (240, 240, 245) if age < 2800 else (150, 150, 155))
        self.pop_clip(prev)

    # ------------------------------------------------------------------ dialog
    def open_dialog(self, title, subtitle, folder, ext, ok_label, cb, dirs=False):
        if dirs:
            files = sorted(n for n in os.listdir(folder) if os.path.isfile(os.path.join(folder, n, "project.json")))
        else:
            files = sorted(f for f in os.listdir(folder) if f.lower().endswith(ext))
        self.dialog = {"title": title, "sub": subtitle, "files": files, "folder": folder, "dirs": dirs,
                       "sel": 0 if files else -1, "scroll": 0, "ok": ok_label, "cb": cb, "info": False}

    def open_info(self, title, lines):
        self.dialog = {"title": title, "sub": "", "files": lines, "folder": "", "dirs": False, "sel": -1,
                       "scroll": 0, "ok": "Close", "cb": None, "info": True}

    def dialog_ok(self, mx=0, my=0):
        d = self.dialog
        if d["info"]:
            self.dialog = None
        elif d["sel"] >= 0:
            n = d["files"][d["sel"]]
            path = os.path.join(d["folder"], n, "project.json") if d["dirs"] else os.path.join(d["folder"], n)
            self.dialog = None
            d["cb"](path)

    def draw_dialog(self):
        d = self.dialog
        ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        self.screen.blit(ov, (0, 0))
        self.hits = []
        self.hit((0, 0, self.W, self.H), lambda mx, my: None)
        box = pygame.Rect(0, 0, 400, 304)
        box.center = (self.W // 2, self.H // 2)
        self.rrect(box, (32, 34, 40), 16)
        self.rrect(box, (70, 70, 78), 16, 1)
        self.hit(box, lambda mx, my: None)
        self.txt(d["title"], box.x + 16, box.y + 16, self.fb2)
        self.txt(d["sub"], box.x + 16, box.y + 48, self.fb)
        lst = pygame.Rect(box.x + 16, box.y + 72, box.w - 32, 160)
        self.rrect(lst, (22, 23, 27), 8)
        if not d["files"]:
            self.txt("(nothing here yet)", lst.x + 8, lst.y + 8, self.f12, COLOR_MUTED)
        for i in range(6):
            idx = d["scroll"] + i
            if idx >= len(d["files"]):
                break
            row = pygame.Rect(lst.x + 4, lst.y + 4 + i * 24, lst.w - 8, 24)
            if idx == d["sel"]:
                self.rrect(row, COLOR_ACCENT, 6)
            self.txt(d["files"][idx], row.x + 8, row.y + 5, self.f12)
            if not d["info"]:
                self.hit(row, lambda mx, my, idx=idx: d.__setitem__("sel", idx))
        if d["folder"]:
            self.txt(os.path.basename(d["folder"]) + "/", box.x + 16, lst.bottom + 8, self.f11, COLOR_MUTED)
        if not d["info"]:
            self.button((box.right - 200, box.bottom - 48, 88, 32), "Cancel",
                        lambda mx, my: setattr(self, "dialog", None), radius=16)
        self.button((box.right - 104, box.bottom - 48, 88, 32), d["ok"], self.dialog_ok, color=COLOR_ACCENT_L,
                    radius=16)

    # ------------------------------------------------------------------ events
    def click(self, pos, button):
        self.wrap_ok, self.wrap_off = False, 0
        if self.mode == "main":
            if self.r_tl.collidepoint(pos):
                self.focus_area = "timeline"                  # arrows now step the playhead
            elif self.r_view.collidepoint(pos):
                self.focus_area = "view"                      # arrows now nudge the selection
        if self.edit and self.edit.get("rect") is not None and self.edit["rect"].collidepoint(pos):   # click inside = place the caret
            ed = self.edit
            ed["fresh"] = False
            tx = ed.get("tx", ed["rect"].x + 8)
            ed["cur"] = min(range(len(ed["text"]) + 1), key=lambda i: abs(tx + self.f12.size(ed["text"][:i])[0] - pos[0]))
            return
        if self.edit and self.sugg_rects:                    # expression suggestions
            for rc, i in self.sugg_rects:
                if rc.collidepoint(pos):
                    self.apply_suggestion(i)
                    return
        if self.mode == "main" and button in (1, 3):
            self.push_undo()
        if self.edit:
            self.commit_edit()
            self.push_undo()
        if self.eyedrop and button == 1:
            self.eyedrop = False
            self.picker_set_rgb(tuple(self.screen.get_at(pos))[:3], self.eyedrop_p)
            return
        self.drag = self.drag_end = None
        for rect, fn, buttons in reversed(self.hits):
            if button in buttons and rect.collidepoint(pos):
                r = fn(pos[0], pos[1])
                if callable(r):
                    self.drag = r
                return

    def lib_target(self, pos):
        return "right" not in self.hidden and self.right_tab == "Library" and self.lib_mode == "Objects" and self.r_right.collidepoint(pos)

    def release(self, pos, button):
        lib_drop = self.autoscroll == "view" and bool(self.sel) and self.lib_target(pos)       # objects dragged from the viewer into the Library panel
        if self.drag_end:
            fn, self.drag_end = self.drag_end, None
            fn()
        self.drag, self.press_slot, self.autoscroll = None, None, None
        if lib_drop:
            for o_, b_, k_ in getattr(self, "_move_undo", []):                   # the drag only carried them there: put them back
                o_.base.update(b_)
                o_.keys = {p: dict(v) for p, v in k_.items()}
            self.lib_save_objs(self.sel)
        self.schem_release(pos)
        self.flyout_release(pos)

    def wheel(self, dy, dx=0):
        pos = pygame.mouse.get_pos()
        mods = pygame.key.get_mods()
        if self.dialog:
            d = self.dialog
            d["scroll"] = int(clamp(d["scroll"] - dy, 0, max(0, len(d["files"]) - 6)))
        elif self.mode == "start":
            self.start_scroll = max(0, self.start_scroll - dy)
        elif self.mode != "main":
            return
        elif self.r_tl.collidepoint(pos):
            self.tl_wheel(dy, dx, pos, mods)
        elif self.r_aux and self.workspace == "Schematic" and self.r_aux.collidepoint(pos):
            self.nd_wheel(dy, pos)
        elif self.r_aux and self.workspace == "Drawing" and self.r_aux.collidepoint(pos):
            self.aux_scroll = clamp(self.aux_scroll - dy * 40, 0, 420)
        elif self.r_view.collidepoint(pos):
            nz = clamp(self.zoom * (1.1 ** dy), 0.02, 8)
            self.ox = pos[0] - (pos[0] - self.ox) * nz / self.zoom
            self.oy = pos[1] - (pos[1] - self.oy) * nz / self.zoom
            self.zoom, self.view_fit = nz, False
        elif self.r_left.w and self.r_left.collidepoint(pos) and self.left_tab == "Footage":
            self.foot_scroll = int(clamp(self.foot_scroll - dy, 0, max(0, len(self.footage) - 6)))
        elif self.r_right.w and self.r_right.collidepoint(pos) and self.right_tab == "Properties":
            self.right_scroll = clamp(self.right_scroll - dy * 40, 0, self.right_max)
        elif self.r_right.collidepoint(pos) and self.right_tab == "Library":
            if self.lib_mode == "Explorer":
                self.ex_scroll = int(clamp(self.ex_scroll - dy, 0, max(0, self.ex_n - 8)))
            else:
                self.lib_scroll = int(clamp(self.lib_scroll - dy, 0, max(0, (len(self.library) + 1) // 2 - 2)))

    def keydown(self, e):
        mods = pygame.key.get_mods()
        ctrl = mods & (pygame.KMOD_CTRL | pygame.KMOD_META)
        k = e.key
        pos = pygame.mouse.get_pos()
        if self.edit:
            ed = self.edit
            sg = self.expr_suggestions()
            if sg and k == pygame.K_TAB:
                self.apply_suggestion(min(self.sugg_i, len(sg) - 1))
                return
            if sg and k in (pygame.K_UP, pygame.K_DOWN):
                self.sugg_i = (self.sugg_i + (1 if k == pygame.K_DOWN else -1)) % len(sg)
                return
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                self.push_undo()
                self.commit_edit()
            elif ctrl and k == pygame.K_a:
                ed["fresh"] = True
            elif ctrl and k in (pygame.K_c, pygame.K_x):
                self.text_clip = ed["text"]
                set_clipboard_text(ed["text"])                            # other programs can paste it too
                if k == pygame.K_x:
                    ed["text"], ed["cur"] = "", 0
            elif ctrl and k == pygame.K_v:
                if ed["fresh"]:
                    ed["text"], ed["cur"] = "", 0
                ins = get_clipboard_text()
                if ins is None:
                    ins = getattr(self, "text_clip", "")
                ins = (ins.strip().splitlines() or [""])[0]
                if ed.get("numeric"):
                    ins = "".join(ch for ch in ins if ch in "0123456789.,-+")
                ed["text"] = ed["text"][:ed["cur"]] + ins + ed["text"][ed["cur"]:]
                ed["cur"], ed["fresh"] = ed["cur"] + len(ins), False
            elif k == pygame.K_ESCAPE:
                self.edit = None
            elif k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_HOME, pygame.K_END):
                ed["fresh"] = False                                   # arrows / click remove the "everything selected" state
                n, c = len(ed["text"]), ed["cur"]
                ed["cur"] = max(0, c - 1) if k == pygame.K_LEFT else (min(n, c + 1) if k == pygame.K_RIGHT else (0 if k == pygame.K_HOME else n))
            elif k == pygame.K_DELETE:
                if ed["fresh"]:
                    ed["text"], ed["cur"] = "", 0
                else:
                    ed["text"] = ed["text"][:ed["cur"]] + ed["text"][ed["cur"] + 1:]
                ed["fresh"] = False
            elif k == pygame.K_BACKSPACE:
                if ed["fresh"]:
                    ed["text"], ed["cur"] = "", 0
                elif ed["cur"] > 0:
                    ed["text"] = ed["text"][:ed["cur"] - 1] + ed["text"][ed["cur"]:]
                    ed["cur"] -= 1
                ed["fresh"] = False
            elif e.unicode and e.unicode.isprintable():
                if ed["fresh"]:
                    ed["text"], ed["cur"] = "", 0
                ed["fresh"] = False
                if not ed["numeric"] or e.unicode in "0123456789.,-+":
                    ed["text"] = ed["text"][:ed["cur"]] + e.unicode + ed["text"][ed["cur"]:]
                    ed["cur"] += 1
                    self.sugg_i = 0
            return
        if k == pygame.K_ESCAPE and self.rest_layer is not None:
            self.rest_layer = None
            self.msg("Back to the rig view")
            return
        if k == pygame.K_ESCAPE:
            self.dialog, self.link_mode, self.menu_open, self.ctx = None, False, None, None
            self.bone_chain, self.layer_dlg, self.render_dlg, self.quit_dlg, self.marker_dlg = False, False, None, None, None
            self.replace_target, self.seq_dlg, self.rename_dlg, self.prefs_open = None, None, None, False
            self.picker, self.flyout, self.eyedrop = None, None, False
            return
        if self.dialog or self.mode != "main":
            return
        self.push_undo()
        if ctrl and k == pygame.K_z:
            self.redo() if mods & pygame.KMOD_SHIFT else self.undo()
        elif ctrl and k == pygame.K_y:
            self.redo()
        elif k == pygame.K_BACKQUOTE:
            pos = pygame.mouse.get_pos()
            if self.maxi:
                self.maxi = None
            elif self.r_tl.collidepoint(pos):
                self.maxi = "timeline"
            elif self.r_aux and self.r_aux.collidepoint(pos):
                self.maxi = "aux"
            elif self.r_view.collidepoint(pos):
                self.maxi = "viewport"
        elif k == pygame.K_SPACE:
            self.toggle_play()
        elif ctrl and k == pygame.K_c:
            self.kf_copy() if (self.kf_sel and self.r_tl.collidepoint(pos)) else self.copy_sel()
        elif ctrl and k == pygame.K_x:
            self.cut_sel()
        elif ctrl and k == pygame.K_v:
            self.kf_paste() if (self.kf_clip and self.r_tl.collidepoint(pos)) else self.paste()
        elif k == pygame.K_d and not ctrl:
            self.default_colors()
        elif k == pygame.K_x and not ctrl:
            self.swap_colors()
        elif k in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET) and (mods & pygame.KMOD_ALT):
            self.trim_at_playhead(k == pygame.K_RIGHTBRACKET)        # Alt+[ keeps the part right of the playhead, Alt+] the part left of it
        elif k == pygame.K_b and not ctrl and (self.r_tl.collidepoint(pos) or (self.workspace == "Schematic" and self.r_aux.collidepoint(pos))):
            self.select_relative(children=bool(mods & pygame.KMOD_SHIFT))     # B = parent, Shift+B = children (over timeline / schematic)
        elif k == pygame.K_u:
            self.toggle_u()
        elif k == pygame.K_m and not ctrl:
            self.markers.append({"f": self.frame, "text": "", "color": [255, 188, 63]})
            self.msg(f"Marker at frame {self.frame} (double-click it to edit)")
        elif k == pygame.K_LEFTBRACKET:
            self.brush_px = max(1, self.brush_px - (5 if mods & pygame.KMOD_SHIFT else 1))
        elif k == pygame.K_RIGHTBRACKET:
            self.brush_px = min(200, self.brush_px + (5 if mods & pygame.KMOD_SHIFT else 1))
        elif k == pygame.K_k:
            self.key_here()
        elif k == pygame.K_i:
            self.work_in = self.frame
            self.msg(f"Work area starts at frame {self.frame}")
        elif k == pygame.K_o:
            self.work_out = self.frame
            self.msg(f"Work area ends at frame {self.frame}")
        elif k == pygame.K_w:
            self.jump_phase(1)
        elif k == pygame.K_q:
            self.jump_phase(-1)
        elif k in (pygame.K_DELETE, pygame.K_BACKSPACE):
            if self.sel_wire is not None and self.workspace == "Schematic":
                self.unlink(self.sel_wire)
                self.sel_wire = None
            elif self.kf_sel and self.r_tl.collidepoint(pygame.mouse.get_pos()):
                self.delete_keys()
            else:
                self.delete_selected()
        elif k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
            self.arrow_key(k, mods)
        elif k == pygame.K_HOME:
            self.view_fit = True
        elif ctrl and k == pygame.K_s:
            self.save_project()
        elif ctrl and k == pygame.K_a:
            self.sel = list(self.objs)
        elif ctrl and k == pygame.K_d:
            self.duplicate_selected()
        elif ctrl and k == pygame.K_g:
            self.group_selected()
        elif ctrl and k == pygame.K_m:
            self.open_render()
        elif ctrl and k == pygame.K_r:
            self.open_rename()
        elif ctrl and k == pygame.K_h and self.left_tab == "Footage" and self.foot_sel is not None:
            self.start_replace(self.foot_sel)
        elif not ctrl and k in (pygame.K_p, pygame.K_r, pygame.K_t, pygame.K_s, pygame.K_e, pygame.K_l) \
                and self.r_tl.collidepoint(pygame.mouse.get_pos()):               # property keys while the cursor is on the timeline
            m = {pygame.K_p: ("x", "y"), pygame.K_r: ("rotation",), pygame.K_t: ("opacity",), pygame.K_s: ("scale",)}
            if k in m:
                self.toggle_props(m[k], bool(mods & pygame.KMOD_SHIFT))
            else:
                self.msg("Effects (E) and audio volume (L) rows: coming soon")
        elif k in KEYMAP and not ctrl:
            self.set_tool(KEYMAP[k])

    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.request_quit()
        elif self.mode == "splash":
            if e.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                self.leave_splash()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 2, 3):
            self.btn = e.button
            self.click(e.pos, e.button)
        elif e.type == pygame.MOUSEMOTION and self.drag:
            x, y = e.pos
            nx = None
            if self.wrap_ok:                                  # Blender style: dragging past the screen edge wraps around
                W = self.screen.get_size()[0]
                nx = W - 3 if x <= 0 else (2 if x >= W - 1 else None)
            self.drag(x + self.wrap_off, y)
            if nx is not None:
                self.wrap_off += x - nx
                pygame.mouse.set_pos((nx, y))
        elif e.type == pygame.MOUSEBUTTONUP:
            self.release(e.pos, e.button)
        elif e.type == pygame.MOUSEWHEEL:
            self.wheel(e.y, e.x)
        elif e.type == pygame.KEYDOWN:
            self.keydown(e)

    def raise_window(self):
        try:
            from pygame._sdl2.video import Window
            w = Window.from_display_module()
            w.restore()
            w.focus()
        except Exception:  # noqa
            pass

    def update(self, dt):
        now = pygame.time.get_ticks()
        if self.workspace != self._ws_prev:                          # Properties / Library are shown in Animate, hidden in the other workspaces
            if self._ws_prev is not None:
                if self.workspace == "Animate":
                    self.hidden.discard("right")
                else:
                    self.hidden.add("right")
            self._ws_prev = self.workspace
        if RAISE_REQUEST[0]:                                         # the program was started a second time: show this window
            RAISE_REQUEST[0] = False
            self.raise_window()
        if self.mode == "splash":
            if now - self.splash_t > 3300:
                self.leave_splash()
            return
        if self.mode != "main":
            return
        sel_ids = tuple(id(o) for o in self.sel)                      # a new selection: centre it in the timeline
        if sel_ids != self._last_sel:
            self._last_sel = sel_ids
            if self.psel is not None and self.focus_area != "timeline":
                self.reveal_in_timeline(self.psel, center=True)
        if self.drag and self.autoscroll and self.btn == 1:        # dragging to the edge scrolls the view
            mx_, my_ = pygame.mouse.get_pos()
            if self.autoscroll == "tl":
                top, bot = self.r_tl.y + 40, self.r_tl.bottom - 10
                if my_ < top + 16 or my_ > bot - 16:
                    self.tl_vy = clamp(self.tl_vy + (-12 if my_ < top + 16 else 12), 0, getattr(self, "tl_vmax", 0))
                    self.drag(mx_, my_)
            elif self.autoscroll == "tlh" and getattr(self, "tl_cells", None):      # playhead dragged to the edge of the timeline
                c_ = self.tl_cells
                dx = -16 if mx_ < c_.x + 20 else (16 if mx_ > c_.right - 20 else 0)
                if dx:
                    self.tl_off = clamp(self.tl_off + dx, 0, self.tl_max)
                    self.drag(mx_, my_)
            elif self.autoscroll == "view" and self.r_view.w:           # dragging objects to the edge of the viewer moves the view
                r_, st = self.r_view, 16
                dx = st if mx_ < r_.x + 24 else (-st if mx_ > r_.right - 24 else 0)
                dy = st if my_ < r_.y + 24 else (-st if my_ > r_.bottom - 24 else 0)
                if dx or dy:
                    self.ox += dx
                    self.oy += dy
                    self.drag(mx_, my_)
            elif self.autoscroll == "nodes" and self.r_aux.w:
                r_, st = self.r_aux, 14
                dx = st if mx_ < r_.x + 30 else (-st if mx_ > r_.right - 30 else 0)
                dy = st if my_ < r_.y + 30 else (-st if my_ > r_.bottom - 60 else 0)
                if dx or dy:
                    self.nd_ox += dx
                    self.nd_oy += dy
                    self.drag(mx_, my_)
        if self.playing:
            self.play_acc += dt * self.fps
            while self.play_acc >= 1:
                self.play_acc -= 1
                lo, hi = self.work_in or 1, min(self.work_out or self.total, self.total)
                if self.frame >= hi:
                    if self.loop:
                        self.frame = lo
                    else:
                        self.playing = False
                        break
                else:
                    self.frame += 1
        kp = pygame.key.get_pressed()                         # hold [ or ] and the brush size keeps changing (faster the longer you hold)
        for key, dr in ((pygame.K_LEFTBRACKET, -1), (pygame.K_RIGHTBRACKET, 1)):
            if kp[key] and not self.edit:
                held = now - self.br_start.setdefault(key, now)
                if held > 300 and now - self.br_last > 40:
                    self.brush_px = int(clamp(self.brush_px + dr * (1 + held // 500), 1, 300))
                    self.br_last = now
            else:
                self.br_start.pop(key, None)
        for key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):          # holding an arrow repeats it
            if kp[key] and not self.edit and not self.dialog:
                held = now - self.ar_start.setdefault(key, now)
                if held > 400 and now - self.ar_last > 45:
                    self.arrow_key(key, pygame.key.get_mods())
                    self.ar_last = now
            else:
                self.ar_start.pop(key, None)
        if self.autosave["on"] and self.project_dir and now - self.last_autosave > max(1, self.autosave["min"]) * 60000:
            self.last_autosave = now
            if self.doc_sig() != self.saved_sig:
                self.save_project(quiet=True)
                self.msg("Autosaved")
        if self.press_slot and pygame.mouse.get_pressed()[0] and self.flyout is None:
            i, t = self.press_slot
            if now - t > 350 and len(SLOTS[i]) > 1:
                self.flyout = i
        self.update_hover()
        self.update_cursor()

    def safe(self, fn, *a):
        try:
            fn(*a)
        except Exception:  # noqa
            self.report_crash()

    def draw_main(self):
        self.compute_layout()
        self.hits, self.row_rects, self.hover_hint, self.sugg_rects = [], [], None, []
        self.screen.fill(COLOR_BG)
        hid = self.hidden
        if self.maxi == "timeline":
            self.safe(self.draw_timeline)
        elif self.maxi == "viewport":
            self.safe(self.draw_canvas)
        elif self.maxi == "aux":
            self.safe(self.draw_aux)
        else:
            if "toolbox" not in hid:
                self.safe(self.draw_toolbox)
            if "left" not in hid:
                self.safe(self.draw_left)
            self.safe(self.draw_canvas)
            if self.r_aux:
                self.safe(self.draw_aux)
            if "right" not in hid:
                self.safe(self.draw_right)
            self.safe(self.draw_transport)
            if "timeline" not in hid:
                self.safe(self.draw_timeline)
            self.safe(self.draw_splitters)
        self.draw_menu_bar()
        self.draw_bar()
        self.draw_toast(self.r_view if self.r_view.w else self.r_aux or self.r_view)
        self.draw_prefs()
        self.draw_layer_dlg()
        self.draw_seq_dlg()
        self.draw_rename_dlg()
        self.draw_render_dlg()
        self.draw_marker_dlg()
        self.draw_picker()
        self.draw_flyout()
        self.draw_menu_dropdown()
        self.draw_ctx()
        self.draw_suggestions()
        self.draw_quit_dlg()
        if self.dialog:
            self.draw_dialog()
        self.draw_render_progress()
        self.draw_tooltip()

    def draw_splitters(self):
        """Drag the gaps between panels to resize them."""
        TOP = 40
        ph = self.r_left.h

        def left(mx, my):
            self.w_left = clamp(mx - self.r_left.x - 4, 160, 400)

        def right(mx, my):
            self.w_right = clamp(self.W - 8 - (mx + 4), 200, 480)

        def bottom(mx, my):
            self.h_tl = clamp(self.H - 24 - (my + 4), 96, 400)
        specs = []
        if self.r_aux:                                       # bar between the viewer and the panel next to it
            def mid(mx, my):
                self.split_frac = clamp((mx - self.r_view.x) / max(1, self.r_aux.right - self.r_view.x - 8), 0.15, 0.85)
            specs.append((pygame.Rect(self.r_view.right, TOP, 8, ph), "sizewe", mid))
        if self.r_left.w:
            specs.append((pygame.Rect(self.r_left.right, TOP, 8, ph), "sizewe", left))
        if self.r_right.w:
            specs.append((pygame.Rect(self.r_right.x - 8, TOP, 8, ph), "sizewe", right))
        if self.r_tl.h and not self.maxi:
            specs.append((pygame.Rect(0, self.r_tl.y - 8, self.W, 8), "sizens", bottom))
        self.splitters = []
        for rc, kind, fn in specs:
            self.splitters.append((rc, kind))
            if self.hovering(rc) or (self.drag is fn):
                bar = pygame.Rect(0, 0, 4, 48) if kind == "sizewe" else pygame.Rect(0, 0, 48, 4)
                bar.center = rc.center
                self.rrect(bar, COLOR_HOVER, 2)
            self.hit(rc, lambda mx, my, fn=fn: fn)

    def draw_frame(self):
        if self.mode == "splash":
            self.draw_splash()
        elif self.mode == "start":
            self.draw_start()
        else:
            self.draw_main()
        pygame.display.flip()

    def report_crash(self):
        """Never let one bug close the window: print + log the error and keep running."""
        tb = traceback.format_exc()
        if tb != getattr(self, "_last_tb", None):
            self._last_tb = tb
            print(tb, file=sys.stderr)
            try:
                with open(os.path.join(DATA_DIR, "crash.log"), "a", encoding="utf-8") as fh:
                    fh.write(time.strftime("%Y-%m-%d %H:%M:%S\n") + tb + "\n")
            except OSError:
                pass
            self.msg("Error: " + tb.strip().splitlines()[-1][:120])
        self.drag = self.drag_end = None

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000
            try:
                if self.mode == "main":
                    self.compute_layout()
                for e in pygame.event.get():
                    self.handle_event(e)
                self.update(dt)
                self.draw_frame()
            except Exception:  # noqa
                self.report_crash()
                if self.mode == "main":
                    try:
                        pygame.display.flip()
                    except Exception:  # noqa
                        pass
        pygame.quit()
        sys.exit()


class App(AppBase, CanvasMixin, PanelsMixin, TimelineMixin, StartMixin):
    pass
