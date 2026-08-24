import argparse
import asyncio
import base64
import html
from importlib import import_module
import json
import os
import re
import sys
import tempfile
import uuid
import warnings
from pathlib import Path
from typing import IO

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

from ._chromium import (
    JS_GET_DOCUMENT_HEIGHT,
    JS_GET_DOCUMENT_WIDTH,
    JS_GRAPH_BBOX,
    attach_navigation_guard,
    attach_navigation_guard_async,
    launch_chromium,
    launch_chromium_async,
    trim_whitespace,
)
from .rstweb_classes import NODE, get_depth, get_left_right
from .rstweb_sql import (
    get_def_rel,
    get_max_right,
    get_multinuc_children_lr,
    get_multinuc_children_lr_ids,
    get_rst_doc,
    get_rst_rels,
    import_document,
    temporary_db,
)

type PathLike = str | os.PathLike[str]

PACKAGE_ROOT_DIR = Path(__file__).resolve().parent
DATA_ROOT_DIR = PACKAGE_ROOT_DIR / "data"


def _html_to_fragment(full_html: str) -> str:
    """
    Convert a full HTML document into a safe inline fragment:
    - keep <style> and <script> blocks from <head>
    - drop <meta>, <title>, etc.
    - include only the inner HTML of <body>
    """
    # scripts/styles from anywhere (mostly head)
    head_assets = re.findall(
        r"(?is)<style[^>]*>.*?</style>|<script[^>]*>.*?</script>",
        full_html,
    )
    assets_html = "".join(head_assets)

    # body inner HTML (fallback to whole string if no <body>)
    m_body = re.search(r"(?is)<body[^>]*>(.*?)</body>", full_html)
    body_inner = m_body.group(1) if m_body else full_html

    return assets_html + body_inner


def rs3tohtml(
    rs3_filepath: PathLike,
    user: str = "temp_user",
    project: str = "rstviewer_temp",
) -> str:
    with temporary_db():
        return _rs3tohtml_with_db(rs3_filepath, user=user, project=project)


