import json,re,sys,os,time,urllib.request,concurrent.futures as cf
from mt_workers_llm_v2 import SYS
# Same prompt as mt_workers_llm_v2.py, sent to an OpenAI-compatible chat API (OpenAI or xAI).
# Keys come from triumvirate/.env. Never the Anthropic API.
ENV={l.split('=',1)[0]:l.split('=',1)[1].strip().strip('"') for l in open(os.path.expanduser('~/repos/triumvirate/.env')) if '=' in l and not l.startswith('#')}
HOSTS={'openai':('https://api.openai.com/v1/chat/completions','OPENAI_API_KEY'),'xai':('https://api.x.ai/v1/chat/completions','XAI_API_KEY')}
USAGE=[]
def call(vendor,model,text):
    url,k=HOSTS[vendor]
    body={'model':model,'messages':[{'role':'system','content':SYS},{'role':'user','content':'Translate this into Mexican Spanish:\n<<<'+text+'>>>'}]}
    if vendor=='openai': body['reasoning_effort']=os.environ.get('EFFORT','low')
    r=urllib.request.Request(url,json.dumps(body).encode(),{'Authorization':'Bearer '+ENV[k],'Content-Type':'application/json'})
    for a in range(4):
        try: d=json.load(urllib.request.urlopen(r,timeout=120)); break
        except Exception as e:
            err=e; err=getattr(e,'read',lambda:b'')()[:300] or e; time.sleep(3*(a+1))
    else: return 'ERROR '+str(err)
    USAGE.append(d.get('usage',{}))
    return d['choices'][0]['message']['content'].strip()
if __name__=='__main__':
    vendor,model,tag=sys.argv[1:4]
    if len(sys.argv)>4: print(call(vendor,model,sys.argv[4]),USAGE); sys.exit()
    S=json.load(open('sample200.json'))
    clean=lambda s: re.sub(r'\s*\([^)]*\)','',s).strip()
    with cf.ThreadPoolExecutor(4) as ex: outs=list(ex.map(lambda p: call(vendor,model,clean(p['en'])),S))
    json.dump([dict(en=clean(p['en']),ref=p['es'],out=o) for p,o in zip(S,outs)],open(f'{tag}_out.json.new','w'),ensure_ascii=False,indent=0)
    os.replace(f'{tag}_out.json.new',f'{tag}_out.json')
    print(tag,'done',sum(o.startswith('ERROR') for o in outs),'errors; tokens in',sum(u.get('prompt_tokens',0) for u in USAGE),'out',sum(u.get('completion_tokens',0) for u in USAGE))
