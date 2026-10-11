import unittest
from unittest.mock import patch
from test_app import APP
from app import MainWindow
from korean_output import valid_korean_caption, translate_to_korean
from slide_context import ServiceError


class KoreanOutputTests(unittest.TestCase):
    def setUp(self):
        self.w=MainWindow(warmup=False)
        self.w.output_language.setCurrentIndex(1)
        self.c=self.w.context
        self.c.timer.stop();self.c.dispatch.stop()
        self.calls=[];self.output=[]
        def job(fn, callback):
            token=object();self.c.jobs.add(token)
            self.calls.append((token,fn,callback))
        self.c.run_job=job

    def tearDown(self):
        self.c.jobs.clear();self.w.close()

    def finish(self, result):
        token,fn,callback=self.calls[0]
        self.c.jobs.discard(token);callback(result);self.c.flush()

    def test_korean_direct_no_model_and_no_clause_delay(self):
        self.c.translate('1','English baseline','이 물질은 효과가 있을 수 있습니다.',lambda *x:self.output.append(x))
        self.assertEqual(self.output[0][1],'이 물질은 효과가 있을 수 있습니다.')
        self.assertFalse(self.calls);self.assertIsNone(self.c.clauses.held)

    def test_english_translation_and_following_korean_keep_order(self):
        self.c.translate('1','This may work, but it is not proven.','',lambda *x:self.output.append(x))
        self.c.translate('2','','다음 실험입니다.',lambda *x:self.output.append(x))
        self.assertFalse(self.output)
        self.finish((True,'효과가 있을 수 있지만 입증되지는 않았습니다.'))
        self.assertEqual([x[0] for x in self.output],['1','2'])
        self.assertTrue(all(valid_korean_caption(x[1]) for x in self.output))

    def test_failure_or_wrong_language_never_falls_back_to_english(self):
        for result in [(False,'error'),(True,'This is English.')]:
            self.c.translate('1','This is English.','',lambda *x:self.output.append(x))
            self.finish(result);self.calls.clear()
        self.assertFalse(self.output)

    def test_switch_language_discards_inflight_translation(self):
        self.c.translate('1','Hello everyone.','',lambda *x:self.output.append(x))
        self.w.output_language.setCurrentIndex(0)
        self.finish((True,'여러분 안녕하세요.'))
        self.assertFalse(self.output)

    def test_output_guard_and_preview_and_control_lock(self):
        self.w.deliver(self.w.session_number,'bad','English sentence.','')
        self.assertFalse(self.w.queue.pending)
        self.w.deliver(self.w.session_number,'good','실험 결과입니다.','')
        self.assertTrue(self.w.queue.pending)
        self.w.demo();self.assertIn('자막 미리보기',self.w.overlay.current_text)
        self.w.set_running(True);self.assertFalse(self.w.output_language.isEnabled())
        self.w.set_running(False);self.assertTrue(self.w.output_language.isEnabled())

    def test_profanity_notice_is_korean(self):
        self.c.translate('1','shit','',lambda *x:self.output.append(x))
        self.assertEqual(self.output[0][1],'[자막 생략]');self.assertFalse(self.calls)

    def test_language_guard_allows_scientific_acronyms_not_english_sentences(self):
        for text in ['PVA','DNA','3.5%','PVA와 붕산입니다.']:
            self.assertTrue(valid_korean_caption(text))
        for text in ['','The results are consistent.']:
            self.assertFalse(valid_korean_caption(text))

    def test_request_contract_and_truncated_response(self):
        response={'choices':[{'finish_reason':'stop','message':{'content':'효과가 있을 수 있습니다.'}}]}
        with patch('korean_output.request_json',return_value=(response,{})) as request:
            text=translate_to_korean('https://test.openai.azure.com','fake','gpt-5-mini','It may work.','PVA',[])
            self.assertIn('있을 수',text)
            payload=request.call_args.args[2]
            self.assertIn('Korean',payload['messages'][0]['content'])
            self.assertIn('PVA',payload['messages'][1]['content'])
        response['choices'][0]['finish_reason']='length'
        with patch('korean_output.request_json',return_value=(response,{})):
            with self.assertRaises(ServiceError):
                translate_to_korean('https://test.openai.azure.com','fake','gpt-5-mini','Test')
