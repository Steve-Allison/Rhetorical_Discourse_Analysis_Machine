"""Publication preserves inputs and existing results unless replacement is explicit."""

import errno
import os
from pathlib import Path
import stat
from typing import BinaryIO, NoReturn

import pytest
from rdam._output import OutputDestination
from rdam.contracts import OperationError
from rdam._strict import Sha256Identity


IDENTITY = Sha256Identity(hex_digest="a" * 64)


def _temporaries(directory: Path) -> list[Path]:
    return list(directory.glob(".rdam-*.tmp"))


def test_atomic_new_file(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    OutputDestination(target).publish(b"{}\n")
    assert target.read_bytes() == b"{}\n"
    assert target.stat().st_mode & 0o777 == 0o600
    assert list(tmp_path.iterdir()) == [target]


def test_no_clobber(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    target.write_bytes(b"original")
    with pytest.raises(OperationError):
        OutputDestination(target).publish(b"replacement")
    assert target.read_bytes() == b"original"


def test_force_replaces_regular_file(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    target.write_bytes(b"original")
    OutputDestination(target, force=True).publish(b"replacement")
    assert target.read_bytes() == b"replacement"


@pytest.mark.parametrize("alias", ("same", "hardlink", "symlink"))
def test_force_cannot_replace_input_alias(tmp_path: Path, alias: str) -> None:
    source = tmp_path / "input.json"
    source.write_bytes(b"input")
    target = source if alias == "same" else tmp_path / "result.json"
    if alias == "hardlink":
        target.hardlink_to(source)
    elif alias == "symlink":
        target.symlink_to(source)
    with pytest.raises(OperationError):
        OutputDestination(target, force=True, inputs=(source,)).publish(b"replacement")
    assert source.read_bytes() == b"input"


@pytest.mark.parametrize("kind", ("missing_parent", "parent_file", "directory", "dangling_symlink"))
@pytest.mark.parametrize("force", (False, True))
def test_invalid_destinations_are_rejected_before_creating_temporary_files(
    tmp_path: Path, kind: str, force: bool,
) -> None:
    target = tmp_path / "result.json"
    if kind == "missing_parent":
        target = tmp_path / "missing" / "result.json"
    elif kind == "parent_file":
        parent = tmp_path / "regular"
        parent.write_bytes(b"parent is a file")
        target = parent / "result.json"
    elif kind == "directory":
        target.mkdir()
    else:
        target.symlink_to(tmp_path / "nonexistent")
    with pytest.raises(OperationError) as caught:
        OutputDestination(target, force=force).publish(b"new", identity=IDENTITY)
    assert caught.value.failure.publication_state == "not_published"
    assert _temporaries(tmp_path) == []
    assert not (tmp_path / "missing").exists()


def test_force_preserves_an_existing_open_reader_and_changes_inode(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    target.write_bytes(b"original")
    old_inode = target.stat().st_ino
    with target.open("rb") as original_reader:
        OutputDestination(target, force=True).publish(b"replacement")
        assert original_reader.read() == b"original"
    assert target.stat().st_ino != old_inode
    assert target.read_bytes() == b"replacement"
    assert _temporaries(tmp_path) == []


def test_no_clobber_is_atomic_when_a_competitor_wins_after_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "result.json"
    original_link = os.link

    def racing_link(
        src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int, follow_symlinks: bool,
    ) -> None:
        target.write_bytes(b"competitor")
        original_link(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd,
                      follow_symlinks=follow_symlinks)

    monkeypatch.setattr(os, "link", racing_link)
    with pytest.raises(OperationError) as caught:
        OutputDestination(target).publish(b"ours", identity=IDENTITY)
    assert target.read_bytes() == b"competitor"
    assert caught.value.failure.publication_state == "not_published"
    assert caught.value.failure.completed_result_identity == IDENTITY
    assert _temporaries(tmp_path) == []


@pytest.mark.parametrize("alias", ("hardlink", "symlink"))
def test_force_rechecks_input_aliases_after_temporary_file_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias: str,
) -> None:
    source = tmp_path / "input.json"
    source.write_bytes(b"protected input")
    target = tmp_path / "result.json"
    original_fsync = os.fsync

    def introduce_alias(fd: int) -> None:
        original_fsync(fd)
        if stat.S_ISREG(os.fstat(fd).st_mode):
            if alias == "hardlink":
                target.hardlink_to(source)
            else:
                target.symlink_to(source)

    monkeypatch.setattr(os, "fsync", introduce_alias)
    with pytest.raises(OperationError) as caught:
        OutputDestination(target, force=True, inputs=(source,)).publish(b"ours", identity=IDENTITY)
    assert caught.value.failure.publication_state == "not_published"
    assert target.samefile(source)
    assert source.read_bytes() == b"protected input"
    assert _temporaries(tmp_path) == []


def test_parent_directory_swap_cannot_redirect_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "destination"
    parent.mkdir()
    displaced = tmp_path / "displaced"
    target = parent / "result.json"
    original_fsync = os.fsync

    def swap_directory(fd: int) -> None:
        original_fsync(fd)
        if stat.S_ISREG(os.fstat(fd).st_mode):
            parent.rename(displaced)
            parent.mkdir()

    monkeypatch.setattr(os, "fsync", swap_directory)
    with pytest.raises(OperationError) as caught:
        OutputDestination(target).publish(b"ours", identity=IDENTITY)
    assert caught.value.failure.publication_state == "not_published"
    assert not target.exists()
    assert list(parent.iterdir()) == []
    assert list(displaced.iterdir()) == []


@pytest.mark.parametrize("force", (False, True))
def test_file_fsync_failure_preserves_prior_target_and_cleans_owned_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, force: bool,
) -> None:
    target = tmp_path / "result.json"
    if force:
        target.write_bytes(b"original")

    def fail_fsync(fd: int) -> NoReturn:
        assert stat.S_ISREG(os.fstat(fd).st_mode)
        raise OSError(errno.EIO, "file synchronization failed")

    monkeypatch.setattr(os, "fsync", fail_fsync)
    with pytest.raises(OperationError) as caught:
        OutputDestination(target, force=force).publish(b"replacement", identity=IDENTITY)
    assert caught.value.failure.publication_state == "not_published"
    assert caught.value.failure.completed_result_identity == IDENTITY
    if force:
        assert target.read_bytes() == b"original"
    else:
        assert not target.exists()
    assert _temporaries(tmp_path) == []


@pytest.mark.parametrize("force", (False, True))
def test_directory_fsync_failure_reports_published_identity_without_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, force: bool,
) -> None:
    target = tmp_path / "result.json"
    if force:
        target.write_bytes(b"original")
    original_fsync = os.fsync

    def fail_directory_fsync(fd: int) -> None:
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError(errno.EIO, "directory synchronization failed")
        original_fsync(fd)

    monkeypatch.setattr(os, "fsync", fail_directory_fsync)
    with pytest.raises(OperationError) as caught:
        OutputDestination(target, force=force).publish(b"complete replacement", identity=IDENTITY)
    assert caught.value.failure.publication_state == "published"
    assert caught.value.failure.completed_result_identity == IDENTITY
    assert target.read_bytes() == b"complete replacement"
    assert _temporaries(tmp_path) == []


@pytest.mark.parametrize("unsupported", (errno.EINVAL, errno.ENOTSUP))
def test_unsupported_directory_fsync_does_not_reclassify_complete_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unsupported: int,
) -> None:
    target = tmp_path / "result.json"
    original_fsync = os.fsync

    def unsupported_directory_fsync(fd: int) -> None:
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError(unsupported, "unsupported directory sync")
        original_fsync(fd)

    monkeypatch.setattr(os, "fsync", unsupported_directory_fsync)
    OutputDestination(target).publish(b"complete", identity=IDENTITY)
    assert target.read_bytes() == b"complete"
    assert _temporaries(tmp_path) == []


