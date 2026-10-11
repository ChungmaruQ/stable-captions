import unittest,json,time,os
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont,QFontMetrics
from dual_translation import decode,encode,translate_with_context,OMITTED_PAIR,unsafe
APP=QApplication.instance() or QApplication([])
PAIR={'ja':'効果はまだ実証されていません。','vi':'Hiệu quả vẫn chưa được chứng minh.'}
class DualTests(unittest.TestCase):
 def test_pair_validation(self):
  self.assertEqual(decode(encode([PAIR])),[PAIR])
  for x in ['English only','{"pairs":[{"ja":"안녕","vi":"こんにちは"}]}','{}','{"pairs":[]}','{"pairs":[{"ja":"はい"}]}']:
   with self.assertRaises((ValueError,TypeError)):decode(x)
 def test_safety(self):
  for value in ('fuck','****','死ね','địt mẹ') :self.assertTrue(unsafe(value))
  self.assertFalse(unsafe('乳がんの治療 ung thư vú PVA'))
  self.assertEqual(decode(encode([{'ja':'死ね','vi':'xin chào'}])),[OMITTED_PAIR])
 def test_direct_sources(self):
  with patch('dual_translation.request_json',return_value=({'choices':[{'finish_reason':'stop','message':{'content':encode([PAIR])}}]},{})) as req:
   for ko,en,lang in [('효과는 아직 입증되지 않았습니다.','Wrong baseline','ko'),('','There is no evidence yet.','en')]:
    self.assertEqual(decode(translate_with_context('https://example.openai.azure.com','secret','gpt-5-mini',ko,en,'',[])),[PAIR])
    body=req.call_args.args[2];data=json.loads(body['messages'][1]['content'])
    self.assertEqual(data['source_language'],lang);self.assertEqual(data['current_speech'],ko.rstrip('.') if ko else en)
 def test_invalid_language_retries_before_display(self):
  bad={'choices':[{'finish_reason':'stop','message':{'content':'{"pairs":[{"ja":"한국어","vi":"日本語"}]}'}}]}
  good={'choices':[{'finish_reason':'stop','message':{'content':encode([PAIR])}}]}
  with patch('dual_translation.request_json',side_effect=[(bad,{}),(good,{})]) as req:
   result=translate_with_context('https://example.openai.azure.com','secret','gpt-5-mini','효과가 없습니다.','','',[])
   self.assertEqual(decode(result),[PAIR]);self.assertEqual(req.call_count,2)
   self.assertEqual(req.call_args.args[2]['reasoning_effort'],'minimal')
   feedback=req.call_args.args[2]['messages']
   self.assertEqual(feedback[-2],{'role':'assistant','content':bad['choices'][0]['message']['content']})
   self.assertIn('EVERY Korean/Hangul',feedback[-1]['content'])
 def test_final_bounded_retry_keeps_image(self):
  from slide_context import ServiceError
  from PySide6.QtGui import QImage
  from slide_image import encode_image
  image=QImage(16,16,QImage.Format.Format_RGB32);image.fill(0xffff0000);png,_=encode_image(image)
  good={'choices':[{'finish_reason':'stop','message':{'content':encode([PAIR])}}]}
  with patch('dual_translation.request_json',side_effect=[ServiceError('timeout'),ServiceError('timeout'),(good,{})]) as req:
   self.assertEqual(decode(translate_with_context('https://example.openai.azure.com','fake','gpt-5-mini','효과가 없습니다.','','',[],slide_image=png)),[PAIR])
   self.assertEqual(req.call_count,3);body=req.call_args.args[2]
   self.assertEqual(body['reasoning_effort'],'minimal');self.assertEqual(body['messages'][1]['content'][0]['type'],'image_url')
   self.assertLessEqual(req.call_args.kwargs['timeout'],2.5)
 def window(self):
  from app import MainWindow
  w=MainWindow(warmup=False);self.addCleanup(w.close);return w
 def test_two_rows_fixed_and_fit(self):
  w=self.window()
  from PySide6.QtCore import QRect
  w.overlay.screen_rect=QRect(0,0,1920,1080);w.overlay.render();initial=(w.overlay.width(),w.overlay.height())
  pairs=[PAIR,{'ja':'東国大学の創立120周年をお祝いします。','vi':'Xin chúc mừng kỷ niệm 120 năm thành lập Đại học Dongguk.'}]
  for p in pairs:
   w.overlay.advance_text(encode([p]));self.assertEqual(len(w.overlay.label.text().splitlines()),2)
   self.assertEqual((w.overlay.width(),w.overlay.height()),initial)
   for text,font in w.overlay.label.rows:
    self.assertLessEqual(QFontMetrics(font).horizontalAdvance(text),w.overlay.max_text_width)
    self.assertGreaterEqual(font.pointSizeF(),16)
  cap=3*(QFontMetrics(QFont('Segoe UI',32)).lineSpacing()+4)+12
  self.assertLessEqual(w.overlay.height(),cap)
 def test_atomic_pages_and_duplicate(self):
  w=self.window();w.deliver(0,'a',encode([PAIR,{'ja':'次へ','vi':'Tiếp theo'}]),'원문');w.deliver(0,'a',encode([PAIR]),'원문')
  self.assertEqual(len(w.queue.pending),1);w.tick();self.assertEqual(w.overlay.label.text(),PAIR['ja']+'\n'+PAIR['vi']);self.assertEqual(len(w.queue.pending),1)
 def test_model_both_languages_order_reset_failure(self):
  w=self.window();c=w.context;callbacks=[];out=[]
  def fake(fn,cb):callbacks.append((fn,cb))
  with patch.object(c,'run_job',side_effect=fake),patch('context_ui.translate_with_context',return_value=encode([PAIR])) as model:
   c.translate_unit('en','This is a statement.','',lambda *x:out.append(x));c.translate_unit('ko','','효과가 없습니다.',lambda *x:out.append(x))
   callbacks[1][1]((True,callbacks[1][0]()));self.assertEqual(out,[])
   callbacks[0][1]((True,callbacks[0][0]()));self.assertEqual([x[0] for x in out],['en','ko']);self.assertEqual(model.call_count,2)
   c.translate_unit('late','Late','','unused');cb=callbacks[-1][1];c.reset();cb((True,encode([PAIR])));self.assertFalse(c.pending)
   c.translate_unit('fail','English must not leak','',lambda *x:out.append(x));callbacks[-1][1]((False,'failure'));self.assertEqual(len(out),2)
if __name__=='__main__':unittest.main()
