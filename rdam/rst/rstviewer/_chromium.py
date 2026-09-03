"""Playwright / Chromium helpers for RST screenshots and PDFs."""

from io import BytesIO

from PIL import Image, ImageChops
from playwright.async_api import Browser as AsyncBrowser
from playwright.async_api import Page as AsyncPage
from playwright.async_api import Playwright as AsyncPlaywright
from playwright.async_api import Route as AsyncRoute
from playwright.sync_api import Browser
from playwright.sync_api import Page
from playwright.sync_api import Playwright
from playwright.sync_api import Route

_PLAYWRIGHT_LAUNCH_ARGS = ("--disable-extensions", "--disable-sync")
_PLAYWRIGHT_DEFAULT_TIMEOUT_MS = 10_000

JS_GET_DOCUMENT_HEIGHT = """
let docHeight = Math.max(
  document.body.scrollHeight, document.documentElement.scrollHeight,
  document.body.offsetHeight, document.documentElement.offsetHeight,
  document.body.clientHeight, document.documentElement.clientHeight
);

// we increase the height by 20% because the calculated value is still too small
return Math.round(docHeight * 1.2);
"""

JS_GET_DOCUMENT_WIDTH = """
let docWidth = Math.max(
  document.body.scrollWidth, document.documentElement.scrollWidth,
  document.body.offsetWidth, document.documentElement.offsetWidth,
  document.body.clientWidth, document.documentElement.clientWidth
);

// we increase the width by 3% because the calculated value is still too small
return Math.round(docWidth * 1.03);
"""

JS_GRAPH_BBOX = """
(() => {
  const root = document.querySelector('#inner_canvas') || document.body;
  const items = root.querySelectorAll(
    '.edu, .group, .num_cont, svg, canvas, path, ._jsPlumb_connector, ._jsPlumb_endpoint'
  );

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  const push = (r) => {
    if (!r) return;
    minX = Math.min(minX, r.left);
    minY = Math.min(minY, r.top);
    maxX = Math.max(maxX, r.right);
    maxY = Math.max(maxY, r.bottom);
  };

  push(root.getBoundingClientRect());
  items.forEach(el => {
    const r = el.getBoundingClientRect?.();
    if (r && Number.isFinite(r.width) && Number.isFinite(r.height)) push(r);
  });

  if (!Number.isFinite(minX) || !Number.isFinite(minY)) {
    const doc = document.documentElement;
    return {x: 0, y: 0, width: doc.scrollWidth, height: doc.scrollHeight};
  }
  return {x: Math.floor(minX), y: Math.floor(minY),
          width: Math.ceil(maxX - minX), height: Math.ceil(maxY - minY)};
})()
"""

JS_GRAPH_READY = """
() => {
  if (document.readyState !== 'complete') return false;
  const root = document.querySelector('#inner_canvas');
  if (!root) return false;
  const nodes = root.querySelectorAll('.edu, .group');
  if (nodes.length === 0) return false;
  return Array.from(nodes).every((node) => {
    const rect = node.getBoundingClientRect();
    return Number.isFinite(rect.left) && Number.isFinite(rect.top)
      && rect.width > 0 && rect.height > 0;
  });
}
"""


def launch_chromium(playwright_api: Playwright, *, headless: bool = True) -> Browser:
    return playwright_api.chromium.launch(
        headless=headless,
        args=list(_PLAYWRIGHT_LAUNCH_ARGS),
    )


async def launch_chromium_async(
    playwright_api: AsyncPlaywright,
    *,
    headless: bool = True,
) -> AsyncBrowser:
    return await playwright_api.chromium.launch(
        headless=headless,
        args=list(_PLAYWRIGHT_LAUNCH_ARGS),
    )


def attach_navigation_guard(page: Page) -> None:
    """Allow only about:/data: navigations and resource loads (offline render)."""

    def _guard(route: Route) -> None:
        url = route.request.url
        if url.startswith(("about:", "data:")):
            route.continue_()
        else:
            route.abort()

    page.route("**/*", _guard)


async def attach_navigation_guard_async(page: AsyncPage) -> None:
    async def _guard(route: AsyncRoute) -> None:
        url = route.request.url
        if url.startswith(("about:", "data:")):
            await route.continue_()
        else:
            await route.abort()

    await page.route("**/*", _guard)


def trim_whitespace(png_bytes: bytes, pad: int = 12) -> bytes:
    im = Image.open(BytesIO(png_bytes)).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if not bbox:
        return png_bytes
    left = max(bbox[0] - pad, 0)
    top = max(bbox[1] - pad, 0)
    right = min(bbox[2] + pad, im.width)
    bottom = min(bbox[3] + pad, im.height)
    cropped = im.crop((left, top, right, bottom))
    out = BytesIO()
    cropped.save(out, format="PNG")
    return out.getvalue()
