import unittest
from unittest.mock import Mock,patch
from caption_logic import CaptionQueue
from event_reference import SlideIndex,tokens
import slide_context as sc

class LatencyTests(unittest.TestCase):
 def test_backlog_shortens_existing_hold_without_dropping_pages(self):
  q=CaptionQueue();q.accept('a','A');self.assertEqual(q.take(0,1.5,True),'A')
  q.accept('b','B');q.accept('c','C')
  self.assertIsNone(q.take(.79,1.5,True))
  self.assertEqual(q.take(.8,1.5,True),'B')
  self.assertEqual(list(q.pending),['C'])
  self.assertIsNone(q.take(1,1.5,True))
  self.assertEqual(q.take(2.3,1.5,True),'C')
 def test_single_caption_mode_honors_hold(self):
  q=CaptionQueue();q.accept('a','A');q.take(0,1.5)
  q.accept('b','B');q.accept('c','C')
  self.assertIsNone(q.take(.8,1.5));self.assertEqual(q.take(1.5,1.5),'B')
 def test_slide_index_invalidates_and_keeps_all_tokens(self):
  s=SlideIndex();first=s.prepare('NOX1 감소 15%')
  self.assertIs(s.prepare('NOX1 감소 15%'),first)
  self.assertEqual(s.prepare('CYP2C19 증가'),tokens('CYP2C19 증가'))
  self.assertEqual(s.prepare(''),set())
 def test_session_leases_are_exclusive_and_reusable(self):
  pool=sc.LifoQueue(maxsize=2)
  with patch.object(sc,'_HTTP_SESSIONS',pool):
   a=sc.acquire_session();b=sc.acquire_session();self.assertIsNot(a,b)
   a.cookies.set('test','value');sc.release_session(a)
   self.assertIs(sc.acquire_session(),a);self.assertEqual(len(a.cookies),0)
   a.close();b.close()
 def test_failed_request_returns_session_and_does_not_retry(self):
  session=Mock();session.request.side_effect=RuntimeError('failure')
  with patch.object(sc,'acquire_session',return_value=session),patch.object(sc,'release_session') as release:
   with self.assertRaises(sc.ServiceError):sc.request_json('https://test.openai.azure.com/openai/v1/chat/completions','fake',{})
   self.assertEqual(session.request.call_count,1);release.assert_called_once_with(session)
if __name__=='__main__':unittest.main()
