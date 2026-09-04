"""Declared locks must not keep weak-referenceable or slotted providers alive."""

import gc
from weakref import ref

import pytest

from rdam import Machine, NativeTechniqueResult, ProviderRequest, Technique
from rdam.machine import _PROVIDER_LOCKS
from tests.machine.test_shared_runtime import declaration, provider


def test_concurrent_provider_has_no_call_lock() -> None:
    instance = provider(Technique.TOULMIN)
    machine = Machine([instance])
    assert not machine._provider_locks
    assert id(instance) not in _PROVIDER_LOCKS


def test_weak_provider_is_collected_with_its_lock() -> None:
    instance = provider(Technique.RST)
    instance._declaration = instance.declaration.model_copy(update={"parallel_safety": "serialized"})
    identity = id(instance)
    reference = ref(instance)
    first, second = Machine([instance]), Machine([instance])
    assert first._provider_locks[Technique.RST] is second._provider_locks[Technique.RST]
    del instance, first, second
    gc.collect()
    assert reference() is None
    assert identity not in _PROVIDER_LOCKS


def test_non_weak_provider_is_not_retained_globally() -> None:
    collected: list[bool] = []

    class SlottedProvider:
        __slots__ = ()

        @property
        def declaration(self):
            return declaration(Technique.RST).model_copy(update={"parallel_safety": "serialized"})

        def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
            raise AssertionError("lifetime checks do not analyse")

        def __del__(self) -> None:
            collected.append(True)

    instance = SlottedProvider()
    identity = id(instance)
    with pytest.raises(TypeError):
        ref(instance)
    machine = Machine([instance])
    assert identity in _PROVIDER_LOCKS
    del instance, machine
    gc.collect()
    assert collected == [True]
    assert identity not in _PROVIDER_LOCKS
