import copy
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

import fire
from tqdm import tqdm

from workbench.archive.legacy_2021.universal_parser.inventory import (
    RestrictedUnpickler,
    dump_relation_inventory,
    ensure_unirst_module_aliases,
    import_relation_table_from_legacy_pickle,
)
from rdam.rst.model_loading.parser_input import ParserInput
from workbench.corpus.unirst.binary_tree import BinaryTree, Node
from workbench.corpus.unirst.data import Rs3Document
from workbench.archive.legacy_2021.universal_parser.src.parser.data import Data
from workbench.archive.legacy_2021.universal_parser.src.parser.data import (
    RelationTableGUM,
    RelationTableRSTDT,
    RelationTableRuRSTB,
)

random.seed(42)


class DataManager:
    def __init__(self, corpus: str, cross_validation: bool = False, nfolds: int = 5) -> None:
        """
        :param corpus: str  - from {'GUM', 'RST-DT', 'RuRSTB', 'RST-DT-tr',}
        :param cross_validation: bool  - whether to split to stratified train/dev/tests randomly
        :param nfolds: int  - [If cross_validation == True] number of splits for cross validation
        """
        assert corpus in ("GUM", "RST-DT", "RuRSTB", "RST-DT-tr", "GUM10-tr", "MAZ-tr")
        self.corpus_name = corpus

        if self.corpus_name == "GUM":
            self._init_gum_corpus(cross_validation, nfolds)

        elif self.corpus_name == "RST-DT":
            self._init_rstdt_corpus(nfolds)

        elif self.corpus_name == "RuRSTB":
            self._init_rurstb_corpus()

        elif self.corpus_name == "RST-DT-tr":
            self._init_rstdt_corpus(nfolds, translated=True)

        elif self.corpus_name == "GUM10-tr":
            self._init_gum_corpus(cross_validation, nfolds, translated=True)

    def _init_gum_corpus(self, cross_validation: bool, nfolds: int, translated: bool = False) -> None:
        if translated:
            self.input_path = Path("data/gum10_tr_rs3")
            self.output_path = Path("data/gum10_tr_prepared")
        else:
            self.input_path = Path("data/gum_rs3")
            self.output_path = Path("data/gum_prepared")

        self.output_path.mkdir(parents=True, exist_ok=True)
        self.cross_validation = cross_validation
        if self.cross_validation:
            self.nfolds = nfolds
            self.folds: dict[int, dict[str, list[str]]] = defaultdict(dict)
            self.mixed_folds_en: dict[int, dict[int, dict[str, list[str]]]] = defaultdict(dict)
            self.mixed_folds_ru: dict[int, dict[int, dict[str, list[str]]]] = defaultdict(dict)
        else:
            self.corpus: dict[str, list[str]] = dict()

            self.mixed_train_en: dict[int, list[list[str]]] = defaultdict(list)
            self.mixed_train_ru: dict[int, list[list[str]]] = defaultdict(list)
            self.mixed_folds = 5
            for i in [25, 50, 75, 100]:
                self.mixed_train_en[i] = []
                self.mixed_train_ru[i] = []

        self.langs = ["en", "ru"]

        self.relation_table = RelationTableGUM
        self.relation_dic = {word.lower(): i for i, word in enumerate(RelationTableGUM)}
        self.relation_fixer = {
            "topic_ns": "contingency_ns",  # One example of this type in GUM v9.1
            "restatement_sn": "restatement_ns",  # 4 examples in GUM_conversation_gossip
        }

    def _init_rstdt_corpus(self, nfolds: int, translated: bool = False) -> None:
        # The corpus is converted to *.rs3 with https://github.com/rst-workbench/rst-converter-service

        if translated:
            self.input_path = Path("data/rstdt_tr_rs3")
            self.output_path = Path("data/rstdt_tr_prepared")
        else:
            self.input_path = Path("data/rstdt_rs3")
            self.output_path = Path("data/rstdt_prepared")

        self.output_path.mkdir(parents=True, exist_ok=True)

        # There is no fixed validation part in RST-DT,
        # so we'll take random parts of training for validation for each "fold"
        self.nfolds = nfolds
        self.folds: dict[int, dict[str, list[str]]] = defaultdict(dict)

        class2rel = {
            "Attribution": ["attribution", "attribution-e", "attribution-n", "attribution-negative"],
            "Background": ["background", "background-e", "circumstance", "circumstance-e"],
            "Cause": [
                "cause",
                "cause-result",
                "result",
                "result-e",
                "consequence",
                "consequence-n-e",
                "consequence-n",
                "consequence-s-e",
                "consequence-s",
            ],
            "Comparison": [
                "comparison",
                "comparison-e",
                "preference",
                "preference-e",
                "analogy",
                "analogy-e",
                "proportion",
            ],
            "Condition": ["condition", "condition-e", "hypothetical", "contingency", "otherwise"],
            "Contrast": ["contrast", "concession", "concession-e", "antithesis", "antithesis-e"],
            "Elaboration": [
                "elaboration-additional",
                "elaboration-additional-e",
                "elaboration-general-specific-e",
                "elaboration-general-specific",
                "elaboration-part-whole",
                "elaboration-part-whole-e",
                "elaboration-process-step",
                "elaboration-process-step-e",
                "elaboration-object-attribute-e",
                "elaboration-object-attribute",
                "elaboration-set-member",
                "elaboration-set-member-e",
                "example",
                "example-e",
                "definition",
                "definition-e",
            ],
            "Enablement": ["purpose", "purpose-e", "enablement", "enablement-e"],
            "Evaluation": [
                "evaluation",
                "evaluation-n",
                "evaluation-s-e",
                "evaluation-s",
                "interpretation-n",
                "interpretation-s-e",
                "interpretation-s",
                "interpretation",
                "conclusion",
                "comment",
                "comment-e",
                "comment-topic",
            ],
            "Explanation": [
                "evidence",
                "evidence-e",
                "explanation-argumentative",
                "explanation-argumentative-e",
                "reason",
                "reason-e",
            ],
            "Joint": ["list", "disjunction"],
            "Manner-Means": ["manner", "manner-e", "means", "means-e"],
            "Topic-Comment": [
                "problem-solution",
                "problem-solution-n",
                "problem-solution-s",
                "question-answer",
                "question-answer-n",
                "question-answer-s",
                "statement-response",
                "statement-response-n",
                "statement-response-s",
                "topic-comment",
                "comment-topic",
                "rhetorical-question",
            ],
            "Summary": ["summary", "summary-n", "summary-s", "restatement", "restatement-e"],
            "Temporal": [
                "temporal-before",
                "temporal-before-e",
                "temporal-after",
                "temporal-after-e",
                "temporal-same-time",
                "temporal-same-time-e",
                "sequence",
                "inverted-sequence",
            ],
            "Topic-Change": ["topic-shift", "topic-drift"],
            "textual-organization": ["textualorganization"],
            "span": ["span"],
            "same-unit": ["same-unit"],
        }
        # rel_status_classes = []
        # for rel in class2rel:
        #     rel_status_classes.append(rel + '_NS')
        #     rel_status_classes.append(rel + '_NN')
        #     rel_status_classes.append(rel + '_SN')

        self.rel2class = {}
        for cl in class2rel:
            self.rel2class[cl.lower()] = cl
            for rel in class2rel[cl]:
                self.rel2class[rel] = cl

        self.relation_table = RelationTableRSTDT
        self.relation_dic = {word.lower(): i for i, word in enumerate(RelationTableRSTDT)}
        self.relation_fixer = dict()

    def _init_rurstb_corpus(self) -> None:
        # The corpus is splitted into separate trees (docname_part*.rs3)
        # "##### " are replaced with <P> tag as in the rst-dt
        # (although it still marks the beginning of a paragraph here, not the ending)
        # Also the corpus converted from rs3 -> isanlp -> rs3 to fix empty spans

        self.input_path = Path("data/rurstb_rs3")
        self.output_path = Path("data/rurstb_prepared")
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.cross_validation = False
        self.corpus: dict[str, list[str]] = {"train": [], "dev": [], "test": []}
        class2rel = {
            "Attribution": ["attribution", "antithesis"],  # Corpus analysis shows often mislabeling
            "Background": ["background"],
            "Cause-effect": ["cause", "effect", "cause-effect"],
            "Comparison": ["comparison"],
            "Concession": ["concession"],
            "Condition": ["condition", "motivation"],
            "Contrast": ["contrast"],
            "Elaboration": ["elaboration"],
            "Preparation": ["preparation"],
            "Purpose": ["purpose"],
            "Interpretation-evaluation": ["evaluation", "interpretation", "interpretation-evaluation"],
            "Evidence": ["evidence"],
            "Joint": ["joint"],
            "Solutionhood": ["solutionhood"],
            "Restatement": ["restatement", "conclusion"],
            "Sequence": ["sequence"],
            "span": ["span"],
            "same-unit": ["same-unit"],
        }

        self.rel2class = {}
        for cl in class2rel:
            self.rel2class[cl.lower()] = cl
            for rel in class2rel[cl]:
                self.rel2class[rel] = cl

        self.relation_table = RelationTableRuRSTB
        self.relation_dic = {word.lower(): i for i, word in enumerate(RelationTableRuRSTB)}
        self.relation_fixer = {
            "restatement_sn": "condition_sn",
            "restatement_ns": "elaboration_ns",
            "solutionhood_ns": "solutionhood_sn",
            "preparation_ns": "elaboration_ns",
            "elaboration_sn": "preparation_sn",
            "background_ns": "elaboration_ns",
        }

    def from_rs3(self) -> None:
        # Collect all *.edus, *.lisp in the same directory
        self.prepare_lisp_format()

        # Collect JSON parser-input files for each document
        self.prepare_parser_format()

        if self.corpus_name in ("GUM", "GUM10-tr"):
            if self.cross_validation:
                # Prepare documents listings for each fold and split, including mixed variants.
                # Populate self.folds = {1: {'train': [...], 'dev': [...], 'test': [...]}, 2: ...}
                self.construct_folds()
                # Populate self.mixed_folds_en = {25: {1: ...}, 50: {1: ...}, 75: {1: ...}}, and self.mixed_folds_ru

                if self.corpus_name == "GUM":
                    self._mixed_folds(25)
                    self._mixed_folds(50)
                    self._mixed_folds(75)
                    self._mixed_folds(100)
            else:
                self.construct_corpus()
                if self.corpus_name == "GUM":
                    self._mixed_train(25)
                    self._mixed_train(50)
                    self._mixed_train(75)
                    self._mixed_train(100)

        elif self.corpus_name in ["RST-DT", "RuRSTB", "RST-DT-tr"]:
            self.construct_corpus()

    def from_pickle(self, filename: str | Path) -> list[str]:
        """One-way import of a published HF pickle → relation labels only."""
        return import_relation_table_from_legacy_pickle(Path(filename))

    def save(self, filename: str | Path) -> None:
        path = Path(filename)
        if path.suffix in {".pickle", ".pkl"}:
            path = path.with_suffix(".json")
        dump_relation_inventory(path, list(self.relation_table), corpus_name=self.corpus_name)

    def _load_prepared_doc(self, docname: str) -> ParserInput | None:
        json_path = self.output_path / f"{docname}.json"
        if json_path.is_file():
            return ParserInput.from_json(json_path)
        pkl_path = self.output_path / f"{docname}.pkl"
        if not pkl_path.is_file():
            return None
        ensure_unirst_module_aliases()
        with pkl_path.open("rb") as handle:
            loaded = RestrictedUnpickler(handle).load()
        if isinstance(loaded, ParserInput):
            return loaded
        return None

    def prepare_lisp_format(self) -> None:
        if self.corpus_name == "GUM":
            for lang in self.langs:
                for rs3_file in (self.input_path / lang).glob("*.rs3"):
                    self.convert_doc(
                        filename=rs3_file.name, input_dir=self.input_path / lang, output_dir=self.output_path
                    )

        elif self.corpus_name == "GUM10-tr":
            for rs3_file in self.input_path.glob("*.rs3"):
                self.convert_doc(filename=rs3_file.name, input_dir=self.input_path, output_dir=self.output_path)

        elif self.corpus_name == "RST-DT":
            for part in ("TRAINING", "TEST"):
                for rs3_file in sorted((self.input_path / part).glob("*.rs3")):
                    self.convert_doc(
                        filename=rs3_file.name, input_dir=self.input_path / part, output_dir=self.output_path
                    )

        elif self.corpus_name == "RST-DT-tr":
            for rs3_file in sorted(self.input_path.glob("*.rs3")):
                try:
                    self.convert_doc(filename=rs3_file.name, input_dir=self.input_path, output_dir=self.output_path)
                except OSError, ValueError, KeyError, AttributeError, TypeError:
                    print(f"Failed to convert {rs3_file}")

        elif self.corpus_name == "RuRSTB":
            for rs3_file in sorted(self.input_path.glob("*.rs3")):
                try:
                    self.convert_doc(filename=rs3_file.name, input_dir=self.input_path, output_dir=self.output_path)
                except OSError, ValueError, KeyError, AttributeError, TypeError:
                    print(rs3_file)
                    raise

    def prepare_parser_format(self) -> None:
        files = list(self.output_path.glob("*.edus"))
        for edu_path in tqdm(files, desc="Reading *.lisp files"):
            lisp_path = edu_path.with_suffix(".lisp")
            try:
                parser_input = self.generate_input(lisp_path, edu_path, edu_path)
            except OSError, ValueError, KeyError, AttributeError, TypeError:
                print("Exception is evoked by:", edu_path)
                raise
            parser_input.write_json(edu_path.with_suffix(".json"))

    def get_fold(self, number: int, lang: str = "en", mixed: int = 0) -> tuple[Data, Data, Data]:
        """
        :param number: int  - fold number
        :param lang: str  - (main) language
        :param mixed: int  - percentage for other part mixing
        :return: tuple(src.parser.data.Data)  - train, dev, test:
        """
        if self.corpus_name == "GUM":
            if mixed == 0:
                fold = copy.deepcopy(self.folds[number])
                if lang == "ru":
                    for key in ["train", "dev", "test"]:
                        fold[key] = [docname + "_RU" for docname in fold[key]]
            else:
                if lang == "en":
                    fold = copy.deepcopy(self.mixed_folds_en[mixed][number])
                elif lang == "ru":
                    fold = copy.deepcopy(self.mixed_folds_ru[mixed][number])
                else:
                    raise KeyError("No such language in the current data manager.")

        elif self.corpus_name in ("RST-DT", "RST-DT-tr", "GUM10-tr"):
            fold = copy.deepcopy(self.folds[number])
        else:
            raise KeyError(self.corpus_name)

        result: dict[str, Data] = {}
        for key in ("train", "dev", "test"):
            docs = []
            for docname in fold[key]:
                loaded = self._load_prepared_doc(docname)
                if loaded is None:
                    print("No such file in the corpus:", docname)
                    continue
                docs.append(loaded)

            input_sentences = [doc.sentences for doc in docs]
            edu_breaks = [doc.edu_breaks for doc in docs]
            decoder_input = [doc.decoder_inputs for doc in docs]
            relation_label = [doc.relation for doc in docs]
            parsing_breaks = [doc.parsing_index for doc in docs]
            golden_metric = [" ".join(doc.label_for_metrics_list) for doc in docs]
            parents_index = [doc.parents for doc in docs]
            sibling = [doc.siblings for doc in docs]
            result[key] = Data(
                input_sentences,
                edu_breaks,
                decoder_input,
                relation_label,
                parsing_breaks,
                golden_metric,
                parents_index,
                sibling,
            )

        return result["train"], result["dev"], result["test"]

    def get_data(self, lang: str = "en", mixed: int = 0, mixed_fold: int = 0) -> tuple[Data, Data, Data]:
        """
        :param lang: str  - (main) language
        :param mixed: int  - percentage for other part mixing
        :return: tuple(src.parser.data.Data)  - train, dev, test:
        """
        corpus = copy.deepcopy(self.corpus)
        if self.corpus_name == "GUM":
            if lang == "ru":
                for key in ["train", "dev", "test"]:
                    corpus[key] = [docname + "_RU" for docname in corpus[key]]

            if mixed:
                if lang == "en":
                    corpus["train"] = copy.deepcopy(self.mixed_train_en[mixed][mixed_fold])
                elif lang == "ru":
                    corpus["train"] = copy.deepcopy(self.mixed_train_ru[mixed][mixed_fold])
                else:
                    raise KeyError("No such language in the current data manager.")

        result: dict[str, Data] = {}
        for key in ("train", "dev", "test"):
            docs = []
            for docname in corpus[key]:
                loaded = self._load_prepared_doc(docname)
                if loaded is None:
                    print("No such file in the corpus:", self.output_path / f"{docname}.json")
                    continue
                docs.append(loaded)

            input_sentences = [doc.sentences for doc in docs]
            edu_breaks = [doc.edu_breaks for doc in docs]
            decoder_input = [doc.decoder_inputs for doc in docs]
            relation_label = [doc.relation for doc in docs]
            parsing_breaks = [doc.parsing_index for doc in docs]
            golden_metric = [" ".join(doc.label_for_metrics_list) for doc in docs]
            parents_index = [doc.parents for doc in docs]
            sibling = [doc.siblings for doc in docs]
            result[key] = Data(
                input_sentences,
                edu_breaks,
                decoder_input,
                relation_label,
                parsing_breaks,
                golden_metric,
                parents_index,
                sibling,
            )

        return result["train"], result["dev"], result["test"]

    def construct_corpus(self) -> None:
        if self.corpus_name == "GUM":
            for part in ("train", "dev", "test"):
                listing = Path("data") / "gum_file_lists" / f"files.{part}"
                self.corpus[part] = listing.read_text(encoding="utf-8").splitlines()

        elif self.corpus_name == "GUM10-tr":
            self.corpus["train"] = [path.stem for path in self.input_path.glob("*.rs3")]
            self.corpus["dev"] = []
            self.corpus["test"] = []

        elif self.corpus_name == "RST-DT":
            test_files = [path.stem for path in (self.input_path / "TEST").glob("*.rs3")]
            all_train_files = [path.stem for path in (self.input_path / "TRAINING").glob("*.rs3")]

            for fold in range(self.nfolds):
                train_n = int(len(all_train_files) * 0.9)
                train_files = random.sample(all_train_files, train_n)
                dev_files = [file for file in all_train_files if file not in train_files]

                self.folds[fold]["train"] = train_files
                self.folds[fold]["dev"] = dev_files
                self.folds[fold]["test"] = test_files

        elif self.corpus_name == "RST-DT-tr":
            all_train_files = [path.stem for path in self.input_path.glob("*.rs3")]

            for fold in range(self.nfolds):
                self.folds[fold]["train"] = all_train_files
                self.folds[fold]["dev"] = []
                self.folds[fold]["test"] = []

        elif self.corpus_name == "RuRSTB":
            seen: set[str] = set()
            prepared = sorted(self.output_path.glob("*.json")) + sorted(self.output_path.glob("*.pkl"))
            for path in prepared:
                clear_filename = path.stem
                if clear_filename in seen:
                    continue
                seen.add(clear_filename)
                part = clear_filename.split(".")[0]
                self.corpus[part].append(clear_filename)

    def _collect_mixed_train(self, train_data: list[str], genres: list[str], n: int, another_lang: str) -> list[str]:
        mixed_train = train_data[:]
        for genre in genres:
            g_train = [filename for filename in train_data if filename.startswith(f"GUM_{genre}")]

            if another_lang == "ru":
                length_of_replacements = int(len(g_train) * n / 100)
                another_lang_sample = random.sample(list(range(len(g_train))), length_of_replacements)
                for ind in another_lang_sample:
                    mixed_train.append(g_train[ind] + "_RU")

            else:
                length_of_replacements = int(len(g_train) * (100 - n) / 100)
                ru_sample_ind = random.sample(list(range(len(g_train))), length_of_replacements)
                for ind in ru_sample_ind:
                    mixed_train.append(g_train[ind] + "_RU")

        return mixed_train

    def _mixed_train(self, n: int) -> None:
        """Makes self.mixed_train_* versions with 100% train files from first language and n% from the second."""

        if self.corpus_name == "GUM":
            genres = [
                "academic",
                "bio",
                "conversation",
                "fiction",
                "interview",
                "news",
                "reddit",
                "speech",
                "textbook",
                "vlog",
                "voyage",
                "whow",
            ]

        elif self.corpus_name == "RuRSTB":
            genres = ["news", "blogs"]
        else:
            raise KeyError(self.corpus_name)

        # Base English, mixing Russian #############
        for _ in range(self.mixed_folds):
            self.mixed_train_en[n].append(
                self._collect_mixed_train(self.corpus["train"], genres, n=n, another_lang="ru")
            )

        # mixed_train = train[:]
        # for genre in genres:
        #     g_train = [filename for filename in train if filename.startswith(f'GUM_{genre}')]
        #     length_of_replacements = int(len(g_train) * n / 100)
        #     ru_sample_ind = random.sample(list(range(len(g_train))), length_of_replacements)
        #     for ind in ru_sample_ind:
        #         mixed_train.append(g_train[ind] + '_RU')
        #
        # self.mixed_train_en[n] = mixed_train

        # Base Russian, mixing English #############
        # train = self.corpus['train'][:]
        # mixed_train = train[:]
        # for genre in genres:
        #     g_train = [filename for filename in train if filename.startswith(f'GUM_{genre}')]

        # Base English, mixing Russian #############
        for _ in range(self.mixed_folds):
            self.mixed_train_ru[n].append(
                self._collect_mixed_train(self.corpus["train"], genres, n=n, another_lang="en")
            )

    def generate_input(
        self,
        lisp_path: str | Path,
        text_path: str | Path,
        edus_path: str | Path,
        is_depth_manner: bool = True,
    ) -> ParserInput:
        tree = BinaryTree(lisp_path, text_path, edus_path)
        edus_list = [edu.split() for edu in Path(edus_path).read_text(encoding="utf-8").splitlines()]
        return self.find_document_span(tree.root, edus_list, is_depth_manner, tree.sentence_span)

    def find_document_span(
        self,
        node: Node,
        edus_list: list[list[str]],
        is_depth_manner: bool,
        sentence_span_dic: dict[str, Any],
    ) -> ParserInput:
        parser_input = self.parse_sentence(node, edus_list, is_depth_manner)
        parser_input.sentence_span = self.get_sentence_span_list(sentence_span_dic)
        return parser_input

    @staticmethod
    def get_sentence_span_list(sentence_span_dic: dict[str, Any]) -> list[list[int]]:
        sentence_list = []
        for key in sentence_span_dic:
            tem_str = key.replace("[", "").replace("]", "")
            tokens = tem_str.split(",")
            left = int(tokens[0])
            right = int(tokens[1])
            sentence_list.append([left, right])
        return sentence_list

    def parse_sentence(
        self, root_node: Node, edus_list: list[list[str]], is_depth_manner: bool, coarse: bool = True
    ) -> ParserInput:
        def get_depth_manner_node_list(root):
            node_list = []
            stack = []
            stack.append(root)
            while len(stack) > 0:
                node = stack.pop()
                node_list.append(node)
                if node.right is not None:
                    stack.append(node.right)
                if node.left is not None:
                    stack.append(node.left)
            return node_list

        def get_width_manner_node_list(root):
            node_list = []
            queue = []
            if root is not None:
                queue.append(root)
            while len(queue) != 0:
                node = queue.pop(0)
                node_list.append(node)
                if node.left is not None:
                    queue.append(node.left)
                if node.right is not None:
                    queue.append(node.right)
            return node_list

        root_node.parent = None
        parser_input = ParserInput()
        if is_depth_manner:
            node_list = get_depth_manner_node_list(root_node)
        else:
            node_list = get_width_manner_node_list(root_node)

        sentences_list = []

        assert root_node.span is not None
        edu_start = root_node.span[0]
        for node in node_list:
            if node.edu_id is not None:
                sentences_list.append([node.edu_id, edus_list[node.edu_id - 1]])
            else:
                assert node.left is not None and node.right is not None
                assert node.left.span is not None and node.right.span is not None
                assert node.span is not None
                assert node.relation is not None
                parser_input.parsing_index.append(node.left.span[1] - edu_start)
                parser_input.decoder_inputs.append(node.span[0] - edu_start)

                parent_index = node.parent.span[1] - edu_start if node.parent is not None else 0
                parser_input.parents.append(parent_index)

                if node.parent is None:
                    sibling_index = 99
                else:
                    if node == node.parent.left:
                        sibling_index = 99
                    else:
                        sibling_index = node.parent.left.span[1] - edu_start

                parser_input.siblings.append(sibling_index)

                #   LabelforMetric:
                left_child_span = node.left.span
                right_child_span = node.right.span
                nuclearity = node.relation[:2]
                relation = node.relation[3:]

                # Label to Class
                if self.corpus_name in ("GUM", "GUM10-tr"):
                    if coarse and relation != "same-unit":
                        relation = relation.split("-")[0]
                elif self.corpus_name in ["RST-DT", "RuRSTB", "RST-DT-tr"]:
                    mapped_relation = self.rel2class.get(relation.lower())
                    assert mapped_relation is not None
                    relation = mapped_relation

                #   Relation:
                lookup_relation = (relation + "_" + nuclearity).lower()
                if lookup_relation in self.relation_fixer:
                    lookup_relation = self.relation_fixer[lookup_relation]
                    relation, nuclearity = lookup_relation.split("_")
                    nuclearity = nuclearity.upper()
                    if relation != "same-unit":
                        relation = relation[0].upper() + relation[1:]

                parser_input.relation.append(self.relation_dic[lookup_relation])
                left_nuclearity = "Nucleus" if nuclearity[0] == "N" else "Satellite"
                right_nuclearity = "Nucleus" if nuclearity[1] == "N" else "Satellite"
                if nuclearity == "NS" or nuclearity == "SN":
                    if nuclearity == "NS":
                        left_relation = "span"
                        right_relation = relation
                    else:
                        left_relation = relation
                        right_relation = "span"
                else:
                    left_relation = relation
                    right_relation = relation
                label_string = (
                    "("
                    + str(left_child_span[0] - edu_start + 1)
                    + ":"
                    + left_nuclearity
                    + "="
                    + left_relation
                    + ":"
                    + str(left_child_span[1] - edu_start + 1)
                    + ","
                    + str(right_child_span[0] - edu_start + 1)
                    + ":"
                    + right_nuclearity
                    + "="
                    + right_relation
                    + ":"
                    + str(right_child_span[1] - edu_start + 1)
                    + ")"
                )
                parser_input.label_for_metrics_list.append(label_string)

        parser_input.LabelforMetric = [" ".join(parser_input.label_for_metrics_list)]
        Sentences_list = sorted(sentences_list, key=lambda x: x[0])

        for i in range(len(Sentences_list)):
            parser_input.sentences += Sentences_list[i][1]
            parser_input.edu_breaks.append(len(parser_input.sentences) - 1)

        return parser_input

    def convert_doc(self, filename: str, input_dir: str | Path, output_dir: str | Path) -> None:
        """Take all rs3 documents and save them in the same directory
        as *.edus and *.lisp files ready for processing."""
        rs3 = Rs3Document(Path(input_dir) / filename)
        rs3.read()
        rs3.writeEdu(output_dir)
        out_ext = ".lisp"
        rs3.writeTree(output_dir, out_ext)

    def construct_folds(self) -> None:
        """Scatter examples on folds divided into train/val/test.
        Preserve subclasses distribution in each fold and split."""

        documents = defaultdict(list)
        for edu_file in self.output_path.glob("*.edus"):
            name = edu_file.stem
            doc_lang = "ru" if "_RU" in name else "en"
            name = name[:-3] if "_RU" in name else name
            documents[doc_lang].append(name)

        all_docs = documents["en"]
        docs_by_class = defaultdict(list)
        for doc_name in all_docs:
            cls = doc_name.split("_")[1]
            docs_by_class[cls].append(doc_name)

        for i in range(self.nfolds):
            fold_docs = {}
            for cls, doc_names in docs_by_class.items():
                fold_cls_docs = doc_names[:]
                random.shuffle(fold_cls_docs)
                fold_docs[cls] = fold_cls_docs

            train_docs = []
            val_docs = []
            test_docs = []

            train_props = {c: int(len(fold_docs[c]) * 0.7) for c in docs_by_class}
            val_props = {c: int(len(fold_docs[c]) * 0.15) for c in docs_by_class}
            remaining = copy.deepcopy(fold_docs)

            for c in docs_by_class:
                train_docs.extend(random.sample(remaining[c], train_props[c]))
                remaining[c] = [d for d in remaining[c] if d not in train_docs]
                val_docs.extend(random.sample(remaining[c], val_props[c]))
                remaining[c] = [d for d in remaining[c] if d not in val_docs]
                test_docs.extend(remaining[c])

            self.folds[i] = {"train": train_docs, "dev": val_docs, "test": test_docs}

    def _mixed_folds(self, n: int) -> None:
        """Populates a self.mixed_folds_en{25: ..., 75: ..., 100: ...} dictionary
        with n% train files from first language and 100-n% from the second."""

        mixed_folds_en: dict[int, dict[str, list[str]]] = defaultdict(dict)
        mixed_folds_ru: dict[int, dict[str, list[str]]] = defaultdict(dict)
        for fold_num, fold in self.folds.items():
            # Base English, mixing Russian #############
            mixed_folds_en[fold_num]["dev"] = fold["dev"][:]
            mixed_folds_en[fold_num]["test"] = fold["test"][:]

            length_of_replacements = int(len(fold["train"]) * n / 100)
            ru_sample_ind = random.sample(list(range(len(fold["train"]))), length_of_replacements)
            train = fold["train"][:]
            for ind in ru_sample_ind:
                train[ind] += "_RU"

            mixed_folds_en[fold_num]["train"] = train

            # Base Russian, mixing English #############
            mixed_folds_ru[fold_num]["dev"] = fold["dev"][:]
            mixed_folds_ru[fold_num]["test"] = fold["test"][:]
            for ind in range(len(fold["dev"])):
                mixed_folds_ru[fold_num]["dev"][ind] += "_RU"

            length_of_replacements = int(len(fold["train"]) * (100 - n) / 100)
            ru_sample_ind = random.sample(list(range(len(fold["train"]))), length_of_replacements)
            train = fold["train"][:]
            for ind in ru_sample_ind:
                train[ind] += "_RU"

            mixed_folds_ru[fold_num]["train"] = train

        self.mixed_folds_en[n] = mixed_folds_en
        self.mixed_folds_ru[n] = mixed_folds_ru


def collect(corpus: str = "GUM", output_path: str = "data/data_manager.json") -> None:
    dp = DataManager(corpus=corpus)
    dp.from_rs3()
    dp.save(output_path)


if __name__ == "__main__":
    fire.Fire(collect)
