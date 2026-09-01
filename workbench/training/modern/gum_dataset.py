"""GUM v12.1.0 Discourse Treebank Extractor, Token Aligner & Target Matrix Generator.

Provides exact recursive parsing of .dis binary LISP trees, subword token offset
alignment against ModernBERT fast tokenizers, and dense binary constituent /
categorical nuclearity / categorical relation supervision matrices.
"""

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Final

import torch
from transformers import PreTrainedTokenizerBase

logger = logging.getLogger(__name__)

# Canonical 15 coarse relation taxonomy
COARSE_RELATIONS: Final[tuple[str, ...]] = (
    "adversative",
    "attribution",
    "causal",
    "context",
    "contingency",
    "elaboration",
    "evaluation",
    "explanation",
    "joint",
    "mode",
    "organization",
    "purpose",
    "restatement",
    "same-unit",
    "topic",
)

RELATION_TO_IDX: Final[dict[str, int]] = {rel: idx for idx, rel in enumerate(COARSE_RELATIONS)}

# Explicit 32 raw GUM fine-grained rel2par -> coarse relation mapping
RAW_TO_COARSE_RELATION: Final[dict[str, str]] = {
    # Adversative
    "adversative-antithesis": "adversative",
    "adversative-concession": "adversative",
    "adversative-contrast": "adversative",
    # Attribution
    "attribution-positive": "attribution",
    "attribution-negative": "attribution",
    # Causal
    "causal-cause": "causal",
    "causal-result": "causal",
    # Context
    "context-background": "context",
    "context-circumstance": "context",
    # Contingency
    "contingency-condition": "contingency",
    # Elaboration
    "elaboration-additional": "elaboration",
    "elaboration-attribute": "elaboration",
    "elaboration-part-whole": "elaboration",
    # Evaluation
    "evaluation-comment": "evaluation",
    # Explanation
    "explanation-evidence": "explanation",
    "explanation-justify": "explanation",
    "explanation-motivation": "explanation",
    # Joint
    "joint-list": "joint",
    "joint-other": "joint",
    "joint-sequence": "joint",
    "joint-disjunction": "joint",
    # Mode
    "mode-manner": "mode",
    "mode-means": "mode",
    # Organization
    "organization-heading": "organization",
    "organization-phatic": "organization",
    "organization-preparation": "organization",
    # Purpose
    "purpose-goal": "purpose",
    "purpose-attribute": "purpose",
    # Restatement
    "restatement-partial": "restatement",
    "restatement-repetition": "restatement",
    # Same-unit
    "same-unit": "same-unit",
    # Topic
    "topic-question": "topic",
    "topic-solutionhood": "topic",
}

# Nuclearity pattern classes
NUCLEARITY_CLASSES: Final[tuple[str, ...]] = ("NS", "SN", "NN")
NUCLEARITY_TO_IDX: Final[dict[str, int]] = {nuc: idx for idx, nuc in enumerate(NUCLEARITY_CLASSES)}


@dataclass(slots=True)
class GUMDisNode:
    """Represents a node in the binary LISP RST tree."""

    node_type: str  # "Root", "Nucleus", "Satellite"
    edu_start: int  # 1-indexed inclusive
    edu_end: int  # 1-indexed inclusive
    rel2par: str  # e.g., "span", "elaboration-additional", etc.
    text: str | None = None  # Populated for leaf nodes
    children: tuple["GUMDisNode", ...] = ()

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0


@dataclass(slots=True, frozen=True)
class ParsedGUMDocument:
    """A fully parsed and token-aligned GUM discourse document."""

    doc_id: str
    split: str  # "train", "dev", "test", "test2"
    edu_texts: tuple[str, ...]
    tree: GUMDisNode
    input_ids: torch.Tensor  # Shape: (1, seq_len)
    attention_mask: torch.Tensor  # Shape: (1, seq_len)
    edu_starts: torch.Tensor  # Shape: (1, num_edus) - token start indices
    edu_ends: torch.Tensor  # Shape: (1, num_edus) - token end indices
    gold_splits: torch.Tensor  # Shape: (1, num_edus, num_edus) - Binary constituent indicator
    gold_nucs: torch.Tensor  # Shape: (1, num_edus, num_edus) - Categorical nuclearity indices
    gold_rels: torch.Tensor  # Shape: (1, num_edus, num_edus) - Categorical relation indices


