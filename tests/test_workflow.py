import importlib.util
from pathlib import Path
import tempfile
import unittest
import json
P=Path(__file__).resolve().parents[1]/'plugins/competition-docs-core/skills/competition-docs/scripts/workflow.py'
spec=importlib.util.spec_from_file_location('workflow',P); w=importlib.util.module_from_spec(spec); spec.loader.exec_module(w)

class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve(); self.s=w.init(self.root,['docx'])
        (self.root/'work/evidence.txt').write_text('review')
    def done(self,n,**kw): w.set_state(self.root,self.s,n,'done',artifacts=['work/evidence.txt'],**kw)
    def chain(self):
        for n in ['requirements','sources','research','plan','content','docx']: self.done(n)
    def test_watch_changes_invalidate_downstream(self):
        (self.root/'input.txt').write_text('one')
        self.done('requirements',watch=['input.txt']); self.done('sources')
        (self.root/'input.txt').write_text('two'); w.refresh(self.root,self.s)
        self.assertEqual(self.s['nodes']['sources']['status'],'stale')
        self.assertEqual(self.s['nodes']['docx']['status'],'stale')
    def test_missing_artifact_rejected(self):
        with self.assertRaises(ValueError): w.set_state(self.root,self.s,'requirements','done',artifacts=['absent'])
    def test_no_confirmation_bypass(self):
        w.set_state(self.root,self.s,'requirements','waiting',reason='need choice')
        with self.assertRaises(ValueError): self.done('sources',partial=True)
    def test_skip_propagates_partial(self):
        self.done('requirements'); w.set_state(self.root,self.s,'sources','skipped',reason='unreachable')
        self.done('research',partial=True)
        with self.assertRaises(ValueError): self.done('plan')
        self.done('plan',partial=True)
        self.assertEqual(w.summary(self.root,self.s)['submission_status'],'partial')
    def test_qa_requires_real_records(self):
        self.chain()
        with self.assertRaises(ValueError): self.done('qa')
    def test_qa_and_output_changes(self):
        self.chain()
        q={'checks':{k:{'status':'passed','evidence':'work/evidence.txt'} for k in w.CHECKS}}
        (self.root/'qa.json').write_text(json.dumps(q)); self.done('qa')
        self.assertEqual(w.summary(self.root,self.s)['submission_status'],'ready')
        (self.root/'work/evidence.txt').write_text('changed')
        self.assertEqual(w.summary(self.root,self.s)['submission_status'],'partial')
        self.assertEqual(self.s['nodes']['qa']['status'],'stale')
    def test_cycle_rejected(self):
        self.s['nodes']['requirements']['deps']=['content']
        with self.assertRaises(ValueError): w.acyclic(self.s['nodes'])
    def test_source_and_outputs_path_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'outside'; p.write_text('read only')
            w.keypath(self.root,str(p))
            with self.assertRaises(ValueError): w.keypath(self.root,str(p),artifact=True)
    def test_init_never_overwrites(self):
        with self.assertRaises(ValueError): w.init(self.root,['pdf'])
    def test_no_formats_is_error(self):
        with self.assertRaises(ValueError): w.init(self.root/'other',[])
if __name__=='__main__': unittest.main()