def _rs3tohtml_with_db(
    rs3_filepath: PathLike,
    user: str = "temp_user",
    project: str = "rstviewer_temp",
) -> str:
    import_document(filename=os.fspath(rs3_filepath), project=project, user=user)

    top_spacing = 0
    layer_spacing = 60

    current_doc = Path(rs3_filepath).name
    current_doc_safe = html.escape(current_doc, quote=True)
    current_project = project

    header = (DATA_ROOT_DIR / "templates" / "main.html").read_text(encoding="utf-8")

    header = header.replace("**page_title**", "RST Viewer")
    header = header.replace("**doc**", current_doc_safe)

    def _load_asset_text(*path_parts: str) -> str:
        return DATA_ROOT_DIR.joinpath(*path_parts).read_text(encoding="utf-8")

    header = header.replace(
        '<link rel="stylesheet" href="**css_dir**/rst.css" type="text/css" charset="utf-8"/>',
        "<style>\n" + _load_asset_text("css", "rst.css") + "\n</style>\n"
        "<style>\n"
        ".rst_rel_wrap{display:inline-flex;align-items:center;justify-content:center}"
        ".rst_rel_label{font-size:8pt;font-weight:bold;"
        " color:red;background-color:rgba(255,255,255,0.85);"
        " padding:0 2px;border-radius:3px;user-select:none;"
        " white-space: nowrap; "
        "}"
        "</style>",
    )

    def _inline_script_tag(script_filename: str) -> str:
        script_text = _load_asset_text("script", script_filename)
        script_text = script_text.replace("</script>", "<\\/script>")
        return "<script>\n" + script_text + "\n</script>"

    header = header.replace(
        '<script src="**script_dir**/jquery-1.11.3.min.js"></script>',
        _inline_script_tag("jquery-1.11.3.min.js"),
    )
    header = header.replace(
        '<script src="**script_dir**/jquery-ui.min.js"></script>',
        _inline_script_tag("jquery-ui.min.js"),
    )

    cpout = ""
    cpout += header
    cpout += """<div>\n"""

    rels = get_rst_rels(current_doc, current_project)
    def_rstrel = get_def_rel("rst", current_doc, current_project)
    multi_rel_entries: list[dict[str, str]] = []
    rst_rel_entries: list[dict[str, str]] = []
    rel_kinds: dict[str, str] = {}
    for rel in rels:
        value = str(rel[0])
        if rel[1] == "multinuc":
            multi_rel_entries.append({"value": value, "label": value.replace("_m", "")})
            rel_kinds[value] = "multinuc"
        else:
            rst_rel_entries.append({"value": value, "label": value.replace("_r", "")})
            rel_kinds[value] = "rst"
    multi_rel_entries.append({"value": str(def_rstrel), "label": "(satellite...)"})

    nodes: dict[str, NODE] = {}
    rows = get_rst_doc(current_doc, current_project, user)
    for row in rows:
        node_id = str(row[0])
        parent = str(row[3])
        kind = str(row[5])
        text = str(row[6])
        relname = str(row[7])
        if relname in rel_kinds:
            relkind = rel_kinds[relname]
        else:
            relkind = "span"
        if kind == "edu":
            nodes[node_id] = NODE(
                node_id,
                float(row[1]),
                float(row[2]),
                parent,
                float(row[4]),
                kind,
                text,
                relname,
                relkind,
            )
        else:
            nodes[node_id] = NODE(node_id, 0, 0, parent, float(row[4]), kind, text, relname, relkind)

    for key in nodes:
        node = nodes[key]
        get_depth(node, node, nodes)

    for key in nodes:
        if nodes[key].kind == "edu":
            get_left_right(key, nodes, 0, 0, rel_kinds)

    # ---- Adaptive horizontal unit to keep coordinates stable on very wide graphs
    # We need max_right before any anchor/pixel calculations.
    max_right = get_max_right(current_doc, current_project, user)
    # Constrain total width roughly <= 100000k px; keep units reasonable.
    px_unit = max(40, min(100, int(100000 / max(1, float(max_right)))))
    edu_inner_w = px_unit - 4  # keeps same 2px margins as before

    anchors = {}
    pix_anchors = {}

    # Calculate anchor points for nodes (proportional within the parent)
    for key in sorted(nodes, key=lambda id: nodes[id].depth, reverse=True):
        node = nodes[key]
        if node.kind == "edu":
            anchors[node.id] = "0.5"
        if node.parent != "0":
            parent = nodes[node.parent]
            parent_wid = (parent.right - parent.left + 1) * px_unit - 4
            child_wid = (node.right - node.left + 1) * px_unit - 4
            if node.relname == "span":
                if node.id in anchors:
                    anchors[parent.id] = str(
                        ((node.left - parent.left) * px_unit) / parent_wid
                        + float(anchors[node.id]) * float(child_wid / parent_wid)
                    )
                else:
                    anchors[parent.id] = str(
                        ((node.left - parent.left) * px_unit) / parent_wid + (0.5 * child_wid) / parent_wid
                    )
            elif node.relkind == "multinuc" and parent.kind == "multinuc":
                lr = get_multinuc_children_lr(node.parent, current_doc, current_project, user)
                lr_wid = (lr[0] + lr[1]) / 2
                lr_ids = get_multinuc_children_lr_ids(node.parent, lr[0], lr[1], current_doc, current_project, user)
                left_child = str(lr_ids[0])
                right_child = str(lr_ids[1])
                if left_child == right_child:
                    anchors[parent.id] = "0.5"
                else:
                    if left_child in anchors and right_child in anchors:
                        len_left = nodes[left_child].right - nodes[left_child].left + 1
                        len_right = nodes[right_child].right - nodes[right_child].left + 1
                        anchors[parent.id] = str(
                            (
                                (
                                    float(anchors[left_child]) * len_left * px_unit
                                    + float(anchors[right_child]) * len_right * px_unit
                                    + (nodes[right_child].left - parent.left) * px_unit
                                )
                                / 2
                            )
                            / parent_wid
                        )
                    else:
                        anchors[parent.id] = str((lr_wid - parent.left + 1) / (parent.right - parent.left + 1))
            else:
                if parent.id not in anchors:
                    anchors[parent.id] = "0.5"

    # Place anchor element to center on proportional position relative to parent
    for key in nodes:
        node = nodes[key]
        pix_anchors[node.id] = str(
            int(
                3
                + node.left * px_unit
                - px_unit
                - 39
                + float(anchors[node.id]) * ((node.right - node.left + 1) * px_unit - 4)
            )
        )

    for key in nodes:
        node = nodes[key]
        if node.kind != "edu":
            g_wid = str(int((node.right - node.left + 1) * px_unit - 4))
            left_px = int(node.left * px_unit - px_unit)
            top_px = int(top_spacing + layer_spacing + node.depth * layer_spacing)
            cpout += (
                f'<div id="lg{node.id}" class="group" style="left: '
                f'{left_px}px; width: {g_wid}px; top:{top_px}px; z-index:1">\n'
            )
            cpout += f'\t<div id="wsk{node.id}" class="whisker" style="width:{g_wid}px;"></div>\n</div>\n'
            num_top = int(4 + top_spacing + layer_spacing + node.depth * layer_spacing)
            z_index = int(200 - (node.right - node.left))
            cpout += (
                f'<div id="g{node.id}" class="num_cont" style="position: absolute; left:'
                f'{pix_anchors[node.id]}px; top:{num_top}px; z-index:{z_index}">\n'
            )
            cpout += '\t<table class="btn_tb">\n\t\t<tr>'
            cpout += f'\n\t\t\t<td rowspan="2"><span class="num_id">{int(node.left)}-{int(node.right)}</span></td>\n'
            cpout += "\t</table>\n</div>\n<br/>\n\n"

        elif node.kind == "edu":
            edu_left = int(int(node.id) * px_unit - px_unit)
            edu_top = int(top_spacing + layer_spacing + node.depth * layer_spacing)
            cpout += (
                f'<div id="edu{node.id}" class="edu" title="{node.id}" style="left:'
                f'{edu_left}px; top:{edu_top}px; width: {int(edu_inner_w)}px">\n'
            )
            cpout += f'\t<div id="wsk{node.id}" class="whisker" style="width:{int(edu_inner_w)}px;"></div>'
            cpout += '\n\t<div class="edu_num_cont">'
            cpout += '\n\t\t<table class="btn_tb">\n\t\t\t<tr>'
            cpout += f'\n\t\t\t\t<td rowspan="2"><span class="num_id">&nbsp;{int(node.left)}&nbsp;</span></td>\n'
            cpout += "</table>\n</div>" + html.escape(node.text or "", quote=False) + "</div>\n"

    jsplumb_src = _load_asset_text("script", "jquery.jsPlumb-1.7.5-min.js")
    cpout += "<script>\n" + jsplumb_src + "\n</script>\n<script>\n"

    cpout += "var multi_rel_entries = " + json.dumps(multi_rel_entries, ensure_ascii=False) + ";\n"
    cpout += "var rst_rel_entries = " + json.dumps(rst_rel_entries, ensure_ascii=False) + ";\n"
    cpout += """function options_html_from_entries(entries){
        return entries.map(function(e){
            var opt = document.createElement("option");
            opt.value = e.value;
            opt.textContent = e.label;
            return opt.outerHTML;
        }).join("");
    }
    function select_my_rel(options,my_rel){
        var entries = (options === "multi") ? multi_rel_entries : rst_rel_entries;
        var html = options_html_from_entries(entries);
        var needle = "<option value='" + my_rel + "'";
        var repl = "<option selected='selected' value='" + my_rel + "'";
        return html.split(needle).join(repl);
    }
"""

    cpout += """function rel_display(rel){
        return (rel || "").replace(/_(m|r)$/, "");
    }
    function make_relchooser(id, option_type, rel){
        var wrap = document.createElement("span");
        wrap.className = "rst_rel_wrap";
        var hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.id = "sel" + id.replace("n", "");
        hidden.value = rel || "";
        wrap.appendChild(hidden);
        var label = document.createElement("span");
        label.className = "rst_rel_label";
        label.textContent = rel_display(rel);
        wrap.appendChild(label);
        return $(wrap);
    }"""

    cpout += """
        var rstStyleTarget = document.body || document.documentElement;
        var rstComputedStyle = (rstStyleTarget && window.getComputedStyle) ? window.getComputedStyle(rstStyleTarget) : null;
        var rstConnectorStroke = '';
        var rstEndpointFill = '';
        if (rstComputedStyle){
            var connectorStrokeValue = rstComputedStyle.getPropertyValue('--rst-connector-stroke');
            if (connectorStrokeValue){
                rstConnectorStroke = connectorStrokeValue.replace(/^\\s+|\\s+$/g, '');
            }
            var endpointFillValue = rstComputedStyle.getPropertyValue('--rst-line-color');
            if (endpointFillValue){
                rstEndpointFill = endpointFillValue.replace(/^\\s+|\\s+$/g, '');
            }
        }
        if (!rstConnectorStroke){
            rstConnectorStroke = 'rgba(0,0,0,0.5)';
        }
        if (!rstEndpointFill){
            rstEndpointFill = '#000000';
        }
            jsPlumb.importDefaults({
            PaintStyle : {
                lineWidth:2,
                strokeStyle: rstConnectorStroke
            },
            HoverPaintStyle : {
                strokeStyle: rstConnectorStroke
            },
            Endpoints : [ [ "Dot", { radius:1 } ], [ "Dot", { radius:1 } ] ],
              EndpointStyles : [{ fillStyle: rstEndpointFill }, { fillStyle: rstEndpointFill }],
              EndpointHoverStyles : [{ fillStyle: rstEndpointFill }, { fillStyle: rstEndpointFill }],
              Anchor:"Top",
                Connector : [ "Bezier", { curviness:50 } ]
            });
        jsPlumb.bind("connection", function(info){
            var overlays = info.connection.getOverlays();
            for (var overlayId in overlays){
                if (!overlays.hasOwnProperty(overlayId)){
                    continue;
                }
                var overlay = overlays[overlayId];
                if (overlay && overlay.type === "Arrow" && overlay.setPaintStyle){
                    overlay.setPaintStyle({ strokeStyle: rstConnectorStroke, fillStyle: rstConnectorStroke });
                }
            }
        });
             jsPlumb.ready(function() {

    jsPlumb.setContainer(document.getElementById("inner_canvas"));
    """

    cpout += "jsPlumb.setSuspendDrawing(true);"

    for key in nodes:
        node = nodes[key]
        if node.kind == "edu":
            node_id_str = "edu" + node.id
        else:
            node_id_str = "g" + node.id
        cpout += 'jsPlumb.makeSource("' + node_id_str + '", {anchor: "Top", filter: ".num_id", allowLoopback:false});'
        cpout += 'jsPlumb.makeTarget("' + node_id_str + '", {anchor: "Top", filter: ".num_id", allowLoopback:false});'

    # Connect nodes
    for key in nodes:
        node = nodes[key]
        if node.parent != "0":
            parent = nodes[node.parent]
            if node.kind == "edu":
                node_id_str = "edu" + node.id
            else:
                node_id_str = "g" + node.id
            if parent.kind == "edu":
                parent_id_str = "edu" + parent.id
            else:
                parent_id_str = "g" + parent.id

            if node.relname == "span":
                cpout += (
                    'jsPlumb.connect({source:"'
                    + node_id_str
                    + '",target:"'
                    + parent_id_str
                    + '", connector:"Straight", anchors: ["Top","Bottom"]});'
                )
            elif parent.kind == "multinuc" and node.relkind == "multinuc":
                cpout += (
                    'jsPlumb.connect({source:"'
                    + node_id_str
                    + '",target:"'
                    + parent_id_str
                    + '", connector:"Straight", anchors: ["Top","Bottom"], overlays: [ ["Custom", {create:function(component) {return make_relchooser('
                    + json.dumps(str(node.id))
                    + ',"multi",'
                    + json.dumps(str(node.relname))
                    + ');},location:0.2,id:"customOverlay"}]]});'
                )
            else:
                cpout += (
                    'jsPlumb.connect({source:"'
                    + node_id_str
                    + '",target:"'
                    + parent_id_str
                    + '", overlays: [ ["Arrow" , { width:12, length:12, location:0.95 }],["Custom", {create:function(component) {return make_relchooser('
                    + json.dumps(str(node.id))
                    + ',"rst",'
                    + json.dumps(str(node.relname))
                    + ');},location:0.1,id:"customOverlay"}]]});'
                )

    cpout += """
        jsPlumb.setSuspendDrawing(false,true);

        jsPlumb.bind("connection", function(info) {
           source = info.sourceId.replace(/edu|g/,"")
           target = info.targetId.replace(/edu|g/g,"")
        });

        jsPlumb.bind("beforeDrop", function(info) {
            $(".minibtn").prop("disabled",true);
    """

    cpout += """
            var node_id = "n"+info.sourceId.replace(/edu|g|lg/,"");
            var new_parent_id = "n"+info.targetId.replace(/edu|g|lg/,"");

            nodes = parse_data();
            new_parent = nodes[new_parent_id];
            relname = nodes[node_id].relname;
            new_parent_kind = new_parent.kind;
            if (nodes[node_id].parent != "n0"){
                old_parent_kind = nodes[nodes[node_id].parent].kind;
            }
            else
            {
                old_parent_kind ="none";
            }

            if (info.sourceId != info.targetId){
                if (!(is_ancestor(new_parent_id,node_id))){
                    jsPlumb.select({source:info.sourceId}).detach();
                    if (new_parent_kind == "multinuc"){
                        relname = get_multirel(new_parent_id,node_id,nodes);
                        jsPlumb.connect({source:info.sourceId, target:info.targetId, connector:"Straight", anchors: ["Top","Bottom"], overlays: [ ["Custom", {create:function(component) {return make_relchooser(node_id,"multi",relname);},location:0.2,id:"customOverlay"}]]});
                    }
                    else{
                        jsPlumb.connect({source:info.sourceId, target:info.targetId, overlays: [ ["Arrow" , { width:12, length:12, location:0.95 }],["Custom", {create:function(component) {return make_relchooser(node_id,"rst",relname);},location:0.1,id:"customOverlay"}]]});
                    }
                    new_rel = document.getElementById("sel"+ node_id.replace("n","")).value;
                    act('up:' + node_id.replace("n","") + ',' + new_parent_id.replace("n",""));
                    update_rel(node_id,new_rel,nodes);
                    recalculate_depth(parse_data());
                }
            }

            $(".minibtn").prop("disabled",false);

        });

    });
</script>

</div>
</body>
</html>
"""
    return cpout


