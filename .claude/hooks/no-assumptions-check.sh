#!/usr/bin/env bash
# .claude/hooks/no-assumptions-check.sh
#
# PreToolUse hook enforcing .claude/rules/no-assumptions.md at write time.
# Blocks Write / Edit / MultiEdit when the proposed content makes a
# canonicity, custom-field, or extension claim WITHOUT a nearby evidence
# anchor or ASSUMED marker.
#
# Written 2026-05-15 after a HARD-RULE breach in which I claimed
# `PictureItem.meta.description` was a "Docling-Machine extension" without
# reading the docling-core PictureMeta schema. Anti-pattern #2 of the rule.

set -euo pipefail

input="$(cat)"
tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty')"

case "$tool_name" in
  Write|Edit|MultiEdit|NotebookEdit) ;;
  *) exit 0 ;;
esac

# Extract proposed new content. Edit uses new_string; Write uses content;
# NotebookEdit uses new_source. MultiEdit has an edits[] array — concatenate.
content="$(
  printf '%s' "$input" | jq -r '
    (.tool_input.new_string // empty),
    (.tool_input.content    // empty),
    (.tool_input.new_source // empty),
    (.tool_input.edits // [] | map(.new_string) | join("\n"))
  ' 2>/dev/null
)"
[ -z "${content// /}" ] && exit 0

# Trigger patterns: claims about canonicity / custom / extension.
# Extended regex; case-insensitive grep below.
triggers='(custom field|extension field|producer-specific|non-canonical|is not canonical|isn'\''t canonical|is the canonical|the canonical [a-z]+ (place|field|location|api|path)|isn'\''t a declared field|is not a declared field|Docling-Machine extension|DM extension|pydantic extra (field|key)|model_extra extension|not in the schema|isn'\''t in the schema|is not in the schema|undocumented field|undocumented extension)'

# Evidence anchors that exempt a claim. Any one of these in the same content
# blob lets the write through.
evidence='(model_fields|model_extra|ASSUMED \(|ASSUMED:|ASSUMED [0-9]|Verified [0-9]|verified [0-9]|verified by reading|verified at [^[:space:]]+:[0-9]|[a-z_/]+\.(py|json|yaml|md):[0-9]+|file:line|`[A-Z][A-Za-z_]+\.[a-z_]+`|primary source|primary-source)'

triggered_phrases="$(printf '%s' "$content" | grep -iE -- "$triggers" || true)"
if [ -z "$triggered_phrases" ]; then
  exit 0
fi

has_evidence="$(printf '%s' "$content" | grep -iE -- "$evidence" || true)"
if [ -n "$has_evidence" ]; then
  exit 0
fi

{
  echo "BLOCKED by .claude/hooks/no-assumptions-check.sh"
  echo
  echo "The proposed content contains a canonicity / custom-field / extension"
  echo "claim WITHOUT a nearby evidence anchor or ASSUMED marker. This violates"
  echo ".claude/rules/no-assumptions.md (anti-pattern #2: pattern-matched"
  echo "conclusion as verified fact)."
  echo
  echo "Triggered phrases (first 10 lines containing them):"
  printf '%s\n' "$triggered_phrases" | head -10 | sed 's/^/  > /'
  echo
  echo "To proceed, either:"
  echo "  1. Verify by reading the relevant schema/source (Pydantic model class,"
  echo "     primary docstring, code at path:line) and include a citation in"
  echo "     the SAME edit: 'Verified <date> at <path>:<line>', or paste the"
  echo "     output of \`Model.model_fields\` etc."
  echo "  2. Mark the claim explicitly: 'ASSUMED (<date>, to verify): <claim>.'"
  echo
  echo "This hook exists because I produced the exact failure it prevents on"
  echo "2026-05-15. Do not bypass — verify."
} >&2

exit 2
