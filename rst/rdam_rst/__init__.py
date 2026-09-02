"""rdam_rst — the machine-facing RST/eRST provider adapter.

Consumes the supported ``isanlp_rst`` public contract and nothing else (FR-010): it never
duplicates, reinterprets, or bypasses the provider's preparation, analysis, capability,
serialization, validation, failure, or provenance authority. The native payload it hands
the machine is ``isanlp_rst``'s own canonical outcome envelope, verbatim.
"""

from importlib.metadata import PackageNotFoundError, version

from rdam_rst.provider import RstProvider, ProviderConfigurationError

try:
    __version__ = version("rdam-rst")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["ProviderConfigurationError", "RstProvider", "__version__"]
