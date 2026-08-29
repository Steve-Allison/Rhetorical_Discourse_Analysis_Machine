"""Measured MPS allocation sampling for independent experiment runs."""

from threading import Event, Lock, Thread
from time import monotonic

import torch


class MpsMemorySampler:
    """Sample driver allocations during a run because PyTorch exposes no MPS peak API."""

    def __init__(self, *, enabled: bool, interval_seconds: float = 0.01) -> None:
        if interval_seconds <= 0.0:
            raise ValueError("MPS sampling interval must be positive")
        self.enabled = enabled
        self.interval_seconds = interval_seconds
        self._stop = Event()
        self._lock = Lock()
        self._thread: Thread | None = None
        self._peak = 0
        self._failure: RuntimeError | None = None
        self._started_at: float | None = None

    @property
    def peak_allocated_bytes(self) -> int | None:
        if not self.enabled:
            return None
        with self._lock:
            return self._peak

    def _sample_loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                allocation = int(torch.mps.driver_allocated_memory())
            except RuntimeError as error:
                with self._lock:
                    self._failure = error
                self._stop.set()
                return
            with self._lock:
                self._peak = max(self._peak, allocation)

    def __enter__(self) -> "MpsMemorySampler":
        if not self.enabled:
            return self
        if not torch.backends.mps.is_available():
            raise RuntimeError("MPS memory sampling was requested but MPS is unavailable")
        self._started_at = monotonic()
        self._peak = int(torch.mps.driver_allocated_memory())
        self._thread = Thread(target=self._sample_loop, name="erst-mps-memory-sampler", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exception_type: object, exception: object, traceback: object) -> None:
        if not self.enabled:
            return
        self._stop.set()
        if self._thread is None or self._started_at is None:
            raise RuntimeError("MPS memory sampler did not start correctly")
        self._thread.join(timeout=max(1.0, self.interval_seconds * 10.0))
        if self._thread.is_alive():
            raise RuntimeError("MPS memory sampler failed to stop")
        if self._failure is not None and exception is None:
            raise RuntimeError("MPS allocation sampling failed during the experiment") from self._failure


__all__ = ["MpsMemorySampler"]
