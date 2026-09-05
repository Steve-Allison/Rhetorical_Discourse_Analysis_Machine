"""Safe, fixed diagnostic messages for public operation boundaries."""

from typing import Literal
from rdam.contracts import OperationError, OperationFailure, Retryability, Sha256Identity

type Operation = Literal[
    "configuration", "capabilities", "prepare", "analyse", "summary", "view", "schema", "version", "serve", "publish"
]
type Category = Literal[
    "invalid_request",
    "source_unavailable",
    "preparation_failed",
    "dependency_unavailable",
    "busy",
    "internal_error",
    "output_error",
    "interrupted",
]

_MESSAGES = {
    "invalid_arguments": "Invalid command arguments. Use the command's --help for accepted input.",
    "invalid_input": "Input does not satisfy the requested contract.",
    "invalid_configuration": "Configuration does not satisfy the machine configuration contract.",
    "source_unavailable": "A requested local input could not be read.",
    "preparation_failed": "The supplied source could not be prepared.",
    "dependency_unavailable": "A required optional dependency is unavailable. Install the matching rdam extra.",
    "output_conflict": "The destination is not a safe, writable non-input file.",
    "output_failed": "Result publication failed; consult publication_state before retrying.",
    "internal_error": "The operation encountered an unexpected internal error.",
    "interrupted": "The operation was interrupted.",
    "busy": "Another operation is running. Retry after it finishes.",
    "invalid_http_request": "The HTTP request does not satisfy the local API contract.",
    "body_too_large": "The request body exceeds the configured limit.",
    "body_timeout": "The request body was not received within the configured deadline.",
}


def failure(
    operation: Operation,
    category: Category,
    code: str,
    *,
    identity: Sha256Identity | None = None,
    publication_state: Literal["not_published", "published", "unknown"] | None = None,
) -> OperationFailure:
    return OperationFailure(
        operation=operation,
        category=category,
        code=code,
        retryability=Retryability.RETRYABLE if category == "busy" else Retryability.NOT_RETRYABLE,
        message=_MESSAGES[code],
        completed_result_identity=identity,
        publication_state=publication_state,
    )


def error(
    operation: Operation,
    category: Category,
    code: str,
    *,
    identity: Sha256Identity | None = None,
    publication_state: Literal["not_published", "published", "unknown"] | None = None,
) -> OperationError:
    return OperationError(failure(operation, category, code, identity=identity, publication_state=publication_state))
