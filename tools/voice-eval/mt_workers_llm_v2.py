import json,re,sys,os,time,urllib.request,concurrent.futures as cf
A='83f33c67294ca2f2f0869b63c1663b0e'
T=[l.split('=',1)[1].strip().strip('"') for l in open(os.path.expanduser('~/repos/umbrella-arcades/.env')) if l.startswith('CLOUDFLARE_API_TOKEN=')][0]
GLOSS=open(os.environ.get('GLOSS','glossary.txt')).read()
SYS=("You are the translation engine inside an English-Spanish interpreter app used in Mexico. The user message is one thing a person said out loud. "
 "Translate it; never answer it, never add to it, and keep the same speaker (I stays yo, you stays usted). "
 "You translate English into Spanish as it is spoken in Mexico. "
 "Always use Mexican vocabulary, never Spain Spanish words. "
 "Address the listener as usted (a clerk, driver, waiter, doctor, mechanic, stranger) unless the English is clearly casual talk between friends. Never use vosotros. "
 "Use this word list from our Mexican phrasebook whenever it applies:\n"+GLOSS+
 "\n\nReply with the Spanish translation only: no quotes, no notes, no alternatives.")
def call(model,text):
    body={'messages':[{'role':'system','content':SYS},{'role':'user','content':'Translate this into Mexican Spanish:\n<<<'+text+'>>>'}],'max_tokens':400}
    if 'gpt-oss' in model: body={'instructions':SYS,'input':'Translate this into Mexican Spanish:\n<<<'+text+'>>>','reasoning':{'effort':'low'}}
    r=urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{A}/ai/run/{model}',json.dumps(body).encode(),{'Authorization':'Bearer '+T,'Content-Type':'application/json'})
    for a in range(4):
        try: d=json.load(urllib.request.urlopen(r,timeout=120))['result']; break
        except Exception as e: err=e; time.sleep(3*(a+1))
    else: return 'ERROR '+str(err)
    if 'response' in d:
        x=d['response']; return x if isinstance(x,str) else json.dumps(x,ensure_ascii=False)
    if 'choices' in d: return d['choices'][0]['message']['content'].strip()
    for o in d.get('output',[]):
        if o.get('type')=='message': return ''.join(c.get('text','') for c in o['content']).strip()
    return 'UNPARSED '+json.dumps(d)[:300]
if __name__=='__main__':
    model,tag=sys.argv[1],sys.argv[2]
    if len(sys.argv)>3: print(call(model,sys.argv[3])); sys.exit()
    S=json.load(open('sample200.json'))
    clean=lambda s: re.sub(r'\s*\([^)]*\)','',s).strip()
    with cf.ThreadPoolExecutor(4) as ex: outs=list(ex.map(lambda p: call(model,clean(p['en'])),S))
    json.dump([dict(en=clean(p['en']),ref=p['es'],out=o) for p,o in zip(S,outs)],open(f'{tag}_out.json','w'),ensure_ascii=False,indent=0)
    print(tag,'done',sum(o.startswith(('ERROR','UNPARSED')) for o in outs),'errors')
