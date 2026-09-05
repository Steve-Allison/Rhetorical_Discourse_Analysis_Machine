# Contract: Unified rdam CLI

**Status**: Proposed grammar; implementation has not started.

## Commands

```text
rdam capabilities [CONFIG] [OUTPUT]
rdam prepare SOURCE [SOURCE_OPTIONS] [--techniques LIST] [CONFIG] [OUTPUT]
rdam prepare --text TEXT [--source-name NAME] [--techniques LIST] [CONFIG] [OUTPUT]
rdam prepare --edus JSON [--source-name NAME] [--techniques LIST] [CONFIG] [OUTPUT]
rdam prepare --request FILE [CONFIG] [OUTPUT]
rdam analyse SOURCE --techniques LIST [SOURCE_OPTIONS] [STRUCTURES] [FORMALISMS] [CONFIG] [OUTPUT]
rdam analyse --text TEXT --techniques LIST [--source-name NAME] [STRUCTURES] [FORMALISMS] [CONFIG] [OUTPUT]
rdam analyse --edus JSON --techniques LIST [--source-name NAME] [STRUCTURES] [FORMALISMS] [CONFIG] [OUTPUT]
rdam analyse --techniques LIST --structured TECHNIQUE=FILE [STRUCTURES] [FORMALISMS] [CONFIG] [OUTPUT]
rdam analyse --request FILE [CONFIG] [OUTPUT]
rdam summary RESULT [OUTPUT]
rdam view RESULT --techniques LIST [OUTPUT]
rdam schema RECORD [--mode validation|serialization] [OUTPUT]
rdam version [OUTPUT]
rdam serve [CONFIG] [--host HOST] [--port PORT] [HTTP_LIMITS]
```

Uppercase groups expand below; they are not literal arguments. `SOURCE`, `FILE`
and `RESULT` accept `-` for stdin except configuration files and upstream files
embedded in a request (which are already materialized, not paths). There is no
implicit stdin read when a source is omitted. `python -m rdam` invokes the same
main function; no separate grammar. No `parse`, `analyze`, `summarise` aliases or
`rdam-rst` compatibility command. The standalone Python function is British
`summarise`; the CLI command is the noun `summary`.

### Common options

| Group | Options | Rules |
|---|---|---|
| OUTPUT | `-o/--output PATH`, `--force`, `--diagnostics json\|text` | Output absent/`-` means stdout. Force requires a file destination. Diagnostics default JSON. |
| SOURCE_OPTIONS | `--source-form FORM`, `--source-name NAME` | FORM is an exact SourceForm value; a name override preserves declared origin and recomputes metadata-bearing identity. |
| STRUCTURES | repeated `--structured dung=FILE` / `--structured ibis=FILE` | At most one each, and only for requested techniques. Values are strict native JSON objects, not strings containing JSON. |
| FORMALISMS | repeated `--formalism TECHNIQUE=FORMALISM` | At most one per selected boundary. `rst=erst_graph` selects eRST. |
| CONFIG | `-c/--config FILE` plus narrow overrides below | Only capabilities/prepare/analyse/serve accept these options. |

Config overrides: `--model MODEL`; repeated `--technique-model TECHNIQUE=MODEL`
for the four LLM techniques; `--rst-model VERSION` or the pair `--model-store PATH
--release-id ID`; `--rst-relinventory NAME`; `--device DEVICE`;
`--erst-checkpoint PATH`; `--rst-evidence-detail DETAIL`;
`--rst-marker-refinement evidence_preserving|disabled`; `--dung-capacity N`;
`--max-workers N`; `--cache-directory PATH`. No free-form `--set`, secret flag,
temperature knob, arbitrary URL or unvalidated provider option bag.

All options follow the subcommand. Every parser disables abbreviation and
rejects repeated singleton options, even when repeated values are equal.
Repeatable mapping options reject duplicate keys. Short aliases have exactly
the same duplicate behavior as long names. Unknown options are errors; no
partial parsing that forwards unknown tokens. LIST is comma-separated exact
lowercase boundary names, whitespace around components is ignored, and empty or
duplicate components are invalid. Order is preserved.

## Acquisition and exclusivity

1. Source positional, `--text`, `--edus` and `--request` are mutually exclusive.
   Structured-only mode requires no document source, only structured boundaries,
   and at least one supplied structure. It uses `AggregateRequest.for_structured`.
2. `--request` is mutually exclusive with techniques, source options, structured
   files and formalism convenience options. Config/output options remain valid.
   Complex declared lineage uses this full canonical request route rather than
   adding loosely coupled upstream-file flags.
3. Exactly one reader may own stdin. Source/request/result and one structure
   may use `-`, but two such uses in one invocation fail before reading either.
   `--config -` is forbidden; config files have a stable path base.
4. Stdin defaults to UTF-8 text; all other forms require `--source-form`.
   There is no archive or JSON sniffing of stdin. `--source-form edus` accepts a
   strict JSON array and preserves its raw byte identity; `--edus` accepts the
   same values inline through the shared constructor.
5. Default names: path basename; `stdin` for stdin; `cli-text` / `cli-edus` for
   inline input; `structured-input` for the synthetic structure source. Python
   callers can use the same names/origin to create an equivalent descriptor.
6. Paths are literal after shell processing. `--` terminates options so a source
   beginning with `-` is usable; `./-` names a literal file rather than stdin.
   `-o ./-` similarly names a file. RDAM expands neither globs nor `~` itself.
