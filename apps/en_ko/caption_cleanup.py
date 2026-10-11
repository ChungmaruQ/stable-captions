"""Local conservative disfluency cleanup; no extra service requests."""
import re
# Whole tokens only: preserve words such as umbrella, 아연, 음성 and 어류.
_FILLER = re.compile(r"(?<![\w])(?:[어음아으]+|u+h+|u+m+|e+r+m+|a+h+)(?![\w])", re.I)
_PUNCT = re.compile(r"^[\s.,!?;:…。，！？、~—–-]*$")
def clean_fillers(text):
    text = _FILLER.sub('', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[\s,.;:…、]+', '', text)
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)
    text = re.sub(r'([,;:])(?:[ ,;:])+', r'\1', text)
    return '' if _PUNCT.fullmatch(text) else text

def clean_sources(en, ko):
    source = ko or en
    if source and not clean_fillers(source):
        return '', ''
    return clean_fillers(en), clean_fillers(ko)

def idle_due(now, last_activity, shown_at, busy, reading_until=0):
    return (shown_at is not None and not busy and
            now >= max(last_activity, shown_at) + 5.0 and now >= reading_until)
