"""Explicit opt-in verification with prerecorded audio, never the microphone."""
import json,threading,time,wave
from pathlib import Path

def run(directory):
    import azure.cognitiveservices.speech as sdk
    from speech_connection import PreparedSpeech
    from embedded_config import SPEECH_KEY,SPEECH_REGION
    root=Path(directory);wav=wave.open(str(root/'continuous-test.wav'),'rb')
    push=sdk.audio.PushAudioInputStream(sdk.audio.AudioStreamFormat(samples_per_second=wav.getframerate(),bits_per_sample=16,channels=1))
    prepared=PreparedSpeech(SPEECH_KEY,SPEECH_REGION,500,audio=sdk.audio.AudioConfig(stream=push))
    ready=threading.Event();recognized=threading.Event();report={'source':'prerecorded audio; no microphone','pass':False}
    r=prepared.recognizer
    r.session_started.connect(lambda _:ready.set())
    r.recognized.connect(lambda e:recognized.set() if e.result.text.strip() else None)
    try:
        t=time.monotonic();report['preconnected']=prepared.open();report['connect_seconds']=round(time.monotonic()-t,3)
        # Keep the real socket idle before beginning recognition on the same object.
        time.sleep(1)
        report['same_recognizer']=r is prepared.recognizer
        t=time.monotonic();r.start_continuous_recognition_async().get();report['session_ready']=ready.wait(5)
        report['start_seconds']=round(time.monotonic()-t,3)
        for i in range(int(wav.getframerate()*12/320)):
            push.write(wav.readframes(320));time.sleep(320/wav.getframerate())
        push.close();report['recognized']=recognized.wait(8)
        report['pass']=all(report[k] for k in ('preconnected','same_recognizer','session_ready','recognized'))
    except Exception as exc:report['error_type']=type(exc).__name__
    finally:
        wav.close()
        try:r.stop_continuous_recognition_async().get()
        except Exception:pass
        prepared.close()
    (root/'preconnect-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)
    return 0 if report['pass'] else 1
