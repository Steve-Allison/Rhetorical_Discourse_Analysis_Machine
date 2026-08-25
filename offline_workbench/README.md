# Offline workbench

This is the single offline ownership surface for corpus preparation, training, evaluation, benchmarking, and local model promotion. It imports the installed `isanlp_rst` production package and production-owned contracts; production never imports this package.

`research_harness/` remains a source directory inside this same operational workbench because moving its complete experiment implementation would add churn without strengthening the package boundary. It uses the one root `offline` Pixi environment and is excluded from all production artifacts.
