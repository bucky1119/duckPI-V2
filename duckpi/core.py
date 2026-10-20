"""Evidence-preserving pedigree organization, without global parentage optimization.

Only a unique eligible candidate per parental role is automatically assigned.
Raw evidence is retained; assignments are inferences, not confirmed corrections.
"""
import csv
import io
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

MISSING = {'', '0', '-9', 'NA', 'N/A', 'nan', 'None', '.'}


def read_table(source):
    text = source.read() if hasattr(source, 'read') else Path(source).read_text(encoding='utf-8-sig')
    if isinstance(text, bytes):
        text = text.decode('utf-8-sig')
    text = text.lstrip('\ufeff')
    first = text.splitlines()[0] if text.strip() else ''
    if not first:
        raise ValueError('Input table is empty.')
    delimiter = '\t' if '\t' in first else ','
    rows = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))
    if not rows:
        raise ValueError('Input table must have a header and at least one data row.')
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError('Inconsistent number of fields in input table.')
    return [{k.strip(): v.strip() for k, v in row.items() if k and not k.startswith('Unnamed:')} for row in rows]


def require(rows, columns, label):
    if not rows:
        raise ValueError(f'{label}: table has no data rows.')
    absent = set(columns) - set(rows[0])
    if absent:
        raise ValueError(f'{label}: missing columns {", ".join(sorted(absent))}.')


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def classify(value, z0):
    """Legacy duckPI relationship thresholds on the KING=2*Kinship / PI_HAT scale."""
    if value is None or z0 is None:
        return None
    if value >= 2 ** -.5 and z0 < .1:
        return 'MZ'
    if 2 ** -1.5 < value <= 2 ** -.5:
        if z0 < .1:
            return 'PO'
        if .1 <= z0 <= .365:
            return 'FS'
    if 2 ** -2.5 < value <= 2 ** -1.5 and .365 <= z0 <= 1 - 2 ** -1.5:
        return '2nd'
    return 'UN'


