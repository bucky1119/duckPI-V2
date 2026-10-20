import copy
import io
import json
import random
import tempfile
import unittest
from pathlib import Path
from duckpi.core import analyze, read_table, render_html, write_outputs, classify
DEMO = Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'synthetic'

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.pairs=read_table(DEMO/'pairs.tsv');self.meta=read_table(DEMO/'metadata.tsv');self.records=read_table(DEMO/'recorded.tsv')
    def report(self,**kw): return analyze(self.pairs,self.meta,recorded=self.records,**kw)
    def test_single_parents_and_isolated(self):
        r={r['ChildID']:r for r in self.report()['pedigree']}
        self.assertEqual(r['OFFSPRING_1']['FatherID'],'SIRE_A');self.assertIsNone(r['OFFSPRING_1']['MotherID'])
        self.assertEqual(r['OFFSPRING_3']['MotherID'],'DAM_B');self.assertIsNone(r['OFFSPRING_3']['FatherID'])
        self.assertEqual(r['ISOLATED']['FatherStatus'],'missing');self.assertIn('SIRE_A',r)
    def test_ambiguity_preserves_evidence(self):
        r=self.report();row=next(x for x in r['pedigree'] if x['ChildID']=='OFFSPRING_2')
        self.assertIsNone(row['FatherID']);self.assertEqual(row['FatherCandidates'],['SIRE_A','SIRE_B'])
        self.assertEqual(row['FatherStatus'],'ambiguous');self.assertEqual(row['MotherID'],'DAM_A')
        c=next(c for c in r['candidatePairs'] if c['parent']=='SIRE_B')
        self.assertEqual(c['comparison'],'recorded_conflict');self.assertEqual(c['evidence'][0]['raw']['Kinship'],'0.24')
    def test_order_and_orientation_independence(self):
        baseline=self.report()['pedigree'];random.Random(1).shuffle(self.pairs)
        for r in self.pairs:r['ID1'],r['ID2']=r['ID2'],r['ID1']
        self.assertEqual(self.report()['pedigree'],baseline)
    def test_duplicate_rows_preserve_evidence(self):
        self.pairs.append(copy.deepcopy(self.pairs[0]));r=self.report()
        c=next(c for c in r['candidatePairs'] if c['child']=='OFFSPRING_1')
        self.assertEqual(len(c['evidence']),2);self.assertEqual(c['assignment'],'unique_inferred')
    def test_conflicting_duplicates(self):
        self.pairs.append(dict(self.pairs[0],KING_Relation='FS'));r=self.report()
        self.assertEqual(r['issues'][0]['reason'],'conflicting_duplicate_calls')
        self.assertFalse(any(c['child']=='OFFSPRING_1' for c in r['candidatePairs']))
    def test_exclusions(self):
        self.pairs.extend({'ID1':a,'ID2':b,'KING_Relation':'PO'} for a,b in [('ABSENT','OFFSPRING_1'),('ISOLATED','OFFSPRING_1'),('SIRE_A','SIRE_A'),('UNKNOWN','OFFSPRING_1')])
        self.meta.append({'ID':'UNKNOWN','Sex':'0','Generation':'0'})
        self.assertEqual({r['reason'] for r in self.report()['issues']},{'missing_metadata','same_generation','self_pair','unknown_parent_sex'})
    def test_records_unchanged_and_unsupported(self):
        r=self.report();self.assertEqual(r['recordedPedigree']['OFFSPRING_2']['MotherID'],'DAM_B')
        self.assertIn({'child':'OFFSPRING_2','parent':'DAM_B','role':'MotherID','status':'not_supported'},r['recordChecks'])
        self.assertEqual(r['summary']['supportedRecordedLinks'],2)
    def test_no_record_no_additional_claim(self):
        r=analyze(self.pairs,self.meta);self.assertTrue(all(c['comparison']=='not_compared' for c in r['candidatePairs']))
        self.assertEqual(r['summary']['additionalCandidates'],0)
    def test_external_calls(self):
        with self.assertRaises(ValueError):self.report(method='EXTERNAL')
        self.assertEqual(len(self.report(method='EXTERNAL',relation_column='KING_Relation')['candidatePairs']),5)
    def test_ids_and_delimiters(self):
        rows=read_table(io.StringIO('ID,Sex,Generation\n001,1,1\nNA,2,2\n'))
        r=analyze([{'ID1':'001','ID2':'NA','KING_Relation':'PO'}],rows)
        self.assertEqual(r['pedigree'][1]['FatherID'],'001');self.assertIn('NA',r['metadata'])
    def test_invalid_inputs(self):
        for row in [{'ID':'SIRE_A','Sex':'1','Generation':'1'},{'ID':'BAD','Sex':'9','Generation':'1'},{'ID':'BAD','Sex':'1','Generation':'nan'}]:
            with self.assertRaises(ValueError):analyze(self.pairs,self.meta+[row])
        with self.assertRaises(ValueError):read_table(io.StringIO('A,B\n1,2,3\n'))
    def test_derive_numeric_calls(self):
        for row in self.pairs:del row['KING_Relation'];del row['KING']
        self.assertEqual(len(self.report()['candidatePairs']),5)
        self.assertEqual(len(self.report(method='PLINK')['candidatePairs']),5)
        self.assertIsNone(classify(None,.01))
    def test_exports_and_html_escape(self):
        r=self.report();r['warnings'].append('</script><script>alert(1)</script>');html=render_html(r)
        self.assertNotIn('</script><script>alert(1)',html);self.assertIn('\\u003c/script',html)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'pedigree.tsv';write_outputs(r,out)
            self.assertEqual(len(list(Path(d).iterdir())),5)
            self.assertEqual(json.loads(Path(str(out)+'.review.json').read_text()),r)
            self.assertEqual(read_table(out)[0]['ChildID'],'DAM_A')
if __name__=='__main__':unittest.main()
