#!/usr/bin/env python3

import os
import subprocess
import argparse
from pathlib import Path
from duckpi.core import analyze, read_table, write_outputs, render_html, classify, number

# Executables resolve relative to the software, independently of the launch directory.
CURRENT_DIR = str(Path(__file__).resolve().parent)
KING_PATH = os.path.join(CURRENT_DIR, 'bin', 'king')
PLINK_PATH = os.path.join(CURRENT_DIR, 'bin', 'plink')

# Command-line argument parser
def parse_args():
    parser = argparse.ArgumentParser(description="Run KING and Plink for kinship analysis and reconstruct pedigree.")
    parser.add_argument('--kinship', action='store_true', help="Perform kinship inference using KING and Plink.")
    parser.add_argument('--id', type=str, help="Individual ID to focus in review reports, or target ID for PNG drawing.")
    parser.add_argument('--pedigree', type=str, help="Pedigree file for visualization.")
    parser.add_argument('--draw_pedigree', action='store_true', help="Draw pedigree graph.")
    # Pedigree reconstruction related parameters
    parser.add_argument('--file', type=str, help="Input data file path.")
    parser.add_argument('--extrainfo', type=str, help="File path containing generation and sex information.")
    # KING and PLINK analysis related parameters
    parser.add_argument('--make-king', action='store_true', help="Use KING for kinship inference.")
    parser.add_argument('--make-plink', action='store_true', help="Use Plink for kinship inference.")
    # Output path
    parser.add_argument('--out', type=str, help="Output file path.")
    parser.add_argument('--recorded', help='Recorded pedigree CSV/TSV: ChildID, FatherID, MotherID.')
    parser.add_argument('--review', help='Write a standalone interactive HTML review report.')
    parser.add_argument('--serve', action='store_true', help='Open the local browser review service.')
    parser.add_argument('--port', type=int, default=8765, help='Loopback review port (default: 8765).')
    parser.add_argument('--relation-column', help='Explicit upstream relationship-call column (PO/FS/2nd/MZ/UN).')
    parser.add_argument('--make-external', action='store_true', help='Organize precomputed external calls; requires --relation-column.')
    args = parser.parse_args()
    if sum([args.make_king, args.make_plink, args.make_external]) > 1:
        parser.error('Choose exactly one reconstruction method.')
    if args.kinship and (args.make_king or args.make_plink or args.make_external or args.serve):
        parser.error('Run kinship estimation and pedigree review as separate commands.')
    if args.kinship and (not args.file or not args.out):
        parser.error('--kinship requires --file and --out.')
    if args.make_king or args.make_plink or args.make_external:
        if not (args.file and args.extrainfo and args.out):
            parser.error('Reconstruction requires --file, --extrainfo and --out.')
    if args.make_external and not args.relation_column:
        parser.error('--make-external requires --relation-column.')
    if args.review and not (args.make_king or args.make_plink or args.make_external):
        parser.error('--review requires a reconstruction method.')
    if args.draw_pedigree and not (args.id and args.pedigree):
        parser.error('--draw_pedigree requires --id and --pedigree.')
    if not (args.kinship or args.make_king or args.make_plink or args.make_external or args.draw_pedigree or args.serve):
        parser.error('Select an action, for example --serve.')
    return args

# Function 1: Kinship inference
def run_king_and_plink(base_filename):
    os.makedirs('./data/King', exist_ok=True)  # Create KING output directory
    os.makedirs('./data/Plink', exist_ok=True)  # Create Plink output directory
    subprocess.run([KING_PATH, '--sexchr', '42', '-b', base_filename + '.bed',
                    '--kinship', '--prefix', './data/King/kinship1'], check=True)
    subprocess.run([PLINK_PATH, '--bfile', base_filename, '--genome', '--chr-set', '40',
                    '--out', './data/Plink/plink_1'], check=True)

# Merge KING and Plink results
def merge_results(kinship_file, genome_file, output_file):
    import pandas as pd
    kinship_df = pd.read_csv(kinship_file, sep=r'\s+', dtype=str, keep_default_na=False)
    genome_df = pd.read_csv(genome_file, sep=r'\s+', dtype=str, keep_default_na=False)
    kinship_df['Kinship'] = pd.to_numeric(kinship_df['Kinship'], errors='raise')
    for col in ['Z0', 'PI_HAT']:
        genome_df[col] = pd.to_numeric(genome_df[col], errors='raise')
    # Normalize unordered pairs before merging KING and PLINK.
    for frame, cols in [(kinship_df, ['ID1', 'ID2']), (genome_df, ['IID1', 'IID2'])]:
        frame[['ID1', 'ID2']] = pd.DataFrame(
            [sorted(pair) for pair in frame[cols].itertuples(index=False, name=None)], index=frame.index)
        if frame.duplicated(['ID1', 'ID2']).any():
            raise ValueError('Duplicate unordered pairs in estimator output; resolve duplicates before merging.')
    df_merge = kinship_df[['ID1', 'ID2', 'Kinship']].copy()
    df_merge['KING'] = df_merge['Kinship'] * 2
    df_merge = pd.merge(df_merge, genome_df[['ID1', 'ID2', 'Z0', 'PI_HAT']],
                        on=['ID1', 'ID2'], how='outer', validate='one_to_one')
    metrics = ['PI_HAT', 'KING']
    for metric in metrics:
        df_merge[f'{metric}_Relation'] = df_merge.apply(lambda row: infer_relationship(row, metric), axis=1)
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    df_merge.to_csv(output_file, index=False, sep='\t')

