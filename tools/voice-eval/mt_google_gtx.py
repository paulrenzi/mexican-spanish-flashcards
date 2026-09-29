import json,re,time,urllib.request,urllib.parse,sys
S=json.load(open('sample200.json'))
def clean(s): return re.sub(r'\s*\([^)]*\)','',s).strip()
out=[]
for i,p in enumerate(S):
    q=clean(p['en'])
    u='https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=es&dt=t&q='+urllib.parse.quote(q)
    try: d=json.load(urllib.request.urlopen(u,timeout=20))
    except urllib.error.HTTPError as e:
        print('HTTP',e.code,'at',i); break
    out.append(dict(en=q,ref=p['es'],google=''.join(x[0] for x in d[0] if x[0])))
    json.dump(out,open('google_out.json','w'),ensure_ascii=False,indent=0)
    time.sleep(2)
print('done',len(out))
