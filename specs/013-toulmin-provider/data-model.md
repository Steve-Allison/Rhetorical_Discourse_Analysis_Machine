# Data Model: Toulmin Provider

**Feature**: 013 | **Date**: 2026-09-03

## ToulminLayout

| Field | Cardinality | Rule |
|---|---:|---|
| `claim` | 1 | Non-empty assertion the arguer wants accepted. |
| `grounds` | 1..* | Non-empty facts or evidence offered for the claim. |
| `warrant` | 1 | Non-empty inference licence; normalized value differs from claim and every ground. |
| `backing` | 0..* | Support for the warrant, never direct support for the claim. |
| `qualifier` | 0..1 | Force attached to the claim. |
| `rebuttals` | 0..* | Defeating conditions on the warranted inference; may retain source text. |

Derived fields: `elements_present` follows Toulmin order; `is_qualified` is true when a
qualifier or rebuttal exists.

## ToulminAnalysis

An ordered collection of zero or more `ToulminLayout` values. Zero is a valid analytical
finding for non-argumentative text. Derived counts report total layouts and layouts with
qualifying material.

## ExtractionEvidence

| Field | Rule |
|---|---|
| `model` | Exact configured model identity. |
| `instructions_digest` | Semantic digest of the instructions used. |
| `output_attempts` | Actual model proposals used by output validation, at least one on success. |
| `transport_attempts` | Actual HTTP attempts, including retries, at least one when a request reached transport. |

## State transitions

`unavailable(model_unavailable) → available` only when the required local credential or
configuration resolves. During analysis, `available → result` for a valid proposal or
`available → failed` for exhausted validation, exhausted transport, invalid input, or an
unexpected client failure. No failed state returns a partial layout.
