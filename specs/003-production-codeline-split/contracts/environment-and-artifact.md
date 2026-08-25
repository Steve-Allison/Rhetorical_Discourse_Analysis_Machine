# Contract: Environments and Production Artifacts

`production` and `offline` are named environments in the one root Pixi workspace and lock. Production is independently solvable and contains no offline-only dependency. Offline consumes the installed production project and adds training/evaluation/research dependencies.

Wheel and sdist contain only approved production code/resources plus standard build metadata. Tests, specs, scripts, offline namespaces, corpora, prepared data, experiment configs, caches, local checkpoints, secrets, and generated evidence are forbidden.

Completion validation installs the exact wheel into a fresh location outside the repository, removes the repository from `sys.path`, disables network fallback, and exercises all supported runtime imports and representative routes. An editable install is not completion evidence.
