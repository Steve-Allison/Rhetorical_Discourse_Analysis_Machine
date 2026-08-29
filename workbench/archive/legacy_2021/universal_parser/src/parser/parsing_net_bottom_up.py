from typing import Any, override

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor

from .parsing_net import ParsingNet
from .data import nucs_and_rels


class ParsingNetBottomUp(ParsingNet):
    """Bottom-up transition-based parser.

    This module reuses the encoder, segmenters and relation classifiers from
    :class:`ParsingNet` but replaces the top-down pointer-network parser with a
    simple bottom-up shift-reduce style parser. The implementation follows the
    transition system described in `Yu et al., 2020` (CoDI; ACL 2020).
    """

    def __init__(self, *args: Any, pair_hidden_size: int = 256, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Remove top-down specific modules
        del self.decoder
        del self.pointer

        # Classifier that scores SHIFT vs REDUCE decisions.
        self.action_scorer = nn.Sequential(
            nn.Linear(self.hidden_size * 3, pair_hidden_size, bias=True, device=self._cuda_device),
            nn.ReLU(),
            nn.Linear(pair_hidden_size, 2, bias=True, device=self._cuda_device),
        )

    class _Node:
        def __init__(
            self,
            start: int,
            end: int,
            split: int | None,
            label: int | None,
            left: ParsingNetBottomUp._Node | None = None,
            right: ParsingNetBottomUp._Node | None = None,
        ) -> None:
            self.start = start
            self.end = end
            self.split = split
            self.label = label
            self.left = left
            self.right = right

    def _build_tree(
        self,
        parsing_index: list[int],
        label_index: list[int],
        edu_number: int,
        start: int = 0,
        end: int | None = None,
        idx: int = 0,
    ) -> tuple[ParsingNetBottomUp._Node, int]:
        """Reconstructs the gold tree from pre-order traversal."""
        if end is None:
            end = edu_number - 1
        if start == end:
            return self._Node(start, end, None, None), idx

        split = parsing_index[idx]
        label = label_index[idx]
        idx += 1
        left, idx = self._build_tree(parsing_index, label_index, edu_number, start=start, end=split, idx=idx)
        right, idx = self._build_tree(parsing_index, label_index, edu_number, start=split + 1, end=end, idx=idx)
        return self._Node(start, end, split, label, left, right), idx

    def _postorder(self, node: ParsingNetBottomUp._Node) -> list[ParsingNetBottomUp._Node]:
        if node.left is None:
            if node.right is not None:
                raise ValueError("bottom-up parser tree contains a right-only node")
            return []
        if node.right is None:
            raise ValueError("bottom-up parser tree contains a left-only node")
        ops = []
        ops.extend(self._postorder(node.left))
        ops.extend(self._postorder(node.right))
        ops.append(node)
        return ops

    def _actions(self, node: ParsingNetBottomUp._Node) -> list[tuple[str, int | None]]:
        """Return gold transition sequence in postorder."""
        if node.left is None:
            if node.right is not None:
                raise ValueError("bottom-up parser tree contains a right-only node")
            return [("SHIFT", None)]
        if node.right is None:
            raise ValueError("bottom-up parser tree contains a left-only node")
        actions = []
        actions.extend(self._actions(node.left))
        actions.extend(self._actions(node.right))
        actions.append(("REDUCE", node.label))
        return actions

    def _span_embedding(self, encodings: Tensor, start: int, end: int) -> Tensor:
        return torch.mean(encodings[start : end + 1], dim=0, keepdim=True)

    @override
    def training_loss(
        self,
        input_texts: list[Any],
        sent_breaks: list[Any] | None,
        entity_ids: list[Any] | None,
        entity_position_ids: list[Any] | None,
        edu_breaks: list[list[int]],
        label_index: list[list[int]],
        parsing_index: list[list[int]],
        decoder_input_index: list[list[int]],
        dataset_index: list[int],
    ) -> tuple[Tensor, Tensor, Tensor]:
        encoder_outputs, _, total_edu_loss, _, _ = self.encoder(
            input_texts,
            entity_ids,
            entity_position_ids,
            edu_breaks,
            sent_breaks=sent_breaks,
            dataset_index=dataset_index,
        )

        if self.label_weights is None:
            raise RuntimeError("bottom-up UniRST training requires classifier label weights")
        label_loss_functions = [nn.NLLLoss(weight=w) for w in self.label_weights]
        struct_loss_fn = nn.NLLLoss()

        loss_label_batch = torch.zeros(1, device=self._cuda_device)
        loss_struct_batch = torch.zeros(1, device=self._cuda_device)
        count_label = 0
        count_struct = 0

        batch_size = len(label_index)
        zero = torch.zeros(1, self.hidden_size, device=self._cuda_device)
        for i in range(batch_size):
            n_edus = len(edu_breaks[i])
            if n_edus == 1:
                continue
            cur_enc = encoder_outputs[i][:n_edus]
            tree, _ = self._build_tree(parsing_index[i], label_index[i], n_edus)
            actions = self._actions(tree)

            stack = []
            buffer = [(j, j, self._span_embedding(cur_enc, j, j)) for j in range(n_edus)]

            for act, lbl in actions:
                top1 = stack[-1][2] if len(stack) >= 1 else zero
                top2 = stack[-2][2] if len(stack) >= 2 else zero
                next_buf = buffer[0][2] if buffer else zero
                feat = torch.cat([top2, top1, next_buf], dim=-1)
                log_probs = F.log_softmax(self.action_scorer(feat), dim=-1)
                gold = torch.tensor([0 if act == "SHIFT" else 1], device=self._cuda_device)
                loss_struct_batch += struct_loss_fn(log_probs, gold)
                count_struct += 1

                if act == "SHIFT":
                    stack.append(buffer.pop(0))
                else:  # REDUCE
                    right = stack.pop()
                    left = stack.pop()
                    input_left = left[2]
                    input_right = right[2]
                    cls_idx = self.dataset2classifier[dataset_index[i]]
                    if self.dataset_masks is not None:
                        mask = self.dataset_masks[cls_idx]
                        _, log_rel_weights = self.label_classifier(input_left, input_right, mask=mask)
                    else:
                        _, log_rel_weights = self.label_classifiers[cls_idx](input_left, input_right)
                    loss_label_batch += label_loss_functions[cls_idx](
                        log_rel_weights, torch.tensor([lbl], device=self._cuda_device)
                    )
                    count_label += 1
                    new_emb = (input_left + input_right) / 2
                    new_span = (left[0], right[1], new_emb)
                    stack.append(new_span)

        loss_label_batch /= max(1, count_label)
        loss_struct_batch /= max(1, count_struct)

        return loss_struct_batch, loss_label_batch, total_edu_loss

    @override
    def testing_loss(
        self,
        input_sentence: list[Any],
        input_sent_breaks: list[Any] | None,
        input_entity_ids: list[Any] | None,
        input_entity_position_ids: list[Any] | None,
        input_edu_breaks: list[list[int]],
        label_index: list[list[int]],
        parsing_index: list[list[int]],
        generate_tree: bool,
        use_pred_segmentation: bool,
        dataset_index: list[int],
    ) -> tuple[float, float, list[list[str]], tuple[list[int], list[int]], list[list[int]]]:
        encoder_outputs, _, _, predicted_edu_breaks, _ = self.encoder(
            input_sentence,
            input_entity_ids,
            input_entity_position_ids,
            input_edu_breaks,
            sent_breaks=input_sent_breaks,
            is_test=use_pred_segmentation,
            dataset_index=dataset_index,
        )

        span_batch = []
        label_batch = []
        tree_batch = []

        effective_edu_breaks = predicted_edu_breaks if use_pred_segmentation else input_edu_breaks
        batch_size = len(effective_edu_breaks)
        zero = torch.zeros(1, self.hidden_size, device=self._cuda_device)
        for i in range(batch_size):
            n_edus = len(effective_edu_breaks[i])
            if n_edus == 1:
                tree_batch.append([])
                label_batch.append([])
                span_batch.append([])
                continue

            cur_enc = encoder_outputs[i][:n_edus]
            stack = []
            buffer = [(j, j, self._span_embedding(cur_enc, j, j)) for j in range(n_edus)]

            cur_tree = []
            cur_labels = []
            cur_span_str = ""

            while buffer or len(stack) > 1:
                top1 = stack[-1][2] if len(stack) >= 1 else zero
                top2 = stack[-2][2] if len(stack) >= 2 else zero
                next_buf = buffer[0][2] if buffer else zero
                feat = torch.cat([top2, top1, next_buf], dim=-1)
                action_scores = self.action_scorer(feat)
                act = int(torch.argmax(action_scores))  # 0=SHIFT, 1=REDUCE

                if act == 0 and buffer:
                    stack.append(buffer.pop(0))
                else:
                    if len(stack) < 2:
                        # force shift if not enough items
                        if buffer:
                            stack.append(buffer.pop(0))
                            continue
                        else:
                            break
                    right = stack.pop()
                    left = stack.pop()
                    input_left = left[2]
                    input_right = right[2]
                    cls_idx = self.dataset2classifier[dataset_index[i]]
                    if self.dataset_masks is not None:
                        mask = self.dataset_masks[cls_idx]
                        relation_weights, _ = self.label_classifier(input_left, input_right, mask=mask)
                    else:
                        relation_weights, _ = self.label_classifiers[cls_idx](input_left, input_right)
                    label_idx = int(torch.argmax(relation_weights))
                    cur_labels.append(label_idx)
                    cur_tree.append(left[1])

                    if generate_tree:
                        relation_inventory = self.relation_vocab if self.dataset_masks is not None else self.relation_tables[cls_idx]
                        nuc_l, nuc_r, rel_l, rel_r = nucs_and_rels(label_idx, relation_inventory)
                        span_s = f"({left[0] + 1}:{nuc_l}={rel_l}:{left[1] + 1},{right[0] + 1}:{nuc_r}={rel_r}:{right[1] + 1})"
                        cur_span_str += " " + span_s

                    new_emb = (input_left + input_right) / 2
                    new_span = (left[0], right[1], new_emb)
                    stack.append(new_span)

            tree_batch.append(cur_tree)
            label_batch.append(cur_labels)
            span_batch.append([cur_span_str.strip()])

        merged_label_gold = []
        for tmp_i in label_index:
            merged_label_gold.extend(tmp_i)
        merged_label_pred = []
        for tmp_i in label_batch:
            merged_label_pred.extend(tmp_i)

        loss_tree = 0.0
        loss_label = 0.0

        return loss_tree, loss_label, span_batch, (merged_label_gold, merged_label_pred), effective_edu_breaks
