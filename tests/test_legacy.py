import importlib.util
import tempfile
import unittest
from pathlib import Path
from duckpi.core import read_table

spec=importlib.util.spec_from_file_location('duckpi_cli',Path(__file__).resolve().parents[1]/'duckPI.py')
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)

class LegacyTests(unittest.TestCase):
    def test_pair_merge_normalizes_orientation_preserves_ids(self):
        try: import pandas
        except ImportError: self.skipTest('Optional pandas dependency not installed')
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);king=d/'king';plink=d/'plink';out=d/'merged.tsv'
            king.write_text('ID1 ID2 Kinship\n001 NA 0.25\n002 003 0.24\n')
            plink.write_text('IID1 IID2 Z0 PI_HAT\nNA 001 0.01 0.5\n003 002 0.01 0.48\n')
            cli.merge_results(king,plink,out)
            rows=read_table(out);self.assertEqual(rows[0]['ID1'],'001');self.assertEqual(rows[0]['ID2'],'NA')
            self.assertEqual([r['KING_Relation'] for r in rows],['PO','PO'])
            self.assertEqual([r['PI_HAT_Relation'] for r in rows],['PO','PO'])
    def test_duplicate_estimator_rows_rejected(self):
        try: import pandas
        except ImportError: self.skipTest('Optional pandas dependency not installed')
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);king=d/'king';plink=d/'plink'
            king.write_text('ID1 ID2 Kinship\nA B 0.25\nB A 0.25\n');plink.write_text('IID1 IID2 Z0 PI_HAT\nA B 0.01 0.5\n')
            with self.assertRaises(ValueError):cli.merge_results(king,plink,d/'out')
if __name__=='__main__':unittest.main()
