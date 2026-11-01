# Motion Box

**A 2D animation program for cut-out rigs and frame-by-frame drawing, written in Python (pygame).**
It borrows its workflow from Toon Boom Harmony and After Effects / Duik: pegs, nulls and a node schematic for hierarchy, a timeline with keyframes and expressions, a *Level Strip* of independent drawings per layer, controllers and sliders for puppet rigs, bones with two-bone IK, and a Duik-style rig generator.

> **Status: alpha.** The file format and the UI still change between builds. Save often (autosave is on by default) and keep copies of projects you care about.

---

## Features

### Drawing
- **Vector layers** hold shapes and brush strokes. Tools: rectangle (with corner radius), ellipse, polygon (adjustable corners), line, pen, brush, eraser, fill bucket, eyedropper, scissors (cut a layer at the playhead), anchor-point tool.
- **Brush smoothing** (`Smooth` 0-100) calms hand jitter; the live stroke has the real width and colour.
- **Level Strip**: every drawing layer owns a pool of drawings that is independent of the timeline. Drawings are created by `+ New`, `Duplicate` or *Auto-create* (drawing on a frame that does not start a drawing makes a new drawing instead of painting over the old one). Reorder by dragging (insertion line), grid or list view, preview with play button, drag a drawing onto the timeline to expose it. A layer always keeps at least one (blank) drawing.
- **Drawing substitution**: `Q` / `W` swap the drawing shown at the playhead (or in the selected frames) for the previous / next drawing of the pool. Nothing new is created.
- **Frame selection** on the timeline: click or drag a rectangle, `Shift` adds, drag to move, `Del` empties, `Ctrl+C/X/V` copy / cut / paste (also into another layer), `Alt`+drag moves the whole layer.
- **Onion skin** shows only the selected layers and their children, with the drawing's own line width in soft translucent colours.
- Flip selected shapes horizontally / vertically (right click), align and centre to the artboard or to each other.

### Rigging and hierarchy
- **Pegs and nulls** as parents; parent by the *Link to Parent* button, by right-click, by dropping a layer on a parent row in the timeline, or by wiring nodes in the Schematic. Hiding / locking a parent applies to its children.
- **Controllers**: position, rotation and position+rotation controllers, sliders (X / Y) and joysticks (XY). Objects can follow several controllers at once, each with a multiplier and a delay in frames (`Drive by controller...`), e.g. pupils that follow the face joystick with a lag and also obey their own controller.
- **Expressions** per property with autocomplete: `layer("Name").x`, `.lx`, `layer("Name", 3).lx` (3 frames late), `wiggle(freq, amp)`, `world("Name")`.
- **Bones**: Create Bones, Edit Skeleton, Animate Bones, Create IK. Two-bone IK with a controller at the tip, joint pins, rotation limits. *Animate Bones* treats a bone and the drawings parented to it as one element. `Generate body drawing layers` + `Do the rig` build a Duik-style humanoid: named, parented drawing layers with anchors on the joints, then bones, IK on arms and legs.
- **Track mattes** (alpha matte with invert and "keep matte visible"), *Only this layer* selection mode.

### Timeline
- Keyframes per property with a **stopwatch** (a value is only keyed when its stopwatch is on), ease types, global key, auto key, copy / paste of keyframes, `Alt`+drag duplicates, rectangle selection of keyframes, `Shift` snaps the playhead to keyframes / layer ends / markers.
- Layer search with a type filter (Drawings, Pegs, Nulls, Bones, Controllers), tree view with children under their parent, controllers pinned on top, global eye and lock.
- Markers, work area (`[` / `]`), layer trim handles (also on several selected layers), `Alt+[` / `Alt+]` trim to the playhead, middle-mouse panning.

### Schematic
- Node graph of the hierarchy: pills for pegs / nulls / bones / controllers, thumbnails for drawings, tree layout, drop a node on a wire to insert it between parent and child, rename in place, centre on the selection.

### Library, footage, colour
- **Library** with real thumbnails, folders, multi-select and drag & drop to and from the viewer and the timeline. **Footage** with an Explorer (several files at once, numbered files imported as an image sequence).
- **Palette** with named colours, folders and three views (circles, rounded tiles, list). Changing the toolbox colour does not repaint selected objects; paint with the Fill Bucket or the Properties panel.

### Output
- Render to **H.264 (ffmpeg)** or a **PNG sequence**, whole scene or work area. Nulls, pegs, controllers and bones are never rendered. `Render View` shows the scene the way it will render.

---

## Install and run

Requirements: **Python 3.10+** and `pygame >= 2.1.4`. For MP4 export either have `ffmpeg` on the `PATH` or `pip install imageio-ffmpeg`.

```bash
git clone https://github.com/kucharskikucharski/Motion-Box.git
cd Motion-Box/motionbox
pip install -r requirements.txt
python motion_box.py            # splash + start window
python motion_box.py --quick    # straight into a new project
```

Launchers: `run_windows.bat`, `run_mac_linux.sh`. Only one instance runs at a time; starting it again brings the first window to the front.

