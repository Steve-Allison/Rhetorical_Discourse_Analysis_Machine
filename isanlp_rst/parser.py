from __future__ import annotations

import json
import os
from glob import glob
from typing import TYPE_CHECKING, Optional, Sequence

from .dmrst_parser.predictor import PredictorDMRST
from .universal_parser.predictor import PredictorUniRST

if TYPE_CHECKING:
    import torch


class Parser:
    """Public façade for the DMRST and UniRST parser families.

    The family is resolved in priority order:

    1. Explicit ``family='dmrst'|'unirst'`` argument.
    2. ``hf_model_version`` (mapped to a family via ``DMRST_PARSERS`` /
       ``UNIVERSAL_PARSERS``).
    3. ``model_dir`` content auto-detection (presence of
       ``data_manager_*.pickle`` or a ``config.json`` with ``data.corpora``
       implies UniRST; otherwise ``relation_table.txt`` implies DMRST).

    Device selection uses ``device=`` (``"auto"`` by default — CUDA if
    present, else MPS on Apple Silicon, else CPU). The legacy integer
    ``cuda_device=`` is still accepted but deprecated.

    Examples:
        >>> Parser(hf_model_version='gumrrg', device='cpu')               # DMRST
        >>> Parser(hf_model_version='unirst', relinventory='eng.erst.gum') # UniRST
        >>> Parser(model_dir='/path/to/checkpoint', family='dmrst')        # local
    """

    DMRST_PARSERS = ('gumrrg', 'rstdt', 'rstreebank')
    UNIVERSAL_PARSERS = ('rrtrrg', 'unirst')
    AVAILABLE_VERSIONS = DMRST_PARSERS + UNIVERSAL_PARSERS
    AVAILABLE_FAMILIES = ('dmrst', 'unirst')

    def __init__(
        self,
        model_dir: Optional[str] = None,
        hf_model_name: Optional[str] = 'tchewik/isanlp_rst_v3',
        hf_model_version: Optional[str] = None,
        relinventory: Optional[str] = None,
        relinventory_idx: int = 0,
        device: 'str | torch.device | None' = None,
        cuda_device: 'int | None' = None,
        family: Optional[str] = None,
        dtype: 'str | torch.dtype | None' = None,
    ):
        resolved_family = self._resolve_family(model_dir, hf_model_version, family)

        # When loading from disk, suppress the default HF repo name so the
        # predictor unambiguously selects local mode.
        effective_hf_name = None if model_dir is not None else hf_model_name

        if resolved_family == 'dmrst':
            self.predictor = PredictorDMRST(
                model_dir=model_dir,
                hf_model_name=effective_hf_name,
                hf_model_version=hf_model_version,
                device=device,
                cuda_device=cuda_device,
                dtype=dtype,
            )
        else:  # 'unirst'
            self.predictor = PredictorUniRST(
                model_dir=model_dir,
                hf_model_name=effective_hf_name,
                hf_model_version=hf_model_version,
                relinventory=relinventory,
                relinventory_idx=relinventory_idx,
                device=device,
                cuda_device=cuda_device,
                dtype=dtype,
            )

    @classmethod
    def _resolve_family(
        cls,
        model_dir: Optional[str],
        hf_model_version: Optional[str],
        family: Optional[str],
    ) -> str:
        if family is not None:
            if family not in cls.AVAILABLE_FAMILIES:
                raise ValueError(
                    f"Unknown family {family!r}. Available: {cls.AVAILABLE_FAMILIES}."
                )
            return family

        if hf_model_version is not None:
            if hf_model_version in cls.DMRST_PARSERS:
                return 'dmrst'
            if hf_model_version in cls.UNIVERSAL_PARSERS:
                return 'unirst'
            raise ValueError(
                f"Unknown hf_model_version {hf_model_version!r}. "
                f"Available: {cls.AVAILABLE_VERSIONS}."
            )

        if model_dir is not None:
            detected = cls._detect_family_from_model_dir(model_dir)
            if detected is None:
                raise ValueError(
                    f"Cannot auto-detect parser family from model_dir={model_dir!r}. "
                    f"Pass family='dmrst' or family='unirst' explicitly."
                )
            return detected

        raise ValueError(
            'Pass `hf_model_version` or `model_dir` (with `family` for local-disk loading). '
            f'Available versions: {cls.AVAILABLE_VERSIONS}.'
        )

    @staticmethod
    def _detect_family_from_model_dir(model_dir: str) -> Optional[str]:
        """Inspect a local checkpoint directory and infer the parser family.

        Returns ``'unirst'``, ``'dmrst'``, or ``None`` if no signature matches.
        """
        unirst_pickles = (
            glob(os.path.join(model_dir, 'data_manager_*.pickle'))
            or glob(os.path.join(model_dir, 'data', 'data_manager_*.pickle'))
            or glob(os.path.join(model_dir, 'data', 'dms', 'data_manager_*.pickle'))
        )
        if unirst_pickles:
            return 'unirst'

        cfg = Parser._safe_load_json(os.path.join(model_dir, 'config.json'))
        if cfg is not None and 'corpora' in cfg.get('data', {}):
            return 'unirst'

        if os.path.isfile(os.path.join(model_dir, 'relation_table.txt')):
            return 'dmrst'

        return None

    @staticmethod
    def _safe_load_json(path: str) -> Optional[dict]:
        """Read ``path`` as JSON. Returns ``None`` if the file is missing,
        unreadable, or contains malformed JSON.
        """
        if not os.path.isfile(path):
            return None
        try:
            with open(path, 'r', encoding='utf8') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def __call__(self, text: str):
        return self.predictor.parse_rst(text)

    def from_edus(self, edus: Sequence[str]):
        """Parse a document using predefined EDUs."""
        return self.predictor.parse_from_edus(edus)