def rs3topng(
    rs3_filepath: PathLike,
    png_filepath: PathLike | None = None,
    base64_encoded: bool = False,
    *,
    device_scale_factor: int = 2,
    timeout_ms: int = 10_000,
) -> bytes | str | None:
    """Convert an RS3 file into a PNG image of the RST tree using Playwright/Chromium."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise RuntimeError(
            "Detected running asyncio loop. Use the async-safe version instead:\n    await rs3topng_async(...)\n"
        )

    html_str = rs3tohtml(os.fspath(rs3_filepath))

    with sync_playwright() as p:
        try:
            browser = launch_chromium(p)
        except Exception as exc:
            raise ImportError("Browser is not installed.\nRun:\n  playwright install chromium") from exc
        context = browser.new_context(
            device_scale_factor=device_scale_factor,
            color_scheme="light",
        )
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        attach_navigation_guard(page)

        try:
            page.set_content(html_str, wait_until="domcontentloaded", timeout=timeout_ms)
        except PlaywrightTimeoutError:
            pass

        page.wait_for_timeout(50)

        doc_width = max(int(page.evaluate(JS_GET_DOCUMENT_WIDTH)), 320)
        doc_height = max(int(page.evaluate(JS_GET_DOCUMENT_HEIGHT)), 240)
        page.set_viewport_size({"width": doc_width, "height": doc_height})
        png_bytes: bytes = page.screenshot(full_page=True, type="png")
        context.close()
        browser.close()

    return _emit_png(png_bytes, png_filepath, base64_encoded)


async def rs3topng_async(
    rs3_filepath: PathLike,
    png_filepath: PathLike | None = None,
    base64_encoded: bool = False,
    *,
    device_scale_factor: int = 2,
    viewport_width: int = 1600,
    viewport_height: int = 1000,
    timeout_ms: int = 10_000,
    margin_px: int = 12,
) -> bytes | str | None:
    html_str = rs3tohtml(os.fspath(rs3_filepath))

    async with async_playwright() as p:
        try:
            browser = await launch_chromium_async(p)
        except Exception as exc:
            raise ImportError("Browser is not installed.\nRun:\n  playwright install chromium") from exc
        context = await browser.new_context(
            device_scale_factor=device_scale_factor,
            viewport={"width": viewport_width, "height": viewport_height},
            color_scheme="light",
        )
        page = await context.new_page()
        page.set_default_timeout(timeout_ms)
        await attach_navigation_guard_async(page)
        try:
            await page.set_content(html_str, wait_until="domcontentloaded", timeout=timeout_ms)
        except PlaywrightTimeoutError:
            pass

        await page.wait_for_timeout(100)
        bbox = await page.evaluate(JS_GRAPH_BBOX)
        x = max(bbox["x"] - margin_px, 0)
        y = max(bbox["y"] - margin_px, 0)
        w = bbox["width"] + margin_px * 2
        h = bbox["height"] + margin_px * 2
        await page.set_viewport_size(
            {
                "width": max(viewport_width, x + w + 20),
                "height": max(viewport_height, y + h + 20),
            }
        )
        png_bytes: bytes = await page.screenshot(
            type="png",
            clip={"x": x, "y": y, "width": w, "height": h},
        )
        await context.close()
        await browser.close()

    return _emit_png(trim_whitespace(png_bytes), png_filepath, base64_encoded)


async def rs3topdf_async(
    rs3_filepath: PathLike,
    pdf_path: str,
    *,
    device_scale_factor: int = 2,
    viewport_width: int = 1600,
    viewport_height: int = 1000,
    timeout_ms: int = 10_000,
    margin_px: int = 12,
) -> None:
    html_str = rs3tohtml(os.fspath(rs3_filepath))

    async with async_playwright() as p:
        try:
            browser = await launch_chromium_async(p)
        except Exception as exc:
            raise ImportError("Browser is not installed.\nRun:\n  playwright install chromium") from exc

        context = await browser.new_context(
            device_scale_factor=device_scale_factor,
            viewport={"width": viewport_width, "height": viewport_height},
            color_scheme="light",
        )
        page = await context.new_page()
        page.set_default_timeout(timeout_ms)
        await attach_navigation_guard_async(page)
        try:
            await page.set_content(html_str, wait_until="domcontentloaded", timeout=timeout_ms)
        except PlaywrightTimeoutError:
            pass
        await page.wait_for_timeout(100)

        bbox = await page.evaluate(JS_GRAPH_BBOX)
        x = max(bbox["x"] - margin_px, 0)
        y = max(bbox["y"] - margin_px, 0)
        w = bbox["width"] + margin_px * 2
        h = bbox["height"] + margin_px * 2

        await page.add_style_tag(
            content=f"""
