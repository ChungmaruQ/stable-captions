"""Local, bounded retrieval from the bundled symposium reference; never executable instructions."""
import json
import math
import re
from collections import Counter
try:
    from event_data import EVENT_DATA
except ImportError:
    EVENT_DATA = {'profiles': [], 'common': '', 'event': ''}

PROFILES = EVENT_DATA['profiles']
STOP = set('the a an of to in and or for from with by as on is are was were this that these those we our their it its can may through using into at be have has will not'.split())

def tokens(text):
    return set(re.findall(r'[a-z0-9]+(?:[-/][a-z0-9]+)*|[가-힣]{2,}', text.lower())) - STOP

DOC_TOKENS = [tokens(p['title']+' '+p['speaker']+' '+p['aliases']+' '+' '.join(p['paragraphs'])+' '+' '.join(x['english'] for x in p.get('bilingual_pairs',[]))) for p in PROFILES]
FREQUENCY = Counter(t for ts in DOC_TOKENS for t in ts)

def score(query, words):
    return sum(math.log(1+(len(PROFILES)+1)/(1+FREQUENCY[t])) for t in query & words)

# Prepare immutable document indices once, before a talk starts. No model call or summary.
SENTENCES = {}
for profile in PROFILES:
    sentences = profile.get('bilingual_pairs') or [s for paragraph in profile['paragraphs']
                 for s in re.split(r'(?<=[.!?])\s+(?=[A-Z가-힣])', paragraph)]
    SENTENCES[profile['id']] = [(s, tokens(json.dumps(s,ensure_ascii=False) if isinstance(s,dict) else s)) for s in sentences]

class SlideIndex:
    def __init__(self):
        self.text = None
        self.words = set()
    def prepare(self, text):
        if text != self.text:
            self.text = text
            self.words = tokens(text[:10000])
        return self.words


def reference_for(korean, english, slide='', previous=(), profile_id='auto', limit=3800, screen_words=None):
    if not PROFILES: return ''
    # Current speech outweighs past context; explicit choice is useful before an introduction.
    current = tokens(korean+' '+english)
    screen = tokens(slide[:10000]) if screen_words is None else screen_words
    prior = tokens(' '.join(previous[-2:]))
    ranks=[]
    for p,ts in zip(PROFILES,DOC_TOKENS):
        ranks.append((score(current,ts)*3+score(screen,ts)+score(prior,ts)*.3,p))
    ranks.sort(key=lambda x:x[0],reverse=True)
    selected=next((p for p in PROFILES if p['id']==profile_id),None)
    if selected is None and ranks and ranks[0][0]>=7:
        # Avoid guessing between almost equally relevant talks.
        if len(ranks)==1 or ranks[0][0]>=ranks[1][0]*1.15: selected=ranks[0][1]
    data={'event':EVENT_DATA['event'],'common_reference':EVENT_DATA['common']}
    if selected:
        data['speaker']=selected['speaker'];data['title']=selected['title']
        indexed = SENTENCES[selected['id']]
        sentences = [s for s, _ in indexed]
        ranked=sorted(enumerate(sentences),key=lambda x:score(current,indexed[x[0]][1])*3+score(screen,indexed[x[0]][1])+score(prior,indexed[x[0]][1])*.3,reverse=True)
        if selected.get('bilingual_pairs'): ranked=ranked[:3]
        budget=max(0,limit-len(json.dumps(data,ensure_ascii=False))-100)
        chosen=[]
        for index,sentence in ranked:
            cost=len(json.dumps(sentence,ensure_ascii=False))+2
            if cost<=budget:
                chosen.append((index,sentence));budget-=cost
        data['document_excerpts']=[s for _,s in sorted(chosen)]
    return json.dumps(data,ensure_ascii=False)[:limit]


def prepared_translation_for(korean):
    """Reuse prepared wording only for an exact complete source passage, never fuzzy matching."""
    import unicodedata
    def normalize(value):
        return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value)).rstrip('.!?。！？')
    key = normalize(korean)
    if not key: return None
    pairs = next((p.get('bilingual_pairs', []) for p in PROFILES if p['id']=='greeting'), [])
    for start in range(len(pairs)):
        for length in range(1,4):
            group=pairs[start:start+length]
            if len(group)!=length: break
            if normalize(' '.join(x['korean'] for x in group))==key:
                return ' '.join(x['english'] for x in group)
    return None
