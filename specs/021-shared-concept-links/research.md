# Implementation decisions and evidence

Runtime projection avoids YAML/LinkML compilation. All declared Central domains load;
labels and declared terminology remain distinct reasons. Unicode normalization maintains
an original-character mapping and preserves punctuation and acronym case by default.

Shared preparation validation and Markdown parsing belong to ingestion. RST tensor imports
are deferred until inference is requested. This was verified in a fresh process that also
rejects network connections during actual concept linking.

The Docling NLP experiment is evaluation-only. Its fixed inputs, offset conversion,
metrics and recommendation are in ../../workbench/experiments/concept_linking/REPORT.md.
No runtime adoption follows from this implementation.
