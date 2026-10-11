"""Commit stable leading clauses without cutting audio or revising shown captions.

Two matching observations, a time threshold and trailing context are required.
Final recognition is reconciled against committed source text, not translation.
"""
import re,unicodedata,difflib
from collections import deque

def norm(text):
    return ''.join(c for c in unicodedata.normalize('NFKC',text).lower() if c.isalnum())

def aligned_boundary(committed,text):
    if not committed:return 0
    old=norm(committed);new=norm(text)
    if new.startswith(old):return len(old)
    matcher=difflib.SequenceMatcher(None,old,new,autojunk=False)
    blocks=[b for b in matcher.get_matching_blocks() if b.size]
    covered=sum(b.size for b in blocks)
    if not blocks or covered/max(1,len(old))<.85:return None
    last=blocks[-1]
    if len(old)-(last.a+last.size)>6:return None
    return min(len(new),last.b+last.size+len(old)-(last.a+last.size))

def split_at_normalized(text,count):
    n=0
    for i,c in enumerate(text):
        n+=len(norm(c))
        if n>=count:
            # Include adjacent punctuation/space in the committed prefix.
            j=i+1
            while j<len(text) and not text[j].isalnum():j+=1
            return text[:j],text[j:]
    return text,''

class StablePrefix:
    def __init__(self):self.states={};self.closed=deque(maxlen=128)
    def observe(self,uid,text,language,now):
        if uid in self.closed:return None
        s=self.states.setdefault(uid,{'history':deque(maxlen=2),'committed':'','start':now,'last':now,'part':0})
        history=s['history'];history.append((now,norm(text)))
        if len(history)<2 or history[-1][0]-history[0][0]<.30:return None
        cut=aligned_boundary(s['committed'],text)
        if cut is None:return None
        common=history[0][1]
        for _,value in history:
            common=common[:next((i for i,(a,b) in enumerate(zip(common,value)) if a!=b),min(len(common),len(value)))]
        spans=list(re.finditer(r'\S+',text));allowed=[]
        for token in spans[:-2]:
            boundary=len(norm(text[:token.end()]))
            if cut<boundary<=len(common):allowed.append(token)
        if not allowed:return None
        # Start at the first wholly uncommitted word.
        allowed=[x for x in allowed if len(norm(text[:x.start()]))>=cut]
        if not allowed:return None
        korean=language.startswith('ko') or any('가'<=c<='힣' for c in text)
        age=now-s['last'];chosen=None
        if korean:
            endings=re.compile(r'(습니다|입니다|됩니다|합니다|랍니다|있다|없다|한다|된다|이다|했다|있어요|없어요|해요|돼요|하죠|되죠|습니까|인가요|바랍니다)[.!?]?$')
            complete=[i+1 for i,x in enumerate(allowed[:22]) if i>=3 and endings.search(x.group())]
            if complete:chosen=complete[0]
            elif not s['committed'] and age>=2.0 and len(allowed)>=3 and allowed[2].group()=='여러분':chosen=3
            elif age>=4.5 and len(allowed)>=8:
                candidates=[i+1 for i,x in enumerate(allowed[:16]) if i>=5 and x.group().endswith(('에서','하며','지만','때','위해','여러분','그리고'))]
                chosen=candidates[-1] if candidates else min(12,len(allowed))
        elif age>=2.5 and len(allowed)>=8:
            limit=min(18,len(allowed));weak={'a','an','the','of','to','in','for','with','by','is','are','will','can','may','not','and','or','as','at','from','into','before','after','when','if','than','more','need','have','did','does','do','i','we','they','you','it','he','she','this','these','that','those','its','their'}
            connectors={'and','but','because','while','whereas','which','we','i','it','these'}
            candidates=[i for i in range(8,limit+1) if i<len(allowed) and allowed[i].group().lower() in connectors and allowed[i-1].group().lower() not in weak]
            chosen=candidates[-1] if candidates else limit
            while chosen>6 and allowed[chosen-1].group().lower() in weak:chosen-=1
            pairs={('drug','discovery'),('natural','products'),('pharmaceutical','sciences'),('clinical','effects'),('biological','activities'),('genus','name'),('specific','epithet'),('natural','world'),('new','approaches'),('university','of'),('school','of'),('institution','of')}
            following=next((x for x in spans if x.start()>=allowed[chosen-1].end()),None)
            if following and (allowed[chosen-1].group().lower(),following.group().lower().strip('.,;:!?')) in pairs:chosen-=1
            while chosen>6 and allowed[chosen-1].group().lower() in weak:chosen-=1
            # Do not gain speed by emitting a tiny fragment after backing off.
            if chosen<8:return None
        if not chosen:return None
        end=allowed[chosen-1].end();piece=text[allowed[0].start():end].strip()
        if not piece:return None
        s['committed']=text[:end];s['last']=now;s['part']+=1
        return (f'{uid}:early:{s["part"]}',piece,korean)
    def finish(self,uid,text):
        s=self.states.pop(uid,None);self.closed.append(uid)
        if not s or not s['committed']:return text,False,True
        cut=aligned_boundary(s['committed'],text)
        if cut is None:
            # Fail visibly; never replay the full phrase over already shown text.
            return '',True,False
        return split_at_normalized(text,cut)[1].strip(),True,True
