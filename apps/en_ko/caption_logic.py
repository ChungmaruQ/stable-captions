"""Display policy independent of the speech service and GUI."""
from collections import deque


class CaptionQueue:
    def __init__(self):
        self.pending = deque()
        self.seen = set()
        self.seen_order = deque()
        self.next_at = 0.0
        self.shown_at = None

    def reset(self):
        self.pending.clear()
        self.seen.clear()
        self.seen_order.clear()
        self.next_at = 0.0
        self.shown_at = None

    def accept(self, result_id, text, is_final=True):
        text = text.strip()
        if not is_final or not text or result_id in self.seen:
            return False
        self.seen.add(result_id)
        self.seen_order.append(result_id)
        if len(self.seen_order) > 2048:
            self.seen.discard(self.seen_order.popleft())
        self.pending.append(text)
        return True

    def take(self, now, minimum_seconds, catch_up=False, fast_rollup=False):
        # Adjust an existing hold when new pages arrive, not only after displaying a page.
        # Preserve every page and its order. Rollup keeps the previous page visible.
        deadline = self.next_at
        if catch_up and len(self.pending) >= (1 if fast_rollup else 2) and self.shown_at is not None:
            deadline = min(deadline, self.shown_at + min(minimum_seconds, 0.65 if fast_rollup else 0.8))
        if not self.pending or now < deadline:
            return None
        self.shown_at = now
        self.next_at = now + minimum_seconds
        return self.pending.popleft()


def split_caption(text, measure, max_width):
    """Sentence/phrase-aware pages of at most two measured lines, no dropped words."""
    import re
    units = re.split(r'(?<=[.!?;:,])\s+', ' '.join(text.split()))
    pages, lines, current = [], [], ''
    def flush_line():
        nonlocal current, lines
        if current:
            lines.append(current)
            current = ''
        if len(lines) == 2:
            pages.append('\n'.join(lines))
            lines = []
    for unit in units:
        for word in unit.split():
            if measure(word) > max_width:
                flush_line()
                for char in word:
                    if current and measure(current + char) > max_width:
                        flush_line()
                    current += char
                flush_line()
                continue
            candidate = (current + ' ' + word).strip()
            if current and measure(candidate) > max_width:
                flush_line()
            current = (current + ' ' + word).strip()
        # Prefer a new page at the end of a full sentence, retaining smaller clauses.
        if unit.endswith(('.', '!', '?')):
            flush_line()
            if lines:
                pages.append('\n'.join(lines))
                lines = []
    flush_line()
    if lines:
        pages.append('\n'.join(lines))
    return pages


def short_phrases(text, maximum_words=8):
    """Lossless display chunks, preferring punctuation and connective boundaries."""
    words = ' '.join(text.split()).split()
    chunks = []
    weak_endings = {'a','an','the','of','to','in','for','with','by','from','at','is','are','was','were','will','can','may','must','should'}
    connectors = {'because','while','whereas','although','but','and','therefore'}
    while words:
        size = min(maximum_words,len(words))
        punctuation = [i for i in range(1,size+1) if words[i-1].endswith(('.', '!', '?', ';', ':', ','))]
        boundaries = [i for i in range(4,size+1) if i<len(words) and words[i].lower() in connectors]
        if punctuation:
            size = punctuation[0]
        elif boundaries:
            size = boundaries[-1]
        elif len(words)>size:
            while size>4 and words[size-1].lower() in weak_endings:size-=1
        chunks.append(' '.join(words[:size]));words=words[size:]
    return chunks


def semantic_lines(text, measure, max_width):
    """Lossless measured lines; prefer complete sentences and clause boundaries.

    No word-count cap. Dynamic programming discourages dangling function words,
    tiny fragments and splitting common scientific expressions.
    """
    import re
    words = ' '.join(text.split()).split()
    if not words:return []
    weak = {'a','an','the','of','to','in','for','with','by','from','at','is','are',
            'was','were','will','can','may','must','should','not','no','and','or',
            'because','although','than','as','its','their','our','this','these'}
    connectors = {'because','while','whereas','although','but','and','which','when','if','so'}
    pairs = {('genus','name'),('species','epithet'),('specific','epithet'),
             ('scientific','name'),('scientific','names'),('clinical','efficacy'),
             ('clinical','trial'),('breast','cancer'),('dead','language'),
             ('statistically','significant'),('natural','products'),('drug','development')}
    def clean(w):return w.lower().strip('.,;:!?()')
    n=len(words);cost=[float('inf')]*(n+1);choice=[None]*(n+1);cost[n]=0
    for i in range(n-1,-1,-1):
        for j in range(i+1,n+1):
            line=' '.join(words[i:j]);width=measure(line)
            if width>max_width:
                if j==i+1:cost[i]=100+cost[j];choice[i]=j
                break
            end=j==n or bool(re.search(r'[.!?][\"\']?$',words[j-1]))
            # A complete sentence that fits should not be split at its comma.
            penalty=2 + (1-width/max_width)**2*4
            if not end:
                left=clean(words[j-1]);right=clean(words[j])
                penalty+=5
                if words[j-1].endswith((',', ';', ':')):penalty-=4
                elif right in connectors:penalty-=3
                if left in weak:penalty+=80
                if (left,right) in pairs:penalty+=24
                if words[j-1].replace('.','',1).isdigit():penalty+=18
            if j-i<3 and not (i==0 and j==n):penalty+=14
            if penalty+cost[j]<cost[i]:cost[i]=penalty+cost[j];choice[i]=j
            if end:break
    result=[];i=0
    while i<n:
        j=choice[i] or i+1;line=' '.join(words[i:j])
        if measure(line)>max_width:
            result.extend(part for page in split_caption(line,measure,max_width) for part in page.splitlines())
        else:result.append(line)
        i=j
    return result


def reading_interval(text, minimum=1.0):
    # Slightly longer for fuller rows; cap the increase to avoid queue lag.
    return max(minimum, min(1.5, 1.0 + max(0,len(text.split())-8)*0.1))


def sentence_pages(text, measure, max_width):
    """Keep up to two natural lines together, ending a page at sentence boundaries."""
    lines = semantic_lines(text, measure, max_width)
    pages, page = [], []
    for line in lines:
        page.append(line)
        if len(page) == 2 or line.rstrip().endswith(('.', '!', '?')):
            pages.append('\n'.join(page)); page = []
    if page: pages.append('\n'.join(page))
    return pages
