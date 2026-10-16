"""Bounded local metadata journal: never store keys, transcript text or images."""
import json,logging,os,re,sys,threading
from collections import deque
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
_lock=threading.RLock();_events=deque(maxlen=300);_sequence=0;_handler=None;_path=None;_error=''
_NUMERIC={'status','elapsed_ms','request_id','image_count','image_bytes','ocr_chars','capture_id','width','height','screen_index','prompt_tokens','cached_tokens','cache_write_tokens','completion_tokens','reasoning_tokens','total_tokens','usage_known','audio_seconds'}
_LABELS={'stage','state','reason','exception','variant','build','model'}

def configure(variant='EN-KO',directory=None):
 global _handler,_path,_error
 with _lock:
  if _handler:_handler.close()
  _handler=None;_path=None;_error=''
  try:
   if directory is None:
    directory=(Path.home()/'Library/Logs/StableCaptions' if sys.platform=='darwin' else Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'StableCaptions'/'Logs')
   root=Path(directory);root.mkdir(parents=True,exist_ok=True)
   _path=root/(variant+'.jsonl')
   _handler=RotatingFileHandler(_path,maxBytes=512*1024,backupCount=2,encoding='utf-8')
   _handler.setFormatter(logging.Formatter('%(message)s'))
  except Exception as e:_error=type(e).__name__;_path=None
 record('app_started',variant=variant,build='2026.10.16.5')
 return _path

def close():
 global _handler,_path
 with _lock:
  if _handler:_handler.close()
  _handler=None;_path=None

def log_path():return _path
def log_error():return _error

def record(event,**fields):
 global _sequence,_error
 if not re.fullmatch(r'[a-z_]{1,64}',event):return 0
 with _lock:
  _sequence+=1
  row={'seq':_sequence,'time':datetime.now().astimezone().isoformat(timespec='seconds'),'event':event}
  for key,value in fields.items():
   if key in _NUMERIC and isinstance(value,(int,float,bool)):row[key]=value
   elif key in _LABELS and isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}',value):row[key]=value
  _events.append(row)
  if _handler:
   try:_handler.handle(logging.LogRecord('captions',logging.INFO,'',0,json.dumps(row,ensure_ascii=False),(),None))
   except Exception as e:_error=type(e).__name__
  return _sequence

def entries_after(sequence=0):
 with _lock:return [dict(x) for x in _events if x['seq']>sequence]


def response_usage(result):
 """Copy only billable counters, never model content or arbitrary response fields."""
 usage=result.get('usage') if isinstance(result,dict) else None
 if not isinstance(usage,dict):return {'usage_known':False}
 fields={'usage_known':all(isinstance(usage.get(k),int) and usage[k]>=0 for k in ('prompt_tokens','completion_tokens'))}
 for key in ('prompt_tokens','completion_tokens','total_tokens'):
  value=usage.get(key)
  if isinstance(value,int) and value>=0:fields[key]=value
 for parent,keys in (('prompt_tokens_details',('cached_tokens','cache_write_tokens')),('completion_tokens_details',('reasoning_tokens',))):
  details=usage.get(parent)
  if isinstance(details,dict):
   for key in keys:
    value=details.get(key)
    if isinstance(value,int) and value>=0:fields[key]=value
 model=result.get('model','')
 if isinstance(model,str) and re.fullmatch(r'gpt-[a-z0-9.-]{1,70}',model):fields['model']=model
 return fields


def request_metadata(url,payload,binary=False):
 stage='ocr' if 'computervision' in url else 'translation'
 count=0
 if isinstance(payload,dict):
  if payload.get('response_format',{}).get('json_schema',{}).get('name')=='transcript_edits':stage='correction'
  for message in payload.get('messages',[]):
   parts=message.get('content')
   if isinstance(parts,list):count+=sum(isinstance(x,dict) and x.get('type')=='image_url' for x in parts)
 return {'stage':stage,'image_count':count,'image_bytes':len(payload) if binary and isinstance(payload,bytes) else 0}

_LABEL={'app_started':'앱 시작','analysis_started':'화면 분석 시작','analysis_stopped':'화면 분석 중지','capture_state':'캡처 상태','capture_ready':'화면 이미지 준비','ocr_ready':'OCR 완료','ocr_failed':'OCR 실패','request_started':'서비스 전송 시작','request_received':'서비스 응답 수신','request_failed':'서비스 요청 실패','caption_skipped':'번역 자막 생략','permission_checked':'화면 기록 권한 확인'}
_STATES={'off':'꺼짐','starting':'시작 중','controls_visible':'설정창 때문에 일시 정지','permission_denied':'화면 기록 권한 필요','permission_unknown':'화면 기록 권한 확인 불가','capture_unavailable':'캡처 불가','waiting_stable':'화면 안정 대기','capture_error':'캡처 오류','ready':'이미지 준비됨','ocr_failed':'이미지는 준비됨 / OCR 실패','unchanged':'현재 이미지 유지','granted':'권한 허용','denied':'권한 없음','unknown':'권한 확인 불가','not_required':'권한 확인 불필요'}

def format_entry(row):
 details=[]
 for key in ('stage','state','status','image_count','image_bytes','ocr_chars','capture_id','elapsed_ms','reason','exception'):
  if key not in row:continue
  value=row[key]
  if key=='state':value=_STATES.get(value,value)
  if key=='stage':value={'ocr':'글자 인식','translation':'번역','correction':'인식문 교정'}.get(value,value)
  label={'image_count':'첨부 이미지','image_bytes':'이미지 bytes','ocr_chars':'추출 글자','capture_id':'캡처 번호','elapsed_ms':'ms','stage':'단계','state':'상태','status':'HTTP','reason':'사유','exception':'오류'}.get(key,key)
  details.append(f'{label}={value}')
 return row['time'][11:19]+' '+_LABEL.get(row['event'],row['event'])+(' · '+' · '.join(details) if details else '')
