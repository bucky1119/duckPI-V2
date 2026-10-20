# Pedigree review user guide

## Start with the full example

Run `python3 run_example.py` from the software root. This validates every input and regenerates both method-specific reports. Open `example_data/results/king_review.html` to inspect the actual NKX family centered on offspring `NKX06X41X13476` and candidate mother `NKX06X40X26603`.

The first report row selected is a display convenience, not a decision between competing parents. All input individuals and eligible candidates remain accessible.

## Analyze your tables

Run `python3 duckPI.py --serve` and visit the printed `127.0.0.1` URL. Select relationship evidence, ID/sex/generation metadata and optionally an independent recorded pedigree. Choose KING, PLINK or External precomputed calls. For External, specify the call column. Click Analyze tables.

The interface processes the inputs on this computer. Standalone HTML reports can load existing review JSON but require the local server to analyze new CSV/TSV files. No estimator is executed by uploading tables.

## Inspect candidates and records

Search for a parent or offspring ID, or filter to competing parents or record discrepancies. Selecting a row updates the family, recorded-parent comparison and evidence inspector. Expand Raw pairwise evidence to see every source row and supplied coefficient. Use the Family individual selector to inspect any individual, including one with no candidate parents.

Solid links indicate unique inference. Orange dashed links indicate competing candidates or discrepancies with supplied records. Gray dotted links show recorded-only links when both individuals have metadata. Green and pale gray links reflect accepted and rejected manual annotations. Generation ordering follows actual metadata values. The default family scope shows parents and up to two ancestral steps. Select Parents and offspring to add direct offspring with their co-parents. Larger families keep readable node sizes and scroll horizontally. This view setting does not remove any candidates from the report.

Without an independent reference, links have `not_compared` status. A missing reference is not evidence that a parent was absent from the farm record. Likewise, a recorded link lacking selected-method support is not automatically a false record.

## Review and export

Select a candidate, choose Pending, Accept or Reject, and enter a reason. Accept/reject requires a note. The interface prevents accepting two candidates for the same offspring and parental role. Review decisions do not change the original inferred result.

Export review JSON before reloading, closing or starting another analysis. Import that JSON to restore decisions. The exports have distinct meanings:

- Inferred pedigree TSV: algorithmic assignments, ambiguity and all candidate IDs.
- Candidate evidence TSV: every eligible candidate, original evidence and review annotations.
- Reviewed pedigree TSV: only explicitly accepted parental roles, with review status.
- Review JSON: the complete analysis and manual decisions for reopening.
- Family SVG: the currently displayed family as a vector diagram.

Review decisions are human annotations, not independent parentage confirmation. Original breeding records are never overwritten.

## Reproducibility and optional components

`example_data/results/validation.json` records sample counts, complete-pair coverage, genotype dimensions, example focus and input hashes. The companion SHA-256 file can be checked from `example_data/` using the platform's checksum utility.

The standard-library example runner and browser workflow do not need pandas, NetworkX or Graphviz. Optional estimator-output merging requires pandas; optional PNG drawing needs pandas, NetworkX, the Graphviz Python package and the system `dot` executable. The supplied estimator archives target Linux x86_64. They are not portable executables for macOS or other CPU architectures.
