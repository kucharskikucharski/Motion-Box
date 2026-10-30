"""Motion Box - timeline (layers, keyframes, ease handles, zoom/pan, scrollbars) and the bottom bar."""
import pygame

from mb_core import *            # noqa

RH = 24            # row height
LCW = 240          # label column width
EXTRA = 24         # empty frames shown after the last frame


class TimelineMixin:
    def obj_depth(self, o):
        d, p = 0, o.parent
        while p in self.objs and d < 20:
            d, p = d + 1, p.parent
        return d

    def tl_rows(self):
        """A tree: every layer is followed by the layers parented to it (a drawing under its peg, a peg under its bone ...)."""
        rows, seen, done = [], set(), set()

        def walk(o):
            if id(o) in done:
                return
            done.add(id(o))
            if o.fold_id is not None:                       # folded layers collapse into one bar
                if o.fold_id not in seen:
                    seen.add(o.fold_id)
                    rows.append(("f", o, o.fold_id))
            else:
                rows.append(("o", o, None))
                if o.expanded:                               # the arrow shows its properties and, below them, the layers parented to it
                    rows.extend(("p", o, p) for p in PROPS if (o.u_props is None or p in o.u_props) and (not o.u_mode or o.keys[p] or p in o.expr))
            if not o.collapsed:                             # the fold icon next to the name hides the children
                for c in self.objs:
                    if c.parent is o and not free(c):
                        walk(c)
        free = self.is_controller                             # controllers and joysticks / sliders stand alone
        for o in self.objs:                                  # controllers and joysticks first, always at the top
            if free(o):
                walk(o)
        for o in self.objs:
            if o.parent is None or o.parent not in self.objs:
                walk(o)
        for o in self.objs:                                  # safety net
            if id(o) not in done and o.parent in self.objs and o.parent.collapsed:
                continue                                      # hidden inside a folded parent
            walk(o)
        return rows

    def toggle_prop_key_at(self, o, p, f):
        if f in o.keys[p]:
            del o.keys[p][f]
        else:
            o.keys[p][f] = o.value(p, f)

    def set_ease(self, o, a, e):
        o.ease[a] = tuple(e)

    def open_ease_menu(self, o, a, pos):
        self.ctx = {"pos": pos, "items": [(n, lambda e=e: self.set_ease(o, a, e)) for n, e in EASE_PRESETS]}

    def draw_ctx(self):
        c = self.ctx
        if not c:
            return
        items = c["items"]
        box = pygame.Rect(c["pos"][0], c["pos"][1], 208, len(items) * 24 + 8)
        box.x, box.y = min(box.x, self.W - box.w - 8), min(box.y, self.H - box.h - 8)
        self.hit((0, 0, self.W, self.H), lambda mx, my: setattr(self, "ctx", None), (1, 2, 3))
        self.rrect(box, (30, 30, 34), 12)
        self.rrect(box, (80, 80, 92), 12, 1)
        self.hit(box, lambda mx, my: None, (1, 2, 3))
        for i, it in enumerate(items):
            label, fn = it[0], it[1]
            rc = pygame.Rect(box.x + 4, box.y + 4 + i * 24, box.w - 8, 24)
            if self.hovering(rc):
                self.rrect(rc, COLOR_HOVER, 8)
            if len(it) > 2 and it[2]:
                pygame.draw.circle(self.screen, it[2], (rc.x + 14, rc.centery), 6)
                self.txt(label, rc.x + 28, rc.y + 5)
            else:
                self.txt(label, rc.x + 12, rc.y + 5)
            if len(it) > 3 and it[3]:                                  # current choice
                x0, y0 = rc.right - 18, rc.centery
                pygame.draw.lines(self.screen, COLOR_ACCENT_L, False, [(x0, y0), (x0 + 4, y0 + 4), (x0 + 11, y0 - 5)], 2)
            self.hit(rc, lambda mx, my, fn=fn: self.run_ctx(fn))

    def run_ctx(self, fn):
        self.ctx = None
        fn()

    def ease_drag(self, o, a, which, xa, xb):
        L = max(1.0, xb - xa)

        def start(mx, my):
            def upd(mx, my):
                e = list(o.ease.get(a, DEFAULT_EASE))
                if which == 0:
                    e[0] = clamp((mx - xa) / L, 0, 0.9)
                else:
                    e[1] = clamp((xb - mx) / L, 0, 0.9)
                e[2] = False
                o.ease[a] = tuple(e)
            return upd
        return start

    # ---- layer / keyframe interaction helpers
    def layer_time_drag(self, o, mx0, frame_at):
        if o not in self.sel:
            self.select(o)
        self.goto(frame_at(mx0))
        cw = max(1.0, self.tl_cw)
        i0, e0 = o.t_in, o.t_out or self.total
        keys0 = {p: dict(o.keys[p]) for p in PROPS}
        ease0, ph0, tout0 = dict(o.ease), list(o.phases), o.t_out
        pit0 = dict(o._pitems)
        last = [0]

        def drag(mx, my):
            d = int(round((mx - mx0) / cw))
            d = max(1 - i0, min(self.total - e0, d))               # the layer stays inside the scene
            if d == last[0]:
                return
            last[0] = d
            o.t_in, o.t_out = i0 + d, (tout0 if d == 0 else e0 + d)
            o.keys = {p: {max(1, f + d): v for f, v in keys0[p].items()} for p in PROPS}      # keyframes travel with the layer
            o.ease = {max(1, f + d): e for f, e in ease0.items()}
            o.phases = [max(1, f + d) for f in ph0]
            o._pitems = {0: pit0.get(0, [])}                  # every drawing travels with its phase
            o._pitems.update({max(1, f + d): pit0[f] for f in ph0 if f in pit0})
        return drag

    def marker_click(self, m):
        now = pygame.time.get_ticks()
        if getattr(self, "_mk_last", (None, 0))[0] is m and now - self._mk_last[1] < 400:
            self.marker_dlg = m
        self._mk_last = (m, now)
        self.goto(m["f"])

    def layer_press(self, o, my0, y0):
        self.layer_click(o)
        self.layer_double_click(o)
        moved = [False]
        self.autoscroll = "tl"

        def drag(mx, my):                                   # drag a layer name up / down; a line shows where it will land
            if abs(my - my0) < 6 and not moved[0]:
                return
            moved[0] = True
            rws = self.tl_rows()
            if not rws:
                return
            rel = my - y0 + self.tl_vy
            idx = int(clamp(rel // RH, 0, len(rws) - 1))
            frac = (rel % RH) / RH
            tgt = rws[idx]
            grp = [x for x in self.objs if x in self.sel] if o in self.sel else [o]
            anc, p = [], tgt[1]
            while p is not None:
                anc.append(p)
                p = p.parent
            if 0.25 < frac < 0.75 and tgt[0] == "o" and not any(x in anc for x in grp):
                self.parent_drop, self.reorder = (tgt[1], y0 + idx * RH - int(self.tl_vy)), None       # the whole row lights up: drop = child of it
                return
            self.parent_drop = None
            lower = frac > 0.5
            self.reorder = (o, self.objs.index(tgt[1]) + (1 if lower else 0), y0 + idx * RH - int(self.tl_vy) + (RH if lower else 0))

        def end():
            r, self.reorder = self.reorder, None
            pd, self.parent_drop = self.parent_drop, None
            if moved[0] and self.lib_target(pygame.mouse.get_pos()):            # dropped into the Library panel: saved there
                self.lib_save_objs([x for x in self.objs if x in self.sel] if o in self.sel else [o])
                return
            if pd and moved[0]:
                group = [x for x in self.objs if x in self.sel] if o in self.sel else [o]
                n = 0
                for x in group:
                    if x is not pd[0] and self.link(x, pd[0], quiet=True) is not False:
                        n += 1
                pd[0].collapsed = False
                self.msg(f"{n} layer(s) are now children of {pd[0].name}")
                return
            if r and moved[0]:
                src, ti, _ = r
                group = [x for x in self.objs if x in self.sel] if src in self.sel else [src]      # all selected layers move together
                ti -= sum(1 for x in group if self.objs.index(x) < ti)
                for x in group:
                    self.objs.remove(x)
                self.objs[ti:ti] = group
        self.drag_end = end
        return drag

    def label_menu(self, o, pos):
        tg = lambda: (self.sel if o in self.sel else [o])         # noqa  (applies to every selected layer)
        items = [("Use type colour", lambda: [setattr(t, "label", None) for t in tg()], self.labels[self.label_key(o)])]
        items += [(n, (lambda c=tuple(c): [setattr(t, "label", c) for t in tg()]), tuple(c)) for n, c in self.label_list]
        self.ctx = {"pos": pos, "items": items}

    def toggle_expr(self, o, p):
        if p in o.expr:
            del o.expr[p]
            self.expr_bad.discard((o.name, p))
        else:
            o.expr[p] = "value"
            self.begin_edit(f"tlexpr_{o.name}_{p}", "value", lambda s, o=o, p=p: self.set_expr(o, p, s))

    def trim_drag(self, o, is_in, frame_at):
        def start(mx, my):
            if o not in self.sel:
                self.select(o)
            group = [x for x in self.sel if not x.owner] or [o]                 # several selected layers are trimmed together
            edge = lambda x: x.t_in if is_in else (x.t_out or self.total)        # noqa
            base = {id(x): edge(x) for x in group}
            ref = base[id(o)]

            def upd(mx, my):
                d = frame_at(mx) - ref
                for x in group:
                    f = base[id(x)] + d
                    if is_in:
                        x.t_in = int(clamp(f, 1, x.t_out or self.total))
                    else:
                        x.t_out = None if f >= self.total else int(clamp(f, x.t_in, self.total))
            return upd
        return start

    def tl_snap(self, f):
        """Shift: the playhead (and trims) stick to keyframes, layer starts / ends and markers - like a magnet."""
        if not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
            return f
        cands = {1, self.total} | {m["f"] for m in self.markers}
        for x in self.objs:
            cands |= set(x.key_frames())
            cands |= {x.t_in, x.t_out or self.total}
        thr = max(1, int(round(10 / max(1.0, self.tl_cw))))
        best = min(cands, key=lambda c: abs(c - f))
        return best if abs(best - f) <= thr else f

    def kf_press(self, item, mx0):
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            if item in self.kf_sel:
                self.kf_sel.remove(item)
            else:
                self.kf_sel.append(item)
        elif item not in self.kf_sel:
            self.kf_sel = [item]
        if item[0] not in self.sel:
            self.sel = [item[0]]
        return self.kf_move_drag(mx0)

    def kf_move_drag(self, mx0):
        """Drag the selected keyframes along the time axis."""
        items, cw = list(self.kf_sel), max(1.0, self.tl_cw)
        objs = []
        for o, _, _ in items:
            if o not in objs:
                objs.append(o)
        orig = {id(o): ({pp: dict(o.keys[pp]) for pp in PROPS}, dict(o.ease)) for o in objs}
        last = [0]
        dup = bool(pygame.key.get_mods() & pygame.KMOD_ALT)          # Alt + drag = duplicate the keyframes

        def apply(delta):
            for o in objs:
                keys0, ease0 = orig[id(o)]
                keys = {pp: dict(keys0[pp]) for pp in PROPS}
                ease = dict(ease0)
                moved, moved_e = [], []
                for oo, p, f in items:
                    if oo is not o:
                        continue
                    for pp in (PROPS if p is None else (p,)):
                        if f in keys[pp]:
                            moved.append((pp, f, keys[pp].get(f) if dup else keys[pp].pop(f)))
                    if p is None and f in ease:
                        moved_e.append((f, ease.get(f) if dup else ease.pop(f)))
                for pp, f, v in moved:
                    keys[pp][int(clamp(f + delta, 1, self.total))] = v
                for f, e in moved_e:
                    ease[int(clamp(f + delta, 1, self.total))] = e
                o.keys, o.ease = keys, ease

        def drag(mx, my):
            last[0] = int(round((mx - mx0) / cw))
            apply(last[0])

        def end():
            self.kf_sel = [(o, p, int(clamp(f + last[0], 1, self.total))) for o, p, f in items]
        self.drag_end = end
        return drag

    def kf_menu(self, item, pos):
        if item not in self.kf_sel:
            self.kf_sel = [item]
        o = item[0]
        items = [("Copy Keyframe(s)  (Ctrl+C)", self.kf_copy), ("Delete Keyframe(s)", self.delete_keys)]
        if self.kf_clip:
            items.insert(1, ("Paste Keyframes at playhead  (Ctrl+V)", self.kf_paste))
        if len(self.kf_sel) >= 2:
            items.append(("Reverse Order in Time", self.reverse_keys))
        items.append(("Select All on this Layer", lambda: setattr(self, "kf_sel", [(o, None, f) for f in o.key_frames()])))
        self.ctx = {"pos": pos, "items": items}

    def cell_menu(self, o, p, f, pos):
        self.select(o)
        items = [(f"Add Keyframe at frame {f}", lambda: self.add_key_at(o, p, f))]
        if self.kf_clip:
            items.append((f"Paste Keyframes at frame {f}", lambda: (self.goto(f), self.kf_paste())))
        self.ctx = {"pos": pos, "items": items}

    def draw_timeline(self):
        tl = self.r_tl
        self.rrect(tl, COLOR_TL, 8)
        cx0 = tl.x + 8 + LCW + 8
        area_w = max(48, tl.right - 24 - cx0)
        y0 = tl.y + 32
        reg = pygame.Rect(tl.x + 8, y0, tl.w - 24, max(8, tl.bottom - 8 - y0))
        rows = self.tl_rows()
        self.prop_rects, self.kf_rects = [], []
        self.tl_vmax = max(0, len(rows) * RH - reg.h)
        self.tl_vy = clamp(self.tl_vy, 0, self.tl_vmax)
        cw = max(4.0, area_w / (self.total + EXTRA)) * self.tl_zoom
        self.tl_cw, self.tl_area, self.tl_cx0 = cw, area_w, cx0
        self.tl_max = max(0.0, cw * (self.total + EXTRA) - area_w)
        if self.playing:                                    # keep the playhead in view while playing
            ph = (self.frame - 1) * cw - self.tl_off
            if ph < 0 or ph > area_w - cw:
                self.tl_off = (self.frame - 1) * cw - area_w / 2
        self.tl_off = clamp(self.tl_off, 0, self.tl_max)
        off = self.tl_off
        cells = pygame.Rect(cx0, tl.y, area_w, tl.h)
        self.tl_cells = cells
        fx = lambda f: cx0 + (f - 1) * cw - off             # noqa
        f0 = max(1, int(off // cw) + 1)
        f1 = min(int((off + area_w) // cw) + 2, self.total + EXTRA)

        def frame_at(mx):
            return self.tl_snap(int(clamp((mx - cx0 + self.tl_off) // cw + 1, 1, self.total)))
        self.tl_frame_at = lambda mx: int(clamp((mx - cx0 + self.tl_off) // cw + 1, 1, self.total))

        def pan(mx, my):                                    # middle mouse drag = pan
            sx, sy, o0, v0 = mx, my, self.tl_off, self.tl_vy

            def d(mx, my):
                self.tl_off = clamp(o0 - (mx - sx), 0, self.tl_max)
                self.tl_vy = clamp(v0 - (my - sy), 0, self.tl_vmax)
            return d
        self.hit(tl, pan, (2,))

        self.txt("TIMELINE", tl.x + 16, tl.y + 8, self.fb2)
        self.tl_edges = []
        xr = pygame.Rect(tl.right - 24, tl.y + 4, 24, 24)             # X closes the timeline dock
        if self.hovering(xr):
            self.hover_hint = "Close this dock (Panels menu shows it again)"
        for a, b in (((-4, -4), (4, 4)), ((-4, 4), (4, -4))):
            pygame.draw.line(self.screen, (170, 170, 170), (xr.centerx + a[0], xr.centery + a[1]), (xr.centerx + b[0], xr.centery + b[1]), 2)
        self.hit(xr, lambda mx, my: self.toggle_dock("timeline"))
        plus = pygame.Rect(tl.x + 140, tl.y + 4, 24, 24)               # + = new vector / raster layer
        self.flat_button(plus, lambda mx, my: setattr(self, "layer_dlg", True), "New layer: choose vector or raster")
        pygame.draw.line(self.screen, (225, 225, 225), (plus.centerx - 6, plus.centery), (plus.centerx + 6, plus.centery), 2)
        pygame.draw.line(self.screen, (225, 225, 225), (plus.centerx, plus.centery - 6), (plus.centerx, plus.centery + 6), 2)
        for i_, (lab_, kind_) in enumerate((("+ Peg", "peg"), ("+ Null", "null"))):        # peg / null straight from the timeline
            self.button((tl.x + 172 + i_ * 62, tl.y + 4, 58, 24), lab_, lambda mx, my, kind_=kind_: self.new_obj(kind_, self.aw // 2, self.ah // 2),
                        radius=8, font=self.f11, hint="New " + kind_)
        pc = self.push_clip(cells)
        step = 1 if cw >= 28 else (5 if cw >= 9 else 10)
        for f in range(f0, f1 + 1):
            if f == 1 or f % step == 0:
                self.txt(f, fx(f) + cw / 2, tl.y + 14, self.f11, COLOR_MUTED, center=True)
                pygame.draw.line(self.screen, (70, 70, 76), (fx(f) + cw / 2, tl.y + 24), (fx(f) + cw / 2, tl.y + 28))
        if self.work_in or self.work_out:                   # work area (I / O)
            lo, hi = self.work_in or 1, min(self.work_out or self.total, self.total)
            self.rrect((fx(lo), tl.y + 26, (hi - lo + 1) * cw, 3), COLOR_PLAYHEAD, 1)
        self.pop_clip(pc)

        def scrub(mx, my):
            self.autoscroll = "tlh"                             # the view follows when the playhead is dragged to the edge
            self.goto(frame_at(mx))

            def d(mx, my):
                self.goto(frame_at(mx))
            return d
        self.hit(pygame.Rect(cx0, tl.y + 4, area_w, 24), scrub)
        pcm = self.push_clip(cells)                           # markers (M adds one, double-click edits it)
        mk_hits = []
        for m in self.markers:
            mxp = fx(m["f"]) + cw / 2
            rpoly(self.screen, tuple(m["color"]), [(mxp - 5, tl.y + 3), (mxp + 5, tl.y + 3), (mxp, tl.y + 12)], 2)
            if m["text"] and cw >= 10:
                self.txt(m["text"], mxp + 8, tl.y + 2, self.f11, COLOR_MUTED)
            mk_hits.append((pygame.Rect(int(mxp) - 7, tl.y + 2, 14, 12).clip(cells), m))
        self.pop_clip(pcm)
        for rc, m in mk_hits:
            self.hit(rc, lambda mx, my, m=m: self.marker_click(m))
            self.hit(rc, lambda mx, my, m=m: setattr(self, "ctx", {"pos": (mx, my), "items": [
                ("Edit marker...", lambda: setattr(self, "marker_dlg", m)), ("Delete marker", lambda: self.markers.remove(m))]}), (3,))

        shift = lambda: bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)   # noqa
        used_mattes = {x.matte for x in self.objs if x.matte}
        prev_all = self.push_clip(reg)
        for i, (kind, o, p) in enumerate(rows):
            y = y0 + i * RH - int(self.tl_vy)
            if y + RH < reg.y or y > reg.bottom:
                continue
            if kind == "f":                                  # folded group: one bar, click to unfold
                members = [m for m in self.objs if m.fold_id == p]
                lab = pygame.Rect(tl.x + 8, y, LCW, RH - 2)
                self.rrect(lab, (50, 50, 62), 6)
                draw_icon(self.screen, "tri_r", pygame.Rect(tl.x + 12, y + 2, 20, 20), (200, 200, 200))
                pcl = self.push_clip(lab)
                self.txt("Folded: " + ", ".join(m.name for m in members), tl.x + 40, y + 5, self.f12, COLOR_MUTED)
                self.pop_clip(pcl)
                pcc = self.push_clip(cells)
                for f in range(f0, f1 + 1):
                    pygame.draw.rect(self.screen, (40, 40, 44) if f > self.total else (46, 46, 50), (fx(f), y, max(1, cw - 1), RH - 2))
                self.rrect((fx(1), y + 8, self.total * cw - 1, 8), (70, 70, 84), 4)
                self.pop_clip(pcc)
                if self.hovering(lab):
                    self.hover_hint = "Folded layers - click to unfold"
                self.hit(pygame.Rect(tl.x + 8, y, LCW + area_w, RH - 2).clip(reg), lambda mx, my, fid=p: self.unfold(fid))
                self.row_rects.append((lab, o))
                continue
            sel, hov = o in self.sel or any(i in self.sel for i in o.items), o is self.hover
            lc = self.label_color(o)
            lab = pygame.Rect(tl.x + 8, y, LCW, RH - 2)
            if kind == "o":
                self.rrect(lab, COLOR_ACCENT if sel else ((36, 46, 90) if hov else (38, 39, 44)), 6)
                self.row_rects.append((lab, o))
                self.hit(lab, lambda mx, my, o=o: self.layer_press(o, my, y0))
                self.hit(lab, lambda mx, my, o=o: self.layer_menu(o, (mx, my)), (3,))
                if any(c.parent is o and not self.is_controller(c) for c in self.objs):
                    ch = pygame.Rect(tl.x + 12, y + 2, 20, 20)             # only a layer with children can be unfolded
                    draw_icon(self.screen, "tri_r" if o.collapsed else "tri_d", ch, (200, 200, 200))
                    if self.hovering(ch):
                        self.hover_hint = "Show / hide the layers parented to this one"
                    self.hit(ch, lambda mx, my, o=o: setattr(o, "collapsed", not o.collapsed))
                ey = pygame.Rect(tl.x + 36, y + 2, 20, 20)
                self.eye_icon(ey.centerx, ey.centery, (220, 220, 220) if o.visible else (80, 80, 80))
                if self.hovering(ey):
                    self.hover_hint = "Show / hide layer"
                self.hit(ey, lambda mx, my, o=o: self.toggle_flag(o, "visible"))
                lk = pygame.Rect(tl.x + 60, y + 2, 20, 20)
                self.lock_icon(lk.centerx, lk.centery, (220, 220, 220) if o.locked else (80, 80, 80), o.locked)
                if self.hovering(lk):
                    self.hover_hint = "Lock layer (locked layers cannot be picked on the artboard)"
                self.hit(lk, lambda mx, my, o=o: self.toggle_flag(o, "locked"))
                dot = pygame.Rect(tl.x + 84, y + 2, 20, 20)
                pygame.draw.circle(self.screen, lc, dot.center, 6)
                if self.hovering(dot):
                    self.hover_hint = "Layer label colour - click to change"
                self.hit(dot, lambda mx, my, o=o: self.label_menu(o, (mx, my)))
                pcl = self.push_clip((tl.x + 8, y, LCW, RH))
                self.txt(self.objs.index(o) + 1, tl.x + 108, y + 6, self.f11, COLOR_MUTED)      # layer number
                rid = f"rename_{id(o)}"
                if self.edit and self.edit.get("id") == rid:
                    self.field((tl.x + 128, y + 1, LCW - 124, RH - 4), o.name, lambda s, o=o: self.rename_obj(o, s), rid)
                else:
                    self.txt(o.name, tl.x + 132 + 12 * min(self.obj_depth(o), 5), y + 5)
                if o.name in used_mattes:                          # this layer is the alpha of another layer
                    self.txt("a", tl.x + LCW - 16, y + 4, self.fb, COLOR_TEAL)
                    if self.hovering(pygame.Rect(tl.x + LCW - 22, y, 20, RH)):
                        self.hover_hint = "Alpha matte of: " + ", ".join(x.name for x in self.objs if x.matte == o.name)
                if False:                                           # (the fold icon moved to the arrow on the left)
                    gr = pygame.Rect(tl.x + LCW - 40, y + 2, 20, 20)
                    draw_icon(self.screen, "tri_r" if o.collapsed else "tri_d", gr, (200, 200, 205))
                    if self.hovering(gr):
                        self.hover_hint = "Fold / unfold the children of this group"
                    self.hit(gr, lambda mx, my, o=o: setattr(o, "collapsed", not o.collapsed))
                self.pop_clip(pcl)
            else:
                self.rrect(lab, (32, 33, 38), 6)
                lab = pygame.Rect(tl.x + 58, y, LCW - 72, RH - 2)
                if self.sel_prop == (o, p):                                  # the value that K will key is highlighted
                    self.rrect(lab, COLOR_ACCENT, 6)
                self.hit(lab, lambda mx, my, o=o, p=p: setattr(self, "sel_prop", (o, p)))
                self.txt(PROP_LABEL[p], tl.x + 60, y + 6, self.f11, COLOR_MUTED if self.sel_prop != (o, p) else (255, 255, 255))
                swr = pygame.Rect(tl.x + 36, y + 2, 20, RH - 4)                 # stopwatch: keyframes for this value on / off
                on = self.watched(o, p)
                scol = COLOR_ACCENT_L if on else (95, 95, 102)
                pygame.draw.circle(self.screen, scol, swr.center, 6, 2)
                pygame.draw.line(self.screen, scol, swr.center, (swr.centerx, swr.centery - 4), 1)
                pygame.draw.line(self.screen, scol, swr.center, (swr.centerx + 3, swr.centery), 1)
                if self.hovering(swr):
                    self.hover_hint = "Stopwatch: click to be able to animate this value (K then keys it). Clicking again removes its keyframes"
                self.hit(swr, lambda mx, my, o=o, p=p: self.set_watch(o, p))
                fxr = pygame.Rect(tl.x + 8 + LCW - 32, y + 1, 28, RH - 4)
                self.txt("fx", fxr.centerx, fxr.centery, self.fb, COLOR_YELLOW if p in o.expr else (90, 90, 96), center=True)
                if self.hovering(fxr):
                    self.hover_hint = "Expression: click to add / remove (e.g. layer('Null Control 1').x + 100)"
                self.hit(fxr, lambda mx, my, o=o, p=p: self.toggle_expr(o, p))
            pc = self.push_clip(cells)
            if cw >= 9:                                      # zoomed in far enough: the frame grid appears
                for f in range(f0, f1 + 1):
                    col = (40, 40, 44) if f > self.total else ((52, 52, 58) if f % 5 == 0 else (46, 46, 50))
                    pygame.draw.rect(self.screen, col, (fx(f), y, max(1, cw - 1), RH - 2))
            else:                                            # zoomed out: flat grey, the scene end is marked by a darker area
                pygame.draw.rect(self.screen, (46, 46, 50), (cx0, y, max(0, fx(self.total + 1) - cx0), RH - 2))
                pygame.draw.rect(self.screen, (40, 40, 44), (max(cx0, fx(self.total + 1)), y, area_w, RH - 2))
            pygame.draw.line(self.screen, (28, 28, 32), (cx0, y + RH - 1), (cx0 + area_w, y + RH - 1))      # line between layers
            kf = o.key_frames(p)
            if kind == "o":
                lo, hi = o.t_in, o.t_out or self.total      # the bar is the layer's in / out - not its keyframes
                bar = pygame.Rect(fx(lo), y + 4, (hi - lo + 1) * cw - 1, 16)
                self.rrect(bar, lc if sel else shade(lc, 0.8), 6)
                if bar.w > 14:                                       # lit top edge, darker bottom edge
                    pygame.draw.line(self.screen, mix(lc, (255, 255, 255), 0.28), (bar.x + 6, bar.y + 1), (bar.right - 6, bar.y + 1), 2)
                    pygame.draw.line(self.screen, shade(lc, 0.62), (bar.x + 6, bar.bottom - 2), (bar.right - 6, bar.bottom - 2), 2)
                if o.collapsed:                                      # folded: a thin line under the bar shows the span of everything inside it
                    ds = self.descendants(o)
                    if ds:
                        lo2, hi2 = min(d.t_in for d in ds), max((d.t_out or self.total) for d in ds)
                        pygame.draw.rect(self.screen, mix(lc, (255, 255, 255), 0.55), (fx(lo2), y + RH - 7, (hi2 - lo2 + 1) * cw - 1, 3))
                        pygame.draw.line(self.screen, (255, 255, 255), (fx(hi2) + cw - 1, y + RH - 10), (fx(hi2) + cw - 1, y + RH - 3), 2)
                for ph_f in o.phases:                      # a new drawing starts here: a light divider and a small light dot
                    px = fx(ph_f)
                    pygame.draw.line(self.screen, mix(lc, (255, 255, 255), 0.6), (px, y + 3), (px, y + RH - 5), 2)
                    pygame.draw.circle(self.screen, mix(lc, (255, 255, 255), 0.9), (int(px + cw / 2 + 1), y + 12), 3)
                for a, b in zip(kf, kf[1:]):
                    xa, xb = fx(a) + cw / 2, fx(b) + cw / 2
                    pygame.draw.line(self.screen, (235, 235, 240), (xa, y + 12), (xb, y + 12))
                    L = xb - xa
                    e = o.ease.get(a, DEFAULT_EASE)
                    if L >= 32 and not (len(e) > 2 and e[2]):
                        ox_, ix_ = xa + clamp(e[0] * L, 10, L / 2 - 2), xb - clamp(e[1] * L, 10, L / 2 - 2)
                        rpoly(self.screen, (255, 255, 255), [(ox_ - 3, y + 8), (ox_ + 4, y + 12), (ox_ - 3, y + 16)], 1)
                        rpoly(self.screen, (255, 255, 255), [(ix_ + 3, y + 8), (ix_ - 4, y + 12), (ix_ + 3, y + 16)], 1)
            rowk = []
            for k in kf:
                item = (o, None if kind == "o" else p, k)
                selk = item in self.kf_sel
                ctr = (fx(k) + cw / 2, y + 12)
                hk = self.hovering(pygame.Rect(int(ctr[0]) - 7, y + 5, 14, 14))
                sz = 7 if (hk or selk) else 5                                  # keys grow a little on hover
                rdiamond(self.screen, ctr, sz + 2, (14, 14, 18), True)         # dark outline separates them from the lines
                rdiamond(self.screen, ctr, sz, COLOR_YELLOW if selk else ((255, 255, 255) if kind == "o" else (200, 200, 210)), True)
                rowk.append((pygame.Rect(int(ctr[0]) - 7, y + 5, 14, 14).clip(cells), item))
                self.kf_rects.append(rowk[-1])
            self.pop_clip(pc)
            row = pygame.Rect(cx0, y, area_w, RH - 2).clip(reg)
            self.row_rects.append((row, o))
            if kind == "p":
                self.prop_rects.append((pygame.Rect(tl.x + 8, y, LCW + area_w + 8, RH - 2).clip(reg), o, p))

            def left(mx, my, o=o):
                x0, y0, base = mx, my, list(self.kf_sel) if shift() else []
                moved = [False]
                if not shift():
                    self.kf_sel = []

                def d(mx, my):                                  # drag on the empty grid: a rectangle selects keyframes
                    if not moved[0] and math.hypot(mx - x0, my - y0) < 5:
                        return
                    moved[0] = True
                    self.tl_marquee = pygame.Rect(min(x0, mx), min(y0, my), abs(mx - x0), abs(my - y0))
                    hit_ = [it for rc, it in self.kf_rects if rc.colliderect(self.tl_marquee)]
                    self.kf_sel = base + [it for it in hit_ if it not in base]

                def end():
                    self.tl_marquee = None
                    if not moved[0]:                           # a plain click: move the playhead and drop the layer selection
                        self.goto(frame_at(x0))
                        if not shift():
                            self.sel = []
                self.drag_end = end
                return d
            self.hit(row, left)
            self.hit(row, lambda mx, my, o=o, p=p, kind=kind: self.cell_menu(o, None if kind == "o" else p, frame_at(mx), (mx, my)), (3,))
            if kind == "p" and p in o.expr:                # expression editor sits right on the property row
                self.field((cx0 + 8, y + 1, max(80, min(area_w - 16, 440)), RH - 4), o.expr[p],
                           lambda s, o=o, p=p: self.set_expr(o, p, s), f"tlexpr_{o.name}_{p}",
                           hint="Expression - Enter to apply")
            if kind == "o":
                lo_, hi_ = o.t_in, o.t_out or self.total               # drag the bar ends to trim, the bar itself to move the layer
                bar_r = pygame.Rect(int(fx(lo_)) + 7, y + 4, max(1, int((hi_ - lo_ + 1) * cw) - 14), 16).clip(cells)
                self.hit(bar_r, lambda mx, my, o=o: self.layer_time_drag(o, mx, frame_at))
                re_l = pygame.Rect(int(fx(lo_)) - 12, y + 3, 16, 18).clip(cells)
                re_r = pygame.Rect(int(fx(hi_) + cw) - 4, y + 3, 16, 18).clip(cells)
                self.tl_edges += [re_l, re_r]
                hl, hr = self.hovering(re_l), self.hovering(re_r)
                if hl or hr:
                    self.hover_hint = "Drag to trim the layer"
                elif self.hovering(bar_r):
                    self.hover_hint = "Drag to move the layer in time"
                if sel or hl or hr or self.hovering(pygame.Rect(cx0, y, area_w, RH)):      # rounded handles on the ends
                    pc2 = self.push_clip(cells)
                    for ex, hv in ((fx(lo_) + 1, hl), (fx(hi_) + cw - 7, hr)):
                        self.rrect((ex - (2 if hv else 0), y + (3 if hv else 6), 6 + (4 if hv else 0), 18 if hv else 12),
                                   (255, 255, 255) if hv else mix(lc, (255, 255, 255), 0.55), 5)
                    self.pop_clip(pc2)
                kf2 = o.key_frames()
                for a, b in zip(kf2, kf2[1:]):
                    xa, xb = fx(a) + cw / 2, fx(b) + cw / 2
                    L = xb - xa
                    e = o.ease.get(a, DEFAULT_EASE)
                    if L >= 32:
                        self.hit(pygame.Rect(int(xa) + 12, y + 6, max(1, int(L) - 24), 12).clip(cells),
                                 lambda mx, my, o=o, a=a: self.open_ease_menu(o, a, (mx, my)), (3,))
                        if not (len(e) > 2 and e[2]):
                            ox_, ix_ = xa + clamp(e[0] * L, 10, L / 2 - 2), xb - clamp(e[1] * L, 10, L / 2 - 2)
                            self.hit(pygame.Rect(int(ox_) - 6, y + 4, 12, 16).clip(cells), self.ease_drag(o, a, 0, xa, xb))
                            self.hit(pygame.Rect(int(ix_) - 6, y + 4, 12, 16).clip(cells), self.ease_drag(o, a, 1, xa, xb))
            for rc, item in rowk:                           # keyframes sit on top of the bar ...
                self.hit(rc, lambda mx, my, item=item: self.kf_press(item, mx))
                self.hit(rc, lambda mx, my, item=item: self.kf_menu(item, (mx, my)), (3,))
            if kind == "o":                                  # ... but the trim handles on its ends are on top of everything
                self.hit(re_l, self.trim_drag(o, True, frame_at))
                self.hit(re_r, self.trim_drag(o, False, frame_at))
        self.pop_clip(prev_all)
        if self.tl_marquee:                                    # keyframe selection rectangle
            pygame.draw.rect(self.screen, COLOR_ACCENT_L, self.tl_marquee, 1)
        if self.parent_drop:                                  # drop target: the whole parent row is highlighted
            pr = pygame.Rect(tl.x + 6, self.parent_drop[1], tl.w - 12, RH)
            pygame.draw.rect(self.screen, COLOR_ACCENT_L, pr, 2, border_radius=6)
        if self.reorder:                                      # where the dragged layer will land
            pygame.draw.line(self.screen, COLOR_PLAYHEAD, (tl.x + 8, self.reorder[2]), (cx0 + area_w, self.reorder[2]), 3)
        vt = pygame.Rect(tl.right - 16, y0, 8, reg.h)       # vertical scrollbar
        self.rrect(vt, (46, 46, 46), 4)
        if self.tl_vmax > 0:
            th = max(24, int(vt.h * reg.h / (len(rows) * RH)))
            ty = vt.y + int((vt.h - th) * self.tl_vy / self.tl_vmax)
            self.rrect((vt.x, ty, 8, th), COLOR_THUMB, 4)

            def vstart(mx, my):
                grab = my - ty

                def u(mx, my):
                    self.tl_vy = clamp((my - grab - vt.y) / max(1, vt.h - th), 0, 1) * self.tl_vmax
                return u
            self.hit(vt.inflate(8, 0), vstart)
        px = fx(self.frame) + cw / 2                        # blue playhead
        if cx0 <= px <= cx0 + area_w:
            pygame.draw.line(self.screen, COLOR_PLAYHEAD, (px, tl.y + 24), (px, tl.bottom - 6), 2)
            rpoly(self.screen, COLOR_PLAYHEAD, [(px - 6, tl.y + 8), (px + 6, tl.y + 8), (px, tl.y + 24)], 2)

    def draw_bar(self):
        """Bottom bar: hints on the left, timeline zoom slider and horizontal scrollbar."""
        b = self.r_bar
        pygame.draw.rect(self.screen, COLOR_TL, b)
        zx = int(self.W * 0.42) // 8 * 8
        hint = self.hover_hint or TOOL_INFO.get(self.tool, ("", "", ""))[2]
        self.txt("Hints", 16, b.y + 5, self.fb, COLOR_MUTED)
        pc = self.push_clip((64, b.y, max(0, zx - 80), b.h))
        self.txt(hint, 64, b.y + 5, self.f11, COLOR_TEXT)
        self.pop_clip(pc)
        draw_icon(self.screen, "mtn_s", pygame.Rect(zx, b.y + 4, 16, 16), (150, 150, 150))
        draw_icon(self.screen, "mtn_l", pygame.Rect(zx + 104, b.y + 4, 20, 16), (150, 150, 150))
        track = pygame.Rect(zx + 24, b.centery - 2, 72, 4)
        self.rrect(track, (70, 70, 70), 2)
        t = (self.tl_zoom - 1) / 7
        pygame.draw.circle(self.screen, (220, 220, 220), (track.x + int(track.w * t), track.centery), 5)

        def zstart(mx, my):
            def upd(mx, my):
                self.tl_zoom = 1 + 7 * clamp((mx - track.x) / track.w, 0, 1)
            upd(mx, my)
            return upd
        self.hit(track.inflate(16, 16), zstart)
        if self.hovering(track.inflate(16, 16)):
            self.hover_hint = "Timeline zoom (Alt + scroll)"
        sx = zx + 144
        sw = max(40, self.W - 16 - sx)
        tr = pygame.Rect(sx, b.centery - 4, sw, 8)
        self.rrect(tr, (46, 46, 46), 4)
        total_w = max(1.0, self.tl_cw * (self.total + EXTRA))
        tw = int(clamp(sw * self.tl_area / total_w, 24, sw))
        tx = sx + ((sw - tw) * self.tl_off / self.tl_max if self.tl_max > 0 else 0)
        self.rrect((tx, tr.y, tw, 8), COLOR_THUMB, 4)          # #4F4F4F

        def sstart(mx, my):
            grab = mx - tx

            def upd(mx, my):
                if self.tl_max > 0 and sw > tw:
                    self.tl_off = clamp((mx - grab - sx) / (sw - tw), 0, 1) * self.tl_max
            return upd
        self.hit(tr.inflate(0, 10), sstart)

    def tl_wheel(self, dy, dx, pos, mods):
        if mods & pygame.KMOD_ALT:                              # Alt + scroll = zoom around the cursor
            old = max(1.0, self.tl_cw)
            fpos = (pos[0] - getattr(self, "tl_cx0", 0) + self.tl_off) / old
            self.tl_zoom = clamp(self.tl_zoom * (1.15 ** (dy or dx)), 1.0, 8.0)
            new = max(4.0, self.tl_area / (self.total + EXTRA)) * self.tl_zoom
            self.tl_off = max(0.0, fpos * new - (pos[0] - getattr(self, "tl_cx0", 0)))
        elif dx or (mods & pygame.KMOD_SHIFT):                  # Shift + scroll / sideways scroll = along time
            self.tl_off = clamp(self.tl_off - (dx or dy) * 30, 0, self.tl_max)
        else:                                                   # plain scroll = up / down through the layers
            self.tl_vy = clamp(self.tl_vy - dy * RH, 0, self.tl_vmax)
