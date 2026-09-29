import json, sys, time, onnx_asr
S=json.load(open('sample.json'))
m=onnx_asr.load_model(sys.argv[1], quantization=sys.argv[3] if len(sys.argv)>3 else None)
m.recognize(f"wav/{S[0]['audio_id']}.wav")  # warm
out={}; audio_s=0; t0=time.time(); per=[]
for x in S:
    t=time.time(); out[x['audio_id']]=m.recognize(f"wav/{x['audio_id']}.wav", language='es') if 'canary' in sys.argv[1] else m.recognize(f"wav/{x['audio_id']}.wav")
    per.append((time.time()-t)/float(x['duration'])); audio_s+=float(x['duration'])
el=time.time()-t0
json.dump(out,open(f'hyp_{sys.argv[2]}.json','w'),ensure_ascii=False,indent=0)
print(sys.argv[2], f'RTF={el/audio_s:.3f}', f'{el:.0f}s', 'median per-clip', round(sorted(per)[len(per)//2],3))