html, body {{
  margin: 0 !important;
  padding: 0 !important;
  width: {w}px !important;
  height: {h}px !important;
  overflow: hidden !important;
}}
#inner_canvas {{
  position: absolute !important;
  left: {-x}px !important;
  top: {-y}px !important;
}}
@page {{
  size: {w}px {h}px;
  margin: 0;
}}
"""
        )
        await page.pdf(
            path=pdf_path,
            width=f"{w}px",
            height=f"{h}px",
            print_background=True,
            prefer_css_page_size=True,
        )
        await context.close()
        await browser.close()


def _emit_png(
    png_bytes: bytes,
    png_filepath: PathLike | None,
    base64_encoded: bool,
) -> bytes | str | None:
    if base64_encoded:
        png_text = base64.b64encode(png_bytes).decode("ascii")
        if png_filepath:
            Path(png_filepath).write_text(png_text, encoding="utf-8")
            return None
        return png_text
    if png_filepath:
        Path(png_filepath).write_bytes(png_bytes)
        return None
    return png_bytes


class RenderedRST(str):
    """String subclass that cooperates with IPython display hooks."""

    _already_displayed: bool
    _display_override: str | None

    def __new__(
        cls,
        value: str,
        *,
        already_displayed: bool,
        display_override: str | None = None,
    ) -> RenderedRST:
        rendered = super().__new__(cls, value)
        rendered._already_displayed = already_displayed
        rendered._display_override = display_override
        return rendered

    def _repr_html_(self) -> str:
        if getattr(self, "_already_displayed", False):
            return ""
        return getattr(self, "_display_override", None) or str(self)


def _new_root_id() -> str:
    return "rst-root-" + uuid.uuid4().hex


def _wrap_for_colab(html_str: str) -> str:
    # Use fragment so we don't inject <html>/<head>/<body> inside a <div>
    frag = _html_to_fragment(html_str)
    root_id = _new_root_id()
    return (
        f'<div id="{root_id}" style="margin:0;padding:0;">{frag}</div>\n'
        "<script>\n"
        "(function() {\n"
        "  const maxFrames = 1000;\n"
        "  const stableNeeded = 20;\n"
        "  let last = -1;\n"
        "  let stable = 0;\n"
        "  let frames = 0;\n"
        "  function hDoc() {\n"
        "    return Math.max(\n"
        "      document.body.scrollHeight,\n"
        "      document.documentElement.scrollHeight,\n"
        "      document.body.offsetHeight,\n"
        "      document.documentElement.offsetHeight,\n"
        "      document.body.clientHeight,\n"
        "      document.documentElement.clientHeight\n"
        "    );\n"
        "  }\n"
        "  function tick() {\n"
        "    try {\n"
        "      const h = hDoc();\n"
        "      if (h !== last) {\n"
        "        last = h;\n"
        "        stable = 0;\n"
        "        google.colab.output.setIframeHeight(h, false);\n"
        "      } else if (++stable === stableNeeded) {\n"
        "        google.colab.output.setIframeHeight(last, false);\n"
        "        return;\n"
        "      }\n"
        "    } catch (e) {}\n"
        "    if (++frames < maxFrames) requestAnimationFrame(tick);\n"
        "    else { try { google.colab.output.setIframeHeight(hDoc(), false); } catch(e) {} }\n"
        "  }\n"
        "  setTimeout(() => requestAnimationFrame(tick), 0);\n"
        "  setTimeout(() => { try { google.colab.output.setIframeHeight(hDoc(), false); } catch(e) {} }, 500);\n"
        "  setTimeout(() => { try { google.colab.output.setIframeHeight(hDoc(), false); } catch(e) {} }, 1500);\n"
        "  setTimeout(() => { try { google.colab.output.setIframeHeight(hDoc(), false); } catch(e) {} }, 3000);\n"
        "})();\n"
        "</script>"
    )


def _wrap_for_notebook(html_str: str) -> str:
    # Use fragment so we don't inject <html>/<head>/<body> inside a <div>
    frag = _html_to_fragment(html_str)
    root_id = _new_root_id()

    return (
        f'<div id="{root_id}" '
        'style="margin:0;padding:0;max-width:100%;overflow-x:auto;overflow-y:visible;">'
        f"{frag}</div>\n"
        f'<script data-rst-resize="{root_id}">\n'
        "(function() {\n"
        f"  var ROOT_ID = {root_id!r};\n"
        "  var cachedScript = null;\n"
        "  function matches(el, sel){var p=Element.prototype;var f=p.matches||p.msMatchesSelector||p.webkitMatchesSelector;return el&&f?f.call(el,sel):false}\n"
        "  function closest(el, sel){if(!el)return null;if(el.closest)return el.closest(sel);while(el&&el.nodeType===1){if(matches(el,sel))return el;el=el.parentElement}return null}\n"
        "  function getScript(){var s=document.currentScript;if(s&&s.dataset&&s.dataset.rstResize===ROOT_ID){cachedScript=s;return s}if(!cachedScript||!cachedScript.isConnected){cachedScript=document.querySelector('script[data-rst-resize=\"'+ROOT_ID+'\"]')}return cachedScript}\n"
        "  function getRoot(s){if(!s)return null;var r=s.previousElementSibling;if(r&&r.id===ROOT_ID)return r;if(s.parentElement){r=s.parentElement.querySelector('#'+ROOT_ID);if(r)return r}return document.getElementById(ROOT_ID)}\n"
        "  function styleEl(el){if(!el)return; if(el.classList&&el.classList.contains('output_scroll'))el.classList.remove('output_scroll'); el.style.maxHeight='none'; el.style.height='auto'; el.style.minHeight='0'; el.style.overflow=''; el.style.overflowX='auto'; el.style.overflowY='visible'}\n"
        "  function measure(root){if(!root)return 0;var rect=root.getBoundingClientRect();var baseTop=rect?rect.top:0;var maxBottom=rect?rect.bottom:0;var els=root.getElementsByTagName('*');for(var i=0;i<els.length;i++){var e=els[i];if(!e||!e.getBoundingClientRect)continue;var r=e.getBoundingClientRect();if(r&&typeof r.bottom==='number'&&r.bottom>maxBottom)maxBottom=r.bottom}var computed=[root.scrollHeight||0,root.offsetHeight||0,rect?rect.height:0,maxBottom-baseTop];var h=0;for(var j=0;j<computed.length;j++){if(computed[j]>h)h=computed[j]}return Math.ceil(h)}\n"
        "  function apply(el,h){if(!el||!h)return;el.style.minHeight=h+'px';el.style.height=h+'px'}\n"
        "  function adjust(){var s=getScript();if(!s)return;var root=getRoot(s);if(!root)return;var container=closest(root,'.output_subarea')||closest(root,'.jp-RenderedHTMLCommon')||closest(root,'.jp-OutputArea-output')||root.parentElement;var scrollable=container?container.querySelector('.output_scroll'):null;var direct=[];if(scrollable)direct.push(scrollable);if(container)direct.push(container);var wrappers=[];var p=container?container.parentElement:null;while(p){wrappers.push(p);if(matches(p,'.output_area')||matches(p,'.jp-OutputArea'))break;p=p.parentElement}var h=measure(root);if(h)h=h+1;direct.forEach(function(el){styleEl(el);apply(el,h)});wrappers.forEach(function(el){styleEl(el);apply(el,h)});if(root)root.style.minHeight=h?h+'px':''}\n"
        "  function run(){adjust();requestAnimationFrame(adjust);setTimeout(adjust,0);setTimeout(adjust,250)}\n"
        "  run();window.addEventListener('resize', run);\n"
        "})();\n"
        "</script>"
    )


def _write_temp_rs3(content: str) -> Path:
    handle = tempfile.NamedTemporaryFile(suffix=".rs3", delete=False)
    try:
        handle.write(content.encode("utf8"))
    finally:
        handle.close()
    return Path(handle.name)


def render(
    rs3_source: PathLike | bytes | IO[str] | IO[bytes],
    *,
    display_inline: bool = True,
    colab: bool = False,
) -> RenderedRST:
    """Render an RST tree and optionally display it inline."""
    temp_path: Path | None = None

    if isinstance(rs3_source, bytes):
        temp_path = _write_temp_rs3(rs3_source.decode("utf8"))
        rs3_path = temp_path
    elif not isinstance(rs3_source, (str, os.PathLike)):
        rs3_content = rs3_source.read()
        if isinstance(rs3_content, bytes):
            rs3_content = rs3_content.decode("utf8")
        temp_path = _write_temp_rs3(rs3_content)
        rs3_path = temp_path
    elif Path(rs3_source).exists():
        rs3_path = Path(rs3_source)
    else:
        temp_path = _write_temp_rs3(str(rs3_source))
        rs3_path = temp_path

    try:
        html_str = rs3tohtml(rs3_path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    already_displayed = False
    if colab:
        display_html = _wrap_for_colab(html_str)
    else:
        display_html = _wrap_for_notebook(html_str)
    if display_inline:
        try:
            ipython_display = import_module("IPython.display")
        except ImportError:
            warnings.warn(
                "IPython is not available; returning HTML string without displaying it.",
                RuntimeWarning,
                stacklevel=2,
            )
        else:
            html_factory = ipython_display.HTML
            display = ipython_display.display
            display(html_factory(display_html))
            already_displayed = True

    return RenderedRST(
        html_str,
        already_displayed=already_displayed,
        display_override=display_html if display_html != html_str else None,
    )


def cli(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(
        description="Convert an RS3 file into an HTML file containing the RST tree.",
    )
    parser.add_argument("rs3_file")
    parser.add_argument("output_file", nargs="?")
    parser.add_argument(
        "-f",
        "--output-format",
        nargs="?",
        default="html",
        help="output format: html (default), png, png-base64",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="run the program in pudb",
    )

    args = parser.parse_args(argv)

    if args.debug:
        debugger = import_module("pudb")
        debugger.set_trace()

    match args.output_format:
        case "png":
            if args.output_file:
                rs3topng(args.rs3_file, args.output_file)
                sys.exit(0)
            sys.stderr.write("No PNG output file given.\n")
            sys.exit(1)
        case "png-base64":
            if args.output_file:
                rs3topng(args.rs3_file, args.output_file, base64_encoded=True)
                sys.exit(0)
            base64_png_str = rs3topng(args.rs3_file, base64_encoded=True)
            assert isinstance(base64_png_str, str)
            sys.stdout.write(base64_png_str)
            sys.exit(0)
        case _:
            if args.output_file:
                Path(args.output_file).write_text(rs3tohtml(args.rs3_file), encoding="utf8")
            else:
                sys.stdout.write(rs3tohtml(args.rs3_file))


if __name__ == "__main__":
    cli(sys.argv[1:])
