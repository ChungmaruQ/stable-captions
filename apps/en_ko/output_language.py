"""Prevent Korean source text from reaching the English caption surface."""
import re
import unicodedata
_HANGUL=re.compile(r'[\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\uac00-\ud7af\ud7b0-\ud7ff]')
def has_hangul(text):
    return bool(_HANGUL.search(unicodedata.normalize('NFKC',text or '')))
def route_source(english,korean):
    if has_hangul(english):
        return '', korean if korean.strip() else english
    return english,korean
