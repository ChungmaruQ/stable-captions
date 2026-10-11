"""Exact opening phrases only: never predict a speaker name or the next sentence."""
import re
PHRASES = {
 '존경하는 내외 귀빈 여러분': 'Distinguished guests,',
 '존경하는 내외 귀빈 여러분 반갑습니다': 'Distinguished guests, it is a pleasure to welcome you.',
 '여러분 안녕하세요': 'Hello, everyone.',
 '여러분 안녕하십니까': 'Hello, everyone.',
 '안녕하세요': 'Hello.',
 '안녕하십니까': 'Hello.',
 '반갑습니다': 'It is a pleasure to meet you.',
}
def exact_translation(text):
    clean=re.sub(r'[\s.!?。？！,，]', '', text)
    return next((value for phrase,value in PHRASES.items() if phrase.replace(' ','')==clean),None)
def opening_end(text):
    for phrase in sorted(PHRASES, key=len, reverse=True):
        match=re.match(r'^'+r'\s*'.join(map(re.escape,phrase.replace(' ','')))+r'(?=$|[\s.!?。？！,，])',text)
        if match:return match.end()
    return None