# Infer relationship label
def infer_relationship(row, metric):
    return classify(number(row[metric]), number(row['Z0'])) or ''

# Function 2: Pedigree reconstruction
def run_pedigree_construction(args):
    method = 'KING' if args.make_king else 'EXTERNAL' if args.make_external else 'PLINK'
    report = analyze(read_table(args.file), read_table(args.extrainfo), method=method,
                     recorded=read_table(args.recorded) if args.recorded else None,
                     relation_column=args.relation_column)
    if args.id:
        if args.id not in report['metadata']:
            raise ValueError(f'Review focus ID {args.id!r} is absent from individual metadata.')
        report['focusIndividual'] = args.id
    write_outputs(report, args.out)
    if args.review:
        Path(args.review).parent.mkdir(parents=True, exist_ok=True)
        Path(args.review).write_text(render_html(report), encoding='utf-8')
    print(f"Pedigree and evidence saved to {args.out}; {report['summary']}")
    return report

# Function 3: Draw pedigree graph
def build_and_draw_pedigree_graph(pedigree_df, extra_info, target_id, output_file='pedigree_picture'):
    import pandas as pd
    import networkx as nx
    from graphviz import Digraph
    G = nx.Graph()
    G.add_nodes_from(extra_info['ID'].dropna().astype(str))
    G.add_nodes_from(pedigree_df['ChildID'].dropna().astype(str))
    for _, row in pedigree_df.iterrows():
        child_id = row['ChildID']
        father_id = row['FatherID']
        mother_id = row['MotherID']
        if pd.notna(father_id) and pd.notna(child_id):
            G.add_edge(father_id, child_id)
        if pd.notna(mother_id) and pd.notna(child_id):
            G.add_edge(mother_id, child_id)

    if target_id not in G:
        raise ValueError(f'Target ID {target_id!r} not found.')
    subgraph_nodes = nx.node_connected_component(G, target_id)
    subgraph = G.subgraph(subgraph_nodes)

    generation_dict = extra_info.set_index('ID')['Generation'].to_dict()
    sex_dict = extra_info.set_index('ID')['Sex'].to_dict()

    dot = Digraph(format='png', engine='dot')
    dot.attr(dpi='300', rankdir='TB', style='solid', labelloc='t')

    generation_nodes = {}
    for node in subgraph.nodes:
        gen = generation_dict.get(node, 0)
        generation_nodes.setdefault(gen, []).append(node)

    for gen in sorted(generation_nodes.keys(), reverse=True):
        with dot.subgraph() as s:
            s.attr(rank='same')
            for node in generation_nodes[gen]:
                s.node(node)

    for node in subgraph.nodes:
        sex = sex_dict.get(node, 0)
        if node == target_id:
            shape = 'box' if sex == 1 else 'ellipse'
            dot.node(node, shape=shape, label=node, color='red')
        else:
            shape = 'box' if sex == 1 else 'ellipse'
            dot.node(node, shape=shape, label=node, color='black')

    for u, v in subgraph.edges:
        u_gen = generation_dict.get(u, 0)
        v_gen = generation_dict.get(v, 0)
        if u_gen < v_gen:
            dot.edge(u, v, dir='forward')
        else:
            dot.edge(v, u, dir='forward')
    dot.render(output_file)

if __name__ == "__main__":
    args = parse_args()
    if args.kinship:
        if args.file:
            run_king_and_plink(args.file)
            kinship_file = "./data/King/kinship1.kin0"
            genome_file = "./data/Plink/plink_1.genome"
            merge_results(kinship_file, genome_file, args.out)
        else:
            print("Please provide a valid file path using --file for kinship analysis.")

    report = None
    if args.make_king or args.make_plink or args.make_external:
        if args.file and args.extrainfo:
            report = run_pedigree_construction(args)
        else:
            print("Please provide both --file kinship analysis results and --extrainfo for pedigree reconstruction.")

    if args.draw_pedigree:
        import pandas as pd
        if args.id and args.pedigree:
            pedigree_df = pd.DataFrame(read_table(args.pedigree)).replace('', float('nan'))
            extra_info = pd.DataFrame(read_table(args.extrainfo)) if args.extrainfo else pd.DataFrame(columns=['ID', 'Sex', 'Generation'])
            for col in ['Sex', 'Generation']:
                extra_info[col] = pd.to_numeric(extra_info[col], errors='coerce')
            build_and_draw_pedigree_graph(pedigree_df, extra_info, args.id, output_file=f"pedigree_{args.id}")
        else:
            print("Please provide both --id and --pedigree for drawing the pedigree.")

    if args.serve:
        from duckpi.server import serve
        serve(args.port, report)
