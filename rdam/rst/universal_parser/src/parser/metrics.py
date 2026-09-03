import re
from rdam.rst._metric_kernel import (
    MetricTriple,
    is_no_tree,
    macro_metrics,
    metric_triple,
    micro_metrics,
)

type SpanLabelMap = dict[str, list[str]]


def _strip_entropy(span: str) -> str:
    return re.sub(r";entropy=[^:]+", "", span)


def get_eval_data_rst_parseval(sen: str, edus: list[int]) -> SpanLabelMap:
    b = re.findall(r"\d+", sen)
    b = [str(edus[int(i) - 1]) for i in b]
    cur_new: list[str] = []
    x = 0
    while x < len(b):
        cur_new.append(b[x] + "-" + b[x + 1])
        x = x + 2
    span = sen.split(r" ")
    # print(span)
    dic: SpanLabelMap = {}
    for i in range(len(span)):
        temp = _strip_entropy(span[i])
        IDK = re.split(r"[:,=]", temp)
        Nuclearity1 = IDK[1]
        relation1 = IDK[2]
        Nuclearity2 = IDK[5]
        relation2 = IDK[6]
        dic[cur_new[2 * i]] = [relation1, Nuclearity1]
        dic[cur_new[2 * i + 1]] = [relation2, Nuclearity2]
    return dic


def get_eval_data_parseval(tree_spans: str, edus: list[int]) -> SpanLabelMap:
    span_list = tree_spans.strip().split()
    dic: SpanLabelMap = {}
    for i in range(len(span_list)):
        temp = _strip_entropy(span_list[i])
        IDK = re.split(r"[:,=]", temp)
        try:
            nuclearity = IDK[1][0] + IDK[5][0]
        except (IndexError, TypeError) as error:
            raise ValueError(f"invalid Parseval span at position {i}: {temp!r}") from error
        relation1 = IDK[2]
        relation2 = IDK[6]
        relation = relation1 if relation1 != "span" else relation2
        start = str(edus[int(IDK[0].strip("(")) - 1])
        end = str(edus[int(IDK[-1].strip(")")) - 1])
        span = start + "-" + end
        dic[span] = [relation, nuclearity]
    return dic


def get_measurement(
    tree1_spans: str,
    tree2_spans: str,
    tree1_edus: list[int],
    tree2_edus: list[int],
    use_org_parseval: bool,
) -> tuple[int, int, int, int, int, int]:
    if use_org_parseval:
        dic1 = get_eval_data_parseval(tree1_spans, tree1_edus)
        dic2 = get_eval_data_parseval(tree2_spans, tree2_edus)
    else:
        dic1 = get_eval_data_rst_parseval(tree1_spans, tree1_edus)
        dic2 = get_eval_data_rst_parseval(tree2_spans, tree2_edus)

    n_ns = 0
    n_relation = 0
    n_full = 0

    # number of right spans
    right_span = list(dic1.keys() & dic2.keys())
    n_spans = len(right_span)

    # Right Number of relations and nuclearity
    for span in right_span:
        if dic1[span][0] == dic2[span][0]:
            n_relation = n_relation + 1
        if dic1[span][1] == dic2[span][1]:
            n_ns = n_ns + 1
        if dic1[span][0] == dic2[span][0] and dic1[span][1] == dic2[span][1]:
            n_full += 1

    correct_span = n_spans
    correct_relation = n_relation
    correct_nuclearity = n_ns
    correct_full = n_full
    no_system = len(dic1.keys())
    no_golden = len(dic2.keys())

    return correct_span, correct_relation, correct_nuclearity, correct_full, no_system, no_golden


def get_seg_measure(pred_seg: list[int], gold_seg: list[int]) -> tuple[int, int, int]:
    num_gold = len(gold_seg)
    num_pred = len(pred_seg)
    correct = len(set(pred_seg) & set(gold_seg))

    return num_gold, num_pred, correct


