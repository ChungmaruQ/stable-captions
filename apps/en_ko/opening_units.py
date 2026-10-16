"""Conservative short opening units; never synthesize unspoken source words."""
import re
EN_GREETING=re.compile(r'^(?:hello(?:\s+everyone)?|hi\s+everyone|good\s+(?:morning|afternoon|evening)(?:\s+everyone)?|thank\s+you)(?=$|[\s,.!?])',re.I)
VERBS={'study','studies','studied','identify','identifies','identified','investigate','investigates','investigated','describe','describes','described','measure','measures','measured','show','shows','showed','demonstrate','demonstrates','demonstrated','provide','provides','provided','improve','improves','improved','explain','explains','explained','discuss','discusses','discussed','compare','compares','compared'}
WEAK={'a','an','the','of','to','in','for','with','by','is','are','will','can','may','not','and','or','as','at','from','into','before','after','when','if','than','more','need','have','did','does','do','i','we','they','you','it','he','she','this','these','that','those','its','their'}
def english_opening_end(text,stable_length,normalize):
    greeting=EN_GREETING.match(text)
    if greeting and len(normalize(text[:greeting.end()]))<=stable_length:
        return greeting.end()
    tokens=list(re.finditer(r'\S+',text))
    for count in range(4,min(9,len(tokens))+1):
        end=tokens[count-1].end()
        if len(normalize(text[:end]))>stable_length:break
        words=[m.group().lower().strip('.,!?;:') for m in tokens[:count]]
        if words[-1] in WEAK:continue
        # Short sentences with explicit punctuation can stand alone.
        if tokens[count-1].group().endswith(('.', '!', '?')):return end
        if count>=len(tokens):continue
        next_word=tokens[count].group().lower().strip('.,!?;:')
        predicate=next((i for i,x in enumerate(words[1:],1) if x in VERBS),None)
        # Require a subject, predicate and at least two words after the predicate.
        # An adverb followed by a new article is a narrow clause boundary;
        # do not split 'we discuss mainly a treatment' or noun/preposition pairs.
        if predicate is not None and count-predicate>=3 and words[-1].endswith('ly') and next_word in {'a','an','the'}:
            return end
    return None
