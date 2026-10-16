"""Regressions when no event reference and no screen analysis are available."""
import unittest
from unittest.mock import patch
from test_app import APP
from app import MainWindow

class GenericTranslationTests(unittest.TestCase):
    def setUp(self):
        self.window=MainWindow(warmup=False)
        self.context=self.window.context
        self.context.use_correction.setChecked(False)
        self.context.timer.stop();self.context.dispatch.stop()
        self.context.active=False;self.context.text='';self.context.slide_image=b''
        self.context.use_documents.setChecked(False)
        self.context.use_translation.setChecked(True)
        self.context.use_speculation.setChecked(True)
        self.calls=[];self.output=[]
        def job(fn,callback):
            token=object();self.context.jobs.add(token)
            self.calls.append((token,fn,callback))
            return token
        self.context.run_job=job

    def tearDown(self):
        self.context.jobs.clear();self.window.close()

    def deliver(self,*args):self.output.append(args)

    def finish(self,index=0,text='The experiment produced consistent results.'):
        token,fn,callback=self.calls[index]
        callback((True,text));self.context.jobs.discard(token);self.context.flush()

    def test_baseline_is_corrected_without_references(self):
        c=self.context
        c.translate_unit('1','The result is constant.','실험 결과가 일관되게 나왔습니다.',self.deliver)
        self.assertEqual(len(self.calls),1);self.assertEqual(self.output,[])
        with patch.object(c,'request_translation',return_value='Corrected') as request:
            self.assertEqual(self.calls[0][1](),'Corrected')
            args=request.call_args.args[0]
            self.assertEqual(args[5],'');self.assertEqual(args[7],'');self.assertEqual(args[-1],b'')
        self.finish()
        self.assertEqual(self.output[0][1],'The experiment produced consistent results.')
        self.assertTrue(c.metrics[0]['context_used'])

    def test_disabled_correction_uses_baseline(self):
        self.context.use_translation.setChecked(False)
        self.context.translate_unit('1','The results are consistent.','실험 결과가 일관되게 나왔습니다.',self.deliver)
        self.assertEqual(self.calls,[]);self.assertEqual(self.output[0][1],'The results are consistent.')

    def test_english_speech_is_direct(self):
        self.context.translate_unit('1','The results are consistent.','',self.deliver)
        self.assertEqual(self.calls,[]);self.assertEqual(self.output[0][1],'The results are consistent.')

    def test_korean_without_baseline_still_requires_english(self):
        self.context.use_translation.setChecked(False)
        self.context.translate_unit('1','','실험 결과가 일관되게 나왔습니다.',self.deliver)
        self.assertEqual(len(self.calls),1);self.finish()
        self.assertEqual(self.output[0][1],'The experiment produced consistent results.')

    def test_screen_off_speculation_is_reused_once(self):
        c=self.context;source='실험 결과가 일관되게 나왔습니다';key=c.context_key()
        c.speculation.observe('1',source[:-1],'baseline',key,0)
        c.speculation.observe('1',source,'baseline',key,.1)
        with patch('context_ui.time.monotonic',return_value=.41):c.try_speculation()
        self.assertEqual(len(self.calls),1)
        c.translate_unit('1','baseline',source,self.deliver,utterance='1')
        self.assertEqual(len(self.calls),1);self.finish()
        self.assertEqual(len(self.output),1);self.assertTrue(c.metrics[0]['speculative'])

    def test_busy_workers_queue_and_deliver_in_order(self):
        c=self.context;busy=[object() for _ in range(3)];c.jobs.update(busy)
        c.translate_unit('1','','실험 결과가 일관되게 나왔습니다.',self.deliver)
        c.translate_unit('2','The next step is a follow-up study.','다음 단계는 후속 연구입니다.',self.deliver)
        self.assertEqual(len(c.pending),2);self.assertEqual(self.calls,[]);self.assertEqual(self.output,[])
        c.jobs.discard(busy[0]);c.flush();self.assertEqual(len(self.calls),1)
        self.finish(0);self.assertEqual(len(self.calls),2)
        self.finish(1,'The next step is a follow-up study.')
        self.assertEqual([x[0] for x in self.output],['1','2']);self.assertFalse(c.pending)

    def test_queued_final_precedes_speculation(self):
        c=self.context;busy=[object() for _ in range(3)];c.jobs.update(busy)
        c.translate_unit('1','baseline','실험 결과가 일관되게 나왔습니다.',self.deliver)
        source='다음 단계는 후속 연구입니다';key=c.context_key()
        c.speculation.observe('2',source[:-1],'baseline',key,0);c.speculation.observe('2',source,'baseline',key,.1)
        c.jobs.clear()
        with patch('context_ui.time.monotonic',return_value=.41):c.try_speculation()
        self.assertEqual(self.calls,[]);self.assertEqual(c.speculation.calls,0)
        c.flush();self.assertEqual(len(self.calls),1)

    def test_queued_deadline_uses_baseline_and_no_late_request(self):
        c=self.context;c.jobs.update(object() for _ in range(3))
        c.translate_unit('1','The results are consistent.','실험 결과가 일관되게 나왔습니다.',self.deliver)
        c.pending[next(iter(c.pending))]['deadline']=0;c.jobs.clear();c.flush()
        self.assertEqual(self.calls,[]);self.assertEqual(self.output[0][1],'The results are consistent.')
        self.assertFalse(c.metrics[0]['context_used'])

    def test_reset_clears_queued_and_ignores_running_result(self):
        c=self.context
        c.translate_unit('1','baseline','실험 결과가 일관되게 나왔습니다.',self.deliver)
        c.jobs.update(object() for _ in range(3))
        c.translate_unit('2','','다음 단계는 후속 연구입니다.',self.deliver)
        c.reset();c.jobs.clear();self.finish()
        self.assertEqual(len(self.calls),1);self.assertEqual(self.output,[]);self.assertFalse(c.pending)

    def test_stt_gpt_failure_skips_source_and_recovers_next_caption(self):
        c=self.context
        c.translate_unit('1','','실험 결과가 일관되게 나왔습니다.',self.deliver)
        token,fn,callback=self.calls[0]
        callback((False,'network failure'));c.jobs.discard(token);c.flush()
        self.assertEqual(self.output,[]);self.assertFalse(c.pending)
        self.assertIn('일부 자막',self.window.status_label.text())
        c.translate_unit('2','The next result is ready.','',self.deliver)
        self.assertEqual(self.output,[('2','The next result is ready.','')])

    def test_stt_timeout_discards_late_response_without_blocking(self):
        c=self.context
        c.translate_unit('1','','실험 결과가 일관되게 나왔습니다.',self.deliver)
        c.pending[next(iter(c.pending))]['deadline']=0;c.flush()
        self.assertEqual(self.output,[]);self.assertFalse(c.pending)
        self.finish();self.assertEqual(self.output,[])
