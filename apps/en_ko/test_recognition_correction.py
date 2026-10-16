import json,unittest
from unittest.mock import patch
from correction_guard import apply_edits
from recognition_correction import correct_and_translate,CorrectedCaption
from test_app import APP
from app import MainWindow

def edit(before,after,evidence):return {'before':before,'after':after,'evidence':evidence}
def response(edits):return ({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'edits':edits},ensure_ascii=False)}}]}, {})

class CorrectionGuardTests(unittest.TestCase):
 def test_local_supported_phonetic_term(self):
  raw='혁명을 사용합니다.';result,accepted,rejected=apply_edits(raw,[edit('혁명을','학명을','학명은 생물의 이름')],'학명은 생물의 이름')
  self.assertEqual(result,'학명을 사용합니다.');self.assertEqual(len(accepted),1);self.assertFalse(rejected)
 def test_english_term(self):
  result,a,r=apply_edits('The genius name.',[edit('genius','genus','genus name')],'genus name')
  self.assertEqual(result,'The genus name.')
 def test_numbers_and_negation_cannot_change(self):
  for raw,before,after in [('40억이 아니라 30억입니다.','40억이','30억이'),('효과가 없습니다.','없습니다.','있습니다.')]:
   result,a,r=apply_edits(raw,[edit(before,after,after)],after)
   self.assertEqual(result,raw);self.assertFalse(a);self.assertTrue(r)
 def test_sentence_replacement_is_blocked(self):
  raw='효과가 있을 수 있지만 아직 입증되지는 않았습니다.'
  result,a,r=apply_edits(raw,[edit(raw,'효과가 확인되었습니다.','효과가 확인되었습니다.')],'효과가 확인되었습니다.')
  self.assertEqual(result,raw);self.assertTrue(r)
 def test_nonexistent_or_ambiguous_before(self):
  for raw in ['다른 말을 합니다.','혁명을 혁명을']:
   result,a,r=apply_edits(raw,[edit('혁명을','학명을','학명')],'학명')
   self.assertEqual(result,raw);self.assertTrue(r)
 def test_missing_evidence_and_language_switch_blocked(self):
  for e in [edit('종소명은','specific','specific epithet'),edit('종소명은','서술어는','종소명')]:
   raw='종소명은 수식어입니다.';result,a,r=apply_edits(raw,[e],'종소명')
   self.assertEqual(result,raw);self.assertTrue(r)

class CorrectionPipelineTests(unittest.TestCase):
 def call(self,source,slide='학명은 생물의 이름'):
  return correct_and_translate('https://test.openai.azure.com','fake','gpt-5-mini',source,'',slide,[])
 def test_corrected_source_goes_to_translation(self):
  with patch('recognition_correction.request_json',return_value=response([edit('혁명을','학명을','학명은 생물의 이름')])),patch('recognition_correction.translate_with_context',return_value='We use scientific names.') as translate:
   out=self.call('혁명을 사용합니다.')
  self.assertEqual(translate.call_args.args[3],'학명을 사용합니다.')
  self.assertTrue(translate.call_args.kwargs['retain_context'])
  self.assertEqual(out.raw_source,'혁명을 사용합니다.');self.assertEqual(out.corrected_source,'학명을 사용합니다.')
 def test_timeout_keeps_raw_transcript(self):
  with patch('recognition_correction.request_json',side_effect=TimeoutError),patch('recognition_correction.translate_with_context',return_value='Translation') as translate:
   out=self.call('혁명을 사용합니다.')
  self.assertEqual(translate.call_args.args[3],out.raw_source);self.assertEqual(out.corrected_source,out.raw_source)
 def test_invalid_number_edit_never_reaches_translator(self):
  with patch('recognition_correction.request_json',return_value=response([edit('40억','30억','30억')])),patch('recognition_correction.translate_with_context',return_value='Not 4 billion but 3 billion.') as translate:
   out=self.call('40억 대신 30억입니다.','30억')
  self.assertEqual(translate.call_args.args[3],'40억 대신 30억입니다.');self.assertTrue(out.rejected_edits)
 def test_without_reference_no_correction_call(self):
  with patch('recognition_correction.request_json') as request,patch('recognition_correction.translate_with_context',return_value='Hello'):
   self.call('안녕하세요','')
  request.assert_not_called()
 def test_english_only_needs_one_model_call(self):
  with patch('recognition_correction.request_json',return_value=response([edit('genius','genus','genus name')])) as request,patch('recognition_correction.translate_with_context') as translate:
   out=correct_and_translate('https://test.openai.azure.com','fake','gpt-5-mini','','The genius name.','genus name',[])
  self.assertEqual(out,'The genus name.');request.assert_called_once();translate.assert_not_called()
 def test_history_retains_raw_and_corrected(self):
  w=MainWindow(warmup=False)
  out=CorrectedCaption('We use scientific names.','혁명을 사용합니다.','학명을 사용합니다.')
  w.deliver(w.session_number,'correction',out,out.raw_source)
  history=w.history.toPlainText();self.assertIn('[음성 인식] 혁명을',history);self.assertIn('[문맥 교정] 학명을',history)
  w.close()
 def test_option_switch_invalidates_pending(self):
  w=MainWindow(warmup=False);c=w.context
  self.assertTrue(c.use_correction.isChecked());session=c.session
  c.pending[1]={'fake':True};c.use_correction.setChecked(False)
  self.assertFalse(c.pending);self.assertGreater(c.session,session);w.close()
 def test_english_with_reference_enters_correction_mode(self):
  w=MainWindow(warmup=False);c=w.context;c.text='genus name';c.use_correction.setChecked(True);jobs=[];out=[]
  with patch.object(c,'run_job',side_effect=lambda fn,cb:jobs.append((fn,cb))),patch('recognition_correction.correct_and_translate',return_value=CorrectedCaption('The genus name.','The genius name.','The genus name.')) as request:
   c.translate_unit('a','The genius name.','',lambda *x:out.append(x))
   self.assertEqual(len(jobs),1);jobs[0][1]((True,jobs[0][0]()));self.assertEqual(out[0][1],'The genus name.');request.assert_called_once()
  c.reset();w.close()

class KoreanAnchorTests(unittest.TestCase):
 def test_same_stem_with_different_ending(self):
  raw='라틴어는 사워이기 때문입니다.'
  result,a,r=apply_edits(raw,[edit('사워이기','사어이기','사어인 라틴어')],'사어인 라틴어')
  self.assertEqual(result,'라틴어는 사어이기 때문입니다.');self.assertFalse(r)
