"""Isolated occurrence extraction; verifies UTF-8 byte offsets against exact text."""
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import resource
from time import perf_counter

from docling_nlp.nlp_utils import init_nlp_model
from docling_nlp.utils.load_pretrained_models import get_resources_dir


def main() -> None:
    root = Path(__file__).parent
    prepared = json.loads((root / "prepared.json").read_text())
    started = perf_counter()
    model = init_nlp_model("language;term")
    initialization = perf_counter() - started
    passages = []
    verified = 0
    character_counterexamples = 0
    whitespace_substitutions = 0
    for passage in prepared["passages"]:
        text = passage["baseline"]["surfaces"][0]["text"]
        start = perf_counter()
        result = model.apply_on_text(text)
        elapsed = perf_counter() - start
        normalized = result["text"]
        if not result["model-application"]["success"]:
            raise ValueError("NLP failed")
        if len(normalized) != len(text) or any(a != b and not (a.isspace() and b.isspace())
                                               for a, b in zip(text, normalized, strict=True)):
            raise ValueError("NLP changed text beyond position-preserving whitespace substitution")
        whitespace_substitutions += sum(a != b for a, b in zip(text, normalized, strict=True))
        instances = result.get("instances", {"headers": [], "data": []})
        occurrences = []
        for row in instances["data"]:
            item = dict(zip(instances["headers"], row, strict=True))
            if item["type"] not in {"term", "name"}:
                continue
            begin, end = item["char_i"], item["char_j"]
            raw = normalized.encode("utf-8")
            quote = raw[begin:end].decode("utf-8", errors="strict")
            if quote != item["original"]:
                raise ValueError(f"native offset mismatch: {item}")
            verified += 1
            character_counterexamples += text[begin:end] != quote
            source_start, source_end = len(raw[:begin].decode("utf-8")), len(raw[:end].decode("utf-8"))
            occurrences.append({"start": source_start,
                "end": source_end, "quote": text[source_start:source_end],
                "type": item["type"], "subtype": item["subtype"]})
        passages.append({"id": passage["id"], "seconds": elapsed, "occurrences": occurrences, "raw": result})
    resources = Path(get_resources_dir())
    model_files = {str(path.relative_to(resources)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in sorted(resources.rglob("*")) if path.is_file()}
    (root / "extracted.json").write_text(json.dumps({"version": version("docling-nlp"),
        "gold_sha256": prepared["gold_sha256"], "models": "language;term", "model_files": model_files,
        "initialization_seconds": initialization, "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "verified_byte_offsets": verified, "position_preserving_whitespace_substitutions": whitespace_substitutions, "python_character_offset_counterexamples": character_counterexamples,
        "passages": passages}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
