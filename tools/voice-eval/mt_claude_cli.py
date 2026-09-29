import json,re,sys,os,time,subprocess,concurrent.futures as cf
from mt_workers_llm_v2 import SYS
# Same prompt as mt_workers_llm_v2.py, run through the claude CLI on the Max plan.
# ANTHROPIC_* is stripped from the child env so the login is used, never the paid API.
ENV={k:v for k,v in os.environ.items() if not k.startswith('ANTHROPIC_')}
LAT=[]
def call(model,text):
    cmd=['claude','-p','--model',model,'--system-prompt',SYS,'--tools','','--output-format','json',
         '--setting-sources','','Translate this into Mexican Spanish:\n<<<'+text+'>>>']
    for a in range(3):
        t=time.time(); p=subprocess.run(cmd,capture_output=True,text=True,env=ENV,timeout=300,cwd='/tmp')
        try:
            d=json.loads(p.stdout)
            if not d.get('is_error'): LAT.append(time.time()-t); return d['result'].strip()
            err=d.get('result')
        except Exception: err=(p.stdout+p.stderr)[:300]
        time.sleep(5*(a+1))
    return 'ERROR '+str(err)
if __name__=='__main__':
    model,tag=sys.argv[1:3]
    if len(sys.argv)>3: print(call(model,sys.argv[3]),LAT); sys.exit()
    S=json.load(open('sample200.json'))
    clean=lambda s: re.sub(r'\s*\([^)]*\)','',s).strip()
    with cf.ThreadPoolExecutor(4) as ex: outs=list(ex.map(lambda p: call(model,clean(p['en'])),S))
    json.dump([dict(en=clean(p['en']),ref=p['es'],out=o) for p,o in zip(S,outs)],open(f'{tag}_out.json.new','w'),ensure_ascii=False,indent=0)
    os.replace(f'{tag}_out.json.new',f'{tag}_out.json')
    LAT.sort(); print(tag,'done',sum(o.startswith('ERROR') for o in outs),'errors; median latency',round(LAT[len(LAT)//2],1) if LAT else None)