def _tokenize_lisp(content: str) -> list[str]:
    """Tokenize LISP S-expression while preserving _!..._! text spans."""
    tokens: list[str] = []
    i = 0
    n = len(content)
    while i < n:
        char = content[i]
        if char.isspace():
            i += 1
            continue
        if char in "()":
            tokens.append(char)
            i += 1
            continue
        if content[i : i + 2] == "_!":
            # Text span
            end = content.find("_!", i + 2)
            if end == -1:
                raise ValueError(f"Unclosed text span at position {i}")
            tokens.append(content[i : end + 2])
            i = end + 2
            continue
        # Regular token
        start = i
        while i < n and not content[i].isspace() and content[i] not in "()":
            i += 1
        tokens.append(content[start:i])
    return tokens


def parse_dis_tree(dis_text: str) -> GUMDisNode:
    """Parse a .dis LISP S-expression into a GUMDisNode tree hierarchy."""
    tokens = _tokenize_lisp(dis_text)
    if not tokens:
        raise ValueError("Empty .dis content")

    pos = 0

    def parse_node() -> GUMDisNode:
        nonlocal pos
        if pos >= len(tokens) or tokens[pos] != "(":
            raise ValueError(f"Expected '(' at token position {pos}, got {tokens[pos] if pos < len(tokens) else 'EOF'}")
        pos += 1  # consume '('

        node_type = tokens[pos]
        pos += 1

        edu_start = 0
        edu_end = 0
        rel2par = "span"
        text = None
        children: list[GUMDisNode] = []

        while pos < len(tokens) and tokens[pos] != ")":
            tok = tokens[pos]
            if tok == "(":
                # Child attribute or child node
                pos += 1
                attr_name = tokens[pos]
                pos += 1
                if attr_name == "span":
                    edu_start = int(tokens[pos])
                    edu_end = int(tokens[pos + 1])
                    pos += 2
                    if tokens[pos] != ")":
                        raise ValueError(f"Expected ')' closing span at {pos}")
                    pos += 1
                elif attr_name == "leaf":
                    leaf_id = int(tokens[pos])
                    edu_start = leaf_id
                    edu_end = leaf_id
                    pos += 1
                    if tokens[pos] != ")":
                        raise ValueError(f"Expected ')' closing leaf at {pos}")
                    pos += 1
                elif attr_name == "rel2par":
                    rel2par = tokens[pos]
                    pos += 1
                    if tokens[pos] != ")":
                        raise ValueError(f"Expected ')' closing rel2par at {pos}")
                    pos += 1
                elif attr_name == "text":
                    raw_text = tokens[pos]
                    pos += 1
                    if raw_text.startswith("_!") and raw_text.endswith("_!"):
                        text = raw_text[2:-2].strip()
                    else:
                        text = raw_text.strip()
                    if tokens[pos] != ")":
                        raise ValueError(f"Expected ')' closing text at {pos}")
                    pos += 1
                elif attr_name in ("Nucleus", "Satellite", "Root"):
                    # Rewind pos to opening '(' for full child node parse
                    pos -= 2
                    children.append(parse_node())
                else:
                    raise ValueError(f"Unexpected attribute '{attr_name}' in node {node_type}")
            else:
                raise ValueError(f"Unexpected token '{tok}' inside node {node_type} at {pos}")

        if pos >= len(tokens) or tokens[pos] != ")":
            raise ValueError(f"Expected ')' closing node {node_type} at {pos}")
        pos += 1  # consume ')'

        return GUMDisNode(
            node_type=node_type,
            edu_start=edu_start,
            edu_end=edu_end,
            rel2par=rel2par,
            text=text,
            children=tuple(children),
        )

    root = parse_node()
    return root


def extract_edus_from_tree(tree: GUMDisNode) -> list[str]:
    """Extract leaf EDU texts in 1-indexed order."""
    edus: list[tuple[int, str]] = []

    def walk(node: GUMDisNode) -> None:
        if node.is_leaf:
            if node.text is not None:
                edus.append((node.edu_start, node.text))
        else:
            for child in node.children:
                walk(child)

    walk(tree)
    edus.sort(key=lambda x: x[0])
    return [text for _, text in edus]


