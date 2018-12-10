from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import datetime
from textwrap import wrap, fill


def wr(k, v, n=18, inter=' '):
    k = wrap(u'{}:'.format(k), n)
    for i, e in enumerate(k):
        e = u'\\bold{{' + e + u'}}'
        k[i] = e
    k = u'\\\\'.join(k)
    k = k.replace(u'_', u'\\_')

    v = wrap(u'{}'.format(v), n)
    v = u'\\\\'.join(v)
    v = v.replace(u'_', u'\\_')
    r = u'{}{}{}'.format(k, inter, v)
    logging.debug('wrapped', k, v, r)
    return r

invalid = (None, 'None', '')


def render_meta(obj, notfound=False, n=30, inter=' ', full=False, zt=0):
    msg = ''
    meta = []
    for k, m in obj.describe().iteritems():
        if m['type'] != 'Meta':
            continue
        meta.append(m)
    meta = sorted(meta, key=lambda m: m['priority'])
    for m in meta:
        c = m['current']
        if c['temp'] in invalid:
            if not notfound:
                continue
            v = notfound
        else:
            v = u'{} {{\\deg}}C'.format(int(c['temp']))
            if full:
                if c['value'] not in invalid:
                    v += u', {:.2f}'.format(c['value'])
                if c['time'] not in invalid:
                    t = c['time']
                    if t > zt:
                        t -= zt
                    logging.debug('render time', c['time'], t, zt)
                    v += u', {}'.format(datetime.timedelta(seconds=int(t)))
        w = wr(m['name'], v, n=n, inter=inter)
        msg += u'\\\\' + w
    return msg