def analyze(pairs, metadata, method='KING', recorded=None, relation_column=None):
    require(pairs, ['ID1', 'ID2'], 'Pairwise relationships')
    require(metadata, ['ID', 'Sex', 'Generation'], 'Individual metadata')
    if method not in {'KING', 'PLINK', 'EXTERNAL'}:
        raise ValueError('Method must be KING, PLINK or EXTERNAL.')
    column = relation_column or ('KING_Relation' if method == 'KING' else 'PI_HAT_Relation')
    metric = 'KING' if method == 'KING' else 'PI_HAT'
    if method == 'EXTERNAL' and not relation_column:
        raise ValueError('EXTERNAL requires --relation-column containing explicit relationship labels.')
    if column not in pairs[0] and (method == 'EXTERNAL' or 'Z0' not in pairs[0] or
            (metric not in pairs[0] and not (method == 'KING' and 'Kinship' in pairs[0]))):
        raise ValueError(f'Provide {column}, or {metric} (KING also accepts Kinship) and Z0.')
    people = {}
    for row in metadata:
        iid = row['ID']
        if not iid or iid in people:
            raise ValueError(f'Empty or duplicate metadata ID: {iid!r}.')
        gen = number(row['Generation'])
        if gen is None:
            raise ValueError(f'Generation must be finite numeric for {iid}.')
        sex = {'1': 'Male', '2': 'Female', '0': 'Unknown', '-9': 'Unknown', '': 'Unknown',
               'male': 'Male', 'female': 'Female', 'm': 'Male', 'f': 'Female', 'unknown': 'Unknown'}.get(row['Sex'].lower())
        if sex is None:
            raise ValueError(f'Invalid Sex for {iid}; use 1, 2 or 0 (unknown).')
        people[iid] = {'sex': sex, 'generation': gen}
    records = {}
    if recorded is not None:
        require(recorded, ['ChildID', 'FatherID', 'MotherID'], 'Recorded pedigree')
        for row in recorded:
            child = row['ChildID']
            if not child or child in records:
                raise ValueError(f'Empty or duplicate recorded ChildID: {child!r}.')
            records[child] = {role: None if row[role] in MISSING else row[role] for role in ['FatherID', 'MotherID']}
    # Group unordered pairs so orientation and input order cannot decide parentage.
    grouped = defaultdict(list)
    warnings = []
    for line, row in enumerate(pairs, 2):
        a, b = row['ID1'], row['ID2']
        if not a or not b:
            raise ValueError(f'Empty pair ID at source row {line}.')
        value = number(row.get(metric))
        if method == 'KING' and value is None:
            kinship = number(row.get('Kinship'))
            value = kinship * 2 if kinship is not None else None
        call = row.get(column, '').upper()
        if not call:
            call = classify(value, number(row.get('Z0'))) if method != 'EXTERNAL' else None
        if call not in {None, 'MZ', 'PO', 'FS', '2ND', '2nd', 'UN'}:
            raise ValueError(f'Unknown relationship label {call!r} at source row {line}.')
        grouped[tuple(sorted((a, b)))].append({'sourceRow': line, 'call': call, 'raw': row})
    candidates = []
    issues = []
    for (a, b), evidence in sorted(grouped.items()):
        calls = {e['call'] for e in evidence}
        if 'PO' not in calls:
            continue
        reason = None
        parent, child = a, b
        if a == b:
            reason = 'self_pair'
        elif a not in people or b not in people:
            reason = 'missing_metadata'
        elif people[a]['generation'] == people[b]['generation']:
            reason = 'same_generation'
        else:
            parent, child = sorted((a, b), key=lambda i: people[i]['generation'])
        role = {'Male': 'FatherID', 'Female': 'MotherID'}.get(people.get(parent, {}).get('sex'))
        if reason is None and role is None:
            reason = 'unknown_parent_sex'
        if reason is None and calls != {'PO'}:
            reason = 'conflicting_duplicate_calls'
        if reason is not None:
            issues.append({'ID1': a, 'ID2': b, 'reason': reason, 'evidence': evidence})
            continue
        old = records.get(child)
        if recorded is None:
            comparison = 'not_compared'
        elif old is None:
            comparison = 'child_not_recorded'
        elif old[role] == parent:
            comparison = 'recorded_match'
        elif old[role] is None:
            comparison = 'unrecorded_role'
        else:
            comparison = 'recorded_conflict'
        candidates.append({'parent': parent, 'child': child, 'role': role,
                           'comparison': comparison, 'recordedParent': old[role] if old else None,
                           'evidence': evidence, 'method': method})
    by_role = defaultdict(list)
    for c in candidates:
        by_role[(c['child'], c['role'])].append(c)
    pedigree = []
    for child in sorted(people, key=lambda i: (people[i]['generation'], i)):
        row = {'ChildID': child, 'FatherID': None, 'MotherID': None}
        for role, short in [('FatherID', 'Father'), ('MotherID', 'Mother')]:
            options = by_role[(child, role)]
            status = 'missing' if not options else 'unique_inferred' if len(options) == 1 else 'ambiguous'
            row[short + 'Status'] = status
            row[short + 'Candidates'] = [c['parent'] for c in options]
            if len(options) == 1:
                row[role] = options[0]['parent']
            for c in options:
                c['assignment'] = status
        pedigree.append(row)
    for i, c in enumerate(candidates, 1):
        c['number'] = i
    # Check recorded links absent from the eligible selected-method candidate set.
    supported = {(c['child'], c['role'], c['parent']) for c in candidates}
    record_checks = []
    for child, record in sorted(records.items()):
        for role, parent in record.items():
            if parent is not None:
                record_checks.append({'child': child, 'parent': parent, 'role': role,
                                      'status': 'supported' if (child, role, parent) in supported else 'not_supported'})
    if any(c['comparison'] == 'recorded_conflict' for c in candidates):
        warnings.append('Genomic candidates conflict with recorded parentage; records were not overwritten.')
    if issues:
        warnings.append(f'{len(issues)} PO pairs excluded from assignment; see issues and raw evidence.')
    return {'schemaVersion': 1, 'softwareVersion': '2.0.1',
            'generatedAt': datetime.now(timezone.utc).isoformat(), 'method': method,
            'relationColumn': column, 'metadata': people, 'candidatePairs': candidates,
            'pedigree': pedigree, 'recordedPedigree': records, 'recordChecks': record_checks,
            'issues': issues, 'warnings': warnings,
            'summary': {'individuals': len(people), 'generations': len({p['generation'] for p in people.values()}),
                        'candidateLinks': len(candidates),
                        'ambiguousRoles': sum(r[s] == 'ambiguous' for r in pedigree for s in ['FatherStatus', 'MotherStatus']),
                        'recordedLinks': len(record_checks),
                        'supportedRecordedLinks': sum(r['status'] == 'supported' for r in record_checks),
                        'additionalCandidates': sum(c['comparison'] in {'child_not_recorded', 'unrecorded_role', 'recorded_conflict'} for c in candidates),
                        'inputPairs': len(pairs), 'excludedPOPairs': len(issues)}}


def write_tsv(path, rows, fields):
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter='\t', extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                             for k, v in row.items()})


def write_outputs(report, out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(out, report['pedigree'], ['ChildID', 'FatherID', 'MotherID', 'FatherStatus', 'MotherStatus', 'FatherCandidates', 'MotherCandidates'])
    write_tsv(str(out) + '.candidates.tsv', report['candidatePairs'],
              ['number', 'parent', 'child', 'role', 'method', 'assignment', 'comparison', 'recordedParent', 'evidence'])
    write_tsv(str(out) + '.issues.tsv', report['issues'], ['ID1', 'ID2', 'reason', 'evidence'])
    write_tsv(str(out) + '.record_checks.tsv', report['recordChecks'], ['child', 'parent', 'role', 'status'])
    Path(str(out) + '.review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def render_html(report=None):
    template = (Path(__file__).resolve().parent.parent / 'web' / 'index.html').read_text(encoding='utf-8')
    payload = json.dumps(report, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return template.replace('/*DUCKPI_PAYLOAD*/null', payload)