def map_nuclearity(left: GUMDisNode, right: GUMDisNode) -> str:
    """Map left and right child node types to canonical nuclearity (NS, SN, NN)."""
    left_nuc = left.node_type == "Nucleus"
    right_nuc = right.node_type == "Nucleus"

    if left_nuc and not right_nuc:
        return "NS"
    elif not left_nuc and right_nuc:
        return "SN"
    elif left_nuc and right_nuc:
        return "NN"
    else:
        # Satellite-Satellite rare edge case defaults to NN
        return "NN"


def map_relation(node: GUMDisNode) -> str:
    """Map fine-grained rel2par on a constituent branch to coarse relation."""
    # Look for the dependent satellite or non-span relation
    for child in node.children:
        if child.rel2par and child.rel2par != "span":
            raw = child.rel2par.strip().lower()
            if raw in RAW_TO_COARSE_RELATION:
                return RAW_TO_COARSE_RELATION[raw]
            # Handle possible prefix/suffix variations
            for k, v in RAW_TO_COARSE_RELATION.items():
                if raw.startswith(k) or k in raw:
                    return v

    # If all children are span or unmapped, check node's own rel2par
    if node.rel2par and node.rel2par != "span":
        raw = node.rel2par.strip().lower()
        if raw in RAW_TO_COARSE_RELATION:
            return RAW_TO_COARSE_RELATION[raw]

    # Default fallback for unannotated span relations
    return "elaboration"


