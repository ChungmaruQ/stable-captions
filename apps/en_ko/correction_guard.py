"""Apply only local, evidenced, sound-alike transcript edits. No model trust."""
import re,unicodedata
from difflib import SequenceMatcher

def norm(s):return ' '.join(unicodedata.normalize('NFKC',s).split()).casefold()
def numeric(s):return re.findall(r'\d+(?:[.,]\d+)*',s)
def protected(s):return bool(re.search(r'\d|아니|않|없|못|아직|있을|가능|불확실|\b(?:not|no|never|may|might|could|without)\b|n.t\b',s,re.I))
def distance(a,b):
 row=list(range(len(b)+1))
 for i,ca in enumerate(a,1):
  new=[i]
  for j,cb in enumerate(b,1):new.append(min(new[-1]+1,row[j]+1,row[j-1]+(ca!=cb)))
  row=new
 return row[-1]
def apply_edits(raw,edits,reference='',image=False):
 if not isinstance(edits,list) or len(edits)>8:raise ValueError('Invalid edit list')
 result=raw;accepted=[];rejected=[];spans=[]
 for edit in edits:
  try:
   if not isinstance(edit,dict) or set(edit)!={'before','after','evidence'}:raise ValueError('fields')
   before,after,evidence=(edit[k] for k in ('before','after','evidence'))
   if not all(isinstance(x,str) for x in (before,after,evidence)):raise ValueError('types')
   if before==after:continue
   if not re.fullmatch(r'\S{1,20}',before) or not re.fullmatch(r'\S{1,20}',after):raise ValueError('local edit only')
   if protected(before) or protected(after):raise ValueError('protected meaning')
   if bool(re.search('[가-힣]',before))!=bool(re.search('[가-힣]',after)):raise ValueError('source language changed')
   matches=list(re.finditer(r'(?<!\w)'+re.escape(before)+r'(?!\w)',raw))
   if len(matches)!=1:raise ValueError('ambiguous source span')
   a,b=matches[0].span()
   if any(a<end and b>start for start,end,_ in spans):raise ValueError('overlapping edits')
   if distance(norm(before),norm(after))>max(1,len(before)//2):raise ValueError('not a local phonetic edit')
   ev=norm(evidence).strip(' \"“”')
   for prefix in ('슬라이드:', '참고:', 'slide:', 'reference:'):
    if ev.startswith(prefix):ev=ev[len(prefix):].strip(' \"“”')
   if not ev or (ev not in norm(reference) and not image):raise ValueError('unverified evidence')
   if re.search('[가-힣]',after):
    term=re.sub(r'(이기|이다|으로|에서|은|는|을|를|에|가|이|와|과)$','',after)
    if len(term)<2:term=after
    if not any(term[i:i+min(3,len(term))] in ev for i in range(max(1,len(term)-2))):raise ValueError('term absent from evidence')
   elif re.sub(r'\W','',after).casefold() not in re.sub(r'\W','',evidence).casefold():raise ValueError('term absent from evidence')
   spans.append((a,b,after));accepted.append(edit)
  except ValueError as error:rejected.append({'edit':edit,'reason':str(error)})
 for a,b,after in sorted(spans,reverse=True):result=result[:a]+after+result[b:]
 assert numeric(raw)==numeric(result)
 return result,accepted,rejected