7. Complete acquisition and validation precede inference. Every local input
   path read (including config and structure files) enters the publication
   alias-check set. Optional dependency failure names the extra safely.

## Configuration precedence

Use data-model.md's single resolution algorithm. CLI model selector flags replace
the complete configured RST model variant; partial `--model-store` or
`--release-id` does not borrow its missing partner from a file. `--rst-model`
and either local selector flag conflict. Other overrides replace only their
named field. Per-technique model overrides remain more specific than `--model`.
No override can silently discard evidence, markers or cache options.

## Output and diagnostics

Capabilities, preparation, analysis, view, schema and version emit exactly one
canonical UTF-8 JSON document plus LF to stdout or the specified file. No BOM,
ANSI escapes, progress display or introductory prose. Output does not vary with
isatty. Result bytes must be fully serialized/validated before publication.

Default diagnostics are one safe OperationFailure JSON line on stderr for a
fatal boundary error. `--diagnostics text` renders the same safe fields. A
partial/unsuccessful aggregate is not a fatal operation error: it is written in
full with the appropriate exit code; stderr may remain empty. No duplicate
count-only result is emitted. Library progress/warnings must not contaminate
stdout; routing must not suppress the underlying warning or validation failure.

`summary` emits the plain-text projection defined in python-api.md with a final
LF. It never overwrites its input, runs analysis or claims the view is canonical
JSON. `-o` uses the same safe publication rules. The separate command preserves
the full result; there is no `analyse --format summary` mode.

`view` emits the canonical AnalysisView specified in [ai-usage.md](ai-usage.md).
Selection is mandatory and contains only requested boundaries from the saved v2
aggregate. A successful projection exits 0 even if the original analysis status
was partial/unsuccessful; that original status remains explicit in the view.
No config is accepted, no inference occurs, and no item-level truncation or
automatic size-based fallback is permitted. Legacy v1 input gives exit 2.

## Exit statuses and precedence

| Exit | Meaning | Result destination |
|---|---|---|
| 0 | All requested outcomes are results; or successful non-analysis command | Complete output |
| 1 | Operational/internal/dependency/preparation/publication failure | No result unless atomic publication already occurred; safe stderr diagnostic identifies that state |
| 2 | Usage, malformed request/config/source encoding, or invalid envelope | No result; safe stderr diagnostic |
| 3 | Some requested boundaries produced results | Complete aggregate retained |
| 4 | No requested boundary produced a result | Complete aggregate retained |
| 130 | User interrupted the operation | No partial published file; already atomically published files remain valid |
| 141 | Downstream stdout pipe closed | No traceback or second write to stdout; result delivery was not successful |

Operational delivery failure overrides the analytical exit class. For example,
partial analysis followed by failed file publication exits 1, not 3. An analysis
with a retained upstream success and no new successes exits 4. Empty-primary RST
is a valid native result and does not alone cause a nonzero status.
Missing local file is exit 1; malformed source encoding/envelope is exit 2;
semantic preparation failure is exit 1; a malformed Dung graph handled by its
provider produces a failed outcome, therefore 4 or 3, not envelope exit 2.

`rdam --help` and command `--help` print human-readable help to stdout and exit 0.
No arguments prints a short usage diagnostic to stderr and exits 2. Global
`--version` emits the same JSON as `version`. Help/version/schema short-circuit
configuration and model resolution, including when an unused config path would
not exist. Usage errors do not echo sensitive raw input values.

## Safe file publication

Before model work: validate destination parent existence/type and obvious
conflicts. Parent directories are not created implicitly. Reject symlink output
targets and aliases of every input (resolved paths and existing inode identity),
including hard links; `--force` never overrides input protection. A config/input
path named as output is rejected even when acquisition has already materialized it.

Serialize first; write a uniquely named sibling temp with owner-only permissions,
flush and fsync it, then publish atomically. Default publication must use an
atomic no-clobber primitive, not a race-prone exists-check then replace. With
`--force`, replace an existing regular non-input file atomically after rechecking
aliases; never truncate it in place. Sync the destination directory as supported.
Clean the owned temp after ordinary failure; preserve the prior target on failures
before atomic publication. A directory fsync failure after publication cannot
guarantee rollback: report published/unknown state and completed result identity,
exit 1, and do not replace the valid result with a diagnostic.
If interruption follows atomic publication, the complete file may exist and
remains valid. No guarantee is made against power loss beyond filesystem/fsync
semantics. Never write a diagnostic into the intended result path.

On stdout, broken pipes can leave the receiver with incomplete bytes; report
non-success and do not pretend pipe writes have file-transaction guarantees.
Ctrl-C stops scheduling, drains already-running in-process work under existing
machine semantics, then exits 130. No new hard thread-kill or retry is invented.

## Help acceptance

Root help lists all commands and explains JSON/stdout, diagnostics/stderr and
exit 3/4. Command help includes required input mode, defaults, explicit model
configuration, supported form/technique choices, missing-extra guidance and a
small runnable example. No model identifiers copied into help as timeless
availability claims; package-derived defaults are labelled defaults, not probes.

`serve` emits a safe listening event to stderr containing the actual bound
loopback URL (including an OS-selected port for `--port 0`), and nothing to stdout.
The event must not include model-store paths or credentials. HTTP_LIMITS and
startup behavior are defined in [http.md](http.md).
