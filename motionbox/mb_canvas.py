"""Motion Box - viewport (artboard), tools, selection/handles and the secondary panels
(Schematic nodes, Level Strip, Fx, Expressions, Script)."""
import math
import os

import pygame

from mb_core import *            # noqa

HSIGN = [(-1, -1), (1, -1), (1, 1), (-1, 1), (0, -1), (1, 0), (0, 1), (-1, 0)]
BBOX_COL = (60, 95, 210)
FX_LIST = ["Blur", "Glow", "Drop Shadow", "Grain", "Tint", "Color Correction", "Displacement", "Particles"]


class CanvasMixin:
    # ------------------------------------------------------------ transforms
    def a2s(self, ax, ay):
        return (self.ox + ax * self.zoom, self.oy + ay * self.zoom)

    def s2a(self, sx, sy):
        return ((sx - self.ox) / self.zoom, (sy - self.oy) / self.zoom)

    @staticmethod
    def xf(x, y, s, r, px, py):
        a = math.radians(r)
        c, sn = math.cos(a), math.sin(a)
        return (x + (px * c - py * sn) * s, y + (px * sn + py * c) * s)

    def obj_pts(self, o, f=None):
        f = f or self.frame
        x, y, s, r = self.world(o, f)
        pts, closed = shape_pts(o, f)
        return [self.a2s(*self.xf(x, y, s, r, px, py)) for px, py in pts], closed

    def box_pts(self, o, pad=0):
        x, y, s, r = self.world(o, self.frame)
        hw = max(o.w / 2 * s, 2) + pad / self.zoom
        hh = max(o.h / 2 * s, 2) + pad / self.zoom
        ax_, ay_ = o.anchor[0] * s, o.anchor[1] * s                      # the box is drawn relative to the anchor
        return [self.a2s(*self.xf(x, y, 1, r, px - ax_, py - ay_)) for px, py in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]

    def handle_points(self, o):
        p = self.box_pts(o, 0 if o.kind in ("null", "peg") else 6)
        mids = [((p[i][0] + p[(i + 1) % 4][0]) / 2, (p[i][1] + p[(i + 1) % 4][1]) / 2) for i in range(4)]
        return p + mids

    def handle_hit(self, mx, my):
        o = self.psel
        if not o or len(self.sel) != 1 or o.locked or self.link_mode or o.kind in ("vlayer", "rlayer"):
            return None
        hps = self.handle_points(o)
        wx, wy, _, _ = self.world(o, self.frame)
        cx, cy = self.a2s(wx, wy)
        if o.kind == "bone":                                 # the ball at the end of a bone sets its bend and length
            tp = self.a2s(*self.bone_end(o))
            if math.hypot(mx - tp[0], my - tp[1]) <= 9:
                return ("tip", 0)
        if o.kind == "rect":
            for i, dp in enumerate(self.radius_dots(o)):
                if math.hypot(mx - dp[0], my - dp[1]) <= 7:
                    return ("radius", i)
        for i, hp in enumerate(hps):
            if not o.kind.startswith("ctrl") and o.kind != "bone" and abs(mx - hp[0]) <= 6 and abs(my - hp[1]) <= 6:
                return ("resize", i)
        if "rotation" in self.locked_props(o):              # joysticks / position controllers cannot be rotated
            return None
        for i in range(4):
            hp = hps[i]
            d = math.hypot(mx - hp[0], my - hp[1])
            if 6 < d <= 24 and math.hypot(mx - cx, my - cy) > math.hypot(hp[0] - cx, hp[1] - cy):
                return ("rotate", i)
        return None

    def radius_dots(self, o):
        x, y, s, rot = self.world(o, self.frame)
        hw, hh = o.w / 2, o.h / 2
        inset = clamp(o.radius + 12 / (self.zoom * max(s, 0.01)), 4, min(hw, hh) * 0.95)
        out = []
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            out.append(self.a2s(*self.xf(x, y, s, rot, sx * (hw - inset) - o.anchor[0], sy * (hh - inset) - o.anchor[1])))
        return out

    def start_radius(self, o):
        self.radius_drag = True

        def drag(mx, my):
            ax, ay = self.s2a(mx, my)
            x, y, s, rot = self.world(o, self.frame)
            a = math.radians(-rot)
            dx, dy = ax - x, ay - y
            lx = (dx * math.cos(a) - dy * math.sin(a)) / max(s, 0.01) + o.anchor[0]
            ly = (dx * math.sin(a) + dy * math.cos(a)) / max(s, 0.01) + o.anchor[1]
            inset = min(o.w / 2 - abs(lx), o.h / 2 - abs(ly))
            o.radius = round(clamp(inset - 12 / (self.zoom * max(s, 0.01)), 0, min(o.w, o.h) / 2), 1)

        def end():
            self.radius_drag = False
        self.drag_end = end
        return drag

    def hit_obj(self, o, ax, ay):
        x, y, s, r = self.world(o, self.frame)
        a = math.radians(-r)
        dx, dy = ax - x, ay - y
        lx = dx * math.cos(a) - dy * math.sin(a)
        ly = dx * math.sin(a) + dy * math.cos(a)
        return (abs(lx + o.anchor[0] * s) <= max(o.w / 2 * s, 8 / self.zoom)
                and abs(ly + o.anchor[1] * s) <= max(o.h / 2 * s, 8 / self.zoom))

    def all_pickables(self):
        out = []
        for o in self.objs:
            if o.kind == "vlayer":
                out += [i for i in o.items if i.visible and not i.locked and self.tool_filter(i)] if o.visible and not o.locked else []
            elif o.kind != "rlayer" and self.tool_filter(o):
                out.append(o)
        return out

    def pick(self, mx, my):
        ax, ay = self.s2a(mx, my)
        for o in self.objs:
            if not o.visible or o.locked or not self.in_range(o) or o.name in self.matte_sources() or (self.view["render"] and not o.render):
                continue
            if o.kind == "vlayer":                           # shapes inside a vector layer
                for it in o.items:
                    if it.visible and not it.locked and self.tool_filter(it) and self.hit_obj(it, ax, ay):
                        return it
            elif o.kind != "rlayer" and self.tool_filter(o) and self.hit_obj(o, ax, ay):
                return o
        return None

    # ----------------------------------------------------------- hover/cursor
    def set_tool(self, tid):
        self.tool, self.link_mode = tid, False
        if tid != "bone":
            self.bone_chain = False
        for i, s in enumerate(SLOTS):
            if s and tid in s:
                self.slot_tool[i] = tid
        n, _, h = TOOL_INFO[tid]
        if h.startswith("Coming soon"):
            self.msg(f"{n}: coming soon")

    def update_hover(self):
        pos = pygame.mouse.get_pos()
        h = None
        if not self.drag and not self.dialog and self.menu_open is None and not self.picker:
            if self.r_view.collidepoint(pos) and self.tool in ("select", "transform"):
                h = self.pick(*pos)
            else:
                for rect, o in self.row_rects:
                    if rect.collidepoint(pos):
                        h = o
                        break
        self.hover = h

    GLYPH_TOOLS = ("fill", "eyedropper", "scissors", "zoom", "lipsync", "taper", "text", "pen", "multiline", "artboard",
                   "select_level", "anchor", "bone", "bone_anim", "bone_ik", "ctrl", "ctrl_rot", "ctrl_posrot", "null", "peg",
                   "joy_x", "joy_y", "joy_xy", "rect", "ellipse", "polygon", "line", "eraser", "view_rotate")

    def update_cursor(self):
        pos = pygame.mouse.get_pos()
        kind = "arrow"
        inv = self.r_view.collidepoint(pos) and not self.dialog and self.menu_open is None
        dn = getattr(self.drag, "__name__", "")
        sp = next((k for rc, k in self.splitters if rc.collidepoint(pos)), None)
        if self.eyedrop:
            kind = "cross"
        elif getattr(self, "rotating", False):
            kind = "rotate"
        elif dn in ("left", "right", "bottom", "mid"):
            kind = "sizens" if dn == "bottom" else "sizewe"
        elif sp and not self.drag and not self.dialog:
            kind = sp
        elif not self.drag and any(rc.collidepoint(pos) for rc in self.tl_edges):
            kind = "sizewe"
        elif self.drag and (self.cursor_kind or "").startswith("resize"):
            kind = self.cursor_kind
        elif (self.tool == "hand" and inv) or (self.drag and self.btn == 2):
            kind = "hand"
        elif inv and not self.drag and self.hover is not None and self.hover.kind.startswith("ctrl") and self.tool in ("select", "transform", "animate", "bone_anim"):
            kind = "rotate" if self.hover.kind == "ctrl_rot" else "move"       # a controller shows what it will do
        elif inv and self.tool in ("select", "transform", "animate") and not self.drag:
            hh = self.handle_hit(*pos)
            if hh:
                i = hh[1]
                kind = "cross" if hh[0] == "tip" else "rotate" if hh[0] == "rotate" else ("resize_d2" if i in (0, 2) else "resize_d1" if i in (1, 3)
                                                           else "resize_v" if i in (4, 6) else "resize_h")
        elif inv and self.tool == "brush":                  # a circle that shows the brush size ([ and ] change it)
            kind = f"brush_{int(clamp(self.brush_px * self.zoom, 8, 120)) // 2 * 2}"
        elif inv and self.tool not in ("select", "hand") and load_icon_state(self.tool, 30, "default")[0] is not None:   # no icon = normal arrow
            kind = "tool_" + self.tool
        if kind != self.cursor_kind:
            self.cursor_kind = kind
            self.apply_cursor(kind)

    def apply_cursor(self, kind):
        try:
            sysmap = {"arrow": pygame.SYSTEM_CURSOR_ARROW, "hand": pygame.SYSTEM_CURSOR_HAND, "cross": pygame.SYSTEM_CURSOR_CROSSHAIR,
                      "sizewe": pygame.SYSTEM_CURSOR_SIZEWE, "sizens": pygame.SYSTEM_CURSOR_SIZENS, "move": pygame.SYSTEM_CURSOR_SIZEALL}
            pygame.mouse.set_cursor(sysmap[kind] if kind in sysmap else self.cursor_surface(kind))
        except Exception:  # noqa
            pass

    def cursor_surface(self, kind):
        if kind in self.cursor_cache:
            return self.cursor_cache[kind]
        png = cursor_png(kind)                                 # your own artwork wins (icons/cursors/<kind>.png)
        if png is not None:
            self.cursor_cache[kind] = pygame.cursors.Cursor((png.get_width() // 2, png.get_height() // 2), png)
            return self.cursor_cache[kind]
        d = pygame.draw
        hot = (20, 20)
        sf = pygame.Surface((40, 40), pygame.SRCALPHA)

        def arrow2(p0, p1):                                  # double-headed arrow, white with a dark outline
            ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
            for col, w in (((0, 0, 0), 5), ((255, 255, 255), 3)):
                d.line(sf, col, p0, p1, w)
                for tip, a in ((p1, ang + math.pi), (p0, ang)):
                    for da in (0.6, -0.6):
                        d.line(sf, col, tip, (tip[0] + math.cos(a + da) * 9, tip[1] + math.sin(a + da) * 9), w)
        if kind == "resize_v":
            arrow2((20, 6), (20, 34))
        elif kind == "resize_h":
            arrow2((6, 20), (34, 20))
        elif kind == "resize_d1":
            arrow2((8, 32), (32, 8))
        elif kind == "resize_d2":
            arrow2((8, 8), (32, 32))
        elif kind == "rotate":                               # arc with an arrow head, as in the design
            for col, w in (((0, 0, 0), 5), ((255, 255, 255), 3)):
                d.arc(sf, col, (6, 12, 28, 28), 0.5, 2.9, w)
                ex, ey = 20 + 14 * math.cos(0.5), 26 - 14 * math.sin(0.5)
                d.line(sf, col, (ex, ey), (ex + 2, ey - 9), w)
                d.line(sf, col, (ex, ey), (ex - 9, ey + 1), w)
        elif kind.startswith("brush_"):
            dd = int(kind[6:])
            sf = pygame.Surface((dd + 8, dd + 8), pygame.SRCALPHA)
            c = (dd + 8) // 2
            hot = (c, c)
            d.circle(sf, (0, 0, 0), (c, c), dd // 2 + 1, 2)
            d.circle(sf, (255, 255, 255), (c, c), dd // 2, 1)
            d.circle(sf, (255, 255, 255), (c, c), 1)
        else:                                                # tool glyph with a dark outline
            tid = kind[5:]                                        # the tool's own icon, with a dark outline
            ic = load_icon_state(tid, 30, "default")[0]
            sf, hot = pygame.Surface((34, 34), pygame.SRCALPHA), (17, 17)
            if ic:
                dark = ic.copy()
                dark.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
                for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    sf.blit(dark, (2 + ox, 2 + oy))
                sf.blit(ic, (2, 2))
        if kind.startswith("resize") or kind == "rotate":      # smaller arrows
            sf, hot = pygame.transform.smoothscale(sf, (28, 28)), (14, 14)
        cur = pygame.cursors.Cursor(hot, sf)
        self.cursor_cache[kind] = cur
        return cur

    # ----------------------------------------------------------- interactions
    def start_pan(self, mx, my):
        sx, sy, ox, oy = mx, my, self.ox, self.oy
        self.view_fit = False

        def pan(mx, my):
            self.ox, self.oy = ox + mx - sx, oy + my - sy
        return pan

    def canvas_click(self, mx, my):
        tool = self.tool
        ax, ay = self.s2a(mx, my)
        if self.btn == 2 or tool == "hand":
            return self.start_pan(mx, my)
        if tool in ("rect", "ellipse", "polygon", "line"):
            return self.start_shape(tool, mx, my)
        if tool == "brush":
            return self.start_brush(mx, my)
        if tool in ("null", "ctrl", "ctrl_rot", "ctrl_posrot", "peg"):
            self.new_obj(tool, round(ax), round(ay))
            self.set_tool("select")
            return
        if tool.startswith("joy_"):
            self.add_joystick(tool[4:], round(ax), round(ay))
            self.set_tool("select")
            return
        if tool == "fill":
            o = self.pick(mx, my)
            if self.fill_opts["mode"] != "click":
                self.msg("Fill by rectangle / lasso selection: coming soon - click mode is active")
            if o and o.kind not in ("null", "peg", "bone") and not o.kind.startswith("ctrl"):
                tg = self.fill_opts["target"]
                if tg in ("fill", "all"):
                    o.fill, o.fill_on = self.def_fill, True
                    if o.kind == "brush":
                        o.closed = True
                if tg in ("stroke", "all"):
                    o.stroke, o.stroke_on = self.def_stroke, True
                self.msg(f"Filled {o.name} ({tg})")
            else:
                self.msg("Fill bucket: click a shape or a brush stroke")
            return
        if tool == "eyedropper":
            c = tuple(self.screen.get_at((int(mx), int(my))))[:3]
            self.color_set("fill", c, 100.0)
            self.msg(f"Picked #{rgb_to_hex(c)} as the fill colour")
            return
        if tool == "scissors":
            o = self.pick(mx, my) or self.psel
            if o:
                self.cut_layer(o.owner or o, self.frame)
            return
        if tool == "zoom":
            nz = clamp(self.zoom * (0.7 if pygame.key.get_mods() & pygame.KMOD_ALT else 1.4), 0.02, 8)
            self.ox, self.oy = mx - (mx - self.ox) * nz / self.zoom, my - (my - self.oy) * nz / self.zoom
            self.zoom, self.view_fit = nz, False
            return
        if tool == "select_level":
            o = self.pick(mx, my)
            if o and o.owner:
                self.sel = list(o.owner.items)
                self.msg(f"Selected the whole level ({len(self.sel)} shapes)")
            return
        if tool == "bone":
            return self.start_bone(mx, my)
        if tool == "eraser":
            rl = self.raster_target()
            if rl:
                return self.start_paint(rl, mx, my, True)
            self.msg("The eraser works on raster layers - create one with + in the timeline")
            return
        if tool == "bone_ik":
            o = self.pick(mx, my)
            if o:
                self.create_ik(o)
            else:
                self.msg("Click the lower bone of a two-bone chain")
            return
        if tool == "bone_anim":
            return self.bone_anim_click(mx, my)
        if tool in ("pen", "multiline", "text", "taper", "lipsync", "view_rotate"):
            self.msg(f"{TOOL_INFO[tool][0]}: coming soon")
            return
        if tool == "anchor":
            return self.start_anchor(mx, my)
        p0 = self.psel
        if p0 and len(self.sel) == 1 and not p0.locked and p0.kind not in ("vlayer", "rlayer", "bone") and not self.link_mode:
            wx, wy = self.world(p0, self.frame)[:2]
            ax_, ay_ = self.a2s(wx, wy)
            if math.hypot(mx - ax_, my - ay_) <= 6:                    # the little cross is the anchor point
                return self.start_anchor(mx, my)
        rc_ = next((c for c in self.sel if c.kind == "ctrl_rot" and not c.locked), None)
        if rc_ is not None and tool in ("select", "transform", "animate"):
            pk = self.pick(mx, my)
            if pk is None or pk is rc_:                              # a rotation controller turns when you drag from anywhere
                return self.start_rotate(rc_, key=self.auto_key)
        hh = self.handle_hit(mx, my) if not (self.psel and self.psel.kind == "bone") else None
        if hh:
            if hh[0] == "radius":
                return self.start_radius(self.psel)
            if hh[0] == "tip":
                return self.start_tip(self.psel)
            return self.start_resize(self.psel, hh[1]) if hh[0] == "resize" else self.start_rotate(self.psel)
        o = self.pick(mx, my)
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
        if self.link_mode:
            if o and self.psel and o is not self.psel:
                for c in self.sel:
                    if c is not o:
                        self.link(c, o)
            self.link_mode = False
            return
        if o is None:
            return self.start_marquee(mx, my, bool(shift))
        if shift:
            self.select(o, add=True)
            return
        if o.kind == "bone":                                         # Select only selects bones (Delete removes them)
            self.sel = [o] if o not in self.sel else self.sel
            return
        if o.kind == "ctrl_rot":
            self.sel = [o]
            return self.start_rotate(o, key=self.auto_key)
        if o not in self.sel:
            self.sel = [o]
        return self.start_move(mx, my)

    def start_move(self, mx, my):
        items = [(o, *self.world(o, self.frame)[:2]) for o in self.sel if not o.locked]
        if not items:
            return
        self.autoscroll = "view"
        self._move_undo = [(o_, dict(o_.base), {p: dict(o_.keys[p]) for p in PROPS}) for o_, *_ in items]
        axis = [None]
        a0x, a0y = self.s2a(mx, my)
        pts = [self.s2a(*q) for q in self.box_pts(items[0][0], 0)]
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        c0, hw, hh = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2), (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2
        lines_x, lines_y = [0, self.aw / 2, self.aw], [0, self.ah / 2, self.ah]
        for o in self.all_pickables():                       # magnet targets (used while Ctrl is held)
            if o not in self.sel and o.visible and self.in_range(o):
                q = [self.s2a(*z) for z in self.box_pts(o, 0)]
                x1, x2, y1, y2 = min(z[0] for z in q), max(z[0] for z in q), min(z[1] for z in q), max(z[1] for z in q)
                lines_x += [x1, (x1 + x2) / 2, x2]
                lines_y += [y1, (y1 + y2) / 2, y2]

        def snap(vals, lines, tol):
            best = 0.0
            for v in vals:
                for ln in lines:
                    if abs(ln - v) <= tol and (best == 0.0 or abs(ln - v) < abs(best)):
                        best = ln - v
            return best

        def drag(mx, my):
            ax, ay = self.s2a(mx, my)
            dx, dy = ax - a0x, ay - a0y
            m = pygame.key.get_mods()
            if m & pygame.KMOD_SHIFT:                          # one axis only - decided once, then it stays
                if axis[0] is None and max(abs(dx), abs(dy)) > 6 / self.zoom:
                    axis[0] = "x" if abs(dx) >= abs(dy) else "y"
                dx, dy = (dx if axis[0] == "x" else 0), (dy if axis[0] == "y" else 0)
            else:
                axis[0] = None
            if m & (pygame.KMOD_CTRL | pygame.KMOD_META):      # magnet to edges, centres and the artboard
                tol = 8 / self.zoom
                dx += snap([c0[0] + dx - hw, c0[0] + dx, c0[0] + dx + hw], lines_x, tol)
                dy += snap([c0[1] + dy - hh, c0[1] + dy, c0[1] + dy + hh], lines_y, tol)
            for o, x0, y0 in items:
                self.set_world_pos(o, round(x0 + dx), round(y0 + dy))
        return drag

    def snap_point(self, o, ax, ay):
        c = [self.s2a(*p) for p in self.box_pts(o, 0)]
        c += [((c[i][0] + c[(i + 1) % 4][0]) / 2, (c[i][1] + c[(i + 1) % 4][1]) / 2) for i in range(4)]
        c += [((c[0][0] + c[2][0]) / 2, (c[0][1] + c[2][1]) / 2), (self.aw / 2, self.ah / 2)]
        best = min(c, key=lambda p: math.hypot(p[0] - ax, p[1] - ay))
        return best if math.hypot(best[0] - ax, best[1] - ay) < 14 / self.zoom else (ax, ay)

    def start_anchor(self, mx, my):
        o = self.psel
        if not o or o.locked or o.kind in ("vlayer", "rlayer"):
            o = self.pick(mx, my)
            if not o:
                self.msg("Select an object first, then drag its anchor point")
                return
            self.select(o)

        def place(mx, my):
            ax, ay = self.s2a(mx, my)
            if pygame.key.get_mods() & (pygame.KMOD_CTRL | pygame.KMOD_META):
                ax, ay = self.snap_point(o, ax, ay)
            x, y, s, r = self.world(o, self.frame)
            a, A = math.radians(r), o.anchor
            cxw = x + (-A[0] * math.cos(a) + A[1] * math.sin(a)) * s          # box centre in the world
            cyw = y + (-A[0] * math.sin(a) - A[1] * math.cos(a)) * s
            dx, dy = ax - cxw, ay - cyw
            o.anchor = ((dx * math.cos(a) + dy * math.sin(a)) / s, (-dx * math.sin(a) + dy * math.cos(a)) / s)
            self.set_world_pos(o, ax, ay)
        place(mx, my)
        return place

    def start_resize(self, o, idx):
        sx, sy = HSIGN[idx]
        wx, wy, s, r = self.world(o, self.frame)
        a = math.radians(r)
        ca, sa = math.cos(a), math.sin(a)
        w0, h0 = o.w, o.h
        anc = (-sx * w0 / 2, -sy * h0 / 2)
        jp = self.joy_parts(o)
        if jp:                                              # joystick: frame and knob always scale together, proportionally
            fr, kn = jp
            orig = (fr.w, fr.h, kn.w, kn.h, kn.limit)

            def jdrag(mx, my):
                ax, ay = self.s2a(mx, my)
                dx, dy = ax - wx, ay - wy
                lx, ly = (dx * ca + dy * sa) / s, (-dx * sa + dy * ca) / s
                k = clamp(max(abs(lx) / (w0 / 2) if sx else 0, abs(ly) / (h0 / 2) if sy else 0), 0.2, 6)
                fr.w, fr.h, kn.w, kn.h = orig[0] * k, orig[1] * k, orig[2] * k, orig[3] * k
                kn.limit = tuple(v * k for v in orig[4])
            return jdrag

        def drag(mx, my):
            ax, ay = self.s2a(mx, my)
            dx, dy = ax - wx, ay - wy
            lx, ly = (dx * ca + dy * sa) / s, (-dx * sa + dy * ca) / s
            lx += o.anchor[0]                           # work relative to the box centre
            ly += o.anchor[1]
            alt = bool(pygame.key.get_mods() & pygame.KMOD_ALT)       # Alt = scale from the centre
            ref, fac = ((0.0, 0.0), 2) if alt else (anc, 1)
            nw = max(4.0, abs(lx - ref[0]) * fac) if sx else w0
            nh = max(4.0, abs(ly - ref[1]) * fac) if sy else h0
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:      # proportional
                if sx and sy:
                    k = max(nw / w0, nh / h0)
                    nw, nh = w0 * k, h0 * k
                elif sx:
                    nh = h0 * nw / w0
                else:
                    nw = w0 * nh / h0
            cl = (0, 0) if alt else (anc[0] + sx * nw / 2 if sx else 0, anc[1] + sy * nh / 2 if sy else 0)
            o.w, o.h = nw, nh
            self.set_world_pos(o, wx + (cl[0] * ca - cl[1] * sa) * s, wy + (cl[0] * sa + cl[1] * ca) * s)
        return drag

    def start_rotate(self, o, key=False):
        wx, wy, _, _ = self.world(o, self.frame)
        r0 = o.value("rotation", self.frame)
        ax0, ay0 = self.s2a(*pygame.mouse.get_pos())
        a0 = math.atan2(ay0 - wy, ax0 - wx)
        self.rotating = True

        def drag(mx, my):
            ax, ay = self.s2a(mx, my)
            v = r0 + math.degrees(math.atan2(ay - wy, ax - wx) - a0)
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:      # 45 degree steps
                v = round(v / 45) * 45
            if key and "rotation" not in self.locked_props(o) and not o.locked:     # Animate Bones always writes a keyframe
                o.keys["rotation"][int(self.frame)] = round(v, 1)
            else:
                self.set_prop(o, "rotation", round(v, 1))

        def end():
            self.rotating = False
        self.drag_end = end
        return drag

    def start_marquee(self, mx, my, add):
        base = list(self.sel) if add else []
        self.sel = list(base)
        x0, y0 = mx, my
        self.marquee = (x0, y0, mx, my)

        def drag(mx, my):
            self.marquee = (x0, y0, mx, my)

        def end():
            x1, y1, x2, y2 = self.marquee
            self.marquee = None
            rc = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            hit = []
            for o in self.all_pickables():
                if o.visible and not o.locked:
                    p = self.box_pts(o, 0)
                    b = pygame.Rect(min(q[0] for q in p), min(q[1] for q in p),
                                    max(q[0] for q in p) - min(q[0] for q in p),
                                    max(q[1] for q in p) - min(q[1] for q in p))
                    if rc.w + rc.h > 4 and rc.colliderect(b) and o not in base:
                        hit.append(o)
            self.sel = base + hit
        self.drag_end = end
        return drag

    def start_shape(self, tool, mx, my):
        x0, y0 = self.s2a(mx, my)
        o = self.new_item(tool, x0, y0, w=1, h=1)

        def drag(mx, my):
            bx, by = self.s2a(mx, my)
            dx, dy = bx - x0, by - y0
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                if tool == "line":
                    L, ang = math.hypot(dx, dy), round(math.atan2(dy, dx) / (math.pi / 4)) * math.pi / 4
                    dx, dy = L * math.cos(ang), L * math.sin(ang)
                else:
                    m = max(abs(dx), abs(dy))
                    dx, dy = m * (1 if dx >= 0 else -1), m * (1 if dy >= 0 else -1)
            if pygame.key.get_mods() & pygame.KMOD_ALT:           # Alt = draw from the centre
                o.w, o.h = max(1.0, 2 * abs(dx)), max(1.0, 2 * abs(dy))
                self.put_base(o, x0, y0)
            else:
                o.w, o.h = max(1.0, abs(dx)), max(1.0, abs(dy))
                self.put_base(o, x0 + dx / 2, y0 + dy / 2)
            if tool == "line":
                o.pts = [(-.5, -.5), (.5, .5)] if dx * dy >= 0 else [(-.5, .5), (.5, -.5)]

        def end():
            if o.w < 4 and o.h < 4:
                o.w, o.h = (200.0, 1.0) if tool == "line" else (200.0, 200.0)
            self.set_tool("select")
        self.drag_end = end
        return drag

    def bone_end(self, b):
        x, y, s, r = self.world(b, self.frame)
        a = math.radians(r)
        return x + math.cos(a) * b.w * s, y + math.sin(a) * b.w * s

    def start_bone(self, mx, my):
        x0, y0 = self.s2a(mx, my)
        parent = None
        if self.bone_chain and self.bone_last in self.objs:      # chain: every new bone starts on the tip of the last one
            (x0, y0), parent = self.bone_end(self.bone_last), self.bone_last
        o = self.new_obj("bone", x0, y0, w=1, h=8)

        def drag(mx, my):
            bx, by = self.s2a(mx, my)
            dx, dy = bx - x0, by - y0
            L = max(1.0, math.hypot(dx, dy))
            o.w, o.h = L, clamp(L * 0.16, 8, 20)
            o.anchor = (-L / 2, 0.0)                              # pivot = the joint at the start of the bone
            o.base["x"], o.base["y"] = round(x0, 1), round(y0, 1)
            o.base["rotation"] = round(math.degrees(math.atan2(dy, dx)), 1)

        def end():
            if o.w < 8:
                self.objs.remove(o)
                self.sel = []
                return
            if parent:
                self.link(o, parent, quiet=True)
            self.bone_last, self.bone_chain = o, True
            self.msg("Bone added - click to continue the chain; Esc or another tool ends it")
        self.drag_end = end
        if parent:
            drag(mx, my)                                          # a single click places the bone straight away
        return drag

    def draw_brush_opts(self, v):
        items = [("auto_close", "Auto close"), ("auto_fill", "Auto fill"), ("draw_under", "Draw under")]
        hints = {"auto_close": "Close every new stroke into a shape", "auto_fill": "Close and fill every new stroke with the fill colour",
                 "draw_under": "New strokes go under the existing ones in the layer"}
        w = sum(self.f12.size(n)[0] + 40 for _, n in items) + 112 + 120
        self.rrect((v.x + 8, v.y + 8, w, 32), (30, 30, 34), 12)
        cx = v.x + 20
        for k, n in items:
            self.checkbox(cx, v.y + 16, self.brush_opts[k], lambda mx, my, k=k: self.brush_opts.__setitem__(k, not self.brush_opts[k]), hints[k])
            self.txt(n, cx + 24, v.y + 16)
            cx += self.f12.size(n)[0] + 40
        self.txt("Size", cx, v.y + 16, self.f11, COLOR_MUTED)
        self.field((cx + 36, v.y + 12, 48, 24), self.brush_px, lambda val: setattr(self, "brush_px", int(clamp(val, 1, 200))),
                   "brush_px", numeric=True, center=True, hint="Brush size (also the line width)")
        self.txt("Smooth", cx + 100, v.y + 16, self.f11, COLOR_MUTED)
        self.field((cx + 148, v.y + 12, 48, 24), self.brush_smooth, lambda val: setattr(self, "brush_smooth", int(clamp(val, 0, 100))),
                   "brush_smooth", numeric=True, center=True, hint="0-100: the higher, the calmer the line (less hand jitter)")

    def bone_anim_click(self, mx, my):
        """A bone and every drawing that follows it are ONE element. Click any of them: the bone gets the keyframe."""
        ax, ay = self.s2a(mx, my)
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:              # Shift + click on a joint: pin / unpin it
            for b in self.objs:
                if b.kind == "bone":
                    jx, jy = self.world(b, self.frame)[:2]
                    if math.hypot(jx - ax, jy - ay) * self.zoom <= 10:
                        b.pin = not b.pin
                        self.msg(f"Joint {b.name} {'pinned (rotation locked)' if b.pin else 'unpinned'}")
                        return
        o = self.pick(mx, my)
        if o and (o.kind.startswith("ctrl") or o.limit):          # IK controllers and joysticks are animated with the same tool
            self.sel = [o]
            return self.start_rotate(o, key=True) if o.kind == "ctrl_rot" else self.start_move(mx, my)
        b = self.pick_bone(mx, my)
        if not b:
            self.msg("Animate Bones: click a bone, an IK controller or a drawing that follows a bone")
            return
        if b.ik:                                                     # a limb with IK is posed by its controller
            c = self.find(b.ik.get("target") or "")
            if c:
                self.sel = [c]
                return self.start_move(mx, my)
        if b.pin:
            self.msg(f"{b.name} is pinned - Shift+click its joint to unpin")
            return
        self.sel = [b]
        return self.start_rotate(b, key=True)

    def pick_bone(self, mx, my):
        o = self.pick(mx, my)
        o = (o.owner or o) if o else None
        while o is not None and o.kind != "bone":
            o = o.parent
        return o

    def tool_filter(self, o):
        if self.single_layer and self.psel is not None and self.tool in ("select", "transform", "animate"):
            if (o.owner or o) is not (self.psel.owner or self.psel):      # only the selected layer can be picked
                return False
        if self.tool in ("bone_ik", "bone_edit"):                # the bone tools only ever touch bones
            return o.kind == "bone"
        if self.tool != "animate":
            return True
        isp = o.kind == "peg"
        isc = o.kind.startswith("ctrl") or bool(o.limit) or o.kind in ("pill", "rsquare")
        f = self.animate_filter
        return (f == "peg" and isp) or (f == "ctrl" and isc) or (f == "both" and (isp or isc))

    def draw_select_opts(self, v):
        self.rrect((v.x + 8, v.y + 8, 214, 32), (30, 30, 34), 16)
        self.layer_lock_checkbox(v.x + 20, v.y + 16)

    def layer_lock_checkbox(self, x, y):
        self.checkbox(x, y, self.single_layer, lambda mx, my: setattr(self, "single_layer", not self.single_layer),
                      "Work only inside the selected layer: nothing else can be clicked by accident (like Photoshop's Auto-Select)")
        self.txt("Only this layer", x + 24, y)

    def draw_animate_opts(self, v):
        self.rrect((v.x + 8, v.y + 8, 450, 32), (30, 30, 34), 16)
        self.layer_lock_checkbox(v.x + 316, v.y + 16)
        for i, (key, n) in enumerate((("peg", "Pegs"), ("ctrl", "Controllers"), ("both", "Both"))):
            self.button((v.x + 14 + i * 96, v.y + 12, 90, 24), n, lambda mx, my, key=key: setattr(self, "animate_filter", key),
                        active=self.animate_filter == key, font=self.f11, hint="Animate tool: only these can be selected and moved")

    def start_tip(self, o):
        """Drag the ball at the end of a bone: its bend and length change, the joint (anchor) stays where it is."""
        x, y, s, r = self.world(o, self.frame)
        pr = self.world(o.parent, self.frame)[3] if o.parent else 0.0
        w0 = o.w
        kids = [c for c in self.objs if c.parent is o and abs(c.base["x"] - w0) < 0.5 and abs(c.base["y"]) < 0.5]

        def drag(mx, my):
            ax, ay = self.s2a(mx, my)
            dx, dy = ax - x, ay - y
            L = max(8.0, math.hypot(dx, dy) / s)
            if "rotation" not in self.locked_props(o):
                o.set_value("rotation", self.frame, round(math.degrees(math.atan2(dy, dx)) - pr, 1))
            o.w, o.h, o.anchor = L, clamp(L * 0.16, 8, 20), (-L / 2, 0.0)
            for c in kids:                                           # the next bone stays attached to the tip
                c.base["x"] = L
        return drag

    def layer_union(self, o, pad=4):
        pts = [q for it in o.items if it.visible for q in self.box_pts(it, pad)]
        if not pts:
            return None
        x1, x2, y1, y2 = min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts)
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    def canvas_menu(self, mx, my):
        o = self.pick(mx, my)
        if o and o not in self.sel:
            self.sel = [o]
        items = []
        if o and (o.owner or o).kind == "vlayer":
            items.append(("Edit drawing without the rig", lambda: self.enter_rest_edit(o)))
        if self.sel:
            items += [("Cut  (Ctrl+X)", self.cut_sel), ("Copy  (Ctrl+C)", self.copy_sel)]
        items.append(("Paste  (Ctrl+V)", lambda: self.paste((mx, my))))
        if self.sel:
            items += [("Duplicate  (Ctrl+D)", self.duplicate_selected), ("Move to new layer", self.move_to_new_layer),
                      ("Delete", self.delete_selected)]
        self.ctx = {"pos": (mx, my), "items": items}

    def draw_fill_opts(self, v):
        x = v.x + 8
        self.rrect((x, v.y + 8, 320, 32), (30, 30, 34), 12)
        cx = x + 8
        for key, items in (("target", (("fill", "Fill"), ("stroke", "Stroke"), ("all", "All"))),
                           ("mode", (("click", "Click"), ("rect", "Rect"), ("lasso", "Lasso")))):
            for val, n in items:
                self.button((cx, v.y + 12, 48, 24), n, lambda mx, my, key=key, val=val: self.fill_opts.__setitem__(key, val),
                            active=self.fill_opts[key] == val, radius=12, font=self.f11,
                            hint="Fill bucket: what to fill" if key == "target" else "Fill bucket: how to choose the area (rect / lasso coming soon)")
                cx += 52
            cx += 8

    def cut_layer(self, layer, f):
        end = layer.t_out or self.total
        if not (layer.t_in < f < end):
            self.msg("Put the playhead inside the layer (not on its first / last frame) to cut it")
            return
        n = Obj.from_dict(layer.to_dict())
        n.name, n.parent = self.unique_name(layer.name + " cut"), layer.parent
        if layer.surf is not None:
            n.surf = layer.surf.copy()
        n.t_in, n.t_out, layer.t_out = f + 1, layer.t_out, f
        self.objs.insert(self.objs.index(layer), n)
        self.sel = [n]
        self.msg(f"Cut {layer.name} at frame {f}")

    def raster_target(self):
        p = self.psel
        if p and p.kind == "rlayer" and not p.locked:
            return p
        if p is None or (not p.owner and p.kind != "vlayer"):
            a = self.active_layer
            if a and a.kind == "rlayer" and a in self.objs and not a.locked:
                return a
        return None

    def start_paint(self, rl, mx, my, erase=False):
        """Paint (or erase) pixels on a raster layer."""
        col = (0, 0, 0, 0) if erase else (*self.def_fill, 255)
        wpx = max(1, self.brush_px * (2 if erase else 1))
        last = [self.art_to_layer(rl, *self.s2a(mx, my))]

        def stamp(p0, p1):
            pygame.draw.line(rl.surf, col, p0, p1, wpx)
            pygame.draw.circle(rl.surf, col, (int(p1[0]), int(p1[1])), max(1, wpx // 2))
            rl.rver = getattr(rl, "rver", 0) + 1

        def drag(mx, my):
            p = self.art_to_layer(rl, *self.s2a(mx, my))
            stamp(last[0], p)
            last[0] = p
        stamp(last[0], last[0])
        return drag

    def start_brush(self, mx, my):
        rl = self.raster_target()
        if rl is not None:
            return self.start_paint(rl, mx, my)
        self.brush_pts = [self.s2a(mx, my)]

        def drag(mx, my):
            p = self.s2a(mx, my)
            lp = self.brush_pts[-1]
            if math.hypot(p[0] - lp[0], p[1] - lp[1]) > 3 / self.zoom:
                self.brush_pts.append(p)

        def end():
            pts, self.brush_pts = self.brush_pts, None
            if len(pts) < 2:
                return
            pts = self.smooth_stroke(pts, self.brush_smooth)
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            w, h = max(1.0, max(xs) - min(xs)), max(1.0, max(ys) - min(ys))
            cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
            o = self.new_item("brush", cx, cy, w=w, h=h)
            o.pts = [((x - cx) / w, (y - cy) / h) for x, y in pts]
            o.stroke_w = self.brush_px                           # the brush size is the line width
            op = self.brush_opts
            if op["auto_close"] or op["auto_fill"]:
                o.closed = True
            if op["auto_fill"]:
                o.fill_on, o.fill = True, self.def_fill
            if op["draw_under"]:                                  # new strokes go below the others in the layer
                o.owner.items.remove(o)
                o.owner.items.append(o)
        self.drag_end = end
        return drag

    # --------------------------------------------------------------- drawing
    def draw_alpha(self, pts, alpha, fn, pad=4):
        if alpha >= 99.5:
            fn(self.screen, pts)
            return
        if alpha <= 0.5 or not pts:
            return
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        r = pygame.Rect(int(min(xs)) - pad, int(min(ys)) - pad, int(max(xs) - min(xs)) + 2 * pad + 1,
                        int(max(ys) - min(ys)) + 2 * pad + 1)
        if r.w > 4000 or r.h > 4000:
            fn(self.screen, pts)
            return
        sf = pygame.Surface(r.size, pygame.SRCALPHA)
        fn(sf, [(p[0] - r.x, p[1] - r.y) for p in pts])
        sf.set_alpha(int(alpha * 2.55))
        self.screen.blit(sf, r.topleft)

    def matte_sources(self):
        """Matte layers that stay hidden (unless a masked layer asks to show its matte)."""
        used = {x.matte for x in self.objs if x.matte}
        shown = {x.matte for x in self.objs if x.matte and x.matte_show}
        return used - shown

    def draw_layer(self, o, f=None):
        """Draw a layer; with a track matte the layer is multiplied by the alpha of its matte layer."""
        f = f or self.frame
        mt = self.find(o.matte) if o.matte else None
        if not mt or mt is o:
            self.draw_tree(o, f)
            return
        saved, size = self.screen, self.screen.get_size()
        la, ma = pygame.Surface(size, pygame.SRCALPHA), pygame.Surface(size, pygame.SRCALPHA)
        try:
            self.screen = la
            self.draw_tree(o, f)
            self.screen = ma
            self.draw_tree(mt, f)
        finally:
            self.screen = saved
        ma.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)          # white, keeps the matte's alpha
        if o.matte_inv:
            inv = pygame.Surface(size, pygame.SRCALPHA)
            inv.fill((255, 255, 255, 255))
            inv.blit(ma, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
            inv.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
            ma = inv
        la.blit(ma, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        saved.blit(la, (0, 0))

    def draw_ctrl(self, o, f, x, y, s, rot, op):
        """Linear controllers: arrows (position) and / or a rotation arc."""
        col, R, d = o.fill, o.w / 2, pygame.draw

        def P(px, py):
            return self.a2s(*self.xf(x, y, s, rot, px, py))

        def seg(a, b):
            d.line(self.screen, col, P(*a), P(*b), 4)
        k = o.kind
        tip = R * (0.62 if k == "ctrl_posrot" else 0.95)
        if k in ("ctrl", "ctrl_posrot"):
            for ang in (0, 90, 180, 270):
                c, sn = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                seg((c * 0.12 * R, sn * 0.12 * R), (c * tip, sn * tip))
                for da in (150, -150):
                    a2 = math.radians(ang + da)
                    seg((c * tip, sn * tip), (c * tip + math.cos(a2) * 0.26 * R, sn * tip + math.sin(a2) * 0.26 * R))
        if k in ("ctrl_rot", "ctrl_posrot"):
            rr = R * (0.92 if k == "ctrl_posrot" else 0.8)
            d.lines(self.screen, col, False, [P(rr * math.cos(math.radians(a)), rr * math.sin(math.radians(a))) for a in range(-150, 71, 10)], 4)
            ae = math.radians(70)
            ex, ey, tg = rr * math.cos(ae), rr * math.sin(ae), math.atan2(math.cos(ae), -math.sin(ae))
            for da in (150, -150):
                a2 = tg + math.radians(da)
                seg((ex, ey), (ex + math.cos(a2) * 0.26 * R, ey + math.sin(a2) * 0.26 * R))
        cx, cy = self.a2s(x, y)
        d.circle(self.screen, col, (int(cx), int(cy)), 4)

    def draw_tree(self, o, f=None, ghost=None):
        f = f or self.frame
        if o.kind == "vlayer":
            for it in reversed(o.items_at(f)):
                if it.visible:
                    self.draw_obj(it, f, ghost)
        else:
            self.draw_obj(o, f, ghost)

    def draw_raster(self, o, f):
        if o.surf is None:
            return
        x, y, s, rot = self.world(o, f)
        op = clamp(self.val(o, "opacity", f) / 100, 0, 1)
        tw, th = int(o.w * s * self.zoom), int(o.h * s * self.zoom)
        if tw < 1 or th < 1 or tw > 4096 or th > 4096:
            return
        key = (id(o.surf), tw, th, getattr(o, "rver", 0))
        sc = self.scaled_cache.get(key)
        if sc is None:
            if len(self.scaled_cache) > 60:
                self.scaled_cache.clear()
            sc = self.scaled_cache[key] = o.surf if (tw, th) == o.surf.get_size() else pygame.transform.smoothscale(o.surf, (tw, th))
        img = pygame.transform.rotate(sc, -rot) if rot else sc
        if op < 0.99:
            img = img.copy()
            img.set_alpha(int(op * 255))
        cx, cy = self.a2s(x, y)
        self.screen.blit(img, img.get_rect(center=(int(cx), int(cy))))

    def draw_obj(self, o, f=None, ghost=None):
        f = f or self.frame
        if o.kind == "vlayer":
            return
        if o.kind == "rlayer":
            self.draw_raster(o, f)
            return
        pts, closed = self.obj_pts(o, f)
        if ghost:                                                     # onion skin: the drawing's own line width, soft and translucent
            s_ = self.world(o, f)[2]
            gw = max(2, int(o.stroke_w * self.zoom * s_)) if o.stroke_on else 0
            soft = (int(ghost[0] * 0.8), int(ghost[1] * 0.8), int(ghost[2] * 0.8))
            if gw and len(pts) >= 2:
                self.draw_alpha(pts, 55, lambda sf, p: pygame.draw.lines(sf, soft, closed, p, gw), pad=gw + 2)
            elif len(pts) >= 3 and (closed or o.fill_on):             # a patch without a line: a calm translucent blob
                self.draw_alpha(pts, 40, lambda sf, p: pygame.draw.polygon(sf, soft, p), pad=4)
            return
        x, y, s, rot = self.world(o, f)
        op = clamp(self.val(o, "opacity", f) / 100, 0, 1)
        if o.owner:
            op *= clamp(self.val(o.owner, "opacity", f) / 100, 0, 1)
        if False and o.kind == "peg":                                  # a peg is a transform-only parent (never rendered)
            cx, cy = self.a2s(x, y)
            col, rr = self.label_color(o), max(6, int(12 * s * self.zoom))
            pygame.draw.circle(self.screen, col, (int(cx), int(cy)), rr, 2)
            pygame.draw.line(self.screen, col, (cx - rr - 3, cy), (cx + rr + 3, cy))
            pygame.draw.line(self.screen, col, (cx, cy - rr - 3), (cx, cy + rr + 3))
            return
        if o.kind.startswith("ctrl"):
            self.draw_ctrl(o, f, x, y, s, rot, op)
            return
        if o.kind == "image":
            self.draw_image(o, f, x, y, s, rot, op)
            return
        if closed and o.fill_on and o.kind not in ("null", "peg"):
            self.draw_alpha(pts, o.fill_a * op, lambda sf, p: pygame.draw.polygon(sf, o.fill, p))
        if o.kind in ("null", "peg") and o not in self.sel:         # selected nulls show the selection box instead
            cx, cy = self.a2s(x, y)                       # a null looks like a bare bounding box
            col = shade(self.label_color(o), 0.5)                 # not selected: dimmed, so the selected one stands out
            pygame.draw.lines(self.screen, col, True, pts, 1)          # a plain square frame: no anchor, no resize squares
        if o.stroke_on:
            w = max(1, int(o.stroke_w * s * self.zoom))

            def stroke(sf, p):
                pygame.draw.lines(sf, o.stroke, closed, p, w)
                if w >= 3:
                    for q in p:
                        pygame.draw.circle(sf, o.stroke, (int(q[0]), int(q[1])), w // 2)
            self.draw_alpha(pts, o.stroke_a * op, stroke, pad=w + 2)
        if o.kind == "bone":                                 # joints at both ends
            for lx_ in (0, o.w):
                jx, jy = self.a2s(*self.xf(x, y, s, rot, lx_, 0))
                pygame.draw.circle(self.screen, o.stroke, (int(jx), int(jy)), max(3, int(5 * self.zoom * s)), 2)
                if lx_ == 0 and o.pin:                               # pinned joint: a small yellow square
                    pygame.draw.rect(self.screen, (255, 205, 60), (int(jx) - 5, int(jy) - 5, 10, 10))
                    pygame.draw.rect(self.screen, (40, 40, 40), (int(jx) - 5, int(jy) - 5, 10, 10), 1)

    def draw_image(self, o, f, x, y, s, rot, op):
        sf = self.footage_surface(o, f)
        cx, cy = self.a2s(x, y)
        tw, th = int(o.w * s * self.zoom), int(o.h * s * self.zoom)
        if sf is None or tw < 1 or th < 1 or tw > 4096 or th > 4096:
            pts, _ = self.obj_pts(o, f)
            pygame.draw.lines(self.screen, (160, 80, 80), True, pts, 1)          # missing / unsupported footage
            return
        key = (id(sf), tw, th)
        sc = self.scaled_cache.get(key)
        if sc is None:
            if len(self.scaled_cache) > 60:
                self.scaled_cache.clear()
            sc = self.scaled_cache[key] = pygame.transform.smoothscale(sf, (tw, th))
        img = pygame.transform.rotate(sc, -rot) if rot else sc
        if op < 0.99:
            img = img.copy()
            img.set_alpha(int(op * 255))
        self.screen.blit(img, img.get_rect(center=(int(cx), int(cy))))

    def eye_icon(self, cx, cy, col):
        pygame.draw.ellipse(self.screen, col, (cx - 8, cy - 5, 16, 10), 2)
        pygame.draw.circle(self.screen, col, (cx, cy), 2)

    def lock_icon(self, cx, cy, col, locked):
        pygame.draw.rect(self.screen, col, (cx - 5, cy - 1, 10, 7), border_radius=2)
        if locked:                                           # closed padlock
            pygame.draw.arc(self.screen, col, (cx - 3, cy - 7, 6, 10), 0, math.pi, 2)
        else:                                                # open padlock: the shackle is lifted and swung aside
            pygame.draw.arc(self.screen, col, (cx + 1, cy - 9, 6, 10), 0, math.pi, 2)
            pygame.draw.line(self.screen, col, (cx + 1, cy - 4), (cx + 1, cy - 1), 2)

    def draw_canvas(self):
        v = self.r_view
        self.rrect(v, COLOR_VIEWPORT, 8)
        self.hit(v, self.canvas_click, (1, 2))
        self.hit(v, self.canvas_menu, (3,))
        prev = self.push_clip(v)
        ax0, ay0 = self.a2s(0, 0)
        ab = pygame.Rect(int(ax0), int(ay0), int(self.aw * self.zoom), int(self.ah * self.zoom))
        pygame.draw.rect(self.screen, self.art_color, ab)
        src = self.matte_sources()
        for o in reversed(self.objs):
            if o.visible and self.in_range(o) and o.name not in src and not (self.view["render"] and (not o.render or o.kind in ("null", "peg", "bone") or o.kind.startswith("ctrl") or self.is_controller(o))) and (self.rest_layer is None or o is self.rest_layer):
                self.draw_layer(o)
                if o.caption:                                  # slider / controller name above the object
                    bp = self.box_pts(o, 6)
                    self.txt(o.caption, sum(p[0] for p in bp) / 4, min(p[1] for p in bp) - 16, self.f11, o.caption_color or (230, 230, 235), center=True)
        if self.view.get("camera"):                                  # camera view: nothing outside the artboard
            vr = self.r_view
            for rc in (pygame.Rect(vr.x, vr.y, vr.w, ab.y - vr.y), pygame.Rect(vr.x, ab.bottom, vr.w, vr.bottom - ab.bottom),
                       pygame.Rect(vr.x, ab.y, ab.x - vr.x, ab.h), pygame.Rect(ab.right, ab.y, vr.right - ab.right, ab.h)):
                if rc.w > 0 and rc.h > 0:
                    pygame.draw.rect(self.screen, COLOR_VIEWPORT, rc)
        o_ = self.psel                                              # a rectangle shows round white dots at its corners: drag = round the corners
        if o_ is not None and o_.kind == "rect" and len(self.sel) == 1 and not o_.locked and self.rest_layer is None:
            mp = pygame.mouse.get_pos()
            for dp in self.radius_dots(o_):
                if getattr(self, "radius_drag", False) or math.hypot(mp[0] - dp[0], mp[1] - dp[1]) < 70:
                    pygame.draw.circle(self.screen, (255, 255, 255), (int(dp[0]), int(dp[1])), 5)
                    pygame.draw.circle(self.screen, (30, 30, 30), (int(dp[0]), int(dp[1])), 5, 1)
        if self.view["onion"]:
            scope = set()                                          # onion skin: only the selected layers and the layers parented to them
            for s_ in self.sel:
                l_ = s_.owner or s_
                scope.add(id(l_))
                scope.update(id(d_) for d_ in self.descendants(l_))
            for o in self.objs:
                if id(o) in scope and o.visible and not o.kind.startswith("ctrl") and o.kind not in ("null", "peg"):
                    for k in range(1, self.onion["before"] + 1):
                        if self.frame - k >= 1:
                            self.draw_tree(o, self.frame - k, shade((205, 95, 95), 1.0 - (k - 1) * 0.2))
                    for k in range(1, self.onion["after"] + 1):
                        if self.frame + k <= self.total:
                            self.draw_tree(o, self.frame + k, shade((95, 185, 120), 1.0 - (k - 1) * 0.2))
        if self.view["safe"]:
            for k in (0.9, 0.8):
                pygame.draw.rect(self.screen, (90, 90, 90), (ab.centerx - ab.w * k / 2, ab.centery - ab.h * k / 2,
                                                            ab.w * k, ab.h * k), 1)
            pygame.draw.line(self.screen, (90, 90, 90), (ab.centerx - 8, ab.centery), (ab.centerx + 8, ab.centery))
            pygame.draw.line(self.screen, (90, 90, 90), (ab.centerx, ab.centery - 8), (ab.centerx, ab.centery + 8))
        if self.view["grid3"]:
            for i in (1, 2):
                pygame.draw.line(self.screen, (90, 90, 90), (ab.x + ab.w * i / 3, ab.y), (ab.x + ab.w * i / 3, ab.bottom))
                pygame.draw.line(self.screen, (90, 90, 90), (ab.x, ab.y + ab.h * i / 3), (ab.right, ab.y + ab.h * i / 3))
        if self.view["gray"]:
            try:
                rc = v.clip(self.screen.get_rect())
                self.screen.blit(pygame.transform.grayscale(self.screen.subsurface(rc).copy()), rc.topleft)
            except Exception:  # noqa
                pass
        # selection boxes
        for o in self.sel:
            if o.kind in ("vlayer", "rlayer"):               # a layer: one box that hugs what is drawn in it
                u = self.layer_union(o) if o.kind == "vlayer" else None
                if u:
                    pygame.draw.polygon(self.screen, self.label_color(o), u, 1)
                continue
            if o.visible:
                single = len(self.sel) == 1
                bb = self.label_color(o)                       # box colour = the layer's label colour
                pygame.draw.polygon(self.screen, bb, self.box_pts(o, 0 if o.kind in ("null", "peg") else (6 if single else 2)), 1)
                if single:
                    for p in ([] if o.kind.startswith("ctrl") or o.kind == "bone" else self.handle_points(o)):
                        self.rrect((p[0] - 3, p[1] - 3, 7, 7), bb, 2)
                    if o.kind == "bone":
                        tp = self.a2s(*self.bone_end(o))
                        pygame.draw.circle(self.screen, bb, (int(tp[0]), int(tp[1])), 6)
                        pygame.draw.circle(self.screen, (255, 255, 255), (int(tp[0]), int(tp[1])), 6, 1)
                    wx, wy, _, _ = self.world(o, self.frame)
                    cx, cy = self.a2s(wx, wy)
                    pygame.draw.line(self.screen, bb, (cx - 6, cy), (cx + 6, cy))
                    pygame.draw.line(self.screen, bb, (cx, cy - 6), (cx, cy + 6))
                    self.rrect((cx - 7, cy - 7, 14, 14), bb, 2, 1)           # square around the cross: the anchor is easy to spot
        # hover: navy outline + name tag
        h = self.hover
        if h and h.visible and (h.kind != "vlayer" or h.items) and h.kind != "rlayer" and not h.kind.startswith("ctrl"):
            bp = self.layer_union(h, 3) if h.kind == "vlayer" else self.box_pts(h, 3)
            pygame.draw.polygon(self.screen, COLOR_NAVY, bp, 2)
            lab = self.f11.render(h.owner.name if h.owner else h.name, True, (255, 255, 255))      # the layer's own name
            lr = pygame.Rect(0, 0, lab.get_width() + 16, lab.get_height() + 8)
            lr.midtop = (sum(p[0] for p in bp) / 4, max(p[1] for p in bp) + 8)
            self.rrect(lr, COLOR_TEAL if h in self.sel else COLOR_NAVY, 8)
            self.screen.blit(lab, (lr.x + 8, lr.y + 4))
        if self.tool == "bone" and self.bone_chain and self.bone_last in self.objs:      # rubber band from the last tip
            mp = pygame.mouse.get_pos()
            if v.collidepoint(mp):
                pygame.draw.line(self.screen, (239, 171, 200), self.a2s(*self.bone_end(self.bone_last)), mp, 1)
        if self.brush_pts and len(self.brush_pts) > 1:                # the live line: the real width, the chosen colour, the same smoothing
            sp = [self.a2s(*p) for p in self.smooth_stroke(self.brush_pts, self.brush_smooth)]
            bw = max(2, int(self.brush_px * self.zoom))
            pygame.draw.lines(self.screen, self.def_fill, False, sp, bw)
            if bw > 3:
                for q in (sp[0], sp[-1]):
                    pygame.draw.circle(self.screen, self.def_fill, (int(q[0]), int(q[1])), bw // 2)
        if self.marquee:
            x1, y1, x2, y2 = self.marquee
            rc = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            pygame.draw.rect(self.screen, BBOX_COL, rc, 1)
        self.pop_clip(prev)
        self.draw_view_icons(v)
        if self.tool == "brush":
            self.draw_brush_opts(v)
        elif self.tool == "fill":
            self.draw_fill_opts(v)
        elif self.tool == "animate":
            self.draw_animate_opts(v)
        elif self.tool in ("select", "transform"):
            self.draw_select_opts(v)
        if self.rest_layer is not None:                              # drawing view banner
            self.rrect((v.x + 8, v.y + 8, 430, 34), (30, 30, 34), 17)
            self.txt(f"Drawing view: {self.rest_layer.name} (no rig, no animation)", v.x + 20, v.y + 17, self.f11)
            self.button((v.x + 346, v.y + 12, 86, 26), "Exit (Esc)", lambda mx, my: setattr(self, "rest_layer", None), font=self.f11,
                        hint="Back to the rig view")

    def draw_view_icons(self, v):
        """View toggles in the top-right corner of the viewport."""
        items = [("render", "Render preview: show only layers enabled for render"), ("grid3", "Grid 3x3"),
                 ("safe", "Safe zone"), ("gray", "Grayscale"), ("onion", "Onion skin (selected layers and their children)"),
                 ("camera", "Camera view: hide everything outside the artboard"), ("threed", "3D view (coming soon)")]
        x = v.right - 8 - 32 * len(items)
        col, d = (235, 235, 235), pygame.draw
        for key, hint in items:
            rc = pygame.Rect(x, v.y + 8, 32, 32)
            if key == "threed":
                self.flat_button(rc, lambda mx, my: self.msg("3D view: coming soon"), hint, hover=False)
            else:
                self.flat_button(rc, lambda mx, my, k=key: self.view.__setitem__(k, not self.view[k]), hint + (" (right-click: frames shown)" if key == "onion" else ""), self.view[key], hover=False)
                if key == "onion":
                    self.hit(rc, lambda mx, my: setattr(self, "ctx", {"pos": (mx, my), "items": [(f"Previous frames: {n}", lambda n=n: self.onion.__setitem__("before", n)) for n in (0, 1, 2, 3, 5)] + [(f"Next frames: {n}", lambda n=n: self.onion.__setitem__("after", n)) for n in (0, 1, 2, 3, 5)]}), (3,))
            cx, cy = rc.center
            if key == "render":
                self.eye_icon(cx, cy, col)
            elif key == "grid3":
                d.rect(self.screen, col, (cx - 8, cy - 8, 16, 16), 2, border_radius=4)
                for o in (-3, 3):
                    d.line(self.screen, col, (cx + o, cy - 8), (cx + o, cy + 8))
                    d.line(self.screen, col, (cx - 8, cy + o), (cx + 8, cy + o))
            elif key == "safe":
                d.rect(self.screen, col, (cx - 9, cy - 7, 18, 14), 2, border_radius=4)
                d.rect(self.screen, col, (cx - 5, cy - 4, 10, 8), 1, border_radius=2)
            elif key == "gray":
                d.circle(self.screen, col, (cx, cy), 8, 2)
                d.circle(self.screen, col, (cx, cy), 8, 0, draw_top_left=True, draw_bottom_left=True)
            elif key == "camera":
                d.rect(self.screen, col, (cx - 9, cy - 5, 18, 13), 2, border_radius=3)
                d.circle(self.screen, col, (cx, cy + 1), 3, 2)
                d.rect(self.screen, col, (cx - 4, cy - 8, 8, 3))
            elif key == "onion":
                d.circle(self.screen, col, (cx - 3, cy), 6, 2)
                d.circle(self.screen, col, (cx + 3, cy), 6, 2)
            else:
                pts = [(cx, cy - 9), (cx + 8, cy - 4), (cx + 8, cy + 5), (cx, cy + 9), (cx - 8, cy + 5), (cx - 8, cy - 4)]
                d.lines(self.screen, col, True, pts, 2)
                d.lines(self.screen, col, False, [(cx - 8, cy - 4), (cx, cy + 1), (cx + 8, cy - 4)], 2)
                d.line(self.screen, col, (cx, cy + 1), (cx, cy + 9), 2)
            x += 32

    # ------------------------------------------------------------- aux panels
    def draw_aux(self):
        r = self.r_aux
        self.rrect(r, COLOR_VIEWPORT, 8)
        ws = self.workspace
        {"Schematic": self.draw_schematic, "Drawing": self.draw_levelstrip, "Fx": self.draw_fx,
         "Expressions": self.draw_expressions, "Script": self.draw_scripts}[ws](r)

    def node_rect(self, o):
        r, z = self.r_aux, self.nd_zoom
        if o.node is None:                                   # first free slot, so new nodes never hide behind old ones
            taken = [p.node for p in self.objs if p is not o and p.node is not None]
            o.node = [32, 64]
            for k in range(400):
                x, y = 32 + (k % 4) * 208, 64 + (k // 4) * 104
                if all(abs(x - tx) >= 196 or abs(y - ty) >= 100 for tx, ty in taken):
                    o.node = [x, y]
                    break
        return pygame.Rect(int(r.x + self.nd_ox + o.node[0] * z), int(r.y + self.nd_oy + o.node[1] * z),
                           int((150 if self.is_pill(o) else 168) * z), int((30 if self.is_pill(o) else (112 if o.node_open else 56)) * z))

    def is_pill(self, o):
        return o.kind in ("peg", "null", "bone") or o.kind.startswith("ctrl")

    def port_y(self, nr):
        if nr.h <= int(34 * self.nd_zoom):                    # a pill: ports in the middle
            return nr.centery
        return nr.y + int(36 * self.nd_zoom)

    def nd_wheel(self, dy, pos):
        r, z0 = self.r_aux, self.nd_zoom
        nz = clamp(z0 * (1.1 ** dy), 0.08, 2.5)
        wx, wy = (pos[0] - r.x - self.nd_ox) / z0, (pos[1] - r.y - self.nd_oy) / z0
        self.nd_ox, self.nd_oy, self.nd_zoom = pos[0] - r.x - wx * nz, pos[1] - r.y - wy * nz, nz

    def arrange_nodes(self):
        """A tree from left to right: parents on the left, their children in a column to the right, centred on the parent."""
        kids = {id(o): [c for c in self.objs if c.parent is o] for o in self.objs}
        roots = [o for o in self.objs if o.parent is None or o.parent not in self.objs]
        row, ypos, done = [0], {}, set()

        def place(o, depth):
            if id(o) in done:
                return ypos[id(o)]
            done.add(id(o))
            ks = kids[id(o)]
            if not ks:
                y = row[0]
                row[0] += 56 if self.is_pill(o) else 112
            else:
                ys = [place(c, depth + 1) for c in ks]
                y = (min(ys) + max(ys)) / 2
            ypos[id(o)] = y
            o.node = [48 + depth * 280, 90 + y]
            return y
        for r in roots:
            place(r, 0)
            row[0] += 40                                       # air between separate trees
        for o in self.objs:
            if id(o) not in done:
                place(o, 0)
        self.nd_reset()
        self.msg("Nodes arranged as a tree")

    def nd_reset(self):
        self.nd_zoom, self.nd_ox, self.nd_oy = 1.0, 0.0, 0.0

    def curve(self, p0, p1, col, w=2):
        dx = max(40, abs(p1[0] - p0[0]) * 0.5)
        c1, c2 = (p0[0] + dx, p0[1]), (p1[0] - dx, p1[1])
        pts = []
        for i in range(21):
            t = i / 20
            u = 1 - t
            pts.append((u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p1[0],
                        u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p1[1]))
        pygame.draw.lines(self.screen, col, False, pts, w)

    def schem_click(self, mx, my):
        mods = pygame.key.get_mods()

        def pan_from(mx, my):
            sx, sy, ox, oy = mx, my, self.nd_ox, self.nd_oy

            def pan(mx, my):
                self.nd_ox, self.nd_oy = ox + mx - sx, oy + my - sy
            return pan
        if self.btn == 2 or mods & pygame.KMOD_ALT:
            return pan_from(mx, my)
        self.kf_sel = []
        self.sel_wire = None
        z = self.nd_zoom
        pr = max(8, int(10 * z))
        tb = self.table_rect()
        if math.hypot(mx - tb.right, my - self.port_y(tb)) <= pr:        # drag from the Table onto a node = make it a root
            self.link_drag, self.link_mouse, self.link_start = ("table", "out"), (mx, my), (mx, my)

            def lt(mx, my):
                self.link_mouse = (mx, my)
            return lt
        for o in self.objs:
            nr = self.node_rect(o)
            py = self.port_y(nr)
            for side, px in (("out", nr.right), ("in", nr.x)):          # links can start from either port
                if math.hypot(mx - px, my - py) <= pr:
                    if o not in self.sel:
                        self.select(o)
                    self.link_drag, self.link_mouse, self.link_start = (o, side), (mx, my), (mx, my)

                    def lm(mx, my):
                        self.link_mouse = (mx, my)
                    return lm
            tg = pygame.Rect(nr.right - int(26 * z), nr.y + 2, int(22 * z), int(20 * z))
            if tg.collidepoint(mx, my):
                o.node_open = not o.node_open
                return
            if nr.collidepoint(mx, my):
                if mods & (pygame.KMOD_SHIFT | pygame.KMOD_CTRL | pygame.KMOD_META):
                    self.select(o, True)
                    return
                if o not in self.sel:
                    self.sel = [o]
                self.layer_double_click(o)                                # double-click the name = rename (the layer too)
                self.reveal_in_timeline(o, center=True)                    # and the timeline shows this layer in the middle
                items = []
                for oo in self.sel:
                    self.node_rect(oo)
                    items.append((oo, oo.node[0], oo.node[1]))
                mx0, my0, ox0, oy0 = mx, my, self.nd_ox, self.nd_oy
                self.autoscroll = "nodes"

                def mv(mx, my):
                    for oo, x0, y0 in items:
                        oo.node = [x0 + ((mx - mx0) - (self.nd_ox - ox0)) / self.nd_zoom, y0 + ((my - my0) - (self.nd_oy - oy0)) / self.nd_zoom]
                    self.drop_wire = None
                    if len(items) == 1:                                   # over a wire between two nodes: it lights up yellow
                        nd = items[0][0]
                        nrd = self.node_rect(nd)
                        wo = self.wire_at(nrd.centerx, self.port_y(nrd), 18)       # the node's middle against the wire
                        if wo is not None and wo is not nd and wo.parent is not nd:
                            self.drop_wire = wo

                def mv_end():
                    dw, self.drop_wire = self.drop_wire, None
                    if dw is not None and len(items) == 1:               # dropped on the wire: parent -> node -> child
                        nd, par = items[0][0], dw.parent
                        if self.link(nd, par, quiet=True) is not False and self.link(dw, nd, quiet=True) is not False:
                            nd.node = [(par.node[0] + dw.node[0]) / 2, (par.node[1] + dw.node[1]) / 2]
                            self.msg(f"{nd.name} inserted between {par.name} and {dw.name}")
                self.drag_end = mv_end
                return mv
        wo = self.wire_at(mx, my)
        self.sel_wire = wo                                        # click a wire to select it (Delete disconnects)
        if wo is not None:
            return
        base = list(self.sel) if mods & pygame.KMOD_SHIFT else []      # empty space: rectangular selection
        self.sel = list(base)
        x0, y0 = mx, my
        self.nd_marquee = (x0, y0, mx, my)

        def drag(mx, my):
            self.nd_marquee = (x0, y0, mx, my)

        def end():
            x1, y1, x2, y2 = self.nd_marquee
            self.nd_marquee = None
            rc = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            if rc.w + rc.h > 4:
                self.sel = base + [o for o in self.objs if o not in base and rc.colliderect(self.node_rect(o))]
        self.drag_end = end
        return drag

    def schem_menu(self, mx, my):
        hit = next((o for o in self.objs if self.node_rect(o).collidepoint(mx, my)), None)
        wo = None if hit else self.wire_at(mx, my)
        if wo is not None:
            self.sel_wire = wo
            self.ctx = {"pos": (mx, my), "items": [("Disconnect", lambda: self.unlink(wo))]}
            return
        if hit and hit not in self.sel:
            self.sel = [hit]
        items = []
        if self.sel:
            items += [("Group  (Ctrl+G)", self.group_selected), ("Ungroup", self.ungroup_selected),
                      ("Show / hide thumbnail", lambda: [setattr(o, "node_open", not o.node_open) for o in self.sel]),
                      ("Delete node  (Del)", self.delete_selected)]
        items.append(("Arrange nodes", self.arrange_nodes))
        self.ctx = {"pos": (mx, my), "items": items}

    def schem_release(self, pos):
        if not self.link_drag:
            return
        src, side = self.link_drag
        self.link_drag = None
        tb = self.table_rect()
        if src == "table":                                       # from the Table onto a node: the node becomes a root
            t = next((o for o in self.objs if self.node_rect(o).collidepoint(pos)), None)
            if t:
                self.unlink(t)
            return
        if side == "in" and tb.collidepoint(pos):                # dropped on the Table: no parent any more
            for c in (self.sel if src in self.sel else [src]):
                self.unlink(c)
            return
        target = next((o for o in self.objs if o is not src and self.node_rect(o).collidepoint(pos)), None)
        if target:
            if side == "out":
                self.link(target, src)                           # right port: src becomes the parent
            else:                                                # left port: every selected node becomes a child of the target
                for c in ([o for o in self.sel if o is not target] if src in self.sel else [src]):
                    self.link(c, target)
        elif side == "in" and src.parent and math.hypot(pos[0] - self.link_start[0], pos[1] - self.link_start[1]) < 5:
            self.unlink(src)

    def fit_text(self, s, font, maxw):
        if font.size(s)[0] <= maxw:
            return s
        while len(s) > 1 and font.size(s + "..")[0] > maxw:
            s = s[:-1]
        return s + ".."

    def nd_fit(self):
        r = self.r_aux
        for o in self.objs:
            self.node_rect(o)
        if not self.objs:
            return
        xs, ys = [o.node[0] for o in self.objs] + [-240], [o.node[1] for o in self.objs]
        bw, bh = max(xs) + 176 - min(xs), max(ys) + 120 - min(ys)
        z = clamp(min((r.w - 64) / bw, (r.h - 136) / bh), 0.08, 1.5)
        self.nd_zoom = z
        self.nd_ox = (r.w - bw * z) / 2 - min(xs) * z
        self.nd_oy = 72 + ((r.h - 136) - bh * z) / 2 - min(ys) * z

    def toggle_all_thumbs(self):
        on = not all(o.node_open for o in self.objs)
        for o in self.objs:
            o.node_open = on

    def node_thumb(self, o, rc, frame=None):
        fr = frame or self.frame
        self.rrect(rc, (22, 22, 24), 6)
        if o.kind == "rlayer" and o.surf is not None:
            w, h = o.surf.get_size()
            k = min((rc.w - 8) / w, (rc.h - 8) / h)
            self.screen.blit(pygame.transform.smoothscale(o.surf, (max(1, int(w * k)), max(1, int(h * k)))),
                             (rc.centerx - int(w * k) // 2, rc.centery - int(h * k) // 2))
            return
        if o.kind == "image":
            sf = self.footage_surface(o, fr)
            if sf:
                k = min((rc.w - 8) / sf.get_width(), (rc.h - 8) / sf.get_height())
                sm = pygame.transform.smoothscale(sf, (max(1, int(sf.get_width() * k)), max(1, int(sf.get_height() * k))))
                self.screen.blit(sm, sm.get_rect(center=rc.center))
            return
        polys = []
        for it in (reversed(o.items_at(fr)) if o.kind == "vlayer" else [o]):
            pts, closed = shape_pts(it, fr)
            if o.kind == "vlayer":
                b = it.base
                pts = [self.xf(b["x"], b["y"], b["scale"], b["rotation"], px, py) for px, py in pts]
            if pts:
                polys.append((it, pts, closed))
        allp = [p for _, pts, _ in polys for p in pts]
        if not allp:
            return
        xs, ys = [p[0] for p in allp], [p[1] for p in allp]
        bw, bh = max(1.0, max(xs) - min(xs)), max(1.0, max(ys) - min(ys))
        k = min((rc.w - 16) / bw, (rc.h - 16) / bh)
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        for it, pts, closed in polys:
            sp = [(rc.centerx + (x - cx) * k, rc.centery + (y - cy) * k) for x, y in pts]
            if it.kind in ("null", "peg"):
                pygame.draw.lines(self.screen, self.label_color(it), True, sp, 1)
                continue
            if closed and it.fill_on and len(sp) > 2:
                pygame.draw.polygon(self.screen, it.fill, sp)
            if (it.stroke_on or not closed) and len(sp) > 1:
                pygame.draw.lines(self.screen, it.stroke, closed, sp, max(1, int(min(3, it.stroke_w * k))))

    def table_rect(self):
        r, z = self.r_aux, self.nd_zoom
        return pygame.Rect(int(r.x + self.nd_ox - 240 * z), int(r.y + self.nd_oy + 64 * z), int(168 * z), int(56 * z))

    def curve_pts(self, p0, p1):
        dx = max(40, abs(p1[0] - p0[0]) * 0.5)
        c1, c2 = (p0[0] + dx, p0[1]), (p1[0] - dx, p1[1])
        pts = []
        for i in range(21):
            t = i / 20
            u = 1 - t
            pts.append((u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p1[0],
                        u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p1[1]))
        return pts

    def wire_at(self, mx, my, tol=6):
        """The child whose wire to its parent passes under the mouse."""
        for o in self.objs:
            if o.parent:
                p, c = self.node_rect(o.parent), self.node_rect(o)
                pts = self.curve_pts((p.right, self.port_y(p)), (c.x, self.port_y(c)))
                for a, b in zip(pts, pts[1:]):
                    vx, vy = b[0] - a[0], b[1] - a[1]
                    L2 = vx * vx + vy * vy or 1
                    t = clamp(((mx - a[0]) * vx + (my - a[1]) * vy) / L2, 0, 1)
                    if math.hypot(mx - (a[0] + t * vx), my - (a[1] + t * vy)) <= tol:
                        return o
        return None

    def draw_schematic(self, r):
        self.hit(r, self.schem_click, (1, 2))
        self.hit(r, self.schem_menu, (3,))
        if self._nd_seen != len(self.objs):                  # new nodes outside the view -> fit everything
            self._nd_seen = len(self.objs)
            if any(not r.colliderect(self.node_rect(o)) for o in self.objs):
                self.nd_fit()
        prev = self.push_clip(r)
        gs = max(8, int(32 * self.nd_zoom))
        for gx in range(r.x + int(self.nd_ox) % gs, r.right, gs):
            for gy in range(r.y + int(self.nd_oy) % gs, r.bottom, gs):
                self.screen.set_at((gx, gy), (50, 50, 50))
        self.txt("SCHEMATIC", r.x + 24, r.y + 24, self.fb2)
        self.txt("Scroll = zoom   |   middle / Alt drag = pan   |   drag empty space = select   |   Del = delete",
                 r.x + 24, r.y + 48, self.f11, COLOR_MUTED)
        z = self.nd_zoom
        tb = self.table_rect()
        for o in self.objs:
            c = self.node_rect(o)
            if o.parent:                                      # parent -> child, the arrow points at the child
                p = self.node_rect(o.parent)
                p0, p1 = (p.right, self.port_y(p)), (c.x, self.port_y(c))
                col, w = ((255, 215, 70), 3) if (o is self.sel_wire or o is self.drop_wire) else ((150, 160, 220), 2)
            else:                                             # nodes without a parent hang on the Table
                p0, p1, col, w = (tb.right, self.port_y(tb)), (c.x, self.port_y(c)), (70, 76, 100), 1
            pygame.draw.lines(self.screen, col, False, self.curve_pts(p0, p1), w)
            rpoly(self.screen, col, [(p1[0] - 2, p1[1]), (p1[0] - 11, p1[1] - 5), (p1[0] - 11, p1[1] + 5)], 1)
        if self.link_drag:
            src, side = self.link_drag
            if src == "table":
                nr, side = tb, "out"
            else:
                nr = self.node_rect(src)
            if side == "out":
                self.curve((nr.right, self.port_y(nr)), self.link_mouse, COLOR_TEAL)
            else:
                self.curve(self.link_mouse, (nr.x, self.port_y(nr)), COLOR_TEAL)
        for o in self.objs:
            nr = self.node_rect(o)
            sel = o in self.sel
            lc = self.label_color(o)
            if self.is_pill(o):                                    # peg / null / bone / controller: just a coloured pill with its name
                self.rrect(nr, shade(lc, 0.62), nr.h // 2)
                self.rrect(nr, (255, 255, 255) if sel else lc, nr.h // 2, 2)
                pc = self.push_clip(nr)
                tid = "ctrl" if o.kind.startswith("ctrl") else o.kind
                draw_tool_icon(self.screen, tid, pygame.Rect(nr.x + 4, nr.y, nr.h, nr.h), (255, 255, 255))
                rid = f"rename_{id(o)}"
                if self.edit and self.edit.get("id") == rid:
                    self.field((nr.x + nr.h, nr.y + 3, nr.w - nr.h - 10, nr.h - 6), o.name, lambda s, o=o: self.rename_obj(o, s), rid)
                else:
                    self.txt(self.fit_text(o.name, self.fb, nr.w - nr.h - 14), nr.x + nr.h + 4, nr.centery - 8, self.fb, (255, 255, 255))
                self.pop_clip(pc)
                prd = max(4, int(6 * z))
                pygame.draw.circle(self.screen, (230, 230, 230), (nr.right, self.port_y(nr)), prd)
                pygame.draw.circle(self.screen, (230, 230, 230) if o.parent else (150, 150, 150), (nr.x, self.port_y(nr)), prd)
                continue
            rad = max(4, int(8 * z))
            self.rrect(nr, (46, 48, 54), rad)
            self.rrect(nr, lc if sel else (80, 80, 90), rad, 2)
            hh = max(12, int(20 * z))
            pygame.draw.rect(self.screen, shade(lc, 0.72), (nr.x + 2, nr.y + 2, nr.w - 4, hh), border_top_left_radius=max(3, int(6 * z)),
                             border_top_right_radius=max(3, int(6 * z)))
            pc = self.push_clip(nr)
            tc = (255, 255, 255)                           # names are always white, with a soft shadow
            nm = self.fit_text(o.name, self.fb, nr.w - 56)
            ty = nr.y + 3 + max(0, (hh - 14) // 2)
            rid = f"rename_{id(o)}"
            if self.edit and self.edit.get("id") == rid:
                self.field((nr.x + 6, nr.y + 3, nr.w - 40, hh - 2), o.name, lambda s, o=o: self.rename_obj(o, s), rid)
            else:
                self.txt(nm, nr.x + 13, ty + 1, self.fb, (0, 0, 0))
                self.txt(nm, nr.x + 12, ty, self.fb, tc)
            draw_icon(self.screen, "tri_d" if o.node_open else "tri_r", pygame.Rect(nr.right - int(26 * z), nr.y + 2, int(22 * z), hh), tc)
            self.txt(o.kind.capitalize(), nr.x + 12, nr.y + hh + 10, self.f11, COLOR_MUTED)
            if o.node_open:
                self.node_thumb(o, pygame.Rect(nr.x + 12, nr.y + int(56 * z), nr.w - 24, nr.h - int(56 * z) - 12))
            self.pop_clip(pc)
            prd = max(4, int(6 * z))
            pygame.draw.circle(self.screen, (230, 230, 230), (nr.right, self.port_y(nr)), prd)
            pygame.draw.circle(self.screen, (230, 230, 230) if o.parent else (150, 150, 150), (nr.x, self.port_y(nr)), prd)
        if self.link_drag:                                   # highlight the node the wire will connect to
            src, side = self.link_drag
            tgt = next((o for o in self.objs if o is not src and self.node_rect(o).collidepoint(self.link_mouse)), None)
            if tgt:
                nr = self.node_rect(tgt)
                self.rrect(nr.inflate(10, 10), (255, 215, 70), max(6, int(12 * z)), 3)
                pygame.draw.circle(self.screen, (255, 215, 70), (nr.x if side == "out" else nr.right, self.port_y(nr)), max(7, int(11 * z)))
        self.rrect(tb, (46, 48, 54), max(4, int(8 * z)))                    # the Table: the root of the scene
        self.rrect(tb, (130, 138, 160), max(4, int(8 * z)), 2)
        pygame.draw.rect(self.screen, (84, 90, 110), (tb.x + 2, tb.y + 2, tb.w - 4, max(12, int(20 * z))),
                         border_top_left_radius=max(3, int(6 * z)), border_top_right_radius=max(3, int(6 * z)))
        pct = self.push_clip(tb)
        self.txt("Table", tb.x + 12, tb.y + 3 + max(0, (max(12, int(20 * z)) - 14) // 2), self.fb, (255, 255, 255))
        self.txt("scene root", tb.x + 12, tb.y + max(12, int(20 * z)) + 10, self.f11, COLOR_MUTED)
        self.pop_clip(pct)
        pygame.draw.circle(self.screen, (230, 230, 230), (tb.right, self.port_y(tb)), max(4, int(6 * z)))
        if self.nd_marquee:
            x1, y1, x2, y2 = self.nd_marquee
            pygame.draw.rect(self.screen, COLOR_TEAL, (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)), 1)
        bar = pygame.Rect(r.x + 8, r.bottom - 48, r.w - 16, 40)          # bottom toolbar
        self.rrect(bar, COLOR_TL, 12)
        x = bar.x + 8
        icons = (("arrange", "Arrange nodes by hierarchy", lambda mx, my: self.arrange_nodes()),
                 ("fit", "Fit all nodes in the view", lambda mx, my: self.nd_fit()),
                 ("one", "Zoom 1:1", lambda mx, my: setattr(self, "nd_zoom", 1.0)),
                 ("thumbs", "Show / hide the thumbnails on all nodes", lambda mx, my: self.toggle_all_thumbs()),
                 ("locate", "Centre the view on the selected node", lambda mx, my: self.nd_center_on(self.psel)))
        for key, hint, fn in icons:
            rc = self.flat_button((x, bar.y + 4, 32, 32), fn, hint)
            col = (225, 225, 225)
            if key == "arrange":
                for k in range(3):
                    self.rrect((rc.x + 8, rc.y + 9 + k * 6, 16 - 3 * (k % 2), 3), col, 1)
            elif key == "fit":
                for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                    cx, cy = rc.centerx + sx * 8, rc.centery + sy * 8
                    pygame.draw.lines(self.screen, col, False, [(cx - sx * 5, cy), (cx, cy), (cx, cy - sy * 5)], 2)
            elif key == "thumbs":
                self.rrect((rc.x + 7, rc.y + 8, 18, 16), col, 3, 2)
                pygame.draw.polygon(self.screen, col, [(rc.x + 10, rc.y + 21), (rc.x + 15, rc.y + 14), (rc.x + 19, rc.y + 21)])
            else:
                self.txt("1:1", rc.centerx, rc.centery, self.fb, col, center=True)
            x += 36
        x += 8
        self.button((x, bar.y + 4, 64, 32), "+ Null", lambda mx, my: self.new_obj("null", self.aw // 2, self.ah // 2), radius=8,
                    hint="New null (a controller to link layers to)")
        self.button((x + 70, bar.y + 4, 60, 32), "+ Peg", lambda mx, my: self.new_obj("peg", self.aw // 2, self.ah // 2), radius=8,
                    hint="New peg: a transform-only parent for drawing layers - give it an expression or script")
        self.txt(f"{int(self.nd_zoom * 100)}%", bar.right - 12, bar.y + 12, self.f11, COLOR_MUTED, right=True)
        self.pop_clip(prev)

    def apply_palette(self, c):
        self.color_set("fill", c, 100.0)

    def scrollbar(self, area, content_h, scroll):
        if content_h <= area.h:
            return
        track = pygame.Rect(area.right - 9, area.y + 4, 4, area.h - 8)
        pygame.draw.rect(self.screen, (52, 52, 58), track, border_radius=2)
        th = max(26, int(track.h * area.h / content_h))
        ty = track.y + int((track.h - th) * scroll / max(1, content_h - area.h))
        pygame.draw.rect(self.screen, (125, 125, 136), (track.x, ty, 4, th), border_radius=2)

    def draw_levelstrip(self, r):
        """Drawing workspace: two tabs. Colors = scrolling palette + a colour wheel that never scrolls. Level Strip = the drawings of the layer."""
        x = r.x + 24
        for i, n in enumerate(("Colors", "Level Strip")):
            self.button((x + i * 116, r.y + 16, 108, 28), n, lambda mx, my, n=n: setattr(self, "drawing_tab", n),
                        active=self.drawing_tab == n, font=self.f11)
        area = pygame.Rect(r.x, r.y + 52, r.w, r.h - 52)
        if self.drawing_tab == "Colors":
            wide = area.w >= 560                                       # wide panel: palette on the left, the wheel fixed on the right
            if wide:
                wh = pygame.Rect(area.right - 258, area.y + 8, 240, 344)
                bar = pygame.Rect(area.x, wh.bottom - 34, area.w - 270, 34)
                pal = pygame.Rect(area.x, area.y, area.w - 270, max(80, bar.y - area.y - 6))
            else:                                                     # narrow panel: palette above, the wheel fixed below it
                wh = pygame.Rect(area.centerx - 120, area.bottom - 352, 240, 344)
                bar = pygame.Rect(area.x, wh.y - 40, area.w, 34)
                pal = pygame.Rect(area.x, area.y, area.w, max(80, bar.y - area.y - 6))
            self.pal_area = pal
            prev = self.push_clip(pal)
            self.hit_clip = pal
            try:
                ed_ = self.edit.get("id", "") if self.edit else ""
                if ed_ == "palfolder" or ed_.startswith("palname_"):
                    self.pal_scroll = 0
                y0 = pal.y + 12 - int(self.pal_scroll)
                end = self.draw_colors_tab(pal, x, y0)
            finally:
                self.hit_clip = None
                self.pop_clip(prev)
            content = end - y0 + 24
            self.pal_max = max(0, content - pal.h)
            self.pal_scroll = clamp(self.pal_scroll, 0, self.pal_max)
            self.scrollbar(pal, content, self.pal_scroll)
            if pal.collidepoint(pygame.mouse.get_pos()):               # the frame shows that this list scrolls on its own
                pygame.draw.rect(self.screen, COLOR_ACCENT_L, pal.inflate(-8, -2), 1, border_radius=6)
            self.draw_palette_bar(bar)
            prev = self.push_clip(wh.inflate(8, 8).clip(area))
            dp = self.dock_picker                                      # the wheel is bound to the fill colour
            rgb, a = self.color_get("fill")
            if tuple(hsv_to_rgb(dp["h"], dp["s"], dp["v"])) != tuple(rgb) and not self.drag:
                h, s_, v = rgb_to_hsv(rgb)
                if s_ > 0.001 and v > 0.001:
                    dp["h"] = h
                dp["s"], dp["v"], dp["a"] = s_, v, a
            self.picker_body(dp, wh)
            self.pop_clip(prev)
        else:
            prev = self.push_clip(area)
            self.hit_clip = area
            try:
                y0 = area.y + 12 - int(self.lvl_scroll)
                end = self.draw_level_tab(area, x, y0)
            finally:
                self.hit_clip = None
                self.pop_clip(prev)
            content = (end or y0) - y0 + 24
            self.lvl_max = max(0, content - area.h)
            self.lvl_scroll = clamp(self.lvl_scroll, 0, self.lvl_max)
            self.scrollbar(area, content, self.lvl_scroll)

    def draw_palette_bar(self, bar):
        """Fixed strip under the palette: + Folder on the left, the three views (circles / rounded tiles / list) on the right."""
        self.button((bar.x + 24, bar.y + 3, 84, 28), "+ Folder", lambda mx, my: (setattr(self, "pal_scroll", 0), self.begin_edit("palfolder", "", self.pal_add_folder)),
                    radius=14, font=self.f11, hint="New folder, e.g. one for every character")
        bx = bar.right - 24 - 3 * 36
        for k, (mode, hint) in enumerate((("circles", "Circles"), ("tiles", "Rounded tiles with the names"), ("list", "List"))):
            rc = pygame.Rect(bx + k * 36, bar.y + 1, 32, 32)
            self.flat_button(rc, lambda mx, my, m=mode: (setattr(self, "pal_view", m), self.save_prefs()), hint, self.pal_view == mode)
            cx, cy = rc.center
            if mode == "circles":
                pygame.draw.circle(self.screen, (235, 235, 235), (cx, cy), 7, 2)
            elif mode == "tiles":
                pygame.draw.rect(self.screen, (235, 235, 235), (cx - 9, cy - 6, 18, 12), 2, border_radius=5)
            else:
                for dy in (-6, 0, 6):
                    pygame.draw.line(self.screen, (235, 235, 235), (cx - 8, cy + dy), (cx + 8, cy + dy), 2)

    def draw_colors_tab(self, r, x, y):
        W = r.w - 48
        if self.pal_folders:                                          # the folder chips appear once there is a folder
            cx0 = x
            for name, val in [("All", None)] + [(f, f) for f in self.pal_folders]:
                tw = self.f11.size(name)[0] + 20
                if cx0 + tw > x + W:
                    cx0, y = x, y + 28
                rc = pygame.Rect(cx0, y, tw, 24)
                self.button(rc, name, lambda mx, my, v=val: setattr(self, "pal_open", v), active=self.pal_open == val, radius=12, font=self.f11)
                if val is not None:
                    self.hit(rc, lambda mx, my, v=val: self.pal_folder_menu(v, (mx, my)), (3,))
                cx0 += tw + 6
            y += 32
        ed_id = self.edit.get("id", "") if self.edit else ""
        if ed_id == "palfolder" or ed_id.startswith("palname_"):       # typing a folder name or a colour name
            self.txt("Folder name:" if ed_id == "palfolder" else "Colour name:", x, y + 6, self.f11, COLOR_MUTED)
            self.field((x + 92, y, W - 92, 28), "", self.edit["cb"], ed_id)
            y += 34
        vis = [i for i, e in enumerate(self.palette) if self.pal_open is None or e["folder"] == self.pal_open]
        view = self.pal_view
        add_rc = None
        for n in range(len(vis) + 1):
            if view == "circles":
                per = max(1, W // 34)
                rc = pygame.Rect(x + (n % per) * 34, y + (n // per) * 34, 28, 28)
            elif view == "tiles":
                per = max(1, (W + 6) // 90)
                rc = pygame.Rect(x + (n % per) * 90, y + (n // per) * 34, 84, 28)
            else:
                rc = pygame.Rect(x, y + n * 30, W, 26)
            if n < len(vis):
                i = vis[n]
                e = self.palette[i]
                c = e["c"]
                lum = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
                tc = (20, 20, 20) if lum > 140 else (245, 245, 245)
                label = e["name"] or "#%02X%02X%02X" % tuple(int(v) for v in c)
                if view == "circles":
                    self.rrect(rc, c, 14)
                    if tuple(c) == tuple(self.def_fill):
                        self.rrect(rc, (255, 255, 255), 14, 2)
                elif view == "tiles":
                    self.rrect(rc, c, 10)
                    if tuple(c) == tuple(self.def_fill):
                        self.rrect(rc, (255, 255, 255), 10, 2)
                    pcl = self.push_clip(rc)
                    self.txt(label, rc.centerx, rc.centery, self.f11, tc, center=True)
                    self.pop_clip(pcl)
                else:
                    self.rrect(rc, COLOR_HOVER if self.hovering(rc) else (34, 34, 38), 8)
                    sw = pygame.Rect(rc.x + 4, rc.y + 3, 20, 20)
                    self.rrect(sw, c, 10)
                    self.txt(label, rc.x + 32, rc.y + 5, self.f11)
                    self.txt("#%02X%02X%02X" % tuple(int(v) for v in c), rc.right - 8, rc.y + 5, self.f11, COLOR_MUTED, right=True)
                self.hit(rc, lambda mx, my, c=c: self.apply_palette(c))
                self.hit(rc, lambda mx, my, i=i: self.pal_menu(i, (mx, my)), (3,))
                if self.hovering(rc):
                    self.hover_hint = (e["name"] + "  " if e["name"] else "") + "Click: use the colour / right-click: rename, move to a folder, delete"
            else:
                add_rc = rc
                self.rrect(rc, (48, 48, 48), 14 if view == "circles" else 10)
                self.txt("+" if view != "list" else "+ Add the current colour", rc.centerx, rc.centery, self.fb2 if view != "list" else self.f11, COLOR_TEXT, center=True)
                self.hit(rc, lambda mx, my: (self.palette.append({"c": tuple(self.color_get("fill")[0]), "name": "", "folder": self.pal_open}), self.save_prefs()))
                if self.hovering(rc):
                    self.hover_hint = "Add the current fill colour to the palette" + (f" (folder {self.pal_open})" if self.pal_open else "")
        if view == "circles":
            y += (len(vis) // max(1, W // 34) + 1) * 34 + 12
        elif view == "tiles":
            y += (len(vis) // max(1, (W + 6) // 90) + 1) * 34 + 12
        else:
            y += (len(vis) + 1) * 30 + 12
        return y

    def draw_level_tab(self, r, x, y):
        o = self.psel
        lyr = (o.owner or o) if o else (self.active_layer if self.active_layer in self.objs else None)
        self.txt("LEVEL STRIP", x, y, self.fb2)
        y += 30
        if not lyr or lyr.kind not in ("vlayer", "rlayer"):
            self.txt("Select a drawing layer to see its drawings.", x, y, self.f12, COLOR_MUTED)
            return y + 30
        self.txt(lyr.name, x, y, self.fb)
        y += 24
        w = r.w - 2 * (x - r.x)
        if lyr.kind == "rlayer":
            self.txt("Raster layers keep one drawing for now.", x, y, self.f11, COLOR_MUTED)
            return y + 30
        keys = ([0] if (not lyr.phases or lyr.phases[0] > 1) else []) + sorted(lyr.phases)
        cur = lyr.phase_key(self.frame)
        # ---- big preview with a small play button: plays the drawings one after another
        pv = pygame.Rect(x, y, w, 112)
        now = pygame.time.get_ticks()
        shown = self.ph_prev if (self.ph_prev in keys) else cur
        if self.ph_play and keys:
            shown = keys[(now // 140) % len(keys)]
        self.node_thumb(lyr, pv, max(1, shown))
        pb = pygame.Rect(pv.right - 28, pv.bottom - 28, 22, 22)
        self.rrect(pb, (0, 0, 0, 150) if False else (20, 20, 24), 11)
        if self.ph_play:
            pygame.draw.rect(self.screen, (235, 235, 235), (pb.x + 6, pb.y + 6, 4, 10))
            pygame.draw.rect(self.screen, (235, 235, 235), (pb.x + 12, pb.y + 6, 4, 10))
        else:
            pygame.draw.polygon(self.screen, (235, 235, 235), [(pb.x + 7, pb.y + 5), (pb.x + 7, pb.y + 17), (pb.x + 17, pb.y + 11)])
        self.hit(pb, lambda mx, my: setattr(self, "ph_play", not self.ph_play))
        y += 122
        # ---- buttons
        bw = (w - 8) // 3
        self.button((x, y, bw, 30), "+ New", lambda mx, my: self.add_phase(lyr), color=COLOR_ACCENT_L, radius=15, font=self.f11,
                    hint="A blank drawing starts at the playhead - the other drawings stay as they are")
        self.button((x + bw + 4, y, bw, 30), "Duplicate", lambda mx, my: self.phase_duplicate(lyr, cur), radius=15, font=self.f11,
                    hint="Copy the active drawing into a new one right after the playhead")
        self.button((x + 2 * (bw + 4), y, bw, 30), "Delete", lambda mx, my: self.phase_delete(lyr, list(self.ph_sel) or [cur]), radius=15, font=self.f11,
                    hint="Delete the selected drawings")
        y += 40
        self.checkbox(x, y + 2, self.auto_phase, lambda mx, my: setattr(self, "auto_phase", not self.auto_phase), "Auto-create a drawing for every new brush stroke")
        self.txt("Auto-create", x + 24, y + 3, self.f11)
        y += 28
        self.txt("Drawings  (click = go to, Shift / Ctrl = several, drag onto the timeline = place)", x, y, self.f11, COLOR_MUTED)
        y += 22
        per = max(1, int((w + 8) // 72))
        for i, k in enumerate(keys):
            cx, cy = x + (i % per) * 72, y + (i // per) * 82
            card = pygame.Rect(cx, cy, 64, 74)
            sel = k in self.ph_sel
            self.rrect(card, COLOR_ACCENT if k == cur else COLOR_BTN, 8)
            if sel:
                self.rrect(card, (255, 255, 255), 8, 2)
            th = pygame.Rect(cx + 6, cy + 6, 52, 40)
            self.node_thumb(lyr, th, max(1, k))
            self.txt(f"F {max(1, k)}", cx + 32, cy + 58, self.f11, center=True)
            if self.hovering(card):
                self.ph_prev = k
            self.hit(card, lambda mx, my, k=k, keys=keys, lyr=lyr: self.level_click(lyr, k, keys, mx, my))
            self.hit(card, lambda mx, my, k=k, lyr=lyr: setattr(self, "ctx", {"pos": (mx, my), "items": [
                ("Go to this drawing", lambda: self.goto(max(1, k))), ("Duplicate", lambda: self.phase_duplicate(lyr, k)),
                ("Delete", lambda: self.phase_delete(lyr, [k]))]}), (3,))
        return y + ((len(keys) - 1) // per + 1) * 82 + 8

    def level_click(self, lyr, k, keys, mx, my):
        mods = pygame.key.get_mods()
        if mods & pygame.KMOD_SHIFT and self.ph_sel:                 # a range
            last = max(self.ph_sel, key=lambda q: abs(q - k)) if self.ph_sel else k
            a, b = sorted((keys.index(last) if last in keys else 0, keys.index(k)))
            self.ph_sel = set(keys[a:b + 1])
        elif mods & pygame.KMOD_CTRL:
            self.ph_sel ^= {k}
        else:
            self.ph_sel = {k}
        self.goto(max(1, k))
        x0, y0 = mx, my

        def drag(mx, my):
            pass

        def end():                                                      # dropped on the timeline: the drawing is placed at that frame
            mp = pygame.mouse.get_pos()
            if self.r_tl.collidepoint(mp) and math.hypot(mp[0] - x0, mp[1] - y0) > 12 and getattr(self, "tl_frame_at", None):
                f = self.tl_frame_at(mp[0])
                for q in sorted(self.ph_sel or {k}):
                    self.phase_set(lyr, int(clamp(f, 1, self.total)), self.clone_items(lyr, lyr._pitems.get(q, [])))
                    f += 1
                self.msg(f"Drawing placed on the timeline at frame {f - len(self.ph_sel or {k})}")
        self.drag_end = end
        return drag

    def draw_fx(self, r):
        x, y = r.x + 16, r.y + 16
        self.txt("EFFECTS", x, y, self.fb2)
        self.txt("Placeholder - effects will apply to the selected layer.", x, y + 24, self.f11, COLOR_MUTED)
        y += 56
        for i, n in enumerate(FX_LIST):
            card = pygame.Rect(x + (i % 3) * 136, y + (i // 3) * 72, 128, 64)
            self.button(card, n, lambda mx, my, n=n: self.msg(f"{n}: coming soon"), radius=8)

    def set_expr(self, o, p, text):
        text = text.strip()
        self.expr_bad.discard((o.name, p))
        if text:
            o.expr[p] = text
        else:
            o.expr.pop(p, None)

    def draw_expressions(self, r):
        x, y, o = r.x + 24, r.y + 24, self.psel
        self.txt("EXPRESSIONS", x, y, self.fb2)
        y += 40
        if not o:
            self.txt("Select a layer to edit its expressions.", x, y, self.f12, COLOR_MUTED)
            return
        self.txt(o.name, x, y, self.fb)
        y += 28
        for p in PROPS:
            self.txt(PROP_LABEL[p], x, y + 9, self.f11, COLOR_MUTED)
            self.field((x + 104, y, r.w - 104 - 48, 32), o.expr.get(p, ""), lambda s, p=p, o=o: self.set_expr(o, p, s),
                       f"expr_{o.name}_{p}", hint="Python expression, e.g. world('Null Control 1')[0] + 100")
            y += 44
        y += 8
        for line in ("Variables: t (frame), time (sec), value, pi, sin, cos, wiggle(freq, amp)",
                     "world('Name') -> (x, y, scale, rotation) of another layer",
                     "Example (follow a null): world('Null Control 1')[0] + 100"):
            self.txt(line, x, y, self.f11, COLOR_MUTED)
            y += 20

    def draw_scripts(self, r):
        x, y = r.x + 16, r.y + 16
        self.txt("SCRIPTS", x, y, self.fb2)
        self.button((r.right - 136, y - 4, 120, 32), "Import...", self.open_script_dialog, color=COLOR_ACCENT_L,
                    radius=16)
        y += 40
        folders = [SCRIPTS_DIR] + ([os.path.join(self.project_dir, "scripts")] if self.project_dir else [])
        for fo in folders:
            if not os.path.isdir(fo):
                continue
            for n in sorted(f for f in os.listdir(fo) if f.endswith(".py")):
                self.rrect((x, y, r.w - 32, 32), COLOR_BTN, 8)
                self.txt(n, x + 12, y + 9)
                self.button((r.right - 112, y + 4, 80, 24), "Run", lambda mx, my, p=os.path.join(fo, n): self.run_script(p),
                            radius=12)
                y += 40
