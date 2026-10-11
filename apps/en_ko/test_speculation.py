import unittest
from speculation import Speculation
from caption_logic import CaptionQueue
class SpecTests(unittest.TestCase):
 def candidate(self,s,text='연구 결과는 40억 원입니다',uid='1',now=0):
  s.observe(uid,text[:-1],'',('ctx',),now)
  s.observe(uid,text,'',('ctx',),now+.1)
  return s.ready(now+.41)
 def test_stability_and_limit(self):
  s=Speculation();c=self.candidate(s);self.assertIsNotNone(c)
  s.begin(c);self.assertIsNone(s.ready(2));s.finish(c['key'],(True,'forty'))
  c=self.candidate(s,'연구 결과는 30억 원입니다',now=1);s.begin(c);s.finish(c['key'],(True,'thirty'))
  self.assertIsNone(self.candidate(s,'연구 결과는 20억 원입니다',now=2));self.assertEqual(s.calls,2)
 def test_exact_only_and_context(self):
  s=Speculation();c=self.candidate(s);s.begin(c);s.finish(c['key'],(True,'four billion'))
  self.assertIsNone(s.final('1','연구 결과는 30억 원입니다',('ctx',)))
  self.assertIsNone(s.final('1','연구 결과는 40억 원입니다',('changed',)))
  self.assertIsNotNone(s.final('1','연구 결과는 40억 원입니다.',('ctx',)))
 def test_failed_and_reset_no_reuse(self):
  s=Speculation();c=self.candidate(s);s.begin(c);s.finish(c['key'],(False,''))
  self.assertIsNone(s.final('1',c['text'],('ctx',)))
  s.reset();s.finish(c['key'],(True,'stale'));self.assertEqual(s.records,{})
 def test_final_prevents_new_calls_and_inflight_listener(self):
  s=Speculation();c=self.candidate(s);s.begin(c)
  r=s.final('1',c['text'],('ctx',));got=[];r['listeners'].append(got.append)
  s.finish(c['key'],(True,'ready'));self.assertEqual(got,[(True,'ready')])
  s.observe('1',c['text'],'',('ctx',),5);self.assertIsNone(s.ready(6))
 def test_single_call_inflight(self):
  s=Speculation();s.begin(self.candidate(s));self.assertIsNone(self.candidate(s,uid='2'))
 def test_fast_rollup_keeps_order(self):
  q=CaptionQueue();q.accept('1','one');q.take(0,1.5,True,True);q.accept('2','two')
  self.assertIsNone(q.take(.64,1.5,True,True));self.assertEqual(q.take(.65,1.5,True,True),'two')

class ControllerSpecTests(unittest.TestCase):
 def test_inflight_exact_match_delivers_once_and_reset_blocks_stale(self):
  from test_app import APP
  from app import MainWindow
  w=MainWindow(warmup=False);c=w.context;c.timer.stop();c.active=False;c.text='';c.use_documents.setChecked(False);c.use_translation.setChecked(True)
  source='학명은 생물을 명확하게 지칭합니다';ctx=c.context_key();c.speculation.observe('1',source[:-1],'baseline',ctx,0);c.speculation.observe('1',source,'baseline',ctx,.1)
  candidate=c.speculation.ready(.41);record=c.speculation.begin(candidate);got=[]
  c.translate('1','baseline',source,lambda *args:got.append(args),utterance='1')
  self.assertEqual(got,[]);self.assertEqual(len(c.jobs),0)
  c.speculation.finish(candidate['key'],(True,'Scientific names identify organisms precisely.'))
  self.assertEqual(len(got),1);self.assertTrue(c.metrics[0]['speculative']);c.flush();self.assertEqual(len(got),1)
  c.reset();ctx=c.context_key();c.speculation.observe('2',source[:-1],'baseline',ctx,0);c.speculation.observe('2',source,'baseline',ctx,.1);candidate=c.speculation.ready(.41);c.speculation.begin(candidate)
  c.translate('2','baseline',source,lambda *args:got.append(args),utterance='2');c.reset();c.speculation.finish(candidate['key'],(True,'stale'))
  self.assertEqual(len(got),1);w.close()
