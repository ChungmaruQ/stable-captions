"""Small runtime vocabulary; data only, never instructions or sentence completions."""
import re
from event_reference import PROFILES, STOP
from caption_safety import flagged
COMMON=[]

def extract(text):
    result=[]
    for chunk in re.split(r'[\n:;|,/()]+',text[:12000]):
        words=re.findall(r'[A-Za-z가-힣][A-Za-z가-힣0-9+\-]*',chunk)
        run=[]
        for word in words+['and']:
            if word.lower() in STOP or len(run)>=5:
                if 1<=len(run)<=5:result.append(' '.join(run))
                run=[]
            if word.lower() not in STOP:run.append(word)
        result.extend(w for w in words if len(w)>=5 and w.lower() not in STOP)
    return result

def build_hints(slide='',profile_id='auto',documents=True):
    base=list(COMMON) if documents else []
    profiles=PROFILES if profile_id=='auto' else [p for p in PROFILES if p['id']==profile_id]
    if documents:
        for p in profiles:
            base.extend(x.strip() for x in p['speaker'].split('/'))
            base.extend(p['aliases'].split())
        for p in profiles:base.extend(extract(p['title']))
    def clean(values,limit):
        out=[];seen=set()
        for value in values:
            value=' '.join(value.split()).strip('- ')
            key=value.casefold()
            if 2<=len(value)<=70 and key not in seen and not flagged(value):
                seen.add(key);out.append(value)
                if len(out)>=limit:break
        return out
    return clean(clean(extract(slide),45)+clean(base,175),220)
