"""Probe every mandatory eRST tokenizer at an immutable revision."""

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import platform
from tempfile import TemporaryDirectory
from typing import Any

import tokenizers
import torch
import transformers
from transformers import AutoTokenizer

from isanlp_rst.contracts.erst import TokenizerCompatibilityReceipt, TokenizerProbeResult
from isanlp_rst.erst.environment import load_repository_environment


@dataclass(frozen=True, slots=True)
class _TokenizerTarget:
    model_id: str
    revision: str


_TARGETS = (
    _TokenizerTarget("google/electra-base-discriminator", "1ae76a97c7e84a4e640876a07453fccd636f0667"),
    _TokenizerTarget("microsoft/deberta-v3-base", "8ccc9b6f36199bec6961081d44eb72fb3f7353f3"),
    _TokenizerTarget("answerdotai/ModernBERT-base", "8949b909ec900327062f0ebf497f51aef5e6f0c8"),
    _TokenizerTarget("answerdotai/ModernBERT-large", "45bb4654a4d5aaff24dd11d4781fa46d39bf8c13"),
    _TokenizerTarget("FacebookAI/xlm-roberta-large", "c23d21b0620b635a76227c604d44e43a9f0ee389"),
    _TokenizerTarget("Qwen/Qwen3-4B", "1cfa9a7208912126459214e8b04321603b3df60c"),
)


def _encoding_payload(tokenizer: Any) -> dict[str, Any]:
    encoding = tokenizer(
        ["However, the first span continues.", "Because evidence matters."],
        padding=True,
        return_tensors="pt",
        return_special_tokens_mask=True,
        return_offsets_mapping=True,
    )
    keys = ("input_ids", "attention_mask", "special_tokens_mask", "offset_mapping")
    return {key: encoding[key].tolist() for key in keys}


def _payload_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


def _probe_target(target: _TokenizerTarget, token: str | None) -> TokenizerProbeResult:
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            target.model_id,
            revision=target.revision,
            token=token,
            use_fast=True,
            trust_remote_code=False,
        )
        if not tokenizer.is_fast:
            raise ValueError("resolved tokenizer is not a fast tokenizer")
        original_payload = _encoding_payload(tokenizer)
        original_hash = _payload_hash(original_payload)
        if not torch.backends.mps.is_available():
            raise RuntimeError("MPS is unavailable for tokenizer tensor compatibility")
        tensor = torch.tensor(original_payload["input_ids"], dtype=torch.int64)
        mps_roundtrip = torch.equal(tensor, tensor.to("mps").cpu())
        with TemporaryDirectory(prefix="isanlp-rst-tokenizer-") as temporary_directory:
            tokenizer.save_pretrained(temporary_directory)
            reloaded = AutoTokenizer.from_pretrained(
                temporary_directory,
                local_files_only=True,
                use_fast=True,
                trust_remote_code=False,
            )
            if not reloaded.is_fast:
                raise ValueError("locally reloaded tokenizer is not fast")
            reloaded_payload = _encoding_payload(reloaded)
        reloaded_hash = _payload_hash(reloaded_payload)
        return TokenizerProbeResult(
            model_id=target.model_id,
            revision=target.revision,
            tokenizer_class=type(tokenizer).__name__,
            is_fast=True,
            encoding_sha256=original_hash,
            local_reload_sha256=reloaded_hash,
            local_reload_equal=original_payload == reloaded_payload,
            mps_tensor_roundtrip=mps_roundtrip,
            succeeded=original_payload == reloaded_payload and mps_roundtrip,
        )
    except (OSError, ValueError, RuntimeError, ImportError, Warning) as error:
        return TokenizerProbeResult(
            model_id=target.model_id,
            revision=target.revision,
            tokenizer_class=None,
            is_fast=False,
            local_reload_equal=False,
            mps_tensor_roundtrip=False,
            succeeded=False,
            failure_type=type(error).__name__,
            failure_message="Pinned fast-tokenizer load, parity, or MPS tensor probe failed",
        )


def probe_mandatory_tokenizers(repository_root: Path) -> TokenizerCompatibilityReceipt:
    """Run all mandatory probes using the explicit repository environment boundary."""

    environment = load_repository_environment(repository_root)
    token = environment.hf_token.get_secret_value() if environment.hf_token is not None else None
    probes = tuple(_probe_target(target, token) for target in _TARGETS)
    return TokenizerCompatibilityReceipt(
        python_version=platform.python_version(),
        transformers_version=transformers.__version__,
        tokenizers_version=tokenizers.__version__,
        mps_available=torch.backends.mps.is_available(),
        probes=probes,
        succeeded=torch.backends.mps.is_available() and all(probe.succeeded for probe in probes),
    )


def main() -> None:
    """Persist a secret-free compatibility receipt at an explicit local path."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = probe_mandatory_tokenizers(args.repository_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
    print(
        f"tokenizer_probes={len(receipt.probes)} succeeded={receipt.succeeded} "
        f"receipt_sha256={receipt.receipt_sha256} output={args.output.name}"
    )
    if not receipt.succeeded:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
