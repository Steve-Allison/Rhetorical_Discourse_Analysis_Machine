from os import PathLike

class ValidationError(Exception): ...

def validate(
    path: str | PathLike[str],
    *,
    allow_empty_namespace: bool = ...,
) -> None: ...
