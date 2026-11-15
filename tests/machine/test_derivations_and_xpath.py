"""2-wave DAG derivations into Dung AF and unified DocLang dclq XPath alignment tests."""

import json
from pathlib import Path

from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
import pytest

from rdam import (
    AggregateAnalysis,
    AggregateRequest,
    DerivationSpec,
    Machine,
    ResultOutcome,
    SourceIdentity,
    StructuredInput,
    Technique,
    UnavailableOutcome,
    UnavailableReason,
    select_analysis,
)
from rdam._strict import JsonValue
from rdam.argument_mining import ArgumentMiningProvider
from rdam.aspic import AspicProvider
from rdam.centering import CenteringProvider
from rdam.classical_rhetoric import ClassicalRhetoricProvider
from rdam.cli import main as cli_main
from rdam.dung import DungProvider
from rdam.ibis import IbisProvider
from rdam.serialization import load
from rdam.toulmin import ToulminProvider
from rdam.walton import WaltonProvider

MODEL = "openai:gpt-5.6-sol"


@pytest.fixture(autouse=True)
def never_a_real_request():
    previous = models.ALLOW_MODEL_REQUESTS
    models.ALLOW_MODEL_REQUESTS = False
    yield
    models.ALLOW_MODEL_REQUESTS = previous


def _noop_dotenv(*_args: object, **_kwargs: object) -> None:
    return None


@pytest.fixture
def with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")


