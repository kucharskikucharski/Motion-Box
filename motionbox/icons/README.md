# Motion Box icons

Tool icons stay in this folder. Interface icons belong in `ui/`.

## Tool icons

Use a tool id or its on-screen name. The tool icon loader ignores letter case and separators, so `Pen_Active.png`, `pen-active.png`, and `Pen Active.png` all match the Pen tool.

```text
icons/
  Pen_Default.png
  Pen_Hover.png
  Pen_Active.png
  Control_Point_Editor_Default.png
  Control_Point_Editor_Hover.png
  Control_Point_Editor_Active.png
```

`Default`, `Hover`, and `Active` are optional states. A single `<tool>.png` works for all states. Tool artwork is displayed at 30×30 pixels; transparent PNGs are recommended.

## Interface icons

Put UI icons in the lowercase `ui` subfolder. Use lowercase `snake_case` filenames. Icons are tinted by the app, so draw a white or light monochrome shape on a transparent background. A 32×32 transparent PNG is a good source size; the app scales it to each button.

```text
icons/ui/
  stretch.png
  repeat.png
  reverse.png
  first.png
  prev.png
  stop.png
  play.png
  pause.png
  next.png
  last.png
  loop.png
  key.png
  key_auto.png
  key_g.png
  key_x.png
  key_all.png
  view_render_default.png
  view_render_active.png
  view_grid3_default.png
  view_grid3_active.png
  view_safe_default.png
  view_safe_active.png
  view_gray_default.png
  view_gray_active.png
  view_onion_default.png
  view_onion_active.png
  view_camera_default.png
  view_camera_active.png
  view_threed.png
  layer_bone.png
  layer_drawing.png
  layer_raster.png
  layer_image.png
  layer_null.png
  layer_peg.png
  layer_controller.png
  layer_joystick.png
```

Interface states use `_default` and `_active`; a plain `<name>.png` is used as a fallback for both. The timeline stretch, repeat, and reverse buttons and the layer-type symbols also have code-drawn fallbacks until you add matching PNGs.
