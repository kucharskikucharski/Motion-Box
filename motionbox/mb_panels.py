"""Motion Box - toolbox, colour picker, left (Edit) panel, right (Properties/Layers/Library) panel,
transport bar and the menu bar."""
import pygame

from mb_core import *            # noqa

SHORTCUTS = ["Space            Play / pause", "K                 Set / remove keyframe",
             "Left / Right     Previous / next frame", "W / Q            Next / previous phase",
             "V T R B P E N J H  Tools", "Shift (drag)    Axis lock / 45 deg rotation / proportional",
             "Alt + scroll      Zoom timeline", "Scroll (timeline) Up / down through layers",
             "Shift + scroll   Along the time axis", "P R T S (on timeline)  Show position / rotation / opacity / scale",
             "Ctrl+H           Replace footage", "Ctrl+R           Rename selected layers", "Arrows           Nudge selection 1 px (Shift 10) / step playhead after clicking the timeline", "[ and ]          Brush size", "Ctrl+M           Render (export video)", "U                 Show only the animated properties",
             "Shift / Ctrl + click on layers   Range / toggle single layer", "Ctrl+Z / Ctrl+Shift+Z  Undo / redo", "I / O             Work area in / out",
             "Middle drag      Pan timeline / viewport", "`  (backtick)    Fullscreen panel under cursor",
             "Ctrl+S           Save", "Ctrl+A / D / G    Select all / duplicate / group",
             "Delete           Delete selection", "Home              Fit viewport"]


def rounded_surface(surf, r):
    mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=r)
    out = surf.convert_alpha()
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