def get_batch_metrics(
    pred_spans_batch: list[list[str]],
    gold_spans_batch: list[str],
    pred_edu_breaks_batch: list[list[int]],
    gold_edu_breaks_batch: list[list[int]],
    use_org_parseval: bool,
) -> tuple[
    int, int, int, int, int, int, list[int], list[int], list[int], list[int], list[int], list[int], tuple[int, int, int]
]:
    correct_span = 0
    correct_relation = 0
    correct_nuclearity = 0
    correct_full = 0
    n_system = 0
    n_golden = 0
    n_gold_seg = 0
    n_pred_seg = 0
    n_correct_seg = 0

    correct_span_batch_list: list[int] = []
    correct_relation_batch_list: list[int] = []
    correct_nuclearity_batch_list: list[int] = []
    correct_full_batch_list: list[int] = []
    no_system_batch_list: list[int] = []
    no_golden_batch_list: list[int] = []

    for i in range(len(pred_spans_batch)):
        # Lowercasing in case the casing is different in the relation table
        cur_pred_spans = pred_spans_batch[i][0].lower()
        cur_gold_spans = gold_spans_batch[i].lower()

        cur_pred_edus = pred_edu_breaks_batch[i]
        cur_gold_edus = gold_edu_breaks_batch[i]

        cur_span_n = 0
        cur_relation_n = 0
        cur_ns_n = 0
        cur_sys_n = 0
        cur_golden_n = 0
        cur_full = 0

        num_gold_seg, num_pred_seg, num_correct_seg = get_seg_measure(cur_pred_edus, cur_gold_edus)
        n_gold_seg += num_gold_seg
        n_pred_seg += num_pred_seg
        n_correct_seg += num_correct_seg

        if not is_no_tree(cur_pred_spans) and not is_no_tree(cur_gold_spans):
            cur_span_n, cur_relation_n, cur_ns_n, cur_full, cur_sys_n, cur_golden_n = get_measurement(
                cur_pred_spans, cur_gold_spans, cur_pred_edus, cur_gold_edus, use_org_parseval
            )

            correct_span += cur_span_n
            correct_relation += cur_relation_n
            correct_nuclearity += cur_ns_n
            correct_full += cur_full
            n_system += cur_sys_n
            n_golden += cur_golden_n

        elif not is_no_tree(cur_pred_spans) and is_no_tree(cur_gold_spans):
            _, _, _, _, cur_sys_n, _ = get_measurement(
                cur_pred_spans, cur_pred_spans, cur_pred_edus, cur_pred_edus, use_org_parseval
            )
            n_system += cur_sys_n

        elif is_no_tree(cur_pred_spans) and not is_no_tree(cur_gold_spans):
            _, _, _, _, _, cur_golden_n = get_measurement(
                cur_gold_spans, cur_gold_spans, cur_gold_edus, cur_gold_edus, use_org_parseval
            )
            n_golden += cur_golden_n

        correct_span_batch_list.append(cur_span_n)
        correct_relation_batch_list.append(cur_relation_n)
        correct_nuclearity_batch_list.append(cur_ns_n)
        correct_full_batch_list.append(cur_full)
        no_system_batch_list.append(cur_sys_n)
        no_golden_batch_list.append(cur_golden_n)

    return (
        correct_span,
        correct_relation,
        correct_nuclearity,
        correct_full,
        n_system,
        n_golden,
        correct_span_batch_list,
        correct_relation_batch_list,
        correct_nuclearity_batch_list,
        correct_full_batch_list,
        no_system_batch_list,
        no_golden_batch_list,
        (n_gold_seg, n_pred_seg, n_correct_seg),
    )


def get_micro_metrics(
    correct_span: float,
    correct_relation: float,
    correct_nuclearity: float,
    correct_full: float,
    n_sys: float,
    n_gold: float,
    n_gold_seg: float,
    n_pred_seg: float,
    n_correct_seg: float,
) -> tuple[MetricTriple, MetricTriple, MetricTriple, float, MetricTriple]:
    return micro_metrics(
        correct_span,
        correct_relation,
        correct_nuclearity,
        correct_full,
        n_sys,
        n_gold,
        n_gold_seg,
        n_pred_seg,
        n_correct_seg,
    )


def calc_metrics(n_correct: float, n_pred: float, n_gold: float) -> MetricTriple:
    return metric_triple(n_correct, n_pred, n_gold)


def get_macro_metrics(
    correct_span_list: list[float],
    correct_nuclearity_list: list[float],
    correct_relation_list: list[float],
    correct_full_list: list[float],
    no_system_list: list[float],
    no_golden_list: list[float],
) -> tuple[MetricTriple, MetricTriple, MetricTriple, MetricTriple]:
    return macro_metrics(
        correct_span_list,
        correct_nuclearity_list,
        correct_relation_list,
        correct_full_list,
        no_system_list,
        no_golden_list,
    )
