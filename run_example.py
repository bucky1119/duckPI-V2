#!/usr/bin/env python3
"""Validate and rerun pedigree organization on the complete bundled dataset.

KING and PLINK executable estimation is not rerun. No farm records are fabricated.
"""
import argparse
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from duckpi.core import analyze, read_table, render_html, write_outputs
ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'example_data'


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def validate_inputs(pairs, individuals):
    ids = [r['ID'] for r in individuals]
    check(len(ids) == len(set(ids)) == 711, 'Expected 711 unique individual IDs.')
    check(all(re.fullmatch(r'NKX\d+X\d+X\d+', i) for i in ids), 'Unexpected individual ID format.')
    check(all(r['Sex'] in {'1', '2'} for r in individuals), 'Every example individual must have known sex.')
    check({r['Generation'] for r in individuals} == {'40', '41', '42'}, 'Expected generations 40, 41 and 42.')
    pair_ids, known = set(), set(ids)
    for row in pairs:
        a, b = row['ID1'], row['ID2']
        check(a in known and b in known and a != b, 'Pairwise IDs must be distinct and present in metadata.')
        pair_ids.add(tuple(sorted((a, b))))
        for field in ['Kinship', 'KING', 'Z0', 'PI_HAT']:
            check(math.isfinite(float(row[field])), f'Non-finite {field} in example input.')
        check(abs(float(row['KING']) - 2 * float(row['Kinship'])) < 1e-9, 'KING scale mismatch.')
    expected = len(ids) * (len(ids) - 1) // 2
    check(len(pairs) == len(pair_ids) == expected, 'Every unordered pair must occur exactly once.')
    fam = [line.split() for line in (DATA / 'IndepSNP1.fam').read_text().splitlines()]
    check(all(len(row) == 6 for row in fam), 'FAM rows must have six fields.')
    check(len(fam) == len(ids) and {row[1] for row in fam} == known, 'FAM IDs do not match metadata.')
    variants = sum(1 for _ in (DATA / 'IndepSNP1.bim').open())
    check(variants == 153117, 'Expected 153117 SNPs.')
    bed = DATA / 'IndepSNP1.bed'
    with bed.open('rb') as f:
        check(f.read(3) == b'\x6c\x1b\x01', 'BED must be a SNP-major PLINK file.')
    check(bed.stat().st_size == 3 + ((len(ids) + 3) // 4) * variants, 'BED dimensions do not match FAM/BIM.')
    upstream_counts = {}
    for name, first, second in [('king.kin0', 'ID1', 'ID2'), ('plink.genome', 'IID1', 'IID2')]:
        observed = set()
        with (DATA / 'upstream' / name).open() as f:
            header = f.readline().split()
            i, j, count = header.index(first), header.index(second), 0
            for line in f:
                row = line.split()
                if row:
                    count += 1
                    observed.add(tuple(sorted((row[i], row[j]))))
        check(count == expected and observed == pair_ids, f'Incomplete or duplicate pairs in upstream/{name}.')
        upstream_counts[name] = count
    return {'individuals': len(ids), 'sexCounts': dict(sorted(Counter(r['Sex'] for r in individuals).items())),
            'generationCounts': dict(sorted(Counter(r['Generation'] for r in individuals).items())),
            'unorderedPairs': len(pair_ids), 'expectedUnorderedPairs': expected, 'variants': variants,
            'genotypeSampleIDsMatchMetadata': True, 'bedDimensionsVerified': True, 'upstreamRows': upstream_counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=DATA / 'results', help='Output directory (default: example_data/results).')
    parser.add_argument('--focus', default='NKX06X40X26603', help='Individual to focus in review reports.')
    args = parser.parse_args()
    pairs = read_table(DATA / 'pairwise_relationships.tsv')
    individuals = read_table(DATA / 'individuals.tsv')
    validation = validate_inputs(pairs, individuals)
    check(args.focus in {r['ID'] for r in individuals}, 'Focus ID is absent from metadata.')
    args.out_dir.mkdir(parents=True, exist_ok=True)
    runs = {}
    for method in ['KING', 'PLINK']:
        report = analyze(pairs, individuals, method=method)
        report['focusIndividual'] = args.focus
        write_outputs(report, args.out_dir / f'{method.lower()}_pedigree.tsv')
        (args.out_dir / f'{method.lower()}_review.html').write_text(render_html(report), encoding='utf-8')
        runs[method] = {'summary': report['summary'], 'focusLinks': [
            {k: c[k] for k in ['parent', 'child', 'role', 'assignment', 'comparison', 'evidence']}
            for c in report['candidatePairs'] if args.focus in {c['parent'], c['child']}]}
        print(f'{method}: {json.dumps(report["summary"])}')
    names = ['pairwise_relationships.tsv', 'individuals.tsv', 'IndepSNP1.bed', 'IndepSNP1.bim', 'IndepSNP1.fam', 'upstream/king.kin0', 'upstream/plink.genome']
    checksums = {name: sha256(DATA / name) for name in names}
    result = {'softwareVersion': '2.0.1', 'generatedAt': datetime.now(timezone.utc).isoformat(),
              'validation': validation, 'focusIndividual': args.focus, 'runs': runs, 'inputSHA256': checksums,
              'scope': 'Pedigree organization rerun from supplied upstream results; estimator executables were not rerun.',
              'recordComparison': 'Not assessed: an independent recorded farm pedigree was not supplied.'}
    (args.out_dir / 'validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (args.out_dir / 'input_checksums.sha256').write_text(''.join(f'{value}  {name}\n' for name, value in checksums.items()), encoding='utf-8')
    print(f'Validated {validation["individuals"]} individuals, {validation["unorderedPairs"]} pairs and {validation["variants"]} SNPs.')
    print(f'Focused individual: {args.focus}')
    print(f'Reports saved to: {args.out_dir}')


if __name__ == '__main__':
    main()
