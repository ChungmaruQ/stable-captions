import unittest
from english_casing import format_english_partial,sentence_ended
from caption_logic import semantic_lines,sentence_pages
class EnglishCasingTests(unittest.TestCase):
 def test_sentence_start_and_continuation(self):
  self.assertEqual(format_english_partial('we study natural products'),'We study natural products')
  self.assertEqual(format_english_partial('because they may have biological activity','we study natural products'),'because they may have biological activity')
  self.assertEqual(format_english_partial('the color changes','if we add the reagent,'),'the color changes')
 def test_real_new_sentence(self):
  self.assertEqual(format_english_partial('next we test the sample','The reaction is complete.'),'Next we test the sample')
  self.assertEqual(format_english_partial('is it effective','The result is positive!'),'Is it effective')
 def test_proper_names_acronyms_pronouns_and_identifiers(self):
  for text in ['Example University leads this study','DNA and RNA were measured','p53 is involved','mRNA was measured','eGFR decreased']:
   self.assertEqual(format_english_partial(text,'we observed'),text)
   self.assertEqual(format_english_partial(text),text)
  self.assertEqual(format_english_partial("i think i'm ready",'and'),'I think I\'m ready')
 def test_abbreviations_are_not_sentence_boundaries(self):
  for text in ['We worked with Dr.','in the U.S.','the value is 3.14','as shown in Fig.']:
   self.assertFalse(sentence_ended(text))
  self.assertTrue(sentence_ended('The results are consistent.'))
 def test_inline_abbreviation_is_not_pronoun(self):
  self.assertEqual(format_english_partial('i.e. the active fraction','we measured'),'i.e. the active fraction')

 def test_visual_lines_keep_original_case_and_punctuation(self):
  text='The samples were collected at Example University because we needed DNA and RNA. Next, we measured p53.'
  for pages in [semantic_lines(text,len,43),sentence_pages(text,len,43)]:
   self.assertEqual(' '.join(' '.join(pages).split()),text)

class TranslationSentenceStateTests(unittest.TestCase):
 def test_concurrent_request_carries_previous_source_boundary(self):
  import json
  from unittest.mock import patch
  from slide_context import translate_with_context
  response={'choices':[{'finish_reason':'stop','message':{'content':'the color changes.'}}]}
  with patch('slide_context.request_json',return_value=(response,{})) as request:
   translate_with_context('https://test.openai.azure.com','fake','gpt-5-mini','색이 변합니다','','',['시약을 넣으면'])
  payload=request.call_args.args[2];data=json.loads(payload['messages'][1]['content'])
  self.assertEqual(data['previous_source_speech_act'],'continuation')
  self.assertEqual(data['last_displayed_pairs'],[])
  self.assertIn('line break is NOT a new sentence',payload['messages'][0]['content'])

class SpeechPipelineCasingTests(unittest.TestCase):
 def test_worker_capitalizes_sentence_not_every_partial(self):
  import azure.cognitiveservices.speech as sdk
  from unittest.mock import patch
  from types import SimpleNamespace
  from app import SpeechWorker
  from test_app import FakeRecognizer,APP
  class PrefixFixture:
   def __init__(self):self.states={};self.index=0
   def observe(self,uid,text,language,now):
    pieces=['we study natural products','because they may have biological activity','next we measure DNA']
    piece=pieces[self.index];self.index+=1
    before=self.states.get(uid,{}).get('committed','')
    self.states[uid]={'committed':(before+' '+piece).strip()+('.' if self.index==2 else '')}
    return (str(self.index),piece,False)
  class Recognizer(FakeRecognizer):
   def start_continuous_recognition_async(self):
    def run():
     self.session_started.emit(None)
     for i in range(3):
      self.recognizing.emit(SimpleNamespace(result=SimpleNamespace(text='English recognition',offset=0,translations={},properties={sdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult:'en-US'})))
     self.session_stopped.emit(None)
    return SimpleNamespace(get=run)
  worker=SpeechWorker('fake','koreacentral',500);worker.prefix=PrefixFixture();out=[];errors=[]
  worker.final.connect(lambda rid,en,ko:out.append(en));worker.failed.connect(errors.append)
  with patch.object(sdk,'SpeechConfig'),patch.object(sdk.audio,'AudioConfig'),patch.object(sdk.PhraseListGrammar,'from_recognizer'),patch.object(sdk,'SpeechRecognizer',Recognizer):
   worker.run();APP.processEvents()
  self.assertEqual(errors,[])
  self.assertEqual(out,['We study natural products','because they may have biological activity','Next we measure DNA'])
