import json, sys, time, re
from faster_whisper import WhisperModel
name, tag = sys.argv[1], sys.argv[2]; prompt = len(sys.argv)>3 and sys.argv[3]=='prompt'
task = sys.argv[4] if len(sys.argv)>4 else 'transcribe'
S=json.load(open('sample.json')); P=json.load(open('phrases.json'))
words=[re.sub(r'^(el|la|los|las) ','',w) for p in P if p.get('kind')=='word' for w in p['es'].split(' / ')]
ptxt = 'Vocabulario: ' + ', '.join(dict.fromkeys(words))
ptxt = ptxt[:600]
m=WhisperModel(name, device='cpu', compute_type='int8', cpu_threads=4)
out={}; audio_s=0; t0=time.time()
for x in S:
    segs,_=m.transcribe(f"wav/{x['audio_id']}.wav", language='es', task=task, beam_size=5,
                        initial_prompt=ptxt if prompt else None, vad_filter=False, condition_on_previous_text=False)
    out[x['audio_id']]=' '.join(s.text.strip() for s in segs); audio_s+=float(x['duration'])
el=time.time()-t0
json.dump(out,open(f'hyp_{tag}.json','w'),ensure_ascii=False,indent=0)
print(tag, f'RTF={el/audio_s:.3f}', f'{el:.0f}s')
