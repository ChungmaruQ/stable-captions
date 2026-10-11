import unittest
from caption_logic import CaptionQueue, split_caption


class CaptionPolicyTests(unittest.TestCase):
    def test_partial_never_replaces_caption(self):
        queue = CaptionQueue()
        self.assertFalse(queue.accept('part1', 'We study', is_final=False))
        self.assertIsNone(queue.take(0, 2))
        queue.accept('final1', 'We study natural products.')
        self.assertEqual(queue.take(0, 2), 'We study natural products.')
        queue.accept('part2', 'This may', is_final=False)
        self.assertIsNone(queue.take(3, 2))

    def test_hold_order_and_no_dedup_by_text(self):
        queue = CaptionQueue()
        queue.accept('one', 'Thank you.')
        queue.accept('two', 'Thank you.')
        self.assertEqual(queue.take(0, 2), 'Thank you.')
        self.assertIsNone(queue.take(1.99, 2))
        self.assertEqual(queue.take(2, 2), 'Thank you.')

    def test_duplicate_event_ignored_and_restart_resets(self):
        queue = CaptionQueue()
        self.assertTrue(queue.accept('one', 'Hello.'))
        self.assertFalse(queue.accept('one', 'Rewritten hello.'))
        self.assertFalse(queue.accept('empty', '  '))
        queue.reset()
        self.assertTrue(queue.accept('one', 'New session.'))
        self.assertEqual(queue.take(0, 2), 'New session.')


class CompactCaptionTests(unittest.TestCase):
    def test_long_translation_preserves_words_and_bounds(self):
        text = 'Today we study natural products. These results explain how the compounds interact with proteins in cells.'
        pages = split_caption(text, len, 28)
        self.assertGreater(len(pages), 1)
        self.assertEqual(' '.join(' '.join(pages).split()), text)
        for page in pages:
            self.assertLessEqual(len(page.splitlines()), 2)
            self.assertTrue(all(len(line) <= 28 for line in page.splitlines()))
        self.assertTrue(pages[0].endswith('products.'))

    def test_empty_and_long_unbroken_term(self):
        self.assertEqual(split_caption(' ', len, 10), [])
        text = 'abcdefghijklmnopqrstuvwxyz'
        pages = split_caption(text, len, 10)
        self.assertEqual(''.join(''.join(pages).split()), text)
        self.assertTrue(all(len(line) <= 10 for page in pages for line in page.splitlines()))


if __name__ == '__main__':
    unittest.main()

class ReadingTests(unittest.TestCase):
    def test_short_chunks_preserve_every_word_and_bound_length(self):
        from caption_logic import short_phrases
        texts=['The reason for using Latin is that, because Latin is a dead language, it is more likely to be transmitted unchanged to later generations.',
               'This result is not statistically significant and must not be interpreted as proof of clinical efficacy.',
               'Revenue was KRW 4 billion, not KRW 400 million.']
        for text in texts:
            chunks=short_phrases(text)
            self.assertEqual(' '.join(chunks),text)
            self.assertTrue(all(len(x.split())<=8 for x in chunks))
    def test_reading_time_is_not_shortened_by_backlog(self):
        from caption_logic import reading_interval
        q=CaptionQueue();q.accept('1','One two three four five six seven eight.');text=q.take(0,1.5)
        q.next_at=reading_interval(text)
        for i in range(10):q.accept(str(i+2),'Next caption.')
        self.assertIsNone(q.take(.5,1.5,catch_up=False))
        self.assertIsNone(q.take(.99,1.5,catch_up=False))
        self.assertEqual(q.take(1.0,1.5,catch_up=False),'Next caption.')

class SemanticLineTests(unittest.TestCase):
    def test_complete_sentence_and_comma_stay_together(self):
        from caption_logic import semantic_lines
        for text in ['We use Latin because it is a dead language.',
                     'Revenue was KRW 4 billion, not KRW 400 million.']:
            self.assertEqual(semantic_lines(text,len,60),[text])
    def test_clause_boundary_and_terms(self):
        from caption_logic import semantic_lines
        text='We use Latin because it is a dead language and remains unchanged for later generations.'
        rows=semantic_lines(text,len,50)
        self.assertEqual(rows,['We use Latin because it is a dead language','and remains unchanged for later generations.'])
        text='A scientific name contains a genus name and a specific epithet.'
        rows=semantic_lines(text,len,43)
        self.assertEqual(' '.join(rows),text)
        self.assertTrue(any('genus name' in x for x in rows))
        self.assertTrue(any('specific epithet' in x for x in rows))
    def test_bounds_and_no_missing_words(self):
        from caption_logic import semantic_lines
        text='These results are not statistically significant and must not be interpreted as proof of clinical efficacy.'
        for width in [30,45,60,100]:
            rows=semantic_lines(text,len,width)
            self.assertEqual(' '.join(rows),text)
            self.assertTrue(all(len(x)<=width for x in rows))
            self.assertFalse(any(x.endswith(' not') for x in rows))
    def test_reading_interval_bounded(self):
        from caption_logic import reading_interval
        self.assertEqual(reading_interval('A short sentence.'),1)
        self.assertEqual(reading_interval(' '.join(['word']*20)),1.5)
        self.assertEqual(reading_interval('Long words',2),2)
