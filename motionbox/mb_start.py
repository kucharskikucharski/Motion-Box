"""Motion Box - splash screen and the start window (LOAD existing project / NEW project)."""
import json
import math
import os
import time

import pygame

from mb_core import *            # noqa

INVALID = '/\\:*?"<>|'


class StartMixin:
    # ------------------------------------------------------------------ splash
    def enter_splash(self):
        self.mode, self.splash_t, self.splash_img = "splash", pygame.time.get_ticks(), None
        size = (720, 380)
        # positions are fractions of the image, so a new splash with the same layout works at any size;
        # a different layout can be described in assets/splash.json
        self.splash_cfg = {"cover": [850 / 1052, 398 / 544, 170 / 1052, 30 / 544], "status": [1000 / 1052, 412 / 544],
                           "bg": [840 / 1052, 412 / 544]}
        try:
            with open(os.path.join(ASSETS_DIR, "splash.json"), encoding="utf-8") as fh:
                self.splash_cfg.update(json.load(fh))
        except Exception:  # noqa
            pass
        try:
            img = pygame.image.load(os.path.join(ASSETS_DIR, "splash.png")).convert_alpha()
            w, h = img.get_size()
            sc = min(1.0, 880 / w)
            size = (int(w * sc), int(h * sc))
            self.splash_img = pygame.transform.smoothscale(img, size)
            self.splash_sc = size[0] / 1052
            bx, by = self.splash_cfg["bg"]
            self.splash_bg = tuple(self.splash_img.get_at((int(bx * size[0]), int(by * size[1]))))[:3]
            self.fsplash = pygame.font.SysFont("inter,notosans,dejavusans,ubuntu,liberationsans,arial", max(11, int(16 * self.splash_sc)))
        except Exception:  # noqa
            self.splash_img = None
        self.screen = pygame.display.set_mode(size, pygame.NOFRAME)
        self.W, self.H = size
        pygame.display.set_caption("Motion Box")

    def leave_splash(self):
        if self.mode == "splash":
            self.enter_start("load")

    def draw_splash(self):
        if self.splash_img:
            bg, sc, W, H, cfg = self.splash_bg, self.splash_sc, self.W, self.H, self.splash_cfg
            self.screen.fill(bg)                                   # transparent corners (if any) show as solid colour
            self.screen.blit(self.splash_img, (0, 0))
            cv = cfg["cover"]
            self.screen.fill(bg, pygame.Rect(int(cv[0] * W), int(cv[1] * H), int(cv[2] * W), int(cv[3] * H)))
            t = (pygame.time.get_ticks() - self.splash_t) / 1000.0
            msgs = ["Loading assets...", "Reading preferences...", "Preparing workspace...",
                    "Starting renderer...", "Ready to launch"]
            sf = self.fsplash.render(msgs[min(len(msgs) - 1, int(t / 0.62))], True, (232, 234, 245))
            tx, cy = int(cfg["status"][0] * W) - sf.get_width(), int(cfg["status"][1] * H)
            self.screen.blit(sf, (tx, cy - sf.get_height() // 2))
            dx = int(math.sin(t * 5) * 5 * sc)                    # the dot sweeps left / right
            pygame.draw.circle(self.screen, (0, 235, 205), (tx - int(15 * sc) + dx, cy), max(3, int(5 * sc)))
        else:
            self.screen.fill((12, 12, 16))
            self.rrect((0, 0, self.W, self.H), COLOR_ACCENT, 32)
            self.txt("MotionBox", self.W // 2, self.H // 2, self.f20, (255, 255, 255), center=True)

    # ------------------------------------------------------------- start window
    def enter_start(self, tab="load"):
        self.mode, self.start_tab = "start", tab
        self.playing, self.edit, self.menu_open, self.dialog, self.picker, self.maxi = False, None, None, None, None, None
        self.screen = pygame.display.set_mode((960, 640))
        self.W, self.H = 960, 640
        self.start_scroll, self.start_sel, self.start_click, self.np_dd = 0, None, (None, 0), False
        self.start_projects = self.list_projects()
        if not hasattr(self, "np"):
            self.np = {"name": "My Animation", "fmt": 0, "w": 1920, "h": 1080, "ratio": 1920 / 1080,
                       "path": PROJECTS_DIR, "lock": True, "fps": 24}
        self.cursor_kind = None
        try:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        except Exception:  # noqa
            pass
        pygame.display.set_caption("Motion Box")

    def enter_main(self):
        self.mode = "main"
        self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        self.W, self.H = 1280, 720
        self.view_fit, self.maxi, self.menu_open, self.edit = True, None, None, None
        self.ctx = None
        self.undo_stack, self.redo_stack, self.kf_sel = [], [], []
        self.compute_layout()
        self.saved_sig, self.last_autosave = self.doc_sig(), pygame.time.get_ticks()
        pygame.display.set_caption(f"Motion Box - {self.project_name}")

    def draw_start(self):
        self.hits, self.hover_hint = [], None
        W, H = self.W, self.H
        self.screen.fill(COLOR_BG)
        rpoly(self.screen, (10, 60, 120), [(36, 38), (50, 24), (64, 38), (50, 52)], 3)
        rpoly(self.screen, COLOR_TEAL, [(36, 32), (50, 18), (64, 32), (50, 46)], 3)
        self.txt("Motion Box", 80, 20, self.f20)
        for key, name, x in (("load", "OPEN PROJECT", 24), ("new", "NEW PROJECT", 184)):
            rc = pygame.Rect(x, 64, 152, 32)
            act = self.start_tab == key
            pygame.draw.rect(self.screen, COLOR_PANEL if act else COLOR_HEAD, rc, border_top_left_radius=12,
                             border_top_right_radius=12)
            self.txt(name, rc.centerx, rc.centery, self.fb if act else self.f12, COLOR_TEXT if act else COLOR_MUTED,
                     center=True)
            self.hit(rc, lambda mx, my, n=key: self.enter_start_tab(n))
        panel = pygame.Rect(24, 96, W - 48, H - 96 - 24)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel, border_top_right_radius=12, border_bottom_left_radius=12,
                         border_bottom_right_radius=12)
        if self.start_tab == "load":
            self.draw_start_load(panel)
        else:
            self.draw_start_new(panel)
        if self.np_dd:
            self.draw_format_dropdown()
        self.draw_toast(pygame.Rect(0, 0, W, H))

    def enter_start_tab(self, tab):
        self.start_tab, self.np_dd = tab, False
        self.start_projects = self.list_projects()

    def open_selected(self, mx=0, my=0):
        if self.start_sel is None or self.start_sel >= len(self.start_projects):
            self.msg("Select a project first")
            return
        self.open_project(self.start_projects[self.start_sel][1])

    def start_card_click(self, i):
        last_i, last_t = self.start_click
        now = pygame.time.get_ticks()
        self.start_sel = i
        self.start_click = (i, now)
        if last_i == i and now - last_t < 400:
            self.open_selected()

    def get_thumb(self, d):
        p = os.path.join(d, "thumb.png")
        try:
            mt = os.path.getmtime(p)
        except OSError:
            return None
        c = self.thumb_cache.get(p)
        if c and c[0] == mt:
            return c[1]
        try:
            img = pygame.image.load(p).convert()
            w, h = img.get_size()
            sc = min(192 / w, 96 / h)
            img = round_surf(pygame.transform.smoothscale(img, (max(1, int(w * sc)), max(1, int(h * sc)))), 8)
        except Exception:  # noqa
            img = None
        self.thumb_cache[p] = (mt, img)
        return img

    def draw_start_load(self, p):
        area = pygame.Rect(p.x + 16, p.y + 16, p.w - 32, p.h - 16 - 72)
        cols = max(1, (area.w + 16) // 224)
        projs = self.start_projects
        if not projs:
            self.txt("No projects yet - create one in the NEW tab.", area.x, area.y + 8, self.f12, COLOR_MUTED)
        rows = (len(projs) + cols - 1) // cols
        self.start_scroll = int(clamp(self.start_scroll, 0, max(0, rows - 2)))
        prev = self.push_clip(area)
        for i, (name, d, mt, w, h) in enumerate(projs):
            card = pygame.Rect(area.x + (i % cols) * 224, area.y + (i // cols - self.start_scroll) * 176, 208, 160)
            if card.bottom < area.y or card.y > area.bottom:
                continue
            self.rrect(card, COLOR_HOVER if self.hovering(card) else COLOR_BTN, 12)
            if self.start_sel == i:
                self.rrect(card, COLOR_NAVY, 12, 2)
            th = pygame.Rect(card.x + 8, card.y + 8, 192, 96)
            self.rrect(th, (24, 24, 24), 8)
            img = self.get_thumb(d)
            if img:
                self.screen.blit(img, img.get_rect(center=th.center))
            else:
                rpoly(self.screen, COLOR_TEAL, [(th.centerx - 16, th.centery), (th.centerx, th.centery - 16),
                                                (th.centerx + 16, th.centery), (th.centerx, th.centery + 16)], 3)
            self.txt(name, card.x + 12, card.y + 112, self.fb)
            self.txt(f"{w} x {h}   {time.strftime('%d %b %Y', time.localtime(mt))}", card.x + 12, card.y + 134,
                     self.f11, COLOR_MUTED)
            self.hit(card, lambda mx, my, i=i: self.start_card_click(i))
        self.pop_clip(prev)
        self.button((p.right - 16 - 120, p.bottom - 16 - 40, 120, 40), "Load", self.open_selected,
                    color=COLOR_ACCENT_L, radius=20, font=self.fb)

    # ---- NEW project form
    def np_pick_format(self, i):
        np = self.np
        np["fmt"], self.np_dd = i, False
        if FORMATS[i][1]:
            np["w"], np["h"] = FORMATS[i][1], FORMATS[i][2]
        np["ratio"] = np["w"] / np["h"]

    def np_set_dim(self, which, v):
        np = self.np
        v = int(clamp(v, 16, 16384))
        if which == "w":
            np["w"] = v
            if np["lock"]:
                np["h"] = max(16, int(round(v / np["ratio"])))
        else:
            np["h"] = v
            if np["lock"]:
                np["w"] = max(16, int(round(v * np["ratio"])))
        np["fmt"] = len(FORMATS) - 1
        for i, f in enumerate(FORMATS[:-1]):
            if (np["w"], np["h"]) == (f[1], f[2]):
                np["fmt"] = i

    def create_from_form(self, mx=0, my=0):
        np = self.np
        name = np["name"].strip()
        if not name or any(c in INVALID for c in name):
            self.msg("Enter a valid project name")
            return
        base = np["path"].strip() or PROJECTS_DIR
        if os.path.exists(os.path.join(base, name)):
            self.msg("A project with this name already exists in that folder")
            return
        try:
            os.makedirs(base, exist_ok=True)
            self.create_project(name, np["w"], np["h"], base, np.get("fps", 24))
        except OSError as e:
            self.msg(f"Cannot create project: {e}")

    def np_pick_fps(self, v):
        self.np["fps"], self.np_dd = v, False

    def draw_start_new(self, p):
        np = self.np
        x, y = p.x + 32, p.y + 32
        fx, fw = x + 112, min(480, p.w - 64 - 112)
        self.txt("Name", x, y + 9)
        self.field((fx, y, fw, 32), np["name"], lambda s: np.__setitem__("name", s), "np_name")
        y += 48
        self.txt("Format", x, y + 9)
        dd = pygame.Rect(fx, y, fw, 32)
        self.button(dd, FORMATS[np["fmt"]][0], lambda mx, my: setattr(self, "np_dd", False if self.np_dd == "fmt" else "fmt"))
        draw_icon(self.screen, "tri_d", pygame.Rect(dd.right - 28, dd.y + 8, 16, 16), (170, 170, 170))
        self.np_dd_pos = {"fmt": (fx, y + 36, fw)}
        y += 56
        self.txt("Width", x, y + 9)
        self.field((fx, y, 112, 32), np["w"], lambda v: self.np_set_dim("w", v), "np_w", numeric=True, center=True)
        self.txt("Height", fx + 136, y + 9)
        self.field((fx + 192, y, 112, 32), np["h"], lambda v: self.np_set_dim("h", v), "np_h", numeric=True, center=True)
        lock = pygame.Rect(fx + 320, y, 32, 32)                          # chain icon (aspect ratio link), grey
        if np["lock"]:
            self.rrect(lock, (70, 70, 76), 8)
        self.flat_button(lock, lambda mx, my: np.__setitem__("lock", not np["lock"]), "Keep the aspect ratio when changing width / height")
        c = (235, 235, 235) if np["lock"] else (130, 130, 130)
        pygame.draw.rect(self.screen, c, (lock.x + 4, lock.y + 11, 15, 10), 2, border_radius=5)
        pygame.draw.rect(self.screen, c, (lock.x + 13, lock.y + 11, 15, 10), 2, border_radius=5)
        y += 56
        self.txt("FPS", x, y + 9)
        fp = pygame.Rect(fx, y, 160, 32)
        self.button(fp, f"{np['fps']} fps", lambda mx, my: setattr(self, "np_dd", False if self.np_dd == "fps" else "fps"))
        draw_icon(self.screen, "tri_d", pygame.Rect(fp.right - 28, fp.y + 8, 16, 16), (170, 170, 170))
        self.np_dd_pos["fps"] = (fx, y + 36, 160)
        y += 56
        self.txt("Path", x, y + 9)
        self.field((fx, y, fw, 32), np["path"], lambda s: np.__setitem__("path", s), "np_path")
        y += 48
        self.txt("The project folder gets: assets, graphics, palettes, scenes, scripts, renders, library", fx, y, self.f11, COLOR_MUTED)
        self.button((p.right - 16 - 120, p.bottom - 16 - 40, 120, 40), "Create", self.create_from_form,
                    color=COLOR_ACCENT_L, radius=20, font=self.fb)

    def draw_format_dropdown(self):
        kind = self.np_dd
        fx, y, w = self.np_dd_pos[kind]
        items = [n for n, _, _ in FORMATS] if kind == "fmt" else [f"{v} fps" for v in FPS_LIST]
        self.hit((0, 0, self.W, self.H), lambda mx, my: setattr(self, "np_dd", False))
        box = pygame.Rect(fx, y, w, len(items) * 32 + 8)
        self.rrect(box, (30, 30, 34), 12)
        self.rrect(box, (80, 80, 92), 12, 1)
        self.hit(box, lambda mx, my: None)
        for i, n in enumerate(items):
            rc = pygame.Rect(box.x + 4, box.y + 4 + i * 32, box.w - 8, 32)
            if self.hovering(rc):
                self.rrect(rc, COLOR_HOVER, 8)
            self.txt(n, rc.x + 12, rc.y + 9)
            self.hit(rc, (lambda mx, my, i=i: self.np_pick_format(i)) if kind == "fmt" else (lambda mx, my, i=i: self.np_pick_fps(FPS_LIST[i])))
