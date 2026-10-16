"""Sentence casing for committed English speech, independent of visual line breaks."""
import re

def sentence_ended(text):
    text=text.rstrip().rstrip('\"\'”’)]').rstrip()
    if not text or text[-1] not in '.!?':return False
    if text.endswith(('...', '…')):return False
    if text[-1] in '!?':return True
    last=text.split()[-1]
    if re.fullmatch(r'(?:[A-Za-z]\.)+',last):return False
    return last.lower() not in {'dr.','prof.','mr.','mrs.','ms.','st.','vs.','e.g.','i.e.','fig.','eq.','no.'}

def format_english_partial(text, preceding=''):
    # The pronoun I is capital even within a sentence. Preserve names, initialisms,
    # and mixed-case scientific identifiers; never lowercase the whole fragment.
    text=re.sub(r"\bi\b(?!\.[A-Za-z])",'I',text)
    if preceding and not sentence_ended(preceding):return text
    if re.match(r'^(?:i\.e\.|e\.g\.)',text):return text
    match=re.search(r"[A-Za-z][A-Za-z0-9'-]*",text)
    if match:
        token=match.group()
        if not any(c.isdigit() or c.isupper() for c in token[1:]):
            text=text[:match.start()]+token[0].upper()+text[match.start()+1:]
    return text