@pytest.mark.parametrize("force", (False, True))
def test_interruption_before_atomic_publication_preserves_prior_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, force: bool,
) -> None:
    target = tmp_path / "result.json"
    if force:
        target.write_bytes(b"original")

    def interrupt_fsync(fd: int) -> NoReturn:
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "fsync", interrupt_fsync)
    with pytest.raises(KeyboardInterrupt):
        OutputDestination(target, force=force).publish(b"replacement", identity=IDENTITY)
    if force:
        assert target.read_bytes() == b"original"
    else:
        assert not target.exists()
    assert _temporaries(tmp_path) == []


@pytest.mark.parametrize("force", (False, True))
def test_interruption_after_atomic_publication_retains_complete_file_and_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, force: bool,
) -> None:
    target = tmp_path / "result.json"
    if force:
        target.write_bytes(b"original")
    original_link = os.link
    original_replace = os.replace

    def interrupt_link(
        src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int, follow_symlinks: bool,
    ) -> NoReturn:
        original_link(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd,
                      follow_symlinks=follow_symlinks)
        raise KeyboardInterrupt

    def interrupt_replace(src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int) -> NoReturn:
        original_replace(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "link", interrupt_link)
    monkeypatch.setattr(os, "replace", interrupt_replace)
    with pytest.raises(KeyboardInterrupt):
        OutputDestination(target, force=force).publish(b"complete replacement", identity=IDENTITY)
    assert target.read_bytes() == b"complete replacement"
    assert _temporaries(tmp_path) == []


