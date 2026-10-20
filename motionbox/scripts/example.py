# Example Motion Box script (File > Import Script...)
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
