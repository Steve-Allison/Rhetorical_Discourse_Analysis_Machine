# Decision: typed in-memory viewer layout

## Decision

RS3-to-HTML rendering parses and lays out a typed in-memory node map. It no longer creates a temporary SQLite database or executes render-time SQL queries.

## Compatibility constraints

- Keep the public `rs3tohtml`, PNG, PDF, and notebook surfaces unchanged.
- Preserve historical `user` and `project` keyword acceptance even though stateless rendering does not use them.
- Keep `rstweb_sql` available for its separately tested legacy editing helpers; it is no longer a render dependency.

## Implemented migration

- `read_rst` is the sole RS3 parse boundary.
- Relation indexes, maximum extent, and multinuclear child extents are derived once from the node map.
- Typed import/render failures propagate and browser resources close in `finally` blocks.
- Browser completion waits on the graph-ready predicate rather than a fixed delay.

## Evidence

The classic fixture load stage improved from 4.82 ms / 185,839 B to 0.160 ms / 133,304 B median/peak. Viewer helper, hardening, reader, render, and audit regression tests pass.
