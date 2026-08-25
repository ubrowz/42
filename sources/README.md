# Sources

The papers `RELATED.md` quotes, so that its verbatim quotations can be checked
rather than trusted.
`tests/test_docs.py::TestRelatedWorkQuotations` extracts the text with
`pdftotext` and asserts every quotation still appears in its source.

**The PDFs are not in this repository.** They are other people's papers, and
redistributing them here is not ours to do. Download them from the links below
into this directory under the file names in the first column, and the quotation
test starts checking; without them it skips itself, so the suite passes either
way.

| file | paper |
|---|---|
| `inv.pdf` | Mu, Hu & Takeichi, *An Injective Language for Reversible Computation*, MPC 2004. <https://takeichi.ipl-lab.org/~scm/pub/reversible.pdf> |
| `pisolang.pdf` | Onodera, Nakano, Asada & Kikuchi, *PisoLang*, RC 2026. <https://www.riec.tohoku.ac.jp/~ksk/pub/Onodera26rc-full.pdf> |
| `pi-information-effects.pdf` | James & Sabry, *Information Effects*, POPL 2012 — the language Π. From the second author's page. |
| `theseus.pdf` | James & Sabry, *Theseus: A High Level Language for Reversible Computing*, 2014 — and the full `Πo` primitive table, which the POPL paper does not give. |
| `janus.pdf` | Yokoyama & Glück, *A Reversible Programming Language and its Invertible Self-Interpreter*, PEPM 2007 — the paper that gave Janus its formal semantics. |
| `rfun.pdf` | Thomsen & Axelsen, *Interpretation and Programming of the Reversible Functional Language RFUN*, IFL 2015. |
| `quantum-effect.pdf` | Carette, Heunen, Kaarsgaard & Sabry, *The Quantum Effect: A Recipe for QuantumΠ*, arXiv:2302.01885, 2023. |
| `one-rig.pdf` | Heunen, Kaarsgaard & Lemonnier, *One rig to control them all*, arXiv:2510.05032, 2025. |
| `chardonnet-fscd2024.pdf` | Chardonnet, Lemonnier & Valiron, *Semantics for a Turing-Complete Reversible Programming Language with Inductive Types*, FSCD 2024 (LIPIcs, open access). |
| `lenses.pdf` | Foster, Greenwald, Moore, Pierce & Schmitt, *Combinators for Bidirectional Tree Transformations*, TOPLAS 29(3), 2007. <https://www.cis.upenn.edu/~bcpierce/papers/lenses-toplas-final.pdf> |
| `matsuda-icfp2007.pdf` | Matsuda, Hu, Nakano, Hamana & Takeichi, *Bidirectionalization Transformation Based on Automatic Derivation of View Complement Functions*, ICFP 2007. <https://zhenjiang888.github.io/pub/icfp07.pdf> |
| `bigul.pdf` | Ko, Zan & Hu, *BiGUL: A Formally Verified Core Language for Putback-Based Bidirectional Programming*, PEPM 2016. <https://zhenjiang888.github.io/pub/pepm16.pdf> |

All are freely available from their authors' pages or from open-access
proceedings.

Bancilhon & Spyratos's *Update Semantics of Relational Views* (TODS 1981) is
cited in §9.4 but is not here: it is behind the ACM paywall with no open copy.
Nothing is quoted from it — §9.4 attributes the constant-complement idea through
Matsuda et al., who state it, and says so.

**Not here, and not checkable.** RELATED.md §0 quotes a 1993 Master's thesis that
exists on paper only. Its quotations were transcribed by hand from page images,
so they are marked **[read]** but are deliberately *not* in `SOURCES` above: a
scan with no text layer would make `pdftotext` return nothing and every quotation
fail. If an OCR'd scan is ever made, adding it here would bring those quotations
under the same check as the rest.
