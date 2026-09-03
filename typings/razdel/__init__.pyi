from collections.abc import Iterator

class Token:
    text: str
    start: int
    stop: int

def tokenize(text: str) -> Iterator[Token]: ...
def sentenize(text: str) -> Iterator[Token]: ...
