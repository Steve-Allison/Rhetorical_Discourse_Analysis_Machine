from os import PathLike

class ValidationError(Exception): ...

def validate(
    path: str | PathLike[str],
    *,
    spec_version: str | None = ...,
    allow_empty_namespace: bool = ...,
) -> None: ...
