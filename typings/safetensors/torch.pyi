from os import PathLike

from torch.nn import Module

def load_model(
    model: Module,
    filename: str | PathLike[str],
    strict: bool = ...,
    device: str | int = ...,
    *,
    backend: str = ...,
) -> tuple[list[str], list[str]]: ...
