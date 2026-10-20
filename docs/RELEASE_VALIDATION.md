# Release validation

Version: 2.0.1

Validation performed on 20 October 2026 with Python 3.14 and Node.js 24. The public review workflow requires Python 3.9 or later; this run does not establish testing across every supported interpreter or operating system.

## Complete example run

`python3 -S run_example.py` completed without third-party site packages. The runner validated all 711 IDs, known sex and generation entries, 252,405 unique unordered pairs, complete raw KING/PLINK pair coverage, the SNP-major BED header and byte dimensions, and the 711-sample / 153,117-SNP FAM/BIM dimensions. Every genotype sample ID has metadata.

Sex counts: 212 male, 499 female. Generation counts: 154 in generation 40, 338 in generation 41, 219 in generation 42.

KING-call and PLINK-call organization each produced 902 eligible PO candidates, zero ambiguous parental roles and zero excluded PO pairs for these supplied inputs. Each generated pedigree contains all 711 individuals. The report focus is NKX06X40X26603, with initial family NKX06X41X13476. Exact results and input hashes are recorded in `example_data/results/validation.json`.

No independent recorded farm pedigree was supplied. Record support, record-external links and pedigree correction accuracy are not assessed. The genotype-estimation executables were not rerun. The example reproduces downstream organization from supplied upstream results, not genotype filtering or the five-estimator benchmark.

## Automated checks

- All 19 Python core, legacy-result merge and loopback API tests passed.
- JavaScript UI unit checks passed for candidate filters, required decision notes, competing-parent acceptance prevention, separate inferred/reviewed exports, JSON review roundtrip, TSV quoting, empty results, real NKX initial focus and readable full-family scrolling.
- The embedded UI script passed JavaScript syntax validation.

## Browser checks

The full pairwise table and metadata were imported through the local interface and analyzed successfully. The result showed 711 individuals and 902 KING candidates. Searching NKX06X40X26603 returned three candidate links. Selecting its relationship to NKX06X41X13476 updated the actual family and evidence inspector. The rendered page's text contained no Chinese characters, including file-selection controls on a non-English host OS. Screenshots under `docs/` show actual supplied NKX data.

Browser download handling and optional Graphviz PNG rendering were not independently revalidated in this release. Export content and review persistence semantics are covered by automated logic tests. Manual review notes must be exported as JSON before closing or reloading the page.

## Distribution checks

The release archive includes the complete example inputs and generated reports. Author-facing Chinese explanations and historical mixed-language assets are kept outside the software distribution. Text and filename audits exclude Chinese characters from distributed text files and paths. Binary genotype and vendor executable archives are retained as supplied. The release manifest records SHA-256 checksums of distributed files.
