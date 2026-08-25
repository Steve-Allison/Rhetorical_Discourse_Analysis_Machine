# Contract: Ownership and Boundary Gate

The ownership authority is the single repository classification source. Every tracked or build-relevant untracked path and every declared dependency resolves to exactly one class.

The routine command must derive production packages from build configuration, parse imports without importing application modules, resolve transitive local imports, reject every path reaching offline/repository/generated code, compare dependencies with dependency ownership, and report the complete offending chain. It must finish within ten seconds locally.

Negative cases seed a direct import, indirect import, offline dependency, and forbidden archive member. Each must fail naming the introduced target and path. There is no suppression for a real violation; ownership or dependency must be corrected.
