"""World-class CLI entrypoint for isanlp_rst discourse parsing and analysis."""

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys
from typing import Any

from isanlp_rst import Parser, RstDocument, __version__
from isanlp_rst.annotation_rst import DiscourseUnit
from isanlp_rst.utils.analysis import tree_stats


def _render_tree_ascii(node: DiscourseUnit, prefix: str = "", is_last: bool = True, is_root: bool = True) -> str:
    """Render a DiscourseUnit binary tree as a beautiful ASCII/Unicode hierarchy."""
    lines: list[str] = []

    branch = "" if is_root else ("└── " if is_last else "├── ")
    connector = prefix + branch

    # Leaf EDU
    if node.left is None and node.right is None:
        rel = f" [{node.nuclearity}: {node.relation}]" if node.relation else ""
        span = f" ({node.start}-{node.end})" if node.start is not None and node.end is not None else ""
        text_snippet = f' "{node.text}"' if node.text else ""
        lines.append(f"{connector}EDU #{node.id}{rel}{span}{text_snippet}")
        return "\n".join(lines)

    # Internal constituent
    nuc_str = f" [{node.nuclearity}: {node.relation}]" if node.relation else (f" [{node.nuclearity}]" if node.nuclearity else "")
    entropy_str = f" [H={node.entropy:.3f}]" if node.entropy is not None and node.entropy > 0 else ""
    span_str = f" ({node.start}-{node.end})" if node.start is not None and node.end is not None else ""
    lines.append(f"{connector}Node #{node.id}{nuc_str}{entropy_str}{span_str}")

    next_prefix = prefix + ("    " if is_last else "│   ")
    children: list[DiscourseUnit] = []
    if node.left is not None:
        children.append(node.left)
    if node.right is not None:
        children.append(node.right)

    for i, child in enumerate(children):
        is_child_last = i == (len(children) - 1)
        child_rendered = _render_tree_ascii(child, prefix=next_prefix, is_last=is_child_last, is_root=False)
        lines.append(child_rendered)

    return "\n".join(lines)


def _load_input_text(args: argparse.Namespace) -> tuple[str, str | None]:
    """Resolve input text and optional filepath."""
    if args.text:
        return args.text, None

    if args.input == "-" or (not args.input and not sys.stdin.isatty()):
        return sys.stdin.read(), None

    if args.input:
        path = Path(args.input)
        if not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")
        return path.read_text(encoding="utf-8"), str(path)

    raise ValueError("No input text provided. Provide an input file, --text string, or pipe via stdin.")


def cmd_parse(args: argparse.Namespace) -> int:
    """Execute the parse command."""
    text, filepath = _load_input_text(args)
    if not text.strip():
        sys.stderr.write("Error: Input text is empty.\n")
        return 1

    device = args.device
    family = args.family or "modernbert"
    parser = Parser(family=family, device=device)

    # Detect input format from extension if available
    input_format = args.input_format
    if not input_format and filepath:
        suffix = Path(filepath).suffix.lower()
        if suffix in (".md", ".markdown"):
            input_format = "markdown"
        elif suffix in (".json",):
            input_format = "docling"
        elif suffix in (".xml", ".dclg"):
            input_format = "doclang"

    # Parse according to format
    doc = RstDocument.from_text(text, document_id=filepath or "cli_doc")
    analysis = parser.parse_document(doc)
    tree = parser.parse_tree(text)

    # Format output
    out_format = args.format.lower()
    output_str = ""

    if out_format == "tree":
        output_str = _render_tree_ascii(tree)
    elif out_format == "json":
        analysis_dict: dict[str, Any] = {
            "schema_version": "1.0",
            "document_id": analysis.document_id,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "kind": node.kind.value if hasattr(node.kind, "value") else str(node.kind),
                    "char_span": list(node.char_span),
                    "text": node.text,
                }
                for node in analysis.nodes
            ],
            "primary_edges": [
                {
                    "parent_id": edge.parent_id,
                    "child_id": edge.child_id,
                    "relation": edge.relation_raw,
                    "concept": edge.relation_concept,
                    "nuclearity": edge.nuclearity.value if hasattr(edge.nuclearity, "value") else str(edge.nuclearity),
                    "confidence": edge.confidence,
                }
                for edge in analysis.primary_edges
            ],
            "secondary_edges": [
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relation": edge.relation_raw,
                    "concept": edge.relation_concept,
                    "confidence": edge.confidence,
                }
                for edge in analysis.secondary_edges
            ],
            "signals": [
                {
                    "signal_id": sig.signal_id,
                    "signal_type": sig.signal_type,
                    "edge_id": sig.edge_id,
                    "token_ids": list(sig.token_ids),
                }
                for sig in analysis.signals
            ],
        }
        output_str = json.dumps(analysis_dict, indent=2, ensure_ascii=False)
    elif out_format == "stats":
        stats = tree_stats(tree)
        output_str = json.dumps(stats, indent=2, ensure_ascii=False)
    elif out_format == "rs3":
        exporter = tree._exporter or None
        if exporter is None:
            from isanlp_rst.annotation_rst import Exporter
            exporter = Exporter()
        output_str = "<rst>\n" + exporter.make_header(tree) + exporter.make_body(tree) + "</rst>"
    else:
        sys.stderr.write(f"Unknown format: {out_format}\n")
        return 1

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_str, encoding="utf-8")
        sys.stderr.write(f"Wrote output to {out_path}\n")
    else:
        print(output_str)

    return 0


