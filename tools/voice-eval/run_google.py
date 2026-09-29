import json, time, speech_recognition as sr
S=json.load(open('sample.json')); r=sr.Recognizer(); out={}; t0=time.time()
for x in S:
    with sr.AudioFile(f"wav/{x['audio_id']}.wav") as f: a=r.record(f)
    for k in range(3):
        try: out[x['audio_id']]=r.recognize_google(a,language='es-MX'); break
        except sr.UnknownValueError: out[x['audio_id']]=''; break
        except Exception as e: print('err',e); time.sleep(3)
json.dump(out,open('hyp_google.json','w'),ensure_ascii=False,indent=0)
print(len(out), round(time.time()-t0,1),'s'); print(list(out.values())[:3])
