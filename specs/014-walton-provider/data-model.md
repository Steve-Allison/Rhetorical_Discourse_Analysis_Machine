# Data Model: Walton Provider

**Feature**: 014 | **Date**: 2026-09-03

## Scheme

Stable `scheme_id`, non-empty name, one or more unique premise-role names, and one or
more ordered critical-question texts.

## CriticalQuestion

An index into the selected scheme, a status (`addressed` or `open`), and an optional
note. `addressed` requires a non-empty note; `open` requires no provider-authored answer.

## SchemeInstance

One scheme identity, non-empty conclusion, exact role-to-source-content mapping, and
zero or more uniquely indexed reported critical questions. `open_questions` is derived
as the exact complement of addressed questions in the scheme catalogue.

## WaltonAnalysis

An ordered collection of zero or more instances plus the stable scheme-set identity.
Derived fields report instance count and total open questions. Zero instances is a valid
finding.

## ExtractionEvidence

Exact model identity, instruction digest, output-attempt count, and transport-attempt
count. Attempt evidence follows the shared contract in Feature 013.
