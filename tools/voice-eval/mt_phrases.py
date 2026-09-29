import json, random, ctranslate2, sacrebleu, time
from transformers import AutoTokenizer
P=[p for p in json.load(open('phrases.json')) if p.get('kind')!='word']
random.seed(7); P=random.sample(P,200)
def run(pair, src):
    tok=AutoTokenizer.from_pretrained(f'Helsinki-NLP/opus-mt-{pair}'); tr=ctranslate2.Translator(f'opus-{pair}-ct2',inter_threads=1,intra_threads=4)
    t0=time.time()
    toks=[tok.convert_ids_to_tokens(tok.encode(s)) for s in src]
    res=tr.translate_batch(toks,beam_size=4)
    out=[tok.decode(tok.convert_tokens_to_ids(r.hypotheses[0]),skip_special_tokens=True) for r in res]
    return out, (time.time()-t0)/len(src)
es=[p['es'] for p in P]; en=[p['en'] for p in P]
o1,t1=run('es-en',es); o2,t2=run('en-es',en)
print('es->en chrF',round(sacrebleu.corpus_chrf(o1,[en]).score,1),f'{t1*1000:.0f}ms/sent')
print('en->es chrF',round(sacrebleu.corpus_chrf(o2,[es]).score,1),f'{t2*1000:.0f}ms/sent')
json.dump([dict(es=a,en=b,mt_en=c,mt_es=d) for a,b,c,d in zip(es,en,o1,o2)],open('mt_phrases_out.json','w'),ensure_ascii=False,indent=1)
