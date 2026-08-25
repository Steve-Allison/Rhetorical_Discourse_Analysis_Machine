# Contract: Local Model Promotion

Production loads only a directory whose manifest and full file inventory validate before reconstruction. Offline promotion verifies the candidate, copies it to a temporary sibling, re-verifies bytes, writes a receipt, and atomically renames it to a content-addressed release path. Existing destinations are immutable.

Required evidence: task, architecture/configuration, runtime request/result contract, immutable source identity, compatibility range, every file hash and role, provenance, licence/use restrictions, and available evaluation evidence. Missing evidence may be declared unavailable; it cannot be fabricated.

Loose checkpoints, mutable training directories, unknown members, symlinks, incomplete manifests, changed hashes, incompatible contracts, and unpromoted candidates fail before inference. Existing released model bytes migrate byte-for-byte without retraining.
