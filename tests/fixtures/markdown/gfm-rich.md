---
title: GFM-rich fixture
author: Steve
tags: [markdown, rst, fixture]
---

# Overview

This fixture exercises every harvest knob: tables, fenced code, blockquotes, lists, images, and a raw HTML block.

## Table

| Feature | Status | Notes |
|---------|--------|-------|
| Tables  | done   | row-major harvest |
| Code    | done   | fenced and indented |
| Images  | done   | alt text inline |

## Code

A fenced code block follows.

```python
def parse_markdown(path):
    return process(path)
```

## Blockquote

> The blockquote contains a single paragraph of prose. The harvester
> treats it as `blockquote_paragraph` while preserving the text.

## List

- The first list item carries one short clause about lists.
- The second list item contrasts with the first.
- The third list item closes the list.

## Image

An inline image follows: ![alt text describing the figure](images/diagram.png) — the alt text becomes part of this paragraph.

## Raw HTML

<div class="callout">
This is a raw HTML block. The harvester captures it as text when include_html is on.
</div>

# Closing

A final paragraph closes the file.
