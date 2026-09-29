import json, re, glob, unicodedata, jiwer
from num2words import num2words
S=json.load(open('sample.json'))
def norm(t, fold=False):
    t=t.lower()
    t=re.sub(r'(\d+)[.,](\d{3})', r'\1\2', t)
    t=re.sub(r'\d+', lambda m: ' '+num2words(int(m.group()),lang='es')+' ', t)
    t=re.sub(r"[^\w\sáéíóúüñ]", ' ', t)
    if fold: t=''.join(c for c in unicodedata.normalize('NFD',t) if unicodedata.category(c)!='Mn')
    return ' '.join(t.split())
refs=[norm(x['normalized_text']) for x in S]
rows=[]
for f in sorted(glob.glob('hyp_*.json')):
    if 'translate' in f: continue
    h=json.load(open(f)); hy=[norm(h.get(x['audio_id'],'')) for x in S]
    w=jiwer.wer(refs,hy); wf=jiwer.wer([norm(r,1) for r in refs],[norm(x,1) for x in hy])
    # per-speaker spread
    rows.append((w,f[4:-5],wf,sum(1 for x in hy if not x)))
for w,n,wf,e in sorted(rows): print(f'{n:22s} WER {w*100:5.1f}%  accent-folded {wf*100:5.1f}%  empty={e}')

FILL={'e','eh','em','mm','mmm','uhum','ajá','este','pues','no','o','ah','mh'}
FIX={'entoces':'entonces','toces':'entonces','toa':'toda','pa':'para','pos':'pues'}
def clean(t):
    w=[FIX.get(x,x) for x in norm(t,1).split()]
    w=[x for x in w if x not in FILL]
    o=[]
    for x in w:
        if not o or o[-1]!=x: o.append(x)
    return ' '.join(o)
print('\n-- content WER (fillers/"no" tags/repeats dropped, accents folded) --')
cref=[clean(x['normalized_text']) for x in S]; R=[]
for f in sorted(glob.glob('hyp_*.json')):
    if 'translate' in f: continue
    h=json.load(open(f)); R.append((jiwer.wer(cref,[clean(h.get(x['audio_id'],'')) for x in S]),f[4:-5]))
for w,n in sorted(R): print(f'{n:22s} {w*100:5.1f}%')