Prebuilt packages for Windows, macOS and Linux are produced by the GitHub Actions workflow (PyInstaller) and attached to releases. They are not signed: on macOS right-click -> Open the first time, on Windows choose *More info -> Run anyway* in SmartScreen.

User data (projects, library, preferences) lives next to the code when running from source and in `~/MotionBox` in a packaged build.

---

## Shortcuts (selection)

| Key | Action | Key | Action |
|---|---|---|---|
| `V` / `T` | Select / Transform | `B` / `E` | Brush / Eraser |
| `R` / `O` | Rectangle / Ellipse | `F` / `I` | Fill bucket / Eyedropper |
| `P` / `N` | Pen / Null | `A` | Animate |
| `J` | Create bones | `Y` | Anchor point |
| `Z` / `H` | Zoom / Hand | `C` | Cut (scissors) |
| `K` | Keyframe (global key / auto key in the transport bar) | `M` | Marker |
| `P R S T` over the timeline | Show Position / Rotation / Scale / Opacity | `U` | Only animated values |
| `Q` / `W` | Drawing substitution backward / forward | `[` `]` | Work area start / end (brush size with a brush or eraser in the viewer) |
| `Alt+[` `Alt+]` | Trim the layer to the playhead | `Ctrl+0` | Fit the artboard |
| `Shift` (drag) | One axis / snap to keyframes | `Alt` (drag) | Draw from centre / duplicate keyframes / move a layer |
| `B` / `Shift+B` over timeline or schematic | Select parent / children | `Ctrl+Z` / `Ctrl+Shift+Z` | Undo / redo |

---

## Architecture

All code is in `motionbox/`; the program is a single pygame loop with an immediate-mode UI (every frame the panels are drawn and the clickable rectangles are registered, the last registered rectangle under the mouse wins).

| Module | Responsibility |
|---|---|
| `mb_core.py` | constants, themes, the `Obj` data model, easing, shape outlines, icon loader (`Tool_Default/Hover/Active.png`, 30x30), clipboard helpers |
| `mb_app.py` | `AppBase`: scene operations, project I/O, undo / redo, clipboard, drivers, frame operations, playback, input |
| `mb_canvas.py` | viewport, tools, selection and handles, IK, schematic nodes, Level Strip, palette |
| `mb_panels.py` | toolbox, colour picker, left and right panels, transport, menus, dialogs, library, explorer, preferences |
| `mb_timeline.py` | timeline rows, keyframes, trim, markers, frame selection, layer reorder / parenting |
| `mb_start.py` | splash and start window |
| `motion_box.py` | entry point, single-instance lock |

### Data model

- Everything on the stage is an `Obj` (`kind`: `rect ellipse polygon line brush vlayer rlayer peg null ctrl ctrl_rot ctrl_posrot bone pill rsquare image`). Animated properties are `x y scale rotation opacity`; each has `base` (static value) and `keys[prop][frame]` (keyframes), plus `ease`, `expr` (per property expression) and `drivers` (controller followers).
- A **vector layer** is an `Obj` of kind `vlayer`. Its shapes live in a bank of **drawings**: `_pitems {id: [shapes]}`, shown order `dorder`, and **exposure markers** `phases` (frames) + `pmap {frame: drawing id}`. The drawing on screen at frame `f` is the one of the last marker `<= f` (`-1` = nothing). `Obj.items` always resolves to the drawing of the current frame, so every tool works on "the current drawing" without knowing about the bank.
- World transforms are computed by walking the `parent` chain (`world(o, frame)` -> x, y, scale, rotation). IK is solved on demand for the bone pair.
- **Projects** are JSON (`Obj.to_dict()` / `from_dict()`, with older formats converted on load) plus an `assets/` folder for footage and raster data. Undo is a snapshot stack; autosave runs in the background.

### Scripting

`File > Import Script...` runs a Python file with an `app` object (`add_box`, `add_null`, `link`, `set_key`, `find`, `msg`); see `scripts/example.py`.

### Icons and assets

Icon files are matched to tools by name (`Select_Default.png`, `Select_Hover.png`, `Select_Active.png`; tool ids or on-screen names both work, the console lists files that match no tool). Fonts go in `fonts/` (Inter), the splash in `assets/splash.png` (optional `splash.json`).

---

## Roadmap

See [`motionbox/BACKLOG.md`](motionbox/BACKLOG.md). Next up: a shared bounding box for several selected objects, position X / Y as one value with optional separation, node groups, gradients, the Text tool, mouse text selection in fields, lipsync.

## Reporting issues and suggestions

Please open an issue and use the templates:
* **Bug reports** - describe the problem and **attach screenshots or a screen recording**. If the program printed an error, attach `crash.log`.
* **Feature requests** - describe the proposal and how it improves the workflow.

## Contributing

1. Fork the repository.
2. Create a branch (`git checkout -b feature/my-new-feature`).
3. Commit your changes (`git commit -m 'Add new feature'`).
4. Push the branch (`git push origin feature/my-new-feature`).
5. Open a **Pull Request**.

## License

MIT - see [LICENCE](LICENCE).
