# Changes

## 2.0.0

- Integrate the supplied pedigree-review interface design with the shared Python analysis engine, replacing fixed seven-case browser data with actual input results.
- Add loopback browser analysis, standalone offline HTML and portable review JSON.
- Preserve each inferred parental role independently; retain founders, single-parent and isolated individuals.
- Keep every competing parent and raw evidence row; mark ambiguity instead of selecting by traversal order.
- Add recorded-pedigree comparisons, unsupported recorded-link checks, and explicit PO exclusion reasons.
- Add candidate filtering, family selection, manual review notes/decisions, and separate inferred versus manually accepted pedigree exports.
- Support upstream external relationship-call columns without claiming built-in GRM/Ukin/Kindred execution.
- Preserve v1 KING/PLINK and optional NetworkX/Graphviz commands; normalize pair orientation during estimator merging, remove shell interpolation, and resolve binaries relative to the script.
- Add synthetic regression fixtures, a generated full-data example and automated core/API checks.

## 2.0.1

- Prepare a fully English software distribution, including documentation and all public data headers.
- Provide one canonical full example: 711 NKX individuals with complete sex and generation metadata, all 252,405 pairwise relationships, the complete 153,117-SNP genotype triplet, and both original upstream estimator outputs.
- Add a standard-library example runner that validates completeness, genotype dimensions, upstream coverage and input hashes before rerunning KING-call and PLINK-call pedigree organization.
- Include method-specific offline reports and validation records, focused on NKX06X40X26603 and its candidate offspring.
- Move synthetic regression examples into tests/fixtures/synthetic; use real study identifiers in the public example.
- Support initial report focus through --id and use English page file controls independently of the host OS language.
