# Design

The design lives in an online design canvas with six boards:

https://claude.ai/artifact/Vt2CpM6gSs84ex9cb4HfW5

`boards/` holds a source copy of those boards (`*.dc.html`, `canvas.json`) and the shared date picker (`datepicker.js`, `datepicker.css`) that the Reserve and Admin boards use. The `.dc.html` files need the design canvas viewer to render; opening them directly in a browser shows markup, not the design. They are kept here as a record and as a reference while building each phase.

Colours, type, spacing and motion are already carried into the code as design tokens in `app/restaurant/static/css/tokens.css`. The board that matches each phase is named in the plan (section 10).