class TestTwoWaveDagDerivations:
    def test_from_ibis_derives_dung_extensions_and_records_intra_aggregate_lineage(self) -> None:
        ibis_payload = {
            "nodes": [
                {"id": "i1", "kind": "issue", "text": "Which database should we adopt?"},
                {"id": "p_pg", "kind": "position", "text": "Adopt Postgres."},
                {"id": "p_mysql", "kind": "position", "text": "Adopt MySQL."},
                {"id": "a_pro_pg", "kind": "argument", "text": "Postgres supports transactional DDL."},
                {"id": "a_con_mysql", "kind": "argument", "text": "MySQL DDL commits implicitly."},
            ],
            "links": [
                {"from": "p_pg", "relation": "responds_to", "to": "i1"},
                {"from": "p_mysql", "relation": "responds_to", "to": "i1"},
                {"from": "a_pro_pg", "relation": "supports", "to": "p_pg"},
                {"from": "a_con_mysql", "relation": "objects_to", "to": "p_mysql"},
            ],
        }
        request = AggregateRequest(
            source=SourceIdentity.from_bytes(b"ibis-dag", media_type="application/json"),
            text=None,
            techniques=(Technique.IBIS, Technique.DUNG),
            structured_inputs=(StructuredInput(technique=Technique.IBIS, payload=ibis_payload),),
            derivations=(
                DerivationSpec(consumer=Technique.DUNG, compiler="from_ibis", upstreams=(Technique.IBIS,)),
            ),
        )
        aggregate = Machine([IbisProvider(model=MODEL), DungProvider()]).analyse(request)
        ibis_out = aggregate.outcome_for(Technique.IBIS)
        dung_out = aggregate.outcome_for(Technique.DUNG)
        assert isinstance(ibis_out, ResultOutcome)
        assert isinstance(dung_out, ResultOutcome)
        assert dung_out.result.payload["input_origin"] == "explicitly_derived"
        semantics = dung_out.result.payload["extensions"]
        assert isinstance(semantics, dict)
        grounded = semantics["grounded"]
        assert isinstance(grounded, list)
        assert "p_pg" in grounded
        assert "p_mysql" not in grounded
        assert len(aggregate.lineage) == 1
        assert aggregate.lineage[0].consumer_technique is Technique.DUNG
        assert aggregate.lineage[0].upstream_technique is Technique.IBIS
        assert aggregate.lineage[0].upstream_result_identity == ibis_out.result.semantic_digest

    def test_from_aspic_derives_dung_extensions(self) -> None:
        aspic_payload = {
            "axioms": ["rain"],
            "ordinary_premises": ["forecast_dry"],
            "strict_rules": [],
            "defeasible_rules": [
                {"id": "d1", "antecedents": ["rain"], "consequent": "wet"},
                {"id": "d2", "antecedents": ["forecast_dry"], "consequent": "~wet"},
            ],
            "contraries": [],
            "premise_preferences": [],
            "rule_preferences": [["d2", "d1"]],
            "ordering_principle": "last_link",
            "set_comparison": "elitist",
        }
        request = AggregateRequest(
            source=SourceIdentity.from_bytes(b"aspic-dag", media_type="application/json"),
            text=None,
            techniques=(Technique.ASPIC, Technique.DUNG),
            structured_inputs=(StructuredInput(technique=Technique.ASPIC, payload=aspic_payload),),
            derivations=(
                DerivationSpec(consumer=Technique.DUNG, compiler="from_aspic", upstreams=(Technique.ASPIC,)),
            ),
        )
        aggregate = Machine([AspicProvider(model=MODEL), DungProvider()]).analyse(request)
        dung_out = aggregate.outcome_for(Technique.DUNG)
        assert isinstance(dung_out, ResultOutcome)
        assert len(aggregate.lineage) == 1
        assert aggregate.lineage[0].upstream_technique is Technique.ASPIC

    def test_from_argument_mining_and_from_toulmin_walton_compile_into_dung(
        self,
        with_credentials: None,
    ) -> None:
        source_text = (
            "Deploy the patch tonight because CVE-2026-991 is actively exploited, "
            "unless the canary region error budget trips. Dr. Patel, Chief Security Architect, "
            "confirms active exploitation; however, have staging telemetry checks completed?"
        )
        iat_raw = {
            "adu_nodes": [
                {
                    "id": "adu_claim",
                    "role": "major_claim",
                    "proposition": "Deploy the patch tonight",
                    "speaker": "author",
                    "evidence": {"quote": "Deploy the patch tonight", "occurrence": 1},
                },
                {
                    "id": "adu_exc",
                    "role": "premise",
                    "proposition": "Canary region error budget trips",
                    "speaker": "author",
                    "evidence": {"quote": "unless the canary region error budget trips.", "occurrence": 1},
                },
            ],
            "relations": [
                {"id": "ca_1", "relation_type": "conflict", "source_id": "adu_exc", "target_id": "adu_claim"},
            ],
            "enthymemes": [],
        }
        iat_provider = ArgumentMiningProvider(model=MODEL)
        with iat_provider.analyst.agent.override(
            model=FunctionModel(
                lambda _m, info: ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=iat_raw)])
            )
        ):
            agg_iat = Machine([iat_provider, DungProvider()]).analyse(
                AggregateRequest.for_text(
                    source_text,
                    (Technique.ARGUMENT_MINING, Technique.DUNG),
                    derivations=(
                        DerivationSpec(
                            consumer=Technique.DUNG,
                            compiler="from_argument_mining",
                            upstreams=(Technique.ARGUMENT_MINING,),
                        ),
                    ),
                )
            )
        dung_iat = agg_iat.outcome_for(Technique.DUNG)
        assert isinstance(dung_iat, ResultOutcome)
        iat_sem = dung_iat.result.payload["extensions"]
        assert isinstance(iat_sem, dict)
        assert iat_sem["grounded"] == ["adu_exc"]

        c_quote = "Deploy the patch tonight"
        g_quote = "CVE-2026-991 is actively exploited"
        r_quote = "unless the canary region error budget trips."
        e_quote = "Dr. Patel, Chief Security Architect, confirms active exploitation"
        cq_quote = "have staging telemetry checks completed?"

        toulmin_raw = {
            "layouts": [
                {
                    "claim": c_quote,
                    "grounds": [g_quote],
                    "warrant": "Actively exploited CVEs warrant immediate patching.",
                    "warrant_origin": "reconstructed",
                    "warrant_evidence": [
                        {
                            "start": source_text.index(g_quote),
                            "end": source_text.index(g_quote) + len(g_quote),
                            "text": g_quote,
                        }
                    ],
                    "warrant_origin_reason": None,
                    "backing": [],
                    "qualifier": None,
                    "rebuttals": [
                        {
                            "condition": "Canary region error budget trips.",
                            "source_text": r_quote,
                        }
                    ],
                }
            ]
        }
        walton_raw: dict[str, JsonValue] = {
            "instances": [
                {
                    "scheme_id": "expert_opinion",
                    "conclusion": c_quote,
                    "premises": {
                        "source": "Dr. Patel, Chief Security Architect",
                        "domain": "Security architecture and active vulnerability exploitation",
                        "assertion": e_quote,
                    },
                    "critical_questions": [
                        {
                            "index": 0,
                            "status": "addressed",
                            "note": "Identifies Dr. Patel as Chief Security Architect.",
                            "evidence": [
                                {
                                    "start": source_text.index(e_quote),
                                    "end": source_text.index(e_quote) + len(e_quote),
                                    "text": e_quote,
                                }
                            ],
                            "reason": None,
                        },
                        {"index": 1, "status": "open", "note": None, "evidence": [], "reason": None},
                        {"index": 2, "status": "open", "note": None, "evidence": [], "reason": None},
                        {"index": 3, "status": "open", "note": None, "evidence": [], "reason": None},
                        {"index": 4, "status": "open", "note": None, "evidence": [], "reason": None},
                        {
                            "index": 5,
                            "status": "addressed",
                            "note": "Raises whether staging telemetry checks completed.",
                            "evidence": [
                                {
                                    "start": source_text.index(cq_quote),
                                    "end": source_text.index(cq_quote) + len(cq_quote),
                                    "text": cq_quote,
                                }
                            ],
                            "reason": None,
                        },
                    ],
                }
            ]
        }
        t_prov = ToulminProvider(model=MODEL)
        w_prov = WaltonProvider(model=MODEL)
        with (
            t_prov.analyst.agent.override(
                model=FunctionModel(
                    lambda _m, info: ModelResponse(
                        parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=toulmin_raw)]
                    )
                )
            ),
            w_prov.analyst.agent.override(
                model=FunctionModel(
                    lambda _m, info: ModelResponse(
                        parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=walton_raw)]
                    )
                )
            ),
        ):
            agg_tw = Machine([t_prov, w_prov, DungProvider()]).analyse(
                AggregateRequest.for_text(
                    source_text,
                    (Technique.TOULMIN, Technique.WALTON, Technique.DUNG),
                    derivations=(
                        DerivationSpec(
                            consumer=Technique.DUNG,
                            compiler="from_toulmin_walton",
                            upstreams=(Technique.TOULMIN, Technique.WALTON),
                        ),
                    ),
                )
            )
        dung_tw = agg_tw.outcome_for(Technique.DUNG)
        assert isinstance(dung_tw, ResultOutcome)
        assert {ref.upstream_technique for ref in agg_tw.lineage} == {Technique.TOULMIN, Technique.WALTON}

    def test_missing_upstream_outcome_leaves_dung_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setattr("rdam._llm.load_dotenv", _noop_dotenv)
        monkeypatch.setattr("rdam._llm._nearest_dotenv", _noop_dotenv)
        agg = Machine([IbisProvider(model=MODEL), DungProvider()]).analyse(
            AggregateRequest.for_text(
                "Should we ship?",
                (Technique.IBIS, Technique.DUNG),
                derivations=(
                    DerivationSpec(consumer=Technique.DUNG, compiler="from_ibis", upstreams=(Technique.IBIS,)),
                ),
            )
        )
        assert isinstance(agg.outcome_for(Technique.IBIS), UnavailableOutcome)
        dung_out = agg.outcome_for(Technique.DUNG)
        assert isinstance(dung_out, UnavailableOutcome)
        assert dung_out.reason is UnavailableReason.MISSING_STRUCTURED_INPUT
        assert agg.lineage == ()

    def test_cli_derive_flag_runs_two_wave_ibis_to_dung_end_to_end(self, tmp_path: Path) -> None:
        ibis_file = tmp_path / "ibis.json"
        out_file = tmp_path / "out.json"
        ibis_file.write_text(
            json.dumps(
                {
                    "nodes": [
                        {"id": "i1", "kind": "issue", "text": "Adopt Ed25519?"},
                        {"id": "p1", "kind": "position", "text": "Yes."},
                        {"id": "a1", "kind": "argument", "text": "Deterministic signatures."},
                    ],
                    "links": [
                        {"from": "p1", "relation": "responds_to", "to": "i1"},
                        {"from": "a1", "relation": "supports", "to": "p1"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        code = cli_main(
            [
                "analyse",
                "--techniques",
                "ibis,dung",
                "--structured",
                f"ibis={ibis_file}",
                "--derive",
                "from_ibis",
                "-o",
                str(out_file),
            ]
        )
        assert code == 0
        loaded = load(out_file.read_bytes())
        assert isinstance(loaded, AggregateAnalysis)
        assert len(loaded.lineage) == 1


class TestUnifiedXPathAlignmentAndViews:
    def test_multi_technique_xpath_alignment_and_view_filtering(
        self,
        tmp_path: Path,
        with_credentials: None,
    ) -> None:
        doc = tmp_path / "unified.dclg"
        doc.write_text(
            '<doclang version="0.9">'
            "<text>Postgres prevents partial schema corruption during deploys.</text>"
            "<table><ched/>Engine<ched/>DDL Safety<nl/><fcel/>Postgres<fcel/>Transactional rollback<nl/></table>"
            '<picture><label value="chart"/><description>Bar chart showing zero partial DDL failures '
            "under Postgres across 500 migrations.</description></picture>"
            "</doclang>",
            encoding="utf-8",
        )
        cr_proposal = {
            "appeals": [
                {
                    "appeal_id": "ap_1",
                    "pistis": "logos",
                    "sub_mode": "data_evidence",
                    "rationale": "Empirical chart evidence across 500 migrations.",
                    "evidence": {
                        "quote": "Bar chart showing zero partial DDL failures under Postgres across 500 migrations.",
                        "occurrence": 1,
                    },
                }
            ],
            "kairos_cues": [],
            "stasis": {"dominant_stasis": "none", "contested_question": None, "evidence": None},
            "figures": [],
        }
        cr_provider = ClassicalRhetoricProvider(model=MODEL)
        with cr_provider.analyst.agent.override(
            model=FunctionModel(
                lambda _m, info: ModelResponse(
                    parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=cr_proposal)]
                )
            )
        ):
            aggregate = Machine([CenteringProvider(), cr_provider]).analyse(
                AggregateRequest.for_source(
                    doc,
                    (Technique.CENTERING, Technique.CLASSICAL_RHETORIC),
                )
            )
        pic_entry = next(
            entry for entry in aggregate.xpath_alignment if entry.xpath == "/d:doclang/d:picture[1]/d:description[1]"
        )
        assert {occ.technique for occ in pic_entry.occurrences} == {
            Technique.CENTERING,
            Technique.CLASSICAL_RHETORIC,
        }

        view = select_analysis(aggregate, techniques=(Technique.CLASSICAL_RHETORIC,))
        assert view.xpath_alignment
        for entry in view.xpath_alignment:
            assert {occ.technique for occ in entry.occurrences} == {Technique.CLASSICAL_RHETORIC}