def cmd_view(args: argparse.Namespace) -> int:
    """Export or visualize an RST tree / RS3 file."""
    from isanlp_rst.rstviewer.main import rs3tohtml, rs3topng

    input_path = Path(args.input)
    if not input_path.is_file():
        sys.stderr.write(f"Error: file not found: {input_path}\n")
        return 1

    out_format = (args.format or input_path.suffix.lstrip(".") or "html").lower()
    target_out = args.output or f"{input_path.stem}.{out_format}"

    if out_format == "html":
        html_content = rs3tohtml(input_path)
        Path(target_out).write_text(html_content, encoding="utf-8")
        sys.stderr.write(f"Rendered HTML to {target_out}\n")
    elif out_format == "png":
        png_bytes = rs3topng(input_path)
        if isinstance(png_bytes, bytes):
            Path(target_out).write_bytes(png_bytes)
        elif isinstance(png_bytes, str):
            Path(target_out).write_text(png_bytes, encoding="utf-8")
        sys.stderr.write(f"Rendered PNG to {target_out}\n")
    else:
        sys.stderr.write(f"Unknown viewer format: {out_format}\n")
        return 1

    if args.open:
        import webbrowser
        webbrowser.open(f"file://{Path(target_out).resolve()}")

    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Run lightweight HTTP discourse parsing server."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    host = args.host or "127.0.0.1"
    port = args.port or 8080
    device = args.device or "auto"

    sys.stderr.write(f"Initializing isanlp_rst parser on device '{device}'...\n")
    parser = Parser(family="modernbert", device=device)

    class ParseRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/health", "/"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {
                    "status": "ok",
                    "package": "isanlp_rst",
                    "version": __version__,
                    "engine": "modernbert",
                }
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self) -> None:
            if self.path == "/parse":
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len)
                try:
                    data = json.loads(body.decode("utf-8"))
                    text = data.get("text", "")
                    if not text.strip():
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'{"error": "empty text"}')
                        return

                    tree = parser.parse_tree(text)
                    stats = tree_stats(tree)
                    doc = RstDocument.from_text(text, document_id="api_request")
                    analysis = parser.parse_document(doc)

                    resp: dict[str, Any] = {
                        "tree_ascii": _render_tree_ascii(tree),
                        "stats": stats,
                        "nodes_count": len(analysis.nodes),
                        "primary_edges_count": len(analysis.primary_edges),
                        "secondary_edges_count": len(analysis.secondary_edges),
                    }
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(resp).encode("utf-8"))
                except (ValueError, TypeError, KeyError, RuntimeError, json.JSONDecodeError) as exc:
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

    server = ThreadingHTTPServer((host, port), ParseRequestHandler)
    sys.stderr.write(f"isanlp_rst server running at http://{host}:{port} (Press Ctrl+C to stop)\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("\nServer stopped.\n")
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    """Print package runtime and environment information."""
    import platform
    import torch

    print(f"isanlp_rst: {__version__}")
    print(f"Python:     {platform.python_version()} ({platform.python_implementation()})")
    print(f"PyTorch:    {torch.__version__}")
    print(f"MPS:        {'available' if torch.backends.mps.is_available() else 'unavailable'}")
    print(f"CUDA:       {'available' if torch.cuda.is_available() else 'unavailable'}")
    print("Backbone:   answerdotai/ModernBERT-base (8,192 token window, RoPE, SDPA)")
    return 0


def create_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="isanlp-rst",
        description="World-class Rhetorical Structure Theory (RST) parser and discourse graph engine.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # parse
    p_parse = subparsers.add_parser("parse", help="Parse text or document into an RST discourse tree/graph")
    p_parse.add_argument("input", nargs="?", help="Input file (.txt, .md, .xml, .json) or '-' for stdin")
    p_parse.add_argument("-t", "--text", help="Raw input string to parse directly")
    p_parse.add_argument("-f", "--format", choices=["tree", "json", "stats", "rs3"], default="tree", help="Output format")
    p_parse.add_argument("-i", "--input-format", choices=["text", "markdown", "docling", "doclang"], help="Explicit input format override")
    p_parse.add_argument("-o", "--output", help="Write output to filepath instead of stdout")
    p_parse.add_argument("-d", "--device", default="auto", choices=["auto", "cpu", "mps", "cuda"], help="Compute device")
    p_parse.add_argument("--family", default="modernbert", help="Model family")
    p_parse.set_defaults(func=cmd_parse)

    # view
    p_view = subparsers.add_parser("view", help="Render RST tree or RS3 XML as interactive HTML, SVG, or PNG")
    p_view.add_argument("input", help="Path to .rs3 file")
    p_view.add_argument("-f", "--format", choices=["html", "svg", "png"], default="html", help="Render output format")
    p_view.add_argument("-o", "--output", help="Output filepath")
    p_view.add_argument("--open", action="store_true", help="Open rendered HTML in web browser")
    p_view.set_defaults(func=cmd_view)

    # serve
    p_serve = subparsers.add_parser("serve", help="Run high-throughput HTTP discourse parsing API server")
    p_serve.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    p_serve.add_argument("-p", "--port", type=int, default=8080, help="Bind port (default: 8080)")
    p_serve.add_argument("-d", "--device", default="auto", choices=["auto", "cpu", "mps", "cuda"], help="Compute device")
    p_serve.set_defaults(func=cmd_serve)

    # version
    p_version = subparsers.add_parser("version", help="Show version and hardware backend info")
    p_version.set_defaults(func=cmd_version)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI main entrypoint."""
    parser = create_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
