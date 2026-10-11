"""Offline last-mile guard for a professional presentation; no service calls.

This is a conservative vocabulary guard, not a guarantee about every possible
inappropriate meaning. Clinical terms (sex, breast, anal, etc.) stay intact.
"""
import re
import unicodedata

OMITTED = '[Caption omitted]'
_SOURCE_NOTICE = '[표현 보호로 해당 자막을 생략했습니다]'
_EN = re.compile(r"\b(?:fuck(?:s|ed|er|ers|ing)?|motherfuck\w*|shit(?:s|ty|ting|ted|head)?|bullshit|bitch(?:es|ing|y)?|cunt(?:s)?|asshole(?:s)?|bastard(?:s)?|dickhead(?:s)?|cock(?:s|sucker(?:s)?)?|pussy|pussies|slut(?:s)?|whore(?:s)?|wanker(?:s)?|nigg(?:er|ers|a|as)|faggot(?:s)?|retard(?:s|ed)?|blowjob(?:s)?|handjob(?:s)?|porn(?:ographic|ography)?|jerk\s+off|suck\s+my\s+\w+)\b",re.I)
# Whole words avoid Scunthorpe/association/analysis; explicit obfuscations are
# matched separately, not by stripping all punctuation from ordinary text.
_OBFUSCATED = re.compile(r"(?<!\w)(?:f[\W_]*[u*@][\W_]*[c*][\W_]*k(?:ing|ed|er)?|s[\W_]*h[\W_]*[i1*!][\W_]*t|b[\W_]*[i1*!][\W_]*t[\W_]*c[\W_]*h)(?!\w)",re.I)
_KO = re.compile(r'씨[\s._*-]*발|시[\s._*-]*발(?:놈|년|새끼)|개[\s._*-]*새끼|병[\s._*-]*신|좆|씹(?:새|할|년|놈)|지랄|엿먹|[ㅅᄉ][\s.]*[ㅂᄇ]|[ㅂᄇ][\s.]*[ㅅᄉ]')
_MASK = re.compile(r'\*{2,}|\[(?:omitted|caption omitted|censored|profanity)\]',re.I)

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKC',text) if unicodedata.category(c)!='Cf')

def flagged(text):
    value=normalized(text or '')
    return bool(_EN.search(value) or _OBFUSCATED.search(value) or _KO.search(value) or _MASK.search(value))

def protect_caption(english,source=''):
    if flagged(english) or flagged(source):return OMITTED, _SOURCE_NOTICE if source else '', True
    return english,source,False
