import json, wave, time, vosk
vosk.SetLogLevel(-1)
S=json.load(open('sample.json')); m=vosk.Model('vosk-model-small-es-0.42'); out={}; t0=time.time(); a=0
for x in S:
    wf=wave.open(f"wav/{x['audio_id']}.wav"); r=vosk.KaldiRecognizer(m,16000)
    while (d:=wf.readframes(4000)): r.AcceptWaveform(d)
    out[x['audio_id']]=json.loads(r.FinalResult())['text']; a+=float(x['duration'])
json.dump(out,open('hyp_vosk_small.json','w'),ensure_ascii=False,indent=0); print('vosk RTF',(time.time()-t0)/a)
