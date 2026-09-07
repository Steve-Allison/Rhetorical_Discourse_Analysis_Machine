# GUM gold RST fixtures

Human RST/eRST trees for real documents across multiple genres, so parser output
can be compared and benchmarked against known-good gold standard analyses.

| File | Genre | Underlying-text licence | EDUs | Secondary Edges | Signals |
| :--- | :--- | :--- | ---: | ---: | ---: |
| `GUM_academic_art.rs4` | Academic / Art History | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | 74 | 0 | 124 |
| `GUM_academic_census.rs4` | Academic / Sociology | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | 110 | 4 | 146 |
| `GUM_bio_byron.rs4` | Biography (Lord Byron) | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) | 91 | 7 | 109 |
| `GUM_bio_dvorak.rs4` | Biography (Antonín Dvořák) | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) | 71 | 0 | 114 |
| `GUM_bio_emperor.rs4` | Biography (Emperor Norton) | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) | 85 | 6 | 118 |
| `GUM_interview_gaming.rs4` | Spoken Interview / Q&A | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | 85 | 7 | 134 |
| `GUM_news_nasa.rs4` | News (NASA Announcement) | Public Domain / [CC BY 2.5](https://creativecommons.org/licenses/by/2.5/) | 124 | 1 | 156 |
| `GUM_news_sensitive.rs4` | News (Wikinews Investigation) | [CC BY 2.5](https://creativecommons.org/licenses/by/2.5/) | 76 | 0 | 125 |
| `GUM_textbook_chemistry.rs4` | Textbook / STEM | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | 127 | 4 | 151 |
| `GUM_voyage_oakland.rs4` | Travel Guide (WikiVoyage) | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) | 85 | 0 | 128 |

Copied **verbatim** from [amir-zeldes/gum](https://github.com/amir-zeldes/gum/) (`rst/rstweb/`). No transformation.

Verified byte-for-byte against upstream revision
`22fdf87f9c71c96bcc771461d06e689b1f90020d` on 2026-09-05.
The [upstream manifest](upstream-manifest.json) records fixture hashes and the
official split inventory from that revision. These fixtures include two training,
three development and five test documents; Dvořák belongs to the test partition.
The combined `quality-baseline.json` is a mixed-partition regression baseline,
not a held-out corpus evaluation. A corpus test designation alone does not prove
that a particular model excluded the document during training; model overlap
remains to be verified before reporting held-out quality.

GUM annotations are [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). All vendored underlying texts are CC BY / CC BY-SA / Public Domain.

Credit: Zeldes, Amir (2017). The GUM Corpus: Creating Multilayer Resources in the Classroom. *Language Resources and Evaluation* 51(3), 581–612. Annotators: [GUM project](https://gucorpling.org/gum/).
