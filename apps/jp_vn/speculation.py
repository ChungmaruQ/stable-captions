"""Bounded speculative requests; exact source matches only, never prefix reuse."""
import unicodedata

def normalized(text):
    return ''.join(unicodedata.normalize('NFKC',text).split()).rstrip('.!?。！？')

class Speculation:
    def __init__(self):
        self.reset()
    def reset(self):
        self.candidate=None
        self.records={}
        self.counts={}
        self.closed=set()
        self.calls=0
        self.hits=0
    def observe(self, utterance, text, baseline, context, now):
        source=normalized(text)
        if utterance in self.closed or len(source)<10: return
        key=(utterance,source,context)
        if self.candidate and self.candidate['key']==key:
            self.candidate['observations']+=1
        else:
            observations=self.candidate['observations']+1 if self.candidate and self.candidate['key'][0]==utterance else 1
            self.candidate=dict(key=key,text=text,baseline=baseline,since=now,observations=observations)
    def ready(self, now):
        c=self.candidate
        if not c or c['observations']<2 or now-c['since']<.3: return None
        key=c['key']; utterance=key[0]
        if not normalized(c['text']).endswith(('다','요','죠','까')):return None
        if utterance in self.closed or key in self.records or self.counts.get(utterance,0)>=2: return None
        if any(not r['done'] for r in self.records.values()): return None
        return c
    def begin(self,c):
        key=c['key'];self.counts[key[0]]=self.counts.get(key[0],0)+1;self.calls+=1
        r={'done':False,'result':None,'listeners':[]}
        self.records[key]=r
        return r
    def finish(self,key,result):
        r=self.records.get(key)
        if r is None:return
        r['done']=True;r['result']=result
        for callback in r['listeners']:callback(result)
        r['listeners'].clear()
    def final(self,utterance,text,context):
        self.closed.add(utterance)
        if len(self.closed)>128:self.closed.pop()
        for old in list(self.records):
            if len(self.records)<=8:break
            if self.records[old]['done'] and old[0]!=utterance:del self.records[old]
        if len(self.counts)>128:self.counts.pop(next(iter(self.counts)))
        if self.candidate and self.candidate['key'][0]==utterance:self.candidate=None
        r=self.records.get((utterance,normalized(text),context))
        if r and (not r['done'] or r['result'][0]): self.hits+=1;return r
        return None
