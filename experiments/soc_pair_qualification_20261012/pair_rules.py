"""Conservative, inert result association and literal-information-use audit."""
import re

SGR=re.compile(r'\x1b\[[0-9;]*m')
ENTITY=re.compile(r'(?<![\w./:-])(?:/(?:[\w.-]+/)*[\w.-]+|(?:[\w-]+\.)+[A-Za-z0-9_-]+)(?![\w./:-])')
CONTROL={'task','clear','exit','history','flag'}

def resolve_text(value, attachments):
    if isinstance(value,str):
        if value.startswith('attachment://'):
            answer=attachments.get(value[len('attachment://'):])
            return answer if isinstance(answer,str) else None
        return value
    if isinstance(value,list) and value:
        if any(not isinstance(x,dict) or x.get('type')!='text' for x in value): return None
        parts=[resolve_text(x.get('text'),attachments) for x in value]
        return '\n'.join(parts) if all(x is not None for x in parts) else None
    return None

def terminal_span(data, command, following=None):
    low=command['output_end_before_enter'];high=command['confirmation_output_end']
    marker=data.find(b'\x1b[?2004l',low,high)
    if marker<0:return None,{'reason':'missing_start'}
    start=marker+8;end=data.find(b'\x1b[?2004h',start)
    if end<start:return None,{'reason':'missing_end'}
    if following is not None and end>following['output_end_before_enter']:
        return None,{'reason':'crosses_next_submission'}
    try: text=data[start:end].decode('utf-8',errors='strict')
    except UnicodeDecodeError:return None,{'reason':'invalid_utf8'}
    return text,{'reason':None,'start':start,'end':end}

def normalize_output(text):
    if text is None:return None,'missing'
    # SGR is appearance-only. Cursor motion/erasure/backspace need screen rendering.
    text=SGR.sub('',text).replace('\r\n','\n')
    if text.startswith('\r'):text=text[1:] # shell Enter's initial carriage return
    if '\x1b' in text or any(ord(c)<32 and c not in '\n\t' for c in text):
        return None,'terminal_control_requires_rendering'
    if re.search(r'(?m)^(?:[\w.-]+@[\w.-]+:[^\n]*[#$] |[\u2500-\u257f]{2,})',text):
        return None,'prompt_or_terminal_frame'
    if re.search(r'(?i)(?:output truncated|truncated output|maximum output length|remaining tokens|time budget remaining)',text):
        return None,'possible_truncation_or_tool_wrapper'
    return text,None

def entities(text):
    # A deliberately narrow lexical proxy. Not a semantic data-flow reconstruction.
    return {m.group() for m in ENTITY.finditer(text) if 3<=len(m.group())<=160
            and not re.fullmatch(r'\d+(?:\.\d+){1,2}',m.group())}

def uptake(response, command_history, following, prior_results=()):
    observed=entities(response)
    previous=set().union(*(entities(c) for c in command_history),*(entities(r) for r in prior_results))
    novel=observed-previous
    used=novel & entities(following)
    return {'candidate_entities':len(observed),'new_to_retained_history':len(novel),
            'reused_in_next_command':len(used),'supported':bool(novel),'hit':bool(used)}

def classify_control(command):
    stripped=command.strip()
    verb=stripped.split(maxsplit=1)[0] if stripped else ''
    return verb in CONTROL or bool(re.search(r'target:9091/(?:done|score)',command))

def joined_transition(a,b):
    if not(a['qualified'] and b['qualified']): return False
    if b['index']!=a['index']+1:return False
    if a['origin']=='H':return a['log']==b['log']
    return a['reply_message']<b['call_message']
