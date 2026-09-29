import json,re,sys,unicodedata
# Spain / non-Mexican term -> what Mexico says. Word-boundary match on the lowercased output.
SPAIN={'lejía':'cloro','sirope':'jarabe','coche':'carro','coches':'carros','móvil':'celular','móviles':'celulares',
'ordenador':'computadora','zumo':'jugo','gafas':'lentes','patata':'papa','patatas':'papas','piscina':'alberca',
'pajita':'popote','pajitas':'popotes','grifo':'llave','aparcar':'estacionar','aparcamiento':'estacionamiento','aparco':'estaciono',
'aparcado':'estacionado','melocotón':'durazno','judías':'ejotes/frijoles','gamba':'camarón','gambas':'camarones',
'nevera':'refri','frigorífico':'refrigerador','cacahuete':'cacahuate','cacahuetes':'cacahuates','tarta':'pastel','maletero':'cajuela',
'bañador':'traje de baño','camarero':'mesero','camarera':'mesera','coger':'agarrar/tomar','cojo':'agarro/tomo','coge':'agarra/toma','coja':'agarre/tome',
'chaqueta':'chamarra','jersey':'suéter','tirita':'curita','tiritas':'curitas','fontanero':'plomero','cerilla':'cerillo','cerillas':'cerillos',
'cubo':'cubeta','bolígrafo':'pluma','mechero':'encendedor','bombilla':'foco','neumático':'llanta','neumáticos':'llantas','pinchazo':'ponchadura',
'pinchado':'ponchado','pinchada':'ponchada','gasoil':'diésel','enfadado':'enojado','enfadada':'enojada','ascensor':'elevador','aseo':'baño','aseos':'baños',
'váter':'baño','retrete':'baño','césped':'pasto','mando':'control','vaqueros':'jeans/mezclilla','zapatillas':'tenis','bocadillo':'torta',
'alubias':'frijoles','guindilla':'chile','ambulatorio':'clínica','conducir':'manejar','conduzco':'manejo','conduce':'maneja','vale':'OK/está bien',
'vosotros':'ustedes','vosotras':'ustedes','os':'les/los','ordenadores':'computadoras','piso':'departamento','cola':'fila','rueda':'llanta','ruedas':'llantas',
'sujetador':'brasier','autocar':'autobús','fregona':'trapeador','chubasquero':'impermeable','constipado':'resfriado','resfriado':None}
SPAIN={k:v for k,v in SPAIN.items() if v}
VOS=re.compile(r'\b\w+(áis|éis)\b')
TU_WORDS=set('tú te ti contigo tu tus puedes tienes quieres sabes estás eres necesitas vas das haces dices vienes conoces podrías tendrías harías darías quisieras '
 'dame dime ayúdame ven oye pon trae tráeme llévame hazme déjame dale pásame avísame llámame escríbeme muéstrame enséñame repite '
 'dímelo dámelo cámbiame revísame cóbrame lléname bájale súbele cuídate pregúntale fíjate siéntate límpialo '
 'podrías gustaría puedas quieras tengas sepas vengas'.split())
TU_WORDS.discard('gustaría')
def toks(s): return re.findall(r"[\wáéíóúñü]+",s.lower())
def tu(s):
    t=toks(s); hit=[w for w in t if w in TU_WORDS or re.fullmatch(r'\w+(ás|és)',w) and w not in ('más','inglés','después','través','francés','japonés','jamás','además','atrás','demás','estés','mes','es','cortés','interés','revés')]
    return hit
def spain(s):
    t=toks(s); return [w for w in t if w in SPAIN]+[m.group(0) for m in VOS.finditer(s.lower())]
def score(rows,key):
    ns=nt=0; lines=[]
    for i,r in enumerate(rows):
        o=r[key]; sp=[w for w in spain(o) if w not in toks(r['ref'])]
        tr=tu(r['ref']); to=tu(o); badtu = bool(to) and not tr
        ns+=bool(sp); nt+=badtu
        if sp or badtu: lines.append(f"{i:3d} {'SP '+','.join(sp) if sp else '':22s} {'TU '+','.join(to) if badtu else '':20s} | {r['en']} || {o} || ref: {r['ref']}")
    return ns,nt,lines
if __name__=='__main__':
    for f,key in [('google_out.json','google')]+[(t+'_out.json','out') for t in ('llama','gptoss','mistral','gpt5mini','gpt5','gpt5min','grok','sonnet','opus','opuslow')]:
        try: rows=json.load(open(f))
        except Exception: continue
        ns,nt,lines=score(rows,key)
        print(f'== {f}: n={len(rows)}  phrases with a Spain/non-Mex term: {ns}   tú where ref has none: {nt}')
        if '-v' in sys.argv: print('\n'.join(lines))
