"""Atomic local publication with no-clobber default and input-alias protection."""

import errno
import os
from pathlib import Path
import stat
import sys
from uuid import uuid4

from rdam._errors import error
from rdam._strict import Sha256Identity


class OutputDestination:
    def __init__(self, path: Path, *, force: bool = False, inputs: tuple[Path, ...] = ()) -> None:
        self.path = path.absolute()
        self.force = force
        self.inputs = tuple(source.absolute() for source in inputs)

    def validate(self) -> None:
        try:
            if not self.path.parent.is_dir() or self.path.is_symlink():
                raise error("publish", "output_error", "output_conflict", publication_state="not_published")
            if self.path.exists() and (not self.path.is_file() or not self.force):
                raise error("publish", "output_error", "output_conflict", publication_state="not_published")
            for source in self.inputs:
                if self.path.resolve() == source.resolve() or (
                    self.path.exists() and source.exists() and self.path.samefile(source)
                ):
                    raise error("publish", "output_error", "output_conflict", publication_state="not_published")
        except OSError as cause:
            raise error("publish", "output_error", "output_conflict", publication_state="not_published") from cause

    def publish(self, payload: bytes, *, identity: Sha256Identity | None = None) -> None:
        self.validate()
        published = False
        temporary = f".rdam-{uuid4().hex}.tmp"
        directory: int | None = None
        owned = False
        try:
            directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory)
            owned = True
            try:
                stream = os.fdopen(descriptor, "wb")
            except BaseException:
                os.close(descriptor)
                raise
            with stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            self.validate()
            # Directory identity must still be the one validated by path-based alias checks.
            opened, current = os.fstat(directory), self.path.parent.stat()
            if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
                raise error(
                    "publish", "output_error", "output_conflict", identity=identity, publication_state="not_published"
                )
            if self.force:
                try:
                    target = os.stat(self.path.name, dir_fd=directory, follow_symlinks=False)
                except FileNotFoundError:
                    target = None
                if target is not None and not stat.S_ISREG(target.st_mode):
                    raise error(
                        "publish",
                        "output_error",
                        "output_conflict",
                        identity=identity,
                        publication_state="not_published",
                    )
                os.replace(temporary, self.path.name, src_dir_fd=directory, dst_dir_fd=directory)
                owned = False
            else:
                os.link(temporary, self.path.name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
            published = True
            if owned:
                os.unlink(temporary, dir_fd=directory)
                owned = False
            try:
                os.fsync(directory)
            except OSError as cause:
                if cause.errno not in {errno.EINVAL, errno.ENOTSUP}:
                    raise
        except OSError as cause:
            raise error(
                "publish",
                "output_error",
                "output_failed",
                identity=identity,
                publication_state="published" if published else "not_published",
            ) from cause
        finally:
            active = sys.exception()
            if directory is not None:
                try:
                    if owned:
                        try:
                            os.unlink(temporary, dir_fd=directory)
                        except FileNotFoundError:
                            # Publication may have moved it immediately before an interrupt.
                            pass
                        except OSError as cleanup_error:
                            if active is not None and active is not cleanup_error:
                                raise active from cleanup_error
                            raise error(
                                "publish",
                                "output_error",
                                "output_failed",
                                identity=identity,
                                publication_state="published" if published else "not_published",
                            ) from cleanup_error
                finally:
                    os.close(directory)
