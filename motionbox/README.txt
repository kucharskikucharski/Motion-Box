MOTION BOX - how to run
=======================
1) Install Python 3.9+ from python.org (macOS: the installer; Linux: your package manager).
2) macOS / Linux: open a terminal in this folder and run:   ./run_mac_linux.sh
   Windows: double-click run_windows.bat
   (first start installs pygame automatically, later starts are instant)
   Tip: add --quick to skip the splash and the start window:  ./run_mac_linux.sh --quick

Your own tool icons: drop PNG files into icons/ named like the tools:
  select transform rect ellipse polygon line brush eraser pen null ctrl joy_x joy_y joy_xy bone hand
(any size, transparent background, they are scaled to 24x24).
Splash image: assets/splash.png.   Scripts: scripts/.   Projects: projects/<name>/project.json

Standalone app (no Python needed afterwards): ./build_app.sh  -> dist/

Click-to-launch icon (Linux Mint / GNOME)
-----------------------------------------
Run ./run_mac_linux.sh once from a terminal (installs pygame), then:   ./install_launcher.sh
"Motion Box" now appears in the applications menu and on the Desktop (right-click it > Allow Launching if asked).
macOS / Windows: ./build_app.sh builds a real app you can double-click (see dist/).

What's new in this version
--------------------------
Ctrl+Z / Ctrl+Shift+Z undo-redo, draggable panel edges, scroll on timeline = up/down (Shift+scroll = sideways,
Alt+scroll = zoom), drag keyframes (Shift+click for many), right-click a keyframe for Delete / Reverse Order,
Delete key removes selected keyframes, drag layer names to reorder, label colours per element type
(click the layer dot, or Edit > Preferences), expressions straight on the timeline (fx on a property row),
project thumbnails on the start screen (created when you save), animated splash, I / O work area,
view icons above the viewport, Tools menu, pill-shaped joysticks, null drawn as a bare bounding box.

Labels (After Effects style): Edit > Preferences opens 16 label colours + editable names
(default palette = Deep Lilac, Bubblegum Pink, Porcelain, Icy Aqua, Night Bordeaux, Tomato, Mustard, Blue Sail, ...).
Each element type (vectors, nulls, controllers...) uses one label; click a row to cycle it.
A layer's bounding box, timeline bar and node header all use its label colour.
Transport bar: key = set keyframe on ALL selected layers, key-x = delete keyframes at the playhead,
key-circle = select all keyframes at the playhead.   Schematic: scroll = zoom, drag empty space = pan.

Tool icons: put PNG files in icons/ named after the tool (select.png, transform.png, rect.png, ellipse.png, polygon.png,
line.png, brush.png, fill.png, eraser.png, pen.png, null.png, ctrl.png, joy_x.png, joy_y.png, joy_xy.png, bone.png, hand.png).
Better text: put Inter-Regular.ttf and Inter-SemiBold.ttf into fonts/ (free from rsms.me/inter) and restart.

Footage: left panel > Footage tab. "Import..." opens Library > Explorer (double-click an image / sequence / video / audio file),
"+ Solid" creates a colour layer, double-click an item (or "Add to Scene") puts it in the scene. Numbered images
(walk_0001.png, walk_0002.png ...) are imported as one image sequence. Copies live in <project>/assets/.
See BACKLOG.md for the full to-do list.

New in this version: layers (+ in the timeline: vector / raster), anchor tool (Y), Ctrl = magnet, chained bones,
linear controllers, alpha matte (Properties > Track matte), expression suggestions (Tab), Ctrl+M render, Save / Discard on quit,
autosave (Edit > Preferences), markers (M). H.264 needs ffmpeg:  sudo apt install ffmpeg

Icons: one white PNG per tool in icons/, transparent background, 96 x 96 px, file name = tool id
(select, select_level, transform, anchor, artboard, rect, ellipse, polygon, line, pen, multiline, brush, eraser, fill, text,
eyedropper, scissors, taper, lipsync, joy_x, joy_y, joy_xy, ctrl, ctrl_rot, ctrl_posrot, null, peg, bone, bone_anim, bone_ik,
hand, zoom, view_rotate). Idle icons are tinted grey by the program, active / hovered ones stay white.
Fonts: copy the whole extracted Inter folder into fonts/ - the program finds Regular and SemiBold by itself.
Themes: Edit > Preferences > Theme (Dark, Graphite, Slate, Steel).
