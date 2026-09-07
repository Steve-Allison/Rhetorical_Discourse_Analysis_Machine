"""Run a fixed local MLX generation job in an isolated Pixi environment.

This module imports only stdlib until execution. It records generated text, not
analytical correctness. The companion llm_evaluation module validates and scores.
"""

import argparse
from datetime import UTC, datetime
from hashlib import sha256
from importlib import import_module, metadata
import json
from pathlib import Path
import resource
from time import perf_counter
from typing import Any, cast


class JsonTreePrefix:
    """Reject impossible prefixes without repairing or accepting unfinished output."""

    def __init__(self, edu_count: int, inventory: tuple[str, ...]) -> None:
        self.edu_count = edu_count
        self.inventory = frozenset(inventory)
        self.buffer = ""
        self.state = "open"
        self.spans: set[tuple[int, int]] = set()

    def feed(self, fragment: str) -> str | None:
        self.buffer += fragment
        while self.buffer.strip():
            self.buffer = self.buffer.lstrip()
            first = self.buffer[0]
            if self.state == "open":
                if first != "[":
                    return "response must begin with a JSON array"
                self.buffer = self.buffer[1:]
                self.state = "first_row_or_end"
            elif self.state in {"first_row_or_end", "row"}:
                if first == "]" and self.state == "first_row_or_end":
                    if len(self.spans) != self.edu_count - 1:
                        return "response closes before providing N-1 internal nodes"
                    self.buffer = self.buffer[1:]
                    self.state = "closed"
                    continue
                if first != "[":
                    return "every internal node must be an array"
                try:
                    row, consumed = json.JSONDecoder().raw_decode(self.buffer)
                except json.JSONDecodeError:
                    return None
                if not isinstance(row, list):
                    return "every internal node requires four fields"
                fields = cast(list[object], row)
                if len(fields) != 4:
                    return "every internal node requires four fields"
                start, end, split, label = fields
                if type(start) is not int or type(end) is not int or type(split) is not int:
                    return "EDU coordinates must be integers"
                if not 1 <= start <= split < end <= self.edu_count:
                    return "internal-node coordinates do not form a valid split"
                if not isinstance(label, str) or label not in self.inventory:
                    return "joint label is absent from the declared inventory"
                if (start, end) in self.spans:
                    return "duplicate internal-node span"
                self.spans.add((start, end))
                if len(self.spans) > self.edu_count - 1:
                    return "response exceeds N-1 internal nodes"
                self.buffer = self.buffer[consumed:]
                self.state = "separator"
            elif self.state == "separator":
                if first == ",":
                    self.state = "row"
                elif first == "]":
                    if len(self.spans) != self.edu_count - 1:
                        return "response closes before providing N-1 internal nodes"
                    self.state = "closed"
                else:
                    return "internal nodes require a comma or closing array"
                self.buffer = self.buffer[1:]
            else:
                return "non-whitespace follows the JSON array"
        return None


def run_generation(jobs_path: Path, model_path: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(output)
    jobs_raw = jobs_path.read_bytes()
    jobs = json.loads(jobs_raw)
    config_raw = (model_path / "config.json").read_bytes()
    config = json.loads(config_raw)
    context_limit = config.get("text_config", config)["max_position_embeddings"]
    if type(context_limit) is not int or context_limit <= 0:
        raise ValueError("model configuration lacks a positive architectural context length")
    mlx = import_module("mlx.core")
    lm = import_module("mlx_lm")
    sampling = import_module("mlx_lm.sample_utils")
    started = perf_counter()
    model, tokenizer = lm.load(str(model_path))
    load_seconds = perf_counter() - started
    results: dict[str, Any] = {
        "schema_version": "rdam.rst.llm-generation/v1", "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "jobs_sha256": sha256(jobs_raw).hexdigest(), "model_path": str(model_path.resolve()),
        "model_config_sha256": sha256(config_raw).hexdigest(),
        "generation_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "runtime": {name: metadata.version(name) for name in ("mlx-lm", "mlx", "transformers")},
        "load_seconds": load_seconds, "decoding": {"selection": "greedy", "enable_thinking": False},
        "prefix_policy": "stop_only_when_prefix_cannot_satisfy_fixed_format; no_output_repair",
        "resource_condition": "other local workloads may be active; timings are observations, not isolated performance",
        "documents": {},
    }
    temporary = output.with_name(output.name + ".partial")
    if temporary.exists():
        raise FileExistsError(temporary)
    for name, job in jobs["documents"].items():
        # Job v1 appends its sole JSON source object after the prose protocol.
        source_input = json.loads(job["prompt"][job["prompt"].index("{"):])
        prefix = JsonTreePrefix(len(source_input["edus"]), tuple(jobs["joint_inventory"]))
        formatted = tokenizer.apply_chat_template(
            [{"role": "user", "content": job["prompt"]}],
            add_generation_prompt=True, tokenize=False, enable_thinking=False,
        )
        input_tokens = len(tokenizer.encode(formatted))
        budget = context_limit - input_tokens
        if budget <= 0:
            raise ValueError(f"input exceeds configured architectural context: {name}")
        mlx.reset_peak_memory()
        started = perf_counter()
        first_response: float | None = None
        chunks: list[str] = []
        last = None
        prefix_failure = None
        for response in lm.stream_generate(
            model, tokenizer, formatted, max_tokens=budget, sampler=sampling.make_sampler(temp=0.0),
        ):
            if first_response is None:
                first_response = perf_counter() - started
            chunks.append(response.text)
            last = response
            prefix_failure = prefix.feed(response.text)
            if prefix_failure is not None:
                break
        if last is None:
            raise ValueError(f"generation returned no response: {name}")
        results["documents"][name] = {
            "prompt_sha256": sha256(job["prompt"].encode()).hexdigest(),
            "fixture_sha256": job["fixture_sha256"], "split": job["split"],
            "response_text": "".join(chunks),
            "finish_reason": last.finish_reason if prefix_failure is None else "invalid_prefix",
            "model_finish_reason": last.finish_reason, "prefix_failure": prefix_failure,
            "architectural_output_budget": budget, "prompt_tokens": last.prompt_tokens,
            "generation_tokens": last.generation_tokens, "elapsed_seconds": perf_counter() - started,
            "first_response_seconds": first_response, "prompt_tokens_per_second": last.prompt_tps,
            "generation_tokens_per_second": last.generation_tps,
            "mlx_peak_allocated_bytes": mlx.get_peak_memory(),
            "process_peak_rss_bytes_macos": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        }
        temporary.write_text(json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        temporary.replace(output)
        print(json.dumps({"document": name, "completed": len(results["documents"]),
                          "total": len(jobs["documents"]), "tokens": last.generation_tokens}), flush=True)
    if jobs_path.read_bytes() != jobs_raw or (model_path / "config.json").read_bytes() != config_raw:
        raise ValueError("generation inputs changed while running")
    results["status"] = "complete"
    results["finished_at"] = datetime.now(UTC).isoformat()
    temporary.write_text(json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_generation(args.jobs, args.model, args.output)


if __name__ == "__main__":
    main()
