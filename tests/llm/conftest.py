"""No test in this directory may reach a real model.

Pydantic AI's global switch makes an accidental network call an error rather than a
silent bill. Tests that deliberately exercise the real model live behind ``-m slow`` in
the technique suites and re-enable it themselves.
"""

from collections.abc import Iterator

from pydantic_ai import models
import pytest


@pytest.fixture(autouse=True)
def no_real_model_requests() -> Iterator[None]:
    previous = models.ALLOW_MODEL_REQUESTS
    models.ALLOW_MODEL_REQUESTS = False
    try:
        yield
    finally:
        models.ALLOW_MODEL_REQUESTS = previous
