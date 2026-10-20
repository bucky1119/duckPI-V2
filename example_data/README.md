# Complete example dataset

This directory contains the supplied study example with original NKX identifiers. It is sufficient to rerun pedigree organization and inspect the associated genotypes and precomputed upstream estimator outputs.

## Inputs

| File | Description | Dimensions |
|---|---|---|
| `individuals.tsv` | Authoritative ID, sex and generation metadata | 711 rows |
| `pairwise_relationships.tsv` | Complete pairwise KING/PLINK evidence and relationship calls | 252,405 rows, one per unordered pair |
| `IndepSNP1.bed` | SNP-major PLINK binary genotypes | 711 individuals × 153,117 SNPs |
| `IndepSNP1.bim` | Six-field SNP annotations | 153,117 rows |
| `IndepSNP1.fam` | Six-field genotype sample IDs in BED sample order | 711 rows |
| `upstream/king.kin0` | Original precomputed KING pairwise output | 252,405 rows |
| `upstream/plink.genome` | Original precomputed PLINK pairwise output | 252,405 rows |

`individuals.tsv` uses sex `1` for male and `2` for female: 212 males and 499 females. Generation 40 contains 154 individuals, generation 41 contains 338, and generation 42 contains 219. There are no missing sex/generation entries. Metadata IDs match the genotype sample IDs exactly; the metadata need not be in FAM order because analysis joins by ID.

The original FAM has unknown sex and parent fields. Use `individuals.tsv` for sex and generation. FAM's missing parents are not an independently recorded farm pedigree. No independent farm pedigree is supplied here, so the example deliberately does not assert seven record-external links or recovery of 895/897 recorded links.

## Reproduction

From the software root:

```bash
python3 run_example.py
```

The runner checks all unordered pairs, uniqueness, metadata coverage, genotype dimensions, original upstream pair coverage and SHA-256 hashes. It writes `results/` with separate KING and PLINK reports, complete inferred pedigree tables, candidate evidence, issues, record checks, review JSON, `validation.json` and `input_checksums.sha256`.

To avoid replacing the included example outputs:

```bash
python3 run_example.py --out-dir results/reproduced_example
```

The default report focus is `NKX06X40X26603`, a generation-40 female. Its candidate offspring include `NKX06X41X13476`, `NKX06X41X13483` and `NKX06X41X15666`. The report initially displays the first of these families; all 902 candidates remain available. Both selected methods produce 902 eligible PO candidates for the supplied input calls, without competing candidates for a parental role. This dataset does not demonstrate every edge case; separate synthetic regression fixtures cover ambiguity and single-parent behavior.

Open `results/king_review.html` or `results/plink_review.html` in a desktop browser. These standalone reports contain actual example results and require no server or internet connection. Open exported review JSON to restore manual notes. To analyze new CSV/TSV tables, start `python3 duckPI.py --serve`.

## Provenance and interpretation

The canonical pair table is the original tab-separated `df_merge2.csv` with an explicit `.tsv` filename. The metadata are the original tab-separated `extra_info.csv` renamed `individuals.tsv`. Data rows and original identifiers were preserved. Input hashes are included with the outputs. The genotype triplet is unchanged. KING's raw `Kinship` is distinct from the `KING = 2 × Kinship` column.

The runner uses supplied precomputed outputs. It does not execute KING or PLINK, redo genotype filtering, or repeat the five-estimator study comparison. Optional instructions for rerunning the two executable estimators are in the main README. Original relationship calls and measured coefficients are used without substituting theoretical values.
