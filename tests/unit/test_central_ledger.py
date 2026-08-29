from pathlib import Path

from workbench.experiments.central_ledger import CentralExperimentLedger, ExperimentRecord


def test_central_ledger_create_and_record(tmp_path: Path) -> None:
    experiments_root = tmp_path / "experiments"
    ledger_path = experiments_root / "central_ledger.jsonl"
    ledger = CentralExperimentLedger(experiments_root=experiments_root, ledger_path=ledger_path)

    # 1. Create run session
    run_id, run_dir = ledger.create_run_session(experiment_type="training", model_id="answerdotai/ModernBERT-base")
    assert run_dir.exists()
    assert "ModernBERT_base" in run_id

    # Create dummy artifact in run_dir
    dummy_artifact = run_dir / "weights.pt"
    dummy_artifact.write_bytes(b"dummy_weights_content")

    # 2. Record run
    record = ledger.record_run(
        run_id=run_id,
        run_dir=run_dir,
        model_id="answerdotai/ModernBERT-base",
        model_revision="8949b909",
        experiment_type="training",
        dataset_name="GUM-12.1.0",
        dataset_digest="blake3_abc123",
        hyperparameters={"epochs": 5, "lr": 1e-4},
        eval_metrics={"full_f1": 0.685, "span_f1": 0.892},
        checkpoint_digest="chk_xyz789",
        tags=["test_tag"],
        notes="Unit test run.",
    )

    assert isinstance(record, ExperimentRecord)
    assert (run_dir / "run_receipt.json").exists()
    assert ledger_path.exists()

    # 3. Verify append-only ledger contents
    runs = ledger.list_runs()
    assert len(runs) == 1
    assert runs[0].run_id == run_id
    assert runs[0].eval_metrics["full_f1"] == 0.685
    assert len(runs[0].artifact_paths) > 0


def test_central_ledger_multiple_runs(tmp_path: Path) -> None:
    experiments_root = tmp_path / "experiments"
    ledger_path = experiments_root / "central_ledger.jsonl"
    ledger = CentralExperimentLedger(experiments_root=experiments_root, ledger_path=ledger_path)

    # Record 3 separate runs
    for i in range(3):
        run_id, run_dir = ledger.create_run_session(experiment_type="evaluation", model_id="model_v1")
        ledger.record_run(
            run_id=run_id,
            run_dir=run_dir,
            model_id="model_v1",
            model_revision="rev1",
            experiment_type="evaluation",
            dataset_name="RST-DT",
            dataset_digest="digest",
            hyperparameters={"eval_idx": i},
            eval_metrics={"full_f1": 0.50 + (i * 0.05)},
        )

    runs = ledger.list_runs()
    assert len(runs) == 3
    assert [r.eval_metrics["full_f1"] for r in runs] == [0.50, 0.55, 0.60]
