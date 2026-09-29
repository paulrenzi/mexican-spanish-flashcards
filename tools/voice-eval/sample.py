import csv, random, json, os, subprocess
rows=[r for r in csv.DictReader(open('meta.tsv'),delimiter='\t')]
random.seed(20260928)
by={}
for r in rows:
    d=float(r['duration'])
    if 3<=d<=12 and len(r['normalized_text'].split())>=5: by.setdefault(r['speaker_id'],[]).append(r)
out=[]
for s in sorted(by):
    out+=random.sample(by[s],3)
os.makedirs('wav',exist_ok=True)
for r in out:
    g='female' if r['gender']=='female' else 'male'
    src=f"test/{g}/{r['speaker_id']}/{r['audio_id']}.flac"
    subprocess.run(['ffmpeg','-loglevel','error','-y','-i',src,'-ar','16000','-ac','1',f"wav/{r['audio_id']}.wav"],check=True)
json.dump(out,open('sample.json','w'),ensure_ascii=False,indent=0)
print(len(out), sum(float(r['duration']) for r in out))
