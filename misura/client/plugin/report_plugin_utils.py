from misura.canon.logger import Log as logging
import datetime
from textwrap import wrap, fill

def wr(k,v,n=18,inter=' '):
	k=wrap('{}:'.format(k),n)
	for i,e in enumerate(k):
		e='\\bold{{'+e+'}}'
		k[i]=e
	k='\\\\'.join(k)
	k=k.replace('_','\\_')
	
	v=wrap('{}'.format(v),n)
	v='\\\\'.join(v)
	v=v.replace('_','\\_')
	r='{}{}{}'.format(k,inter,v)
	logging.debug('%s %s %s %s', 'wrapped', k, v, r)
	return r

invalid=(None,'None','')

def render_meta(obj,notfound=False,n=30,inter=' ', full=False, zt=0):
	msg=''
	meta=[]
	for k,m in obj.describe().iteritems():
		if m['type']!='Meta':
			continue
		meta.append(m)
	meta=sorted(meta,key=lambda m: m['priority'])
	for m in meta:
		c=m['current']
		if c['temp'] in invalid:
			if not notfound:
				continue
			v=notfound
		else:
			v='{} {{\\deg}}C'.format(int(c['temp']))
			if full:
				if c['value'] not in invalid:
					v+=', {:.2f}'.format(c['value'])
				if c['time'] not in invalid:
					t=c['time']
					if t>zt: t-=zt
					logging.debug('%s %s %s %s', 'render time', c['time'], t, zt)
					v+=', {}'.format(datetime.timedelta(seconds=int(t)))
		w=wr(m['name'],v, n=n,inter=inter)
		msg+='\\\\'+w
	return msg