class PanelsMixin:
    # ----------------------------------------------------------------- toolbox
    def slot_press(self, i):
        self.set_tool(self.slot_tool.get(i, SLOTS[i][0]))
        self.press_slot = (i, pygame.time.get_ticks())
        self.flyout = None

    def draw_toolbox(self):
        """One fixed column. Tools that do not fit (the timeline was dragged up) move into the arrow menu at the bottom."""
        top = self.r_tool.y
        limit = self.r_tool.bottom - 92
        y, hidden = top, []
        self.slot_pos = {}
        for i, slot in enumerate(SLOTS):
            step = 10 if slot is None else 34                      # 30 px icons, 4 px gap
            if y + step > limit:
                if slot:
                    hidden.append(slot)
                continue
            x = 13
            if slot is None:
                pygame.draw.line(self.screen, COLOR_LINE, (x, y + 4), (x + 30, y + 4))
                y += 10
                continue
            tid = self.slot_tool.get(i, slot[0])
            rc = pygame.Rect(x, y, 30, 30)
            self.slot_pos[i] = rc
            active, hov = self.tool in slot, self.hovering(rc)
            ic, spec = load_icon_state(tid, 30, "active" if active else ("hover" if hov else "default"))
            if (active or hov) and not spec:        # idle = same colour as the background
                self.rrect(rc, COLOR_ACCENT if active else COLOR_HOVER, 8)
            ic, spec = load_icon_state(tid, 30, "active" if active else ("hover" if hov else "default"))
            if ic:                                  # your own Default / Hover / Active artwork is used as it is
                self.screen.blit(ic if (spec or active or hov) else self.idle_icon(ic), ic.get_rect(center=rc.center))
            else:
                draw_tool_icon(self.screen, tid, rc, (235, 235, 235) if (active or hov) else (178, 178, 182))
            if len(slot) > 1:                       # small rounded triangle = hold for more tools
                rpoly(self.screen, (170, 170, 170), [(rc.right - 3, rc.bottom - 9), (rc.right - 3, rc.bottom - 3), (rc.right - 9, rc.bottom - 3)], 1.2)
            if hov:
                n, k, h = TOOL_INFO[tid]
                self.hover_hint = f"{n}{' (' + k + ')' if k else ''}: {h}"
            self.hit(rc, lambda mx, my, i=i: self.slot_press(i))
            y += 34
        if hidden:
            ar = pygame.Rect(13, limit, 30, 24)
            self.flat_button(ar, lambda mx, my, h=hidden, a=ar: self.hidden_tools_menu(h, (a.right + 8, a.y)),
                             "More tools: there is not enough height for all of them")
            draw_icon(self.screen, "tri_d", ar, (200, 200, 205))
        self.draw_swatches(12, min(y + 8, self.r_tool.bottom - 64))

    def hidden_tools_menu(self, hidden, pos):
        items = []
        for slot in hidden:
            for tid in slot:
                n, k, _ = TOOL_INFO[tid]
                items.append((f"{n}" + (f"  ({k})" if k else ""), (lambda tid=tid: self.set_tool(tid))))
        self.ctx = {"pos": pos, "items": items}

    def pick_flyout(self, tid):
        self.set_tool(tid)
        self.flyout = None

    def draw_flyout(self):
        self.flyout_rects = []
        if self.flyout is None:
            return
        slot, rc = SLOTS[self.flyout], self.slot_pos[self.flyout]
        self.hit((0, 0, self.W, self.H), lambda mx, my: setattr(self, "flyout", None))
        box = pygame.Rect(rc.right + 8, rc.y, 192, len(slot) * 32 + 8)
        self.rrect(box, (30, 30, 34), 12)
        self.rrect(box, (80, 80, 92), 12, 1)
        self.hit(box, lambda mx, my: None)
        for j, tid in enumerate(slot):
            it = pygame.Rect(box.x + 4, box.y + 4 + j * 32, 184, 32)
            if self.hovering(it):
                self.rrect(it, COLOR_HOVER, 8)
            ic = load_icon_state(tid, 30, "hover" if self.hovering(it) else "default")[0]
            ir = pygame.Rect(it.x + 2, it.y + 1, 30, 30)
            if ic:
                self.screen.blit(ic, ir)
            else:
                draw_tool_icon(self.screen, tid, ir, (235, 235, 235))
            n, k, _ = TOOL_INFO[tid]
            self.txt(n, it.x + 40, it.y + 9)
            self.txt(k, it.right - 12, it.y + 9, self.f11, COLOR_MUTED, right=True)
            self.flyout_rects.append((it, tid))
            self.hit(it, lambda mx, my, tid=tid: self.pick_flyout(tid))

    def flyout_release(self, pos):
        if self.flyout is not None:
            for rect, tid in getattr(self, "flyout_rects", []):
                if rect.collidepoint(pos):
                    self.pick_flyout(tid)
                    return

    # ------------------------------------------------------- colours / picker
    def color_get(self, field):
        if field == "cap":
            return (self.psel.caption_color if self.psel and self.psel.caption_color else (230, 230, 235)), 100.0
        if field == "art":
            return self.art_color, 100.0
        if field.startswith("lab:"):
            return tuple(self.label_list[int(field[4:])][1]), 100.0
        o = self.psel
        if o:
            return (o.fill, o.fill_a) if field == "fill" else (o.stroke, o.stroke_a)
        return (self.def_fill if field == "fill" else self.def_stroke), 100.0

    def color_set(self, field, rgb, alpha):
        rgb = tuple(rgb)
        if field == "cap":
            for o in self.sel:
                o.caption_color = rgb
            return
        if field == "art":
            self.art_color = rgb
            return
        if field.startswith("lab:"):
            self.label_list[int(field[4:])][1] = rgb
            self.labels_sync()
            self.save_prefs()
            return
        if field == "fill":                                 # also remembered as the colour for the next shapes / fill bucket
            self.def_fill = rgb
        else:
            self.def_stroke = rgb
        for o in self.sel:
            if field == "fill":
                o.fill, o.fill_a, o.fill_on = rgb, alpha, True
            else:
                o.stroke, o.stroke_a, o.stroke_on = rgb, alpha, True

    def open_picker(self, field, anchor):
        rgb, a = self.color_get(field)
        h, s, v = rgb_to_hsv(rgb)
        box = pygame.Rect(anchor[0], anchor[1], 240, 344)
        box.x = clamp(box.x, 8, self.W - 248)
        box.y = clamp(box.y, 8, self.H - 352)
        self.picker = {"field": field, "h": h, "s": s, "v": v, "a": a, "rect": box, "sv_h": None}
        if not hasattr(self, "_hue_bar"):
            t = pygame.Surface((7, 1))
            for i, c in enumerate([(255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255),
                                   (255, 0, 255), (255, 0, 0)]):
                t.set_at((i, 0), c)
            self._hue_bar = rounded_surface(pygame.transform.smoothscale(t, (168, 16)), 8)

    def close_picker(self):
        self.picker, self.eyedrop = None, False

    def picker_apply(self, p=None):
        p = p or self.picker
        self.color_set(p["field"], hsv_to_rgb(p["h"], p["s"], p["v"]), p["a"])

    def picker_set_rgb(self, rgb, p=None):
        p = p or self.picker
        if not p:
            return
        h, s, v = rgb_to_hsv(rgb)
        if s > 0.001 and v > 0.001:
            p["h"] = h
        p["s"], p["v"] = s, v
        self.picker_apply()

    def draw_picker(self):
        p = self.picker
        if not p:
            return
        if not self.eyedrop:
            self.hit((0, 0, self.W, self.H), lambda mx, my: self.close_picker())
        b = p["rect"]
        self.rrect(b, (30, 30, 34), 16)
        self.rrect(b, (80, 80, 92), 16, 1)
        self.hit(b, lambda mx, my: None)
        x = b.x + 16
        self.txt("Custom", x, b.y + 14, self.fb2)
        cl = pygame.Rect(b.right - 40, b.y + 8, 32, 32)
        self.flat_button(cl, lambda mx, my: self.close_picker())
        pygame.draw.line(self.screen, (200, 200, 200), (cl.centerx - 5, cl.centery - 5), (cl.centerx + 5, cl.centery + 5), 2)
        pygame.draw.line(self.screen, (200, 200, 200), (cl.centerx + 5, cl.centery - 5), (cl.centerx - 5, cl.centery + 5), 2)
        self.picker_body(p, b)

    def ensure_hue_bar(self):
        if not hasattr(self, "_hue_bar"):
            t = pygame.Surface((7, 1))
            for i, c in enumerate([(255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 0, 255), (255, 0, 0)]):
                t.set_at((i, 0), c)
            self._hue_bar = rounded_surface(pygame.transform.smoothscale(t, (168, 16)), 8)

    def picker_body(self, p, b):
        """The colour wheel area (also used permanently inside the Drawing panel)."""
        x = b.x + 16
        self.ensure_hue_bar()
        # saturation / value square
        sv = pygame.Rect(x, b.y + 44, 208, 176)
        if p["sv_h"] != p["h"]:
            t = pygame.Surface((2, 2))
            t.set_at((0, 0), (255, 255, 255))
            t.set_at((1, 0), hsv_to_rgb(p["h"], 1, 1))
            t.set_at((0, 1), (0, 0, 0))
            t.set_at((1, 1), (0, 0, 0))
            p["sv_img"], p["sv_h"] = rounded_surface(pygame.transform.smoothscale(t, sv.size), 12), p["h"]
        self.screen.blit(p["sv_img"], sv.topleft)

        def sv_start(mx, my):
            def u(mx, my):
                p["s"], p["v"] = clamp((mx - sv.x) / sv.w, 0, 1), 1 - clamp((my - sv.y) / sv.h, 0, 1)
                self.picker_apply(p)
            u(mx, my)
            return u
        self.hit(sv, sv_start)
        cur = hsv_to_rgb(p["h"], p["s"], p["v"])
        mk = (int(sv.x + p["s"] * sv.w), int(sv.y + (1 - p["v"]) * sv.h))
        pygame.draw.circle(self.screen, cur, mk, 7)
        pygame.draw.circle(self.screen, (255, 255, 255), mk, 8, 3)
        # eyedropper
        ey = pygame.Rect(x, b.y + 242, 32, 32)
        self.flat_button(ey, lambda mx, my: (setattr(self, "eyedrop", True), setattr(self, "eyedrop_p", p)), "Eyedropper: click any pixel on screen",
                         self.eyedrop)
        pygame.draw.line(self.screen, (220, 220, 220), (ey.centerx - 6, ey.centery + 6), (ey.centerx + 3, ey.centery - 3), 3)
        pygame.draw.circle(self.screen, (220, 220, 220), (ey.centerx + 5, ey.centery - 5), 4)
        # hue bar
        hb = pygame.Rect(x + 40, b.y + 236, 168, 16)
        self.screen.blit(self._hue_bar, hb.topleft)

        def hue_start(mx, my):
            def u(mx, my):
                p["h"] = clamp((mx - hb.x) / hb.w, 0, 0.999)
                self.picker_apply(p)
            u(mx, my)
            return u
        self.hit(hb.inflate(0, 12), hue_start)
        pygame.draw.circle(self.screen, hsv_to_rgb(p["h"], 1, 1), (int(hb.x + p["h"] * hb.w), hb.centery), 7)
        pygame.draw.circle(self.screen, (255, 255, 255), (int(hb.x + p["h"] * hb.w), hb.centery), 8, 3)
        # alpha bar
        ab = pygame.Rect(x + 40, b.y + 264, 168, 16)
        if p.get("ab_key") != cur:
            sf = pygame.Surface(ab.size)
            for cx in range(0, ab.w, 8):
                for cy in range(0, ab.h, 8):
                    sf.fill((90, 90, 90) if (cx // 8 + cy // 8) % 2 else (60, 60, 60), (cx, cy, 8, 8))
            ov = pygame.Surface(ab.size, pygame.SRCALPHA)
            for cx in range(ab.w):
                pygame.draw.line(ov, (*cur, int(255 * cx / ab.w)), (cx, 0), (cx, ab.h))
            sf.blit(ov, (0, 0))
            p["ab_img"], p["ab_key"] = rounded_surface(sf, 8), cur
        self.screen.blit(p["ab_img"], ab.topleft)

        def a_start(mx, my):
            def u(mx, my):
                p["a"] = round(clamp((mx - ab.x) / ab.w, 0, 1) * 100)
                self.picker_apply(p)
            u(mx, my)
            return u
        self.hit(ab.inflate(0, 12), a_start)
        ax = int(ab.x + p["a"] / 100 * ab.w)
        pygame.draw.circle(self.screen, (255, 255, 255), (ax, ab.centery), 8, 3)
        # hex + opacity
        row = b.y + 296
        self.rrect((x, row, 56, 32), COLOR_BTN, 8)
        self.txt("Hex", x + 12, row + 9)
        draw_icon(self.screen, "tri_d", pygame.Rect(x + 36, row + 8, 16, 16), (170, 170, 170))
        self.field((x + 64, row, 88, 32), rgb_to_hex(cur), lambda s: self.picker_set_rgb(hex_to_rgb(s) or cur, p),
                   "pk_hex", hint="Hex colour, e.g. 1631A7")
        self.field((x + 160, row, 32, 32), f"{p['a']:.0f}", lambda v: (p.__setitem__("a", clamp(v, 0, 100)), self.picker_apply(p)),
                   "pk_a", numeric=True, center=True, hint="Opacity %")
        self.txt("%", x + 196, row + 9, self.f11, COLOR_MUTED)

    def draw_swatches(self, x, y):
        """Adobe-style Fill / Stroke: two overlapping squares, swap arrow, reset to defaults."""
        fill, _ = self.color_get("fill")
        stroke, _ = self.color_get("stroke")
        st, fr = pygame.Rect(x + 14, y + 14, 26, 26), pygame.Rect(x, y, 26, 26)
        self.rrect(st, stroke, 6)
        self.rrect(st, (120, 120, 120), 6, 2)
        self.rrect(fr, fill, 6)
        self.rrect(fr, (230, 230, 230), 6, 2)
        sw = pygame.Rect(x + 30, y - 4, 16, 14)
        pygame.draw.lines(self.screen, (200, 200, 200), False, [(sw.x + 1, sw.bottom - 2), (sw.x + 1, sw.y + 4), (sw.right - 4, sw.y + 4)], 2)
        rpoly(self.screen, (200, 200, 200), [(sw.right, sw.y + 4), (sw.right - 6, sw.y), (sw.right - 6, sw.y + 8)], 1)
        df = pygame.Rect(x, y + 34, 16, 16)
        self.rrect((df.x + 6, df.y + 6, 9, 9), (15, 15, 15), 2)
        self.rrect((df.x + 6, df.y + 6, 9, 9), (200, 200, 200), 2, 1)
        self.rrect((df.x, df.y, 9, 9), (235, 235, 235), 2)
        anchor = (self.r_tool.right + 8, self.r_tool.y + 8)
        for rect, hint in ((fr, "Fill colour - click to open the colour picker"), (st, "Stroke colour - click to open the colour picker"),
                           (sw, "Swap Fill and Stroke"), (df, "Default colours")):
            if self.hovering(rect):
                self.hover_hint = hint
        self.hit(st, lambda mx, my: self.open_picker("stroke", anchor))
        self.hit(fr, lambda mx, my: self.open_picker("fill", anchor))
        self.hit(sw, lambda mx, my: self.swap_colors())
        self.hit(df, lambda mx, my: self.default_colors())

    def swap_colors(self):
        f, fa = self.color_get("fill")
        s, sa = self.color_get("stroke")
        self.color_set("fill", s, sa)
        self.color_set("stroke", f, fa)

    def default_colors(self):
        self.color_set("fill", (255, 255, 255), 100.0)          # D = white fill, black stroke
        self.color_set("stroke", (0, 0, 0), 100.0)

    # -------------------------------------------------------------- left panel
    def draw_left(self):
        r = self.r_left
        self.panel(r, "left")
        self.tabs(r.x, r.y, [("Footage", 88), ("Edit", 72)], self.left_tab, lambda n: setattr(self, "left_tab", n))
        x, y, w = r.x + 16, r.y + 40, r.w - 32
        if self.left_tab == "Footage":
            self.draw_footage(r, x, y, w)
            return
        o = self.psel
        if not o:
            self.txt("Select an object to", x, y, self.f12, COLOR_MUTED)
            self.txt("edit its values.", x, y + 20, self.f12, COLOR_MUTED)
            return
        self.txt(o.name if len(self.sel) == 1 else f"{len(self.sel)} objects", x, y, self.fb)
        y += 32
        prev = self.push_clip(r)
        for p in PROPS:
            if p in self.locked_props(o):
                continue                                  # joysticks: no rotation; the knob follows the frame's scale
            self.slider_row(x, y, w, o, p)
            y += 48
        k = self.button((x, y, w, 32), "Set Keyframe (K)", self.key_here, hint="Add or remove a keyframe on all properties")
        draw_icon(self.screen, "key", pygame.Rect(k.x + 8, k.y + 8, 16, 16), (235, 235, 235))
        self.pop_clip(prev)

    def slider_row(self, x, y, w, o, p):
        lo, hi = PROP_RANGE[p]
        if p == "x":
            hi = self.aw
        elif p == "y":
            hi = self.ah
        if p in ("x", "y") and o.parent:
            lo, hi = -1000, 1000
        v = self.val(o, p, self.frame)
        self.txt(PROP_LABEL[p], x, y + 4, self.f11, COLOR_MUTED)
        if p in o.expr:
            self.txt("fx", x + 72, y + 4, self.f11, COLOR_YELLOW)
        fmt = f"{v:.2f}" if p == "scale" else f"{v:.0f}"

        def commit(val, p=p, o=o):
            self.set_prop(o, p, round(val, 2) if p == "scale" else round(val, 1))
        self.field((x + w - 80, y - 4, 56, 24), fmt, commit, f"edit_{p}", numeric=True, center=True,
                   hint="Click to type a value")
        dc = (x + w - 8, y + 8)
        keyed, here = bool(o.keys[p]), self.frame in o.keys[p]
        if not o.owner:
            rdiamond(self.screen, dc, 6, COLOR_YELLOW if here else (150, 150, 150), keyed)
        if self.hovering(pygame.Rect(dc[0] - 10, dc[1] - 10, 20, 20)):
            self.hover_hint = f"Keyframe {PROP_LABEL[p]} at this frame"
        if not o.owner:
            self.hit((dc[0] - 10, dc[1] - 10, 20, 20), lambda mx, my: self.toggle_prop_key(o, p))
        tr = pygame.Rect(x, y + 28, w, 6)
        self.rrect(tr, (60, 60, 60), 3)
        t = clamp((v - lo) / (hi - lo), 0, 1)
        self.rrect((tr.x, tr.y, int(tr.w * t), tr.h), COLOR_ACCENT_L, 3)
        pygame.draw.circle(self.screen, (235, 235, 235), (tr.x + int(tr.w * t), tr.centery), 8)

        def start(mx, my):
            def upd(mx, my):
                val = lo + (hi - lo) * clamp((mx - tr.x) / tr.w, 0, 1)
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:        # stepped values
                    st = SHIFT_STEP[p]
                    val = round(val / st) * st
                self.set_prop(o, p, round(val, 2) if p == "scale" else round(val))
            upd(mx, my)
            return upd
        self.hit(tr.inflate(16, 20), start)

    # ------------------------------------------------------------- right panel
    def draw_right(self):
        r = self.r_right
        self.panel(r, "right")
        self.tabs(r.x, r.y, [("Properties", 80), ("Layers", 72), ("Library", 72)], self.right_tab,
                  lambda n: setattr(self, "right_tab", n))
        prev = self.push_clip(r)
        if self.right_tab == "Properties":                          # long panel: scroll with the wheel
            self.right_scroll = clamp(self.right_scroll, 0, self.right_max)
            self._content_end = 0
            self.hit_clip = pygame.Rect(r.x, r.y + 26, r.w, r.h - 26)
            try:
                self.draw_properties(pygame.Rect(r.x, r.y - int(self.right_scroll), r.w, r.h))
            finally:
                self.hit_clip = None
            self.right_max = max(0, int(self._content_end + self.right_scroll - (r.bottom - 10)))
        else:
            {"Layers": self.draw_layers, "Library": self.draw_library}[self.right_tab](r)
        self.pop_clip(prev)

    def toggle_paint(self, field):
        if not self.psel:
            return
        on = not getattr(self.psel, field + "_on")
        for o in self.sel:
            setattr(o, field + "_on", on)

    def paint_section(self, x, y, w, o, field):
        on = getattr(o, field + "_on")
        self.checkbox(x, y, on, lambda mx, my: self.toggle_paint(field), f"Enable / disable {field}")
        self.txt(field.capitalize(), x + 28, y, self.fb)
        y += 28
        if not on:
            return y
        rgb, a = (o.fill, o.fill_a) if field == "fill" else (o.stroke, o.stroke_a)
        sw = pygame.Rect(x, y, 32, 32)
        self.rrect(sw, rgb, 8)
        self.rrect(sw, (200, 200, 200), 8, 1)
        self.hit(sw, lambda mx, my: self.open_picker(field, (self.r_right.x - 248, y)))
        self.field((x + 40, y, w - 40 - 64, 32), rgb_to_hex(rgb),
                   lambda s, f=field, a=a: self.color_set(f, hex_to_rgb(s) or rgb, a), f"hex_{field}",
                   hint="Hex colour")
        self.field((x + w - 56, y, 40, 32), f"{a:.0f}", lambda v, f=field, rgb=rgb: self.color_set(f, rgb, clamp(v, 0, 100)),
                   f"op_{field}", numeric=True, center=True, hint="Opacity %")
        self.txt("%", x + w - 12, y + 9, self.f11, COLOR_MUTED)
        y += 40
        if field == "stroke":
            self.button((x, y, w // 2 - 4, 32), "Center", lambda mx, my: self.msg("Stroke alignment: coming soon"))
            self.field((x + w // 2 + 4, y, w // 2 - 4, 32), f"{o.stroke_w:g}",
                       lambda v: [setattr(s, "stroke_w", clamp(v, 0.5, 200)) for s in self.sel], "stroke_w", numeric=True,
                       center=True, hint="Stroke width")
            y += 40
        return y

    def draw_properties(self, r):
        x, y, w = r.x + 16, r.y + 40, r.w - 32
        o = self.psel
        if not o:
            self.txt("No selection", x, y, self.fb)
            y += 32
            self.txt("Document", x, y, self.fb)
            y += 28
            self.txt("Artboard", x, y + 9, self.f11, COLOR_MUTED)
            sw = pygame.Rect(x + 72, y, 32, 32)
            self.rrect(sw, self.art_color, 8)
            self.rrect(sw, (200, 200, 200), 8, 1)
            self.hit(sw, lambda mx, my: self.open_picker("art", (self.r_right.x - 248, y)))
            if self.hovering(sw):
                self.hover_hint = "Artboard colour - click to open the colour picker"
            self.field((x + 112, y, w - 112, 32), rgb_to_hex(self.art_color),
                       lambda s: setattr(self, "art_color", hex_to_rgb(s) or self.art_color), "art_hex", hint="Hex colour")
            y += 40
            for label, attr, lo, hi in (("Width", "aw", 16, 16384), ("Height", "ah", 16, 16384), ("FPS", "fps", 1, 240),
                                        ("Frames", "total", 1, 10000)):
                self.txt(label, x, y + 9, self.f11, COLOR_MUTED)
                self.field((x + 72, y, w - 72, 32), getattr(self, attr),
                           lambda v, a=attr, lo=lo, hi=hi: self.set_doc(a, v, lo, hi), f"doc_{attr}",
                           numeric=True, center=True, hint=f"Document {label.lower()}")
                y += 40
            self.txt("Objects", x, y + 2, self.f11, COLOR_MUTED)
            self.txt(len(self.objs), x + w, y + 2, self.f12, COLOR_TEXT, right=True)
            y += 28
            self.button((x, y, w, 32), "+ Null Control", lambda mx, my: self.new_obj("null", self.aw // 2, self.ah // 2))
            self.button((x, y + 40, w, 32), "+ Box Object", lambda mx, my: self.new_obj("rect", self.aw // 2, self.ah // 2))
            return
        th = pygame.Rect(x, y, 112, 62)                                    # what is on the layer
        if o.kind not in ("vlayer", "rlayer") or o.kind == "rlayer" or o.items:
            self.node_thumb(o, th)
        else:
            self.rrect(th, (22, 22, 24), 6)
        pcl = self.push_clip((x + 124, y, w - 124, 62))
        self.txt(o.name if len(self.sel) == 1 else f"{len(self.sel)} objects", x + 124, y + 4, self.fb2)
        self.pop_clip(pcl)
        self.txt(f"Frame {self.frame}", x, y + 66, self.f11, COLOR_MUTED)
        y += 92
        self.button((x, y, w, 34), "Click a parent..." if self.link_mode else "Link to Parent", self.toggle_link_mode,
                    color=COLOR_ACCENT_L if self.link_mode else COLOR_BTN, radius=17, font=self.f12,
                    hint="Link: select children, press this, then click the object that should be their parent. "
                         "Children then follow the parent's movement, rotation and scale.")
        y += 44
        if o.parent:
            self.txt("Parent: " + o.parent.name, x, y + 6, self.f12)
            self.button((x + w - 64, y, 64, 24), "Unlink", lambda mx, my: self.unlink(o), radius=12)
            y += 32
        kids = [c.name for c in self.objs if c.parent is o]
        if kids:
            self.txt("Children: " + ", ".join(kids), x, y, self.f11, COLOR_MUTED)
            y += 24
        if o.ik:
            self.button((x, y, w // 2 - 4, 32), "Flip IK", lambda mx, my, o=o: self.flip_ik(o), radius=8, hint="Bend the joint the other way")
            self.button((x + w // 2 + 4, y, w // 2 - 4, 32), "Remove IK", lambda mx, my, o=o: self.remove_ik(o), radius=8,
                        hint="Go back to rotating the bones by hand")
            y += 44
        if self.is_joy(o) or o.kind.startswith("ctrl"):             # name shown above sliders / controllers
            self.txt("Label", x, y + 9, self.f11, COLOR_MUTED)
            self.field((x + 56, y, w - 96, 32), o.caption, lambda s, o=o: setattr(o, "caption", s), "caption",
                       hint="Text shown above this slider / controller (what it controls)")
            csw = pygame.Rect(x + w - 32, y, 32, 32)
            self.rrect(csw, o.caption_color or (230, 230, 235), 16)
            self.rrect(csw, (200, 200, 200), 16, 1)
            if self.hovering(csw):
                self.hover_hint = "Colour of the label (so it never blends into the background)"
            self.hit(csw, lambda mx, my: self.open_picker("cap", (self.r_right.x - 248, y)))
            y += 44
        self.divider(x, y, w)
        y += 12
        self.heading(x, y, "Arrange", "Align to")
        y += 28
        if len(self.sel) >= 2:                                         # two or more objects: align to the artboard or to each other
            for i, (key, n) in enumerate((("artboard", "Artboard"), ("selection", "Selection"))):
                self.button((x + i * (w // 2 + 2), y, w // 2 - 2, 26), n, lambda mx, my, key=key: setattr(self, "align_to", key),
                            active=self.align_to == key, font=self.f11, hint="Align to the artboard, or to the selected objects")
            y += 32
        gap = (w - 4 * 40) // 3
        for i, kind in enumerate(("left", "bottom", "top", "right")):
            rc = self.flat_button((x + i * (40 + gap), y, 40, 40), lambda mx, my, k=kind: self.align(k),
                                  f"Align to the {kind} edge of the artboard")
            draw_arrange_icon(self.screen, kind, rc, (225, 225, 225))
        y += 48
        if not o.owner and o.kind not in ("null", "peg", "bone") and not o.kind.startswith("ctrl"):
            self.divider(x, y, w)                                # alpha matte (e.g. an eye shape that masks the pupil)
            y += 12
            self.heading(x, y, "Track matte", "alpha")
            y += 28
            self.button((x, y, w - 72, 32), (o.matte or "None") + "  v", lambda mx, my: self.matte_menu(o, (mx, my)), radius=8,
                        hint="Show this layer only where another layer is opaque (alpha matte)")
            self.button((x + w - 64, y, 64, 32), "Invert", lambda mx, my: setattr(o, "matte_inv", not o.matte_inv),
                        active=o.matte_inv, radius=8, hint="Use the opposite of the matte (show where it is transparent)")
            y += 40
            if o.matte:
                self.checkbox(x, y + 4, o.matte_show, lambda mx, my: setattr(o, "matte_show", not o.matte_show),
                              "Keep the matte layer visible too (e.g. the eye under the masked iris)")
                self.txt("Show the matte layer too", x + 28, y + 4)
                y += 32
            y += 4
        if not o.owner and not o.kind.startswith("ctrl") and not self.is_joy(o):
            self.button((x, y, w, 32), "Drive by controller...", lambda mx, my, o=o: self.drive_menu(o, (mx, my)), radius=8,
                        hint="Make this layer follow a joystick / controller; a negative multiplier moves the opposite way (pseudo 3D)")
            y += 44
        shapes = [s for s in self.sel if s.kind in ("rect", "ellipse", "polygon")]
        if len(shapes) >= 2:
            self.divider(x, y, w)
            y += 12
            self.heading(x, y, "Pathfinder", "Combine shapes")
            y += 28
            for i, kind in enumerate(("Unite", "Minus Front", "Intersect", "Exclude")):
                bx = x + i * (40 + gap)
                rc = self.flat_button((bx, y, 40, 40), lambda mx, my, k=kind: self.msg(f"Pathfinder {k}: coming soon (needs vector paths)"),
                                      f"Pathfinder: {kind}")
                draw_pathfinder_icon(self.screen, kind, rc)
                self.txt(kind, bx + 20, y + 50, self.f11, COLOR_TEXT, center=True)
            y += 72
        if o.kind in ("null", "ctrl"):
            self.divider(x, y, w)
            y += 12
            self.heading(x, y, "Controller")
            self.txt("Link objects to this layer, or use Schematic.", x, y + 24, self.f11, COLOR_MUTED)
        if o.kind in VECTOR_KINDS:
            self.divider(x, y, w)
            y += 12
            y = self.paint_section(x, y, w, o, "stroke")
            y += 8
            y = self.paint_section(x, y, w, o, "fill")
        self._content_end = max(self._content_end, y)

    def align(self, kind):
        objs = [o for o in self.sel if not o.locked]
        boxes = {}
        for o in objs:
            q = [self.s2a(*p) for p in self.box_pts(o, 0)]
            boxes[id(o)] = (min(p[0] for p in q), max(p[0] for p in q), min(p[1] for p in q), max(p[1] for p in q))
        if len(objs) >= 2 and self.align_to == "selection":              # align the objects to each other
            ref = (min(b[0] for b in boxes.values()), max(b[1] for b in boxes.values()),
                   min(b[2] for b in boxes.values()), max(b[3] for b in boxes.values()))
        else:
            ref = (0, self.aw, 0, self.ah)
        for o in objs:
            x1, x2, y1, y2 = boxes[id(o)]
            x, y = self.world(o, self.frame)[:2]
            dx = dy = 0.0
            if kind == "left":
                dx = ref[0] - x1
            elif kind == "right":
                dx = ref[1] - x2
            elif kind == "top":
                dy = ref[2] - y1
            else:
                dy = ref[3] - y2
            self.set_world_pos(o, x + dx, y + dy)

    def toggle_link_mode(self, mx=0, my=0):
        self.link_mode = not self.link_mode
        self.msg("Click the object that should become the parent (Esc cancels)" if self.link_mode else "Link cancelled")

    def draw_layers(self, r):
        x, y, w = r.x + 8, r.y + 40, r.w - 16
        self.button((x, y, w, 28), "+ New Layer", lambda mx, my: setattr(self, "layer_dlg", True), radius=14,
                    hint="New layer: choose vector or raster")
        y += 36
        for o in self.objs:
            row = pygame.Rect(x, y, w, 32)
            if o in self.sel:
                self.rrect(row, (56, 60, 72), 8)
            elif o is self.hover:
                self.rrect(row, (36, 46, 90), 8)
            self.row_rects.append((row, o))
            self.hit(row, lambda mx, my, o=o: (self.layer_click(o), self.layer_double_click(o)) and None)
            eye = pygame.Rect(x + 4, y + 4, 24, 24)
            self.eye_icon(eye.centerx, eye.centery, (220, 220, 220) if o.visible else (80, 80, 80))
            if self.hovering(eye):
                self.hover_hint = "Show / hide layer"
            self.hit(eye, lambda mx, my, o=o: self.toggle_flag(o, "visible"))
            lk = pygame.Rect(x + 32, y + 4, 24, 24)
            self.lock_icon(lk.centerx, lk.centery, (220, 220, 220) if o.locked else (80, 80, 80), o.locked)
            if self.hovering(lk):
                self.hover_hint = "Lock layer (locked layers cannot be picked on the artboard)"
            self.hit(lk, lambda mx, my, o=o: self.toggle_flag(o, "locked"))
            rd = pygame.Rect(x + 60, y + 4, 24, 24)
            pygame.draw.circle(self.screen, COLOR_TEAL if o.render else (80, 80, 80), rd.center, 6, 0 if o.render else 2)
            if self.hovering(rd):
                self.hover_hint = "Render: include this layer in the final render"
            self.hit(rd, lambda mx, my, o=o: setattr(o, "render", not o.render))
            pygame.draw.circle(self.screen, o.fill, (x + 98, y + 16), 5)
            rid = f"rename_{id(o)}"
            if self.edit and self.edit.get("id") == rid:
                self.field((x + 108, y + 4, w - 112, 24), o.name, lambda s, o=o: self.rename_obj(o, s), rid)
            else:
                self.txt(o.name + ("  > " + o.parent.name if o.parent else ""), x + 112, y + 9)
            y += 36

    def draw_library(self, r):
        x, y, w = r.x + 16, r.y + 40, r.w - 32
        for i, m in enumerate(("Objects", "Explorer")):
            self.button((x + i * (w // 2 + 2), y, w // 2 - 2, 28), m, lambda mx, my, m=m: setattr(self, "lib_mode", m),
                        active=self.lib_mode == m, radius=14,
                        hint="Saved objects" if m == "Objects" else "Browse files on your disk and import them as footage")
        y += 36
        if self.lib_mode == "Explorer":
            self.draw_explorer(r, x, y, w)
            return
        self.button((x, y, w // 2 - 4, 32), "Save selected", self.lib_save_selected, radius=8)
        self.button((x + w // 2 + 4, y, w // 2 - 4, 32), "From project...", lambda mx, my: self.open_dialog(
            "LIBRARY", "Import objects from a project", PROJECTS_DIR, "", "Import", self.import_to_library, dirs=True), radius=8)
        y += 48
        if not self.library:
            self.txt("The library is empty.", x, y, self.f11, COLOR_MUTED)
            self.txt("Save the selected object or import", x, y + 16, self.f11, COLOR_MUTED)
            self.txt("objects from another project.", x, y + 32, self.f11, COLOR_MUTED)
            return
        cw = (w - 8) // 2
        for idx in range(self.lib_scroll * 2, len(self.library)):
            i = idx - self.lib_scroll * 2
            cx, cy = x + (i % 2) * (cw + 8), y + (i // 2) * 104
            if cy > r.bottom:
                break
            card = pygame.Rect(cx, cy, cw, 96)
            self.rrect(card, COLOR_HOVER if self.hovering(card) else COLOR_BTN, 12)
            d = self.library[idx]
            th = pygame.Rect(0, 0, 40, 40)
            th.center = (card.centerx, card.y + 36)
            self.rrect(th, tuple(d["fill"]), 8)
            self.txt(d["name"][:16], card.centerx, card.bottom - 16, self.f11, center=True)
            self.hit(card, lambda mx, my, idx=idx: self.lib_insert(idx))
            xr = pygame.Rect(card.right - 24, card.y + 4, 20, 20)
            self.txt("x", xr.centerx, xr.centery, self.fb, COLOR_MUTED, center=True)
            self.hit(xr, lambda mx, my, idx=idx: self.lib_delete(idx))

    # ---------------------------------------------------------------- footage
    def draw_footage(self, r, x, y, w):
        self.button((x, y, w // 2 - 4, 32), "Import...", self.show_explorer,
                    hint="Import: browse your disk in Library > Explorer, double-click a file")
        self.button((x + w // 2 + 4, y, w // 2 - 4, 32), "+ Solid", self.new_solid,
                    hint="New solid: a flat colour layer (uses the current fill colour)")
        y += 40
        area = pygame.Rect(r.x + 8, y, r.w - 16, r.bottom - y - 56)
        if not self.footage:
            self.txt("No footage yet.", x, y + 4, self.f12, COLOR_MUTED)
            self.txt("Import images, sequences, video", x, y + 24, self.f11, COLOR_MUTED)
            self.txt("or audio, or create a solid.", x, y + 40, self.f11, COLOR_MUTED)
        used = {o.src for o in self.objs if o.src is not None}
        pc = self.push_clip(area)
        for i, fo in enumerate(self.footage[self.foot_scroll:]):
            rc = pygame.Rect(x, y + i * 44, w, 40)
            if rc.y > area.bottom:
                break
            sel = fo["id"] == self.foot_sel
            self.rrect(rc, COLOR_ACCENT if sel else (COLOR_HOVER if self.hovering(rc) else COLOR_BTN), 8)
            th = pygame.Rect(rc.x + 6, rc.y + 6, 40, 28)
            self.footage_thumb(fo, th)
            pcl = self.push_clip((rc.x + 52, rc.y, rc.w - 56, rc.h))
            self.txt(fo["name"], rc.x + 52, rc.y + 4)
            sub = {"image": f"Image {fo['w']}x{fo['h']}", "sequence": f"Sequence, {len(fo.get('files', []))} frames",
                   "video": "Video (linked)", "audio": "Audio (linked)", "solid": "Solid"}[fo["type"]]
            self.txt(sub + ("" if fo["id"] in used else "  - unused"), rc.x + 52, rc.y + 22, self.f11, COLOR_MUTED)
            self.pop_clip(pcl)
            self.hit(rc, lambda mx, my, fid=fo["id"]: self.footage_click(fid))
            self.hit(rc, lambda mx, my, fid=fo["id"]: self.footage_menu(fid, (mx, my)), (3,))
        self.pop_clip(pc)
        self.button((x, r.bottom - 48, w, 32), "Add to Scene", lambda mx, my: self.add_footage(), color=COLOR_ACCENT_L, radius=16,
                    hint="Add the selected footage to the scene (or double-click it). Right-click for more.")

    def footage_thumb(self, fo, rc):
        self.rrect(rc, (22, 22, 24), 6)
        t = fo["type"]
        if t == "solid":
            self.rrect(rc.inflate(-6, -6), tuple(fo["color"]), 4)
        elif t in ("image", "sequence"):
            path = self.footage_abs(fo, fo["files"][0] if t == "sequence" and fo.get("files") else None)
            sf = self.small_thumb(path, (rc.w - 4, rc.h - 4))
            if sf:
                self.screen.blit(sf, sf.get_rect(center=rc.center))
        elif t == "video":
            draw_icon(self.screen, "play", rc, (200, 200, 205))
        else:
            for k, hh in enumerate((6, 12, 8, 14, 6)):
                pygame.draw.line(self.screen, (200, 200, 205), (rc.x + 8 + k * 6, rc.centery - hh // 2), (rc.x + 8 + k * 6, rc.centery + hh // 2), 2)

    def ex_entries(self):
        try:
            names = sorted(os.listdir(self.ex_dir), key=str.lower)
        except OSError:
            return []
        dirs = [n for n in names if not n.startswith(".") and os.path.isdir(os.path.join(self.ex_dir, n))]
        files = [n for n in names if not n.startswith(".") and os.path.isfile(os.path.join(self.ex_dir, n))]
        out = [("..", "up")] if os.path.dirname(self.ex_dir) != self.ex_dir else []
        return (out + [(n, "dir") for n in dirs] + [(n, "file") for n in files])[:600]

    def ex_open(self, idx, entries):
        name, kind = entries[idx]
        now = pygame.time.get_ticks()
        dbl = self.ex_click[0] == idx and now - self.ex_click[1] < 400
        self.ex_sel, self.ex_click = idx, (idx, now)
        if not dbl:
            return
        if kind == "up":
            self.ex_dir, self.ex_scroll, self.ex_sel = os.path.dirname(self.ex_dir), 0, None
        elif kind == "dir":
            self.ex_dir, self.ex_scroll, self.ex_sel = os.path.join(self.ex_dir, name), 0, None
        else:
            self.import_footage(os.path.join(self.ex_dir, name))

    def draw_explorer(self, r, x, y, w):
        self.button((x, y, w // 2 - 4, 28), "Project", lambda mx, my: self.set_ex_dir(self.project_dir), radius=8, hint="Jump to the project folder")
        self.button((x + w // 2 + 4, y, w // 2 - 4, 28), "Home", lambda mx, my: self.set_ex_dir(os.path.expanduser("~")), radius=8, hint="Jump to your home folder")
        y += 36
        self.field((x, y, w, 28), self.ex_dir, lambda s: self.set_ex_dir(s), "ex_path", hint="Folder path")
        y += 36
        entries = self.ex_entries()
        self.ex_n = len(entries)
        self.ex_scroll = int(clamp(self.ex_scroll, 0, max(0, len(entries) - 8)))
        area = pygame.Rect(r.x + 8, y, r.w - 16, r.bottom - y - 8)
        pc = self.push_clip(area)
        for k, idx in enumerate(range(self.ex_scroll, len(entries))):
            rc = pygame.Rect(x, y + k * 34, w, 32)
            if rc.y > area.bottom:
                break
            name, kind = entries[idx]
            self.rrect(rc, COLOR_ACCENT if idx == self.ex_sel else (COLOR_HOVER if self.hovering(rc) else COLOR_PANEL), 8)
            ic = pygame.Rect(rc.x + 4, rc.y + 4, 24, 24)
            full = os.path.join(self.ex_dir, name)
            low = os.path.splitext(name)[1].lower()
            if kind in ("dir", "up"):
                self.rrect((ic.x + 1, ic.y + 6, 22, 15), (190, 160, 90), 4)
                self.rrect((ic.x + 1, ic.y + 3, 10, 6), (190, 160, 90), 2)
            elif low in IMG_EXT and (sf := self.small_thumb(full, (24, 24))):
                self.screen.blit(sf, sf.get_rect(center=ic.center))
            else:
                self.rrect((ic.x + 4, ic.y + 1, 16, 22), (110, 110, 120), 3)
                if low in VID_EXT:
                    draw_icon(self.screen, "play", ic, (230, 230, 235))
            pcl = self.push_clip((rc.x + 32, rc.y, rc.w - 36, rc.h))
            self.txt(name, rc.x + 34, rc.y + 8, self.f12, COLOR_TEXT if kind != "file" or low in IMG_EXT + VID_EXT + AUD_EXT else COLOR_MUTED)
            self.pop_clip(pcl)
            self.hit(rc, lambda mx, my, idx=idx, entries=entries: self.ex_open(idx, entries))
            if kind == "file" and low in IMG_EXT + VID_EXT + AUD_EXT:
                self.hit(rc, lambda mx, my, full=full: setattr(self, "ctx", {"pos": (mx, my), "items": [("Import to footage", lambda: self.import_footage(full))]}), (3,))
        self.pop_clip(pc)

    def set_ex_dir(self, d):
        if d and os.path.isdir(d):
            self.ex_dir, self.ex_scroll, self.ex_sel = os.path.abspath(d), 0, None
        else:
            self.msg("Folder not found")

    # --------------------------------------------------------------- transport
    def draw_transport(self):
        r = self.r_trans
        self.rrect(r, (46, 46, 50), 12)
        self.txt(f"F {self.frame} / {self.total}   {self.frame / self.fps:.2f}s", r.x + 16, r.centery - 7)
        items = [("first", lambda mx, my: self.goto(1), "Go to first frame", False),
                 ("prev", lambda mx, my: self.goto(self.frame - 1), "Previous frame (Left)", False),
                 ("stop", self.stop, "Stop and return to the first frame", False),
                 ("pause" if self.playing else "play", self.toggle_play, "Play / pause (Space)", self.playing),
                 ("next", lambda mx, my: self.goto(self.frame + 1), "Next frame (Right)", False),
                 ("last", lambda mx, my: self.goto(self.total), "Go to last frame", False),
                 ("loop", self.toggle_loop, "Loop playback", self.loop), None,
                 ("chev_l", lambda mx, my: self.jump_key(-1), "Previous keyframe", False),
                 ("key", self.key_here, "Set keyframe on the selected layer(s) at the playhead (K)", False),
                 ("chev_r", lambda mx, my: self.jump_key(1), "Next keyframe", False),
                 ("key_x", self.delete_keys_here, "Delete keyframes at the playhead on the selected layers", False),
                 ("key_all", self.select_keys_frame, "Select all keyframes at the playhead", False)]
        total = sum(16 if it is None else 36 for it in items)
        x = r.centerx - total // 2 + 40
        for it in items:
            if it is None:
                pygame.draw.line(self.screen, COLOR_LINE, (x + 8, r.y + 8), (x + 8, r.bottom - 8))
                x += 16
                continue
            icon, fn, hint, act = it
            self.icon_button((x, r.y, 32, 32), icon, fn, act, hint)
            x += 36

    # -------------------------------------------------------------------- menus
    def draw_menu_bar(self):
        x = 16
        for name in MENU_NAMES:
            w = self.f12.size(name)[0]
            rc = pygame.Rect(x - 8, 4, w + 16, 24)
            if self.menu_open == name:
                self.rrect(rc, COLOR_HOVER, 8)
            elif self.menu_open and self.hovering(rc):
                self.menu_open = name
            self.txt(name, x, 9)
            self.hit(rc, lambda mx, my, n=name: setattr(self, "menu_open", None if self.menu_open == n else n))
            x += w + 24
        widths = [self.f11.size(w)[0] + 32 for w in WORKSPACES]          # pills grow with their text
        wx = self.W - sum(widths) - 4 * len(WORKSPACES) - 8
        for ws, ww in zip(WORKSPACES, widths):
            self.button((wx, 4, ww, 24), ws, lambda mx, my, w=ws: setattr(self, "workspace", w),
                        active=ws == self.workspace, radius=12, font=self.f11, hint=f"{ws} workspace")
            wx += ww + 4

    def menu_items(self, name):
        soon = lambda n: (lambda: self.msg(f"{n}: coming soon"))          # noqa
        tog = lambda k: (lambda: self.view.__setitem__(k, not self.view[k]))  # noqa
        V = self.view
        return {
            "File": [("New Project...", lambda: self.guard(lambda: self.enter_start("new")), "", None),
                     ("Open Project...", lambda: self.guard(lambda: self.enter_start("load")), "", None), None,
                     ("Save Project", self.save_project, "Ctrl+S", None), ("Save As...", soon("Save As"), "", None), None,
                     ("Import Script...", self.open_script_dialog, "", None),
                     ("Import Asset...", self.show_explorer, "", None),
                     ("Export Render...", self.open_render, "Ctrl+M", None), None,
                     ("Close Project", lambda: self.guard(lambda: self.enter_start("load")), "", None),
                     ("Quit", self.request_quit, "", None)],
            "Edit": [("Undo", self.undo, "Ctrl+Z", None), ("Redo", self.redo, "Ctrl+Shift+Z", None), None,
                     ("Duplicate", self.duplicate_selected, "Ctrl+D", None),
                     ("Delete", self.delete_selected, "Del", None),
                     ("Select All", lambda: setattr(self, "sel", list(self.objs)), "Ctrl+A", None), None,
                     ("Preferences...", lambda: setattr(self, "prefs_open", True), "", None),
                     ("Keyboard Shortcuts...", lambda: self.open_info("KEYBOARD SHORTCUTS", SHORTCUTS), "", None)],
            "Object": [("New Layer...", lambda: setattr(self, "layer_dlg", True), "", None),
                       ("New Peg", lambda: self.new_obj("peg", self.aw // 2, self.ah // 2), "", None),
                       ("Reset Anchor Point", self.reset_anchor, "", None),
                       ("Create Skeleton from Selection", self.skeleton_from_selection, "", None), None,
                       ("Group", self.group_selected, "Ctrl+G", None), ("Ungroup", self.ungroup_selected, "", None),
                       ("Fold Layers", self.fold_selected, "", None),
                       ("Pre-compose...", soon("Pre-compose"), "", None), None,
                       ("Link to Parent", self.toggle_link_mode, "", None),
                       ("Unlink", lambda: [self.unlink(o) for o in self.sel], "", None),
                       ("Lock / Unlock", lambda: [setattr(o, "locked", not o.locked) for o in self.sel], "", None),
                       ("Hide / Show", lambda: [setattr(o, "visible", not o.visible) for o in self.sel], "", None), None,
                       ("Track Matte (mask)...", lambda: self.matte_menu(self.psel, pygame.mouse.get_pos()) if self.psel else self.msg("Select a layer first"), "", None)],
            "Type": [("Add Text Layer", soon("Text Layer"), "", None), ("Character...", soon("Character"), "", None)],
            "Effects": [(n, soon(n), "", None) for n in ("Blur", "Glow", "Drop Shadow", "Grain", "Tint")] +
                       [None, ("Open Fx Workspace", lambda: setattr(self, "workspace", "Fx"), "", None)],
            "View": [("Safe Zone", tog("safe"), "", V["safe"]), ("Grid 3x3", tog("grid3"), "", V["grid3"]),
                     ("Grayscale", tog("gray"), "", V["gray"]), ("3D View", soon("3D View"), "", None),
                     ("Onion Skin", tog("onion"), "", V["onion"]), ("Render Preview", tog("render"), "", V["render"]), None,
                     ("Set Work Area In", lambda: setattr(self, "work_in", self.frame), "I", None),
                     ("Set Work Area Out", lambda: setattr(self, "work_out", self.frame), "O", None),
                     ("Clear Work Area", lambda: (setattr(self, "work_in", None), setattr(self, "work_out", None)), "", None), None,
                     ("Fit to Window", lambda: setattr(self, "view_fit", True), "Home", None)],
            "Tools": [(TOOL_INFO[t][0], (lambda t=t: self.set_tool(t)), TOOL_INFO[t][1], self.tool == t) for s in SLOTS if s for t in s],
            "Panels": [("Toolbox", lambda: self.toggle_dock("toolbox"), "", "toolbox" not in self.hidden),
                       ("Edit Panel", lambda: self.toggle_dock("left"), "", "left" not in self.hidden),
                       ("Properties / Layers / Library", lambda: self.toggle_dock("right"), "", "right" not in self.hidden),
                       ("Timeline", lambda: self.toggle_dock("timeline"), "", "timeline" not in self.hidden), None,
                       ("Properties", lambda: setattr(self, "right_tab", "Properties"), "", None),
                       ("Layers", lambda: setattr(self, "right_tab", "Layers"), "", None),
                       ("Library", lambda: setattr(self, "right_tab", "Library"), "", None), None,
                       ("Level Strip", lambda: setattr(self, "workspace", "Drawing"), "", None),
                       ("Schematic", lambda: setattr(self, "workspace", "Schematic"), "", None),
                       ("Expressions", lambda: setattr(self, "workspace", "Expressions"), "", None)],
        }[name]

    def draw_menu_dropdown(self):
        name = self.menu_open
        if not name:
            return
        items = self.menu_items(name)
        x = 8
        for n in MENU_NAMES:
            if n == name:
                break
            x += self.f12.size(n)[0] + 24
        h = sum(8 if it is None else 24 for it in items) + 8
        box = pygame.Rect(x, 32, 248, h)
        self.hit((0, 0, self.W, self.H), lambda mx, my: setattr(self, "menu_open", None))
        self.rrect(box, (30, 30, 34), 12)
        self.rrect(box, (80, 80, 92), 12, 1)
        self.hit(box, lambda mx, my: None)
        y = box.y + 4
        for it in items:
            if it is None:
                pygame.draw.line(self.screen, COLOR_LINE, (box.x + 12, y + 4), (box.right - 12, y + 4))
                y += 8
                continue
            label, fn, key, chk = it
            rc = pygame.Rect(box.x + 4, y, box.w - 8, 24)
            if self.hovering(rc):
                self.rrect(rc, COLOR_HOVER, 8)
            if chk:
                pygame.draw.lines(self.screen, (255, 255, 255), False, [(rc.x + 8, rc.y + 12), (rc.x + 11, rc.y + 15), (rc.x + 16, rc.y + 8)], 2)
            self.txt(label, rc.x + 24, rc.y + 5)
            self.txt(key, rc.right - 8, rc.y + 5, self.f11, COLOR_MUTED, right=True)
            self.hit(rc, lambda mx, my, fn=fn: (setattr(self, "menu_open", None), fn())[0] if False else self.run_menu(fn))
            y += 24

    def matte_menu(self, o, pos):
        ok = ("vlayer", "rlayer", "rect", "ellipse", "polygon", "image", "line", "brush", "pill", "rsquare")   # no pegs, nulls, bones, controllers
        names = [x.name for x in self.objs if x is not o and x.kind in ok][:16]
        self.ctx = {"pos": pos, "items": [("None", lambda: setattr(o, "matte", None), None, not o.matte)] +
                    [(n, (lambda n=n: setattr(o, "matte", n)), None, o.matte == n) for n in names]}

    def draw_quit_dlg(self):
        q = self.quit_dlg
        if not q:
            return
        box = pygame.Rect(0, 0, 460, 200)
        box.center = (self.W // 2, self.H // 2)
        self.hit((0, 0, self.W, self.H), lambda mx, my: None, (1, 2, 3))
        self.rrect(box, (32, 34, 40), 16)
        self.rrect(box, (70, 70, 78), 16, 1)
        self.hit(box, lambda mx, my: None, (1, 2, 3))
        self.txt("Unsaved changes", box.x + 24, box.y + 20, self.f20)
        self.txt(f"Save the changes to \"{self.project_name}\" first?", box.x + 24, box.y + 64, self.f12)
        self.txt("Discard Changes closes without saving.", box.x + 24, box.y + 88, self.f11, COLOR_MUTED)

        def finish(save):
            self.quit_dlg = None
            if save:
                self.save_project(quiet=True)
            q["after"]()
        by = box.bottom - 24 - 36
        self.button((box.x + 24, by, 100, 36), "Cancel", lambda mx, my: setattr(self, "quit_dlg", None), radius=18)
        self.button((box.right - 24 - 120 - 148, by, 140, 36), "Discard Changes", lambda mx, my: finish(False), radius=18)
        self.button((box.right - 24 - 120, by, 120, 36), "Save", lambda mx, my: finish(True), color=COLOR_ACCENT_L, radius=18, font=self.fb)

    def draw_marker_dlg(self):
        m = self.marker_dlg
        if not m:
            return
        box = pygame.Rect(0, 0, 420, 250)
        box.center = (self.W // 2, self.H // 2)
        self.hit((0, 0, self.W, self.H), lambda mx, my: setattr(self, "marker_dlg", None))
        self.rrect(box, (32, 34, 40), 16)
        self.rrect(box, (70, 70, 78), 16, 1)
        self.hit(box, lambda mx, my: None)
        self.txt(f"Marker at frame {m['f']}", box.x + 24, box.y + 20, self.f20)
        self.field((box.x + 24, box.y + 64, box.w - 48, 32), m["text"], lambda s: m.__setitem__("text", s), "marker_text", hint="Marker text")
        for i, (n, c) in enumerate(self.label_list):
            sw = pygame.Rect(box.x + 24 + (i % 8) * 46, box.y + 112 + (i // 8) * 40, 36, 32)
            self.rrect(sw, c, 8)
            if list(c) == list(m["color"]):
                self.rrect(sw, (255, 255, 255), 8, 2)
            self.hit(sw, lambda mx, my, c=c: m.__setitem__("color", list(c)))
        self.button((box.x + 24, box.bottom - 24 - 32, 100, 32), "Delete", lambda mx, my: (self.markers.remove(m) if m in self.markers else None, setattr(self, "marker_dlg", None)), radius=16)
        self.button((box.right - 24 - 100, box.bottom - 24 - 32, 100, 32), "Done", lambda mx, my: setattr(self, "marker_dlg", None), color=COLOR_ACCENT_L, radius=16)

    def draw_suggestions(self):
        sg = self.expr_suggestions()
        if not sg or not self.edit or "rect" not in self.edit:
            return
        r = self.edit["rect"]
        box = pygame.Rect(r.x, r.bottom + 2, max(r.w, 220), 24 * len(sg) + 8)
        self.rrect(box, (24, 24, 28), 10)
        self.rrect(box, (90, 90, 104), 10, 1)
        for i, (label, rep, ins) in enumerate(sg):
            rc = pygame.Rect(box.x + 4, box.y + 4 + i * 24, box.w - 8, 24)
            if i == min(self.sugg_i, len(sg) - 1):
                self.rrect(rc, COLOR_ACCENT, 8)
            self.txt(label, rc.x + 10, rc.y + 5, self.f12)
            self.sugg_rects.append((rc, i))
        self.txt("Tab = insert", box.right - 8, box.bottom - 18, self.f11, COLOR_MUTED, right=True)

    def draw_rename_dlg(self):
        d = self.rename_dlg
        if not d:
            return
        box = pygame.Rect(0, 0, 520, 360)
        box.center = (self.W // 2, self.H // 2)
        self.hit((0, 0, self.W, self.H), lambda mx, my: None, (1, 2, 3))
        self.rrect(box, (32, 34, 40), 16)
        self.rrect(box, (70, 70, 78), 16, 1)
        self.hit(box, lambda mx, my: None, (1, 2, 3))
        self.txt(f"Rename  ({len(d['targets'])} layer(s))", box.x + 24, box.y + 20, self.f20)
        self.checkbox(box.right - 130, box.y + 26, d["suffix_on"], lambda mx, my: d.__setitem__("suffix_on", not d["suffix_on"]), "Add the suffix")
        self.txt("Suffix", box.right - 102, box.y + 26)
        fx, fw, y = box.x + 110, box.w - 134, box.y + 72
        self.txt("Replace", box.x + 24, y + 9)
        self.field((fx, y, fw, 32), d["find"], lambda s: d.__setitem__("find", s), "rn_find", hint="The part of the name to replace")
        y += 48
        self.txt("With", box.x + 24, y + 9)
        self.field((fx, y, fw, 32), d["repl"], lambda s: d.__setitem__("repl", s), "rn_repl", hint="What it becomes")
        y += 48
        self.txt("Suffix", box.x + 24, y + 9, color=COLOR_TEXT if d["suffix_on"] else COLOR_MUTED)
        self.field((fx, y, fw, 32), d["suffix"], lambda s: d.__setitem__("suffix", s), "rn_suffix",
                   hint="Appended to every name, e.g. _L. A # becomes a running number: _# gives _1, _2, _3")
        y += 44
        self.txt("# = running number   (_#  ->  _1, _2, _3)", fx, y, self.f11, COLOR_MUTED)
        y += 28
        for o, new in self.rename_preview(d)[:3]:
            self.txt(f"{o.name}   ->   {new}", box.x + 24, y, self.f11)
            y += 18
        by = box.bottom - 24 - 36
        self.button((box.x + 24, by, 110, 36), "Cancel", lambda mx, my: setattr(self, "rename_dlg", None), radius=18)
        self.button((box.right - 24 - 130, by, 130, 36), "Confirm", lambda mx, my: self.apply_rename(), color=COLOR_ACCENT_L, radius=18, font=self.fb)

    def draw_seq_dlg(self):
        d = self.seq_dlg
        if not d:
            return
        box = pygame.Rect(0, 0, 460, 210)
        box.center = (self.W // 2, self.H // 2)
        self.hit((0, 0, self.W, self.H), lambda mx, my: None, (1, 2, 3))
        self.rrect(box, (32, 34, 40), 16)
        self.rrect(box, (70, 70, 78), 16, 1)
        self.hit(box, lambda mx, my: None, (1, 2, 3))
        self.txt("Numbered images found", box.x + 24, box.y + 20, self.f20)
        self.txt(f"{d['n']} files with consecutive numbers next to this one.", box.x + 24, box.y + 62, self.f12)
        self.checkbox(box.x + 24, box.y + 96, d["as_seq"], lambda mx, my: d.__setitem__("as_seq", not d["as_seq"]), "Import all of them as one image sequence")
        self.txt("Sequence", box.x + 52, box.y + 96)
        self.txt("Off = import only the file you chose, as a single image.", box.x + 24, box.y + 122, self.f11, COLOR_MUTED)
        by = box.bottom - 24 - 36
        self.button((box.x + 24, by, 100, 36), "Cancel", lambda mx, my: setattr(self, "seq_dlg", None), radius=18)
        self.button((box.right - 24 - 120, by, 120, 36), "Import",
                    lambda mx, my: (setattr(self, "seq_dlg", None), self.import_footage(d["path"], as_seq=d["as_seq"])),
                    color=COLOR_ACCENT_L, radius=18, font=self.fb)

    def draw_layer_dlg(self):
        if not self.layer_dlg:
            return
        box = pygame.Rect(0, 0, 440, 270)
        box.center = (self.W // 2, self.H // 2)
        self.hit((0, 0, self.W, self.H), lambda mx, my: setattr(self, "layer_dlg", False))
        self.rrect(box, (32, 34, 40), 16)
        self.rrect(box, (70, 70, 78), 16, 1)
        self.hit(box, lambda mx, my: None)
        self.txt("New Layer", box.x + 24, box.y + 20, self.f20)
        self.txt("What are you going to draw on it?", box.x + 24, box.y + 52, self.f12, COLOR_MUTED)
        for i, (kind, title, d1, d2) in enumerate((("vlayer", "Vector", "Shapes and strokes", "you can edit later"),
                                                    ("rlayer", "Raster", "Pixels: paint", "and erase"))):
            card = pygame.Rect(box.x + 24 + i * 196, box.y + 84, 184, 120)
            self.rrect(card, COLOR_HOVER if self.hovering(card) else COLOR_BTN, 12)
            cx, cy = card.centerx, card.y + 32
            if kind == "vlayer":
                self.rrect((cx - 22, cy - 14, 28, 24), (200, 200, 205), 6, 2)
                pygame.draw.circle(self.screen, (200, 200, 205), (cx + 12, cy + 6), 11, 2)
            else:
                for gx in range(4):
                    for gy in range(3):
                        self.rrect((cx - 24 + gx * 13, cy - 14 + gy * 12, 9, 9), (200, 200, 205) if (gx + gy) % 2 else (90, 90, 96), 2)
            self.txt(title, cx, card.y + 66, self.fb2, center=True)
            self.txt(d1, cx, card.y + 88, self.f11, COLOR_MUTED, center=True)
            self.txt(d2, cx, card.y + 104, self.f11, COLOR_MUTED, center=True)
            self.hit(card, lambda mx, my, k=kind: self.new_layer(k))
        self.button((box.right - 24 - 96, box.bottom - 24 - 28, 96, 28), "Cancel", lambda mx, my: setattr(self, "layer_dlg", False), radius=14)

    def draw_render_dlg(self):
        d = self.render_dlg
        if not d or self.rend_prog:
            return
        box = pygame.Rect(0, 0, 560, 400)
        box.center = (self.W // 2, self.H // 2)
        self.hit((0, 0, self.W, self.H), lambda mx, my: setattr(self, "render_dlg", None))
        self.rrect(box, (32, 34, 40), 16)
        self.rrect(box, (70, 70, 78), 16, 1)
        self.hit(box, lambda mx, my: None)
        self.txt("Render", box.x + 24, box.y + 20, self.f20)
        x, y, fx, fw = box.x + 24, box.y + 72, box.x + 136, box.w - 160
        self.txt("Name", x, y + 9)
        self.field((fx, y, fw, 32), d["name"], lambda s: d.__setitem__("name", s), "rd_name")
        y += 48
        self.txt("Format", x, y + 9)
        for i, n in enumerate(("H.264  (.mp4)", "PNG sequence")):
            self.button((fx + i * (fw // 2 + 4), y, fw // 2 - 4, 32), n, lambda mx, my, i=i: d.__setitem__("fmt", i),
                        active=d["fmt"] == i, radius=16)
        y += 48
        self.txt("Range", x, y + 9)
        for i, n in enumerate(("Whole timeline", "Work area (I / O)")):
            self.button((fx + i * (fw // 2 + 4), y, fw // 2 - 4, 32), n, lambda mx, my, i=i: d.__setitem__("range", i),
                        active=d["range"] == i, radius=16)
        y += 48
        self.txt("Path", x, y + 9)
        self.field((fx, y, fw, 32), d["path"], lambda s: d.__setitem__("path", s), "rd_path")
        y += 48
        ff = self.ffmpeg_path()
        self.txt("ffmpeg found - H.264 is ready." if ff else "ffmpeg not found: install it (sudo apt install ffmpeg) for H.264;",
                 fx, y, self.f11, (120, 200, 140) if ff else COLOR_YELLOW)
        if not ff:
            self.txt("until then the render is saved as a PNG sequence.", fx, y + 18, self.f11, COLOR_YELLOW)
        self.txt(f"{self.aw} x {self.ah}, {self.fps} fps, nulls / controllers / bones / pegs are not rendered", fx, y + 40, self.f11, COLOR_MUTED)
        self.button((box.right - 24 - 120, box.bottom - 24 - 36, 120, 36), "Render", self.run_render, color=COLOR_ACCENT_L, radius=18, font=self.fb)
        self.button((box.right - 24 - 120 - 112, box.bottom - 24 - 36, 100, 36), "Cancel", lambda mx, my: setattr(self, "render_dlg", None), radius=18)

    def draw_render_progress(self):
        if not self.rend_prog:
            return
        i, n = self.rend_prog
        ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        self.screen.blit(ov, (0, 0))
        box = pygame.Rect(0, 0, 400, 120)
        box.center = (self.W // 2, self.H // 2)
        self.rrect(box, (32, 34, 40), 16)
        self.txt(f"Rendering frame {i + 1} / {n}", box.centerx, box.y + 32, self.fb2, center=True)
        bar = pygame.Rect(box.x + 24, box.y + 64, box.w - 48, 12)
        self.rrect(bar, (50, 50, 56), 6)
        self.rrect((bar.x, bar.y, int(bar.w * (i + 1) / n), bar.h), COLOR_ACCENT_L, 6)

    PREF_SECTIONS = ["General", "Interface", "Labels", "Tools", "Preview", "Onion Skin"]

    def draw_prefs(self):
        if not self.prefs_open:
            return
        box = pygame.Rect(0, 0, 800, min(620, self.H - 24))
        box.center = (self.W // 2, self.H // 2)
        if not self.picker:
            self.hit((0, 0, self.W, self.H), lambda mx, my: setattr(self, "prefs_open", False))
        self.rrect(box, (32, 34, 40), 16)
        self.hit(box, lambda mx, my: None)
        nav = pygame.Rect(box.x, box.y, 190, box.h)
        pygame.draw.rect(self.screen, (24, 25, 29), nav, border_top_left_radius=16, border_bottom_left_radius=16)
        self.rrect(box, (70, 70, 78), 16, 1)
        self.txt("Preferences", nav.x + 24, nav.y + 22, self.fb2)
        q, y = self.pref_q.lower(), nav.y + 64
        for n in self.PREF_SECTIONS:
            if q and q not in n.lower():
                continue
            rc = pygame.Rect(nav.x + 12, y, nav.w - 24, 32)
            if self.prefs_tab == n:
                self.rrect(rc, COLOR_ACCENT, 16)
            elif self.hovering(rc):
                self.rrect(rc, COLOR_HOVER, 16)
            self.txt(n, rc.x + 18, rc.y + 8)
            self.hit(rc, lambda mx, my, n=n: setattr(self, "prefs_tab", n))
            y += 36
        self.txt("Search", nav.x + 24, nav.bottom - 84, self.f11, COLOR_MUTED) if False else self.txt("Search", nav.x + 24, nav.bottom - 88, color=COLOR_MUTED)
        self.field((nav.x + 16, nav.bottom - 62, nav.w - 32, 32), self.pref_q, lambda s: setattr(self, "pref_q", s), "pref_q", hint="Filter the sections")
        self.button((box.right - 24 - 100, box.bottom - 24 - 36, 100, 36), "Close", lambda mx, my: setattr(self, "prefs_open", False),
                    color=COLOR_ACCENT_L, radius=18, font=self.fb)
        area = pygame.Rect(nav.right + 8, box.y + 8, box.w - nav.w - 16, box.h - 16 - 56)
        pc = self.push_clip(area)
        x0, y0, w0 = nav.right + 32, box.y + 28, box.w - nav.w - 64
        sec = self.prefs_tab
        self.txt(sec, x0, y0, self.f20)
        y0 += 44
        getattr(self, "pref_" + sec.lower().replace(" ", "_"))(x0, y0, w0, box)
        self.pop_clip(pc)

    def pref_general(self, x, y, w, box):
        self.checkbox(x, y + 4, self.autosave["on"], lambda mx, my: (self.autosave.__setitem__("on", not self.autosave["on"]), self.save_prefs()), "Autosave the project")
        self.txt("Autosave every", x + 28, y + 4)
        self.field((x + 160, y - 2, 56, 28), self.autosave["min"], lambda v: (self.autosave.__setitem__("min", int(clamp(v, 1, 120))), self.save_prefs()),
                   "autosave_min", numeric=True, center=True, hint="Minutes between autosaves")
        self.txt("min", x + 224, y + 4, self.f11, COLOR_MUTED)
        self.button((x, y + 52, 140, 32), "Clean cache", self.clean_cache, hint="Forget cached images, thumbnails and cursors (rebuilt when needed)")

    def pref_interface(self, x, y, w, box):
        self.txt("Theme", x, y + 8)
        for i, tn in enumerate(THEMES):
            self.button((x + 70 + i * 86, y, 80, 30), tn, lambda mx, my, tn=tn: self.set_theme(tn), active=self.theme == tn, font=self.f11, hint="Interface theme")

    def pref_labels(self, x, y, w, box):
        self.txt("Label colours and names:", x, y - 6, self.fb)
        y += 24
        for i, (name, c) in enumerate(self.label_list):
            lx, ly = x + (i // 8) * 280, y + (i % 8) * 34
            sw = pygame.Rect(lx, ly, 30, 26)
            self.rrect(sw, c, 13)
            self.rrect(sw, (200, 200, 200), 13, 1)
            if self.hovering(sw):
                self.hover_hint = "Click to change this label colour"
            self.hit(sw, lambda mx, my, i=i: self.open_picker(f"lab:{i}", (box.right + 8, box.y + 8)))
            self.field((lx + 38, ly, 196, 26), name, lambda s, i=i: self.set_label_name(i, s), f"labname_{i}")
        y += 8 * 34 + 6
        self.button((x, y, 130, 30), "Reset Labels", self.reset_labels, font=self.f11)
        y += 44
        self.txt("Element types use these labels (click to cycle):", x, y, self.fb)
        y += 28
        for j, (key, name) in enumerate(LABEL_NAMES.items()):
            lx, ly = x + (j // 4) * 280, y + (j % 4) * 34
            self.txt(name, lx, ly + 6)
            idx = self.type_label[key]
            b = self.button((lx + 108, ly, 150, 26), "", lambda mx, my, k=key: self.cycle_type_label(k), radius=13)
            pygame.draw.circle(self.screen, self.label_list[idx][1], (b.x + 14, b.centery), 6)
            self.txt(self.label_list[idx][0], b.x + 28, b.y + 5)

    def pref_tools(self, x, y, w, box):
        self.txt("All tools (drag & drop toolbox building is coming):", x, y - 6, self.f11, COLOR_MUTED)
        y += 24
        for i, tid in enumerate(TOOL_INFO):
            cell = pygame.Rect(x + (i % 6) * 88, y + (i // 6) * 84, 80, 76)
            self.rrect(cell, COLOR_BTN if not self.hovering(cell) else COLOR_HOVER, 12)
            ic = load_icon_state(tid, 30, "default")[0]
            ir = pygame.Rect(0, 0, 30, 30)
            ir.center = (cell.centerx, cell.y + 26)
            if ic:
                self.screen.blit(ic, ir)
            else:
                draw_tool_icon(self.screen, tid, ir, (235, 235, 235))
            pcl = self.push_clip(cell)
            self.txt(TOOL_INFO[tid][0], cell.centerx, cell.bottom - 16, self.f11, COLOR_MUTED, center=True)
            self.pop_clip(pcl)
            if self.hovering(cell):
                self.hover_hint = TOOL_INFO[tid][2]

    def pref_preview(self, x, y, w, box):
        self.checkbox(x, y + 4, self.loop, lambda mx, my: self.toggle_loop(), "Loop playback")
        self.txt("Loop playback", x + 28, y + 4)
        self.txt("More preview options (cache, frame skipping) will live here.", x, y + 44, self.f11, COLOR_MUTED)

    def pref_onion_skin(self, x, y, w, box):
        for i, (key, n) in enumerate((("before", "Previous frames"), ("after", "Next frames"))):
            self.txt(n, x, y + i * 44 + 8)
            self.field((x + 150, y + i * 44, 64, 32), self.onion[key], lambda v, key=key: self.onion.__setitem__(key, int(clamp(v, 0, 12))),
                       f"onion_{key}", numeric=True, center=True, hint="How many frames are shown")
        self.txt("Turn onion skin on with the icon above the viewport (right-click it for quick counts).", x, y + 100, self.f11, COLOR_MUTED)

    def run_menu(self, fn):
        self.menu_open = None
        fn()
