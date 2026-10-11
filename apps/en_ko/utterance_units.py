"""Conservative Korean clause buffering; punctuation alone is not a question."""
import re
QUESTION=re.compile(r'(습니까|입니까|합니까|됩니까|봅니까|갑니까|옵니까|인가요|나요|까요|니|냐|는가|인가|어때요|뭐예요|뭔가요)$')
STATEMENT=re.compile(r'(습니다|입니다|합니다|됩니다|했습니다|있어요|없어요|돼요|해요|있다|없다|한다|된다|이다|바랍니다|인데요|있는데요)$')
INCOMPLETE=re.compile(r'(으면|다면|라면|면서|지만|는데|므로|니까|위해|통해|때|그리고|또는|거나|하고|이고|이며|하며|면서도|면서|와|과|은|는|을|를|의|에|에서|으로|로|고)$')
def speech_act(text):
    clean=text.strip().rstrip('.?!。？！… ').strip()
    if QUESTION.search(clean):return 'question'
    if text.rstrip().endswith(('?','？')) and re.search(r'(해요|있어요|없어요|돼요)$',clean):return 'unknown'
    if STATEMENT.search(clean):return 'statement'
    if INCOMPLETE.search(clean):return 'continuation'
    return 'unknown'
def normalize_source(text):
    act=speech_act(text)
    if act in ('continuation','statement'):
        text=text.rstrip().rstrip('.?!。？！… ').strip()
    return text
class ClauseBuffer:
    def __init__(self,wait=1.2):self.wait=wait;self.held=None
    def reset(self):self.held=None
    def pop(self):
        value=self.held;self.held=None
        return value
    def due(self,now):return self.held is not None and now>=self.held['deadline']
    def push(self,rid,en,ko,deliver,utterance,now):
        ready=[]
        if self.held and (not ko.strip() or self.due(now)):
            ready.append(self.pop())
        current={'rid':rid,'en':en,'ko':ko,'deliver':deliver,'utterance':utterance,'deadline':now+self.wait}
        if self.held:
            previous=self.pop()
            current.update(rid=previous['rid']+'+'+rid,en='',ko=normalize_source(previous['ko'])+' '+normalize_source(ko),utterance=None,deadline=previous['deadline'])
        if ko.strip() and speech_act(current['ko'])=='continuation':
            current['ko']=normalize_source(current['ko']);current['en']='';current['utterance']=None
            self.held=current
        else:ready.append(current)
        return ready