def build_target_matrices(tree: GUMDisNode, num_edus: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Construct (gold_splits, gold_nucs, gold_rels) target matrices from the gold tree.

    Returns:
        gold_splits: (1, num_edus, num_edus) float32 binary constituent indicator
        gold_nucs: (1, num_edus, num_edus) int64 categorical nuclearity class (0=NS, 1=SN, 2=NN, -100=masked)
        gold_rels: (1, num_edus, num_edus) int64 categorical relation class (0..14, -100=masked)
    """
    gold_splits = torch.zeros((1, num_edus, num_edus), dtype=torch.float32)
    gold_nucs = torch.full((1, num_edus, num_edus), -100, dtype=torch.long)
    gold_rels = torch.full((1, num_edus, num_edus), -100, dtype=torch.long)

    def populate(node: GUMDisNode) -> None:
        # 0-indexed inclusive span [i, j]
        i = node.edu_start - 1
        j = node.edu_end - 1
        if 0 <= i < num_edus and 0 <= j < num_edus and i <= j:
            gold_splits[0, i, j] = 1.0

            if not node.is_leaf and len(node.children) >= 2:
                left = node.children[0]
                right = node.children[1]
                nuc_str = map_nuclearity(left, right)
                rel_str = map_relation(node)

                nuc_idx = NUCLEARITY_TO_IDX.get(nuc_str, 0)
                rel_idx = RELATION_TO_IDX.get(rel_str, 0)

                gold_nucs[0, i, j] = nuc_idx
                gold_rels[0, i, j] = rel_idx

        for child in node.children:
            populate(child)

    populate(tree)
    return gold_splits, gold_nucs, gold_rels


def align_edus_with_tokenizer(
    edu_texts: list[str],
    tokenizer: PreTrainedTokenizerBase,
    max_seq_len: int = 8192,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Tokenize document text and compute exact token start/end offsets for each EDU.

    Returns:
        input_ids: (1, seq_len)
        attention_mask: (1, seq_len)
        edu_starts: (1, num_edus)
        edu_ends: (1, num_edus)
    """
    if not hasattr(tokenizer, "is_fast") or not tokenizer.is_fast:
        raise ValueError("ModernBERT subword alignment requires a fast HuggingFace tokenizer with offset mapping")

    full_text = " ".join(edu_texts)
    encoding = tokenizer(
        full_text,
        max_length=max_seq_len,
        truncation=False,
        return_offsets_mapping=True,
        return_tensors="pt",
    )

    input_ids = encoding["input_ids"]
    attention_mask = encoding["attention_mask"]
    offsets = encoding["offset_mapping"][0].tolist()  # list of (char_start, char_end)

    edu_starts: list[int] = []
    edu_ends: list[int] = []

    current_char = 0
    for _edu_idx, edu in enumerate(edu_texts):
        # Locate exact character start/end in full_text
        char_start = full_text.find(edu, current_char)
        if char_start == -1:
            char_start = current_char
        char_end = char_start + len(edu)
        current_char = char_end

        # Map character bounds to token indices
        tok_start: int | None = None
        tok_end: int | None = None

        for tok_idx, (t_start, t_end) in enumerate(offsets):
            if t_start == 0 and t_end == 0 and tok_idx > 0 and tok_idx == len(offsets) - 1:
                # Special end token (e.g., [SEP] or </s>)
                continue
            if tok_start is None and t_end > char_start:
                tok_start = tok_idx
            if t_start < char_end:
                tok_end = tok_idx

        if tok_start is None:
            tok_start = 0 if not edu_starts else edu_ends[-1] + 1
        if tok_end is None or tok_end < tok_start:
            tok_end = tok_start

        # Cap within sequence length
        tok_start = min(tok_start, input_ids.shape[1] - 1)
        tok_end = min(tok_end, input_ids.shape[1] - 1)

        edu_starts.append(tok_start)
        edu_ends.append(tok_end)

    return (
        input_ids,
        attention_mask,
        torch.tensor([edu_starts], dtype=torch.long),
        torch.tensor([edu_ends], dtype=torch.long),
    )


def load_gum_splits(splits_path: Path) -> dict[str, list[str]]:
    """Parse splits.md and return mapping from split name to list of doc IDs."""
    if not splits_path.is_file():
        raise FileNotFoundError(f"Splits file not found: {splits_path}")

    splits: dict[str, list[str]] = {"train": [], "dev": [], "test": [], "test2": []}
    current_split: str | None = None

    for line in splits_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## "):
            section = line[3:].strip().lower()
            if section in splits:
                current_split = section
            else:
                current_split = None
        elif line.startswith("* ") and current_split is not None:
            doc_name = line[2:].strip()
            if doc_name:
                splits[current_split].append(doc_name)

    return splits


class GUMTreebankDataset:
    """Authority dataset loader for GUM v12.1.0 RST treebanks."""

    def __init__(
        self,
        corpus_dir: Path,
        splits_file: Path,
        tokenizer: PreTrainedTokenizerBase,
        max_seq_len: int = 8192,
    ) -> None:
        self.corpus_dir = corpus_dir
        self.splits_file = splits_file
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len

        self.splits_map = load_gum_splits(splits_file)
        self.documents_by_split: dict[str, list[ParsedGUMDocument]] = {
            "train": [],
            "dev": [],
            "test": [],
            "test2": [],
        }
        self._load_and_parse_all()

    def _load_and_parse_all(self) -> None:
        dis_dir = self.corpus_dir / "rst" / "lisp_binary"
        if not dis_dir.is_dir():
            raise FileNotFoundError(f"LISP binary tree directory not found: {dis_dir}")

        total_loaded = 0
        for split_name, doc_ids in self.splits_map.items():
            for doc_id in doc_ids:
                dis_path = dis_dir / f"{doc_id}.dis"
                if not dis_path.is_file():
                    raise FileNotFoundError(f"Expected .dis tree not found: {dis_path}")

                tree = parse_dis_tree(dis_path.read_text(encoding="utf-8"))
                edu_texts = tuple(extract_edus_from_tree(tree))
                if len(edu_texts) < 2:
                    logger.warning(f"Document {doc_id} has < 2 EDUs ({len(edu_texts)}), skipping.")
                    continue

                input_ids, att_mask, edu_starts, edu_ends = align_edus_with_tokenizer(
                    list(edu_texts),
                    self.tokenizer,
                    max_seq_len=self.max_seq_len,
                )

                gold_splits, gold_nucs, gold_rels = build_target_matrices(tree, len(edu_texts))

                doc = ParsedGUMDocument(
                    doc_id=doc_id,
                    split=split_name,
                    edu_texts=edu_texts,
                    tree=tree,
                    input_ids=input_ids,
                    attention_mask=att_mask,
                    edu_starts=edu_starts,
                    edu_ends=edu_ends,
                    gold_splits=gold_splits,
                    gold_nucs=gold_nucs,
                    gold_rels=gold_rels,
                )
                self.documents_by_split[split_name].append(doc)
                total_loaded += 1

        logger.info(
            f"Loaded {total_loaded} GUM documents across splits: "
            f"train={len(self.documents_by_split['train'])}, "
            f"dev={len(self.documents_by_split['dev'])}, "
            f"test={len(self.documents_by_split['test'])}, "
            f"test2={len(self.documents_by_split['test2'])}"
        )