def test_file_descriptor_is_closed_when_fdopen_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "result.json"
    descriptors: list[int] = []

    def fail_fdopen(fd: int, mode: str) -> BinaryIO:
        descriptors.append(fd)
        raise OSError(errno.EMFILE, "cannot construct stream")

    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    with pytest.raises(OperationError):
        OutputDestination(target).publish(b"complete", identity=IDENTITY)
    assert len(descriptors) == 1
    try:
        with pytest.raises(OSError) as caught:
            os.fstat(descriptors[0])
        assert caught.value.errno == errno.EBADF
    finally:
        # A failing implementation must not leak this real descriptor into other tests.
        try:
            os.fstat(descriptors[0])
        except OSError as failure:
            assert failure.errno == errno.EBADF
        else:
            os.close(descriptors[0])
    assert not target.exists()
    assert _temporaries(tmp_path) == []


def test_private_complete_temp_is_synced_before_no_clobber_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "result.json"
    payload = b'{"complete":true}\n'
    events: list[str] = []
    original_fsync = os.fsync
    original_link = os.link

    def observe_fsync(fd: int) -> None:
        events.append("directory_sync" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file_sync")
        original_fsync(fd)

    def observe_link(
        src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int, follow_symlinks: bool,
    ) -> None:
        temporary = tmp_path / src
        assert temporary.read_bytes() == payload
        assert temporary.stat().st_mode & 0o777 == 0o600
        assert not target.exists()
        assert events == ["file_sync"]
        events.append("publish")
        original_link(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd,
                      follow_symlinks=follow_symlinks)

    monkeypatch.setattr(os, "fsync", observe_fsync)
    monkeypatch.setattr(os, "link", observe_link)
    OutputDestination(target).publish(payload, identity=IDENTITY)
    assert events == ["file_sync", "publish", "directory_sync"]
    assert target.read_bytes() == payload


def test_owned_temp_cleanup_failure_reports_safe_published_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "result.json"
    original_unlink = os.unlink
    denied: list[str] = []

    def deny_temp_unlink(path: str, *, dir_fd: int | None = None) -> None:
        if path.startswith(".rdam-"):
            denied.append(path)
            raise PermissionError(errno.EACCES, "temporary unlink denied")
        original_unlink(path, dir_fd=dir_fd)

    with monkeypatch.context() as boundary:
        boundary.setattr(os, "unlink", deny_temp_unlink)
        with pytest.raises(OperationError) as caught:
            OutputDestination(target).publish(b"complete", identity=IDENTITY)
    assert denied
    assert caught.value.failure.publication_state == "published"
    assert caught.value.failure.completed_result_identity == IDENTITY
    assert target.read_bytes() == b"complete"
    # An OS denial makes cleanup impossible; the library must report it safely,
    # not claim rollback or replace the successfully published payload.
    for temporary in _temporaries(tmp_path):
        temporary.unlink()
