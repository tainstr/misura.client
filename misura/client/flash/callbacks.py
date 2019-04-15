from misura.canon.option import ConfigurationProxy
from thegram.model.gembarovic import search_diameter

def calc_baseline_shifted(params, key, old, val):
    """Returns the shifted guessBaseline level by adding up the shifting parameter"""
    prefix = ''
    if '_' in key:
        prefix = key.split('_')[0] + '_'
    val = params[prefix + 'guessBaseline'] + \
        (params[prefix + 'baselineShift'] / 1000.)
    return val

ConfigurationProxy.callbacks_get.add(calc_baseline_shifted)


def set_baseline_shifted(params, key, old, val):
    prefix = ''
    if '_' in key:
        prefix = key.split('_')[0] + '_'
    # Update the baseline shift value
    old_shift = old - params[prefix + 'guessBaseline']
    shift = val - params[prefix + 'guessBaseline']
    params[prefix + 'baselineShift'] = shift * 1000.
    params[prefix + 'guessTmax'] += old_shift-shift
    from misura.client.live import registry
    registry.force_redraw([params.getattr(prefix + 'baselineShift', 'kid')])
    registry.force_redraw([params.getattr(prefix + 'guessTmax', 'kid')])
    return val
    
ConfigurationProxy.callbacks_set.add(set_baseline_shifted)    
    
def calc_halftimes_multiple(conf, key, old, val):
    prefix = key.split('_')
    if len(prefix)>1:
        prefix = prefix[0]+'_'
    else:
        prefix = ''
    if (prefix+'halftimeSrc') not in conf:
        return val
    ht = conf[prefix+'halftimeSrc']
    if ht<=1e-20:
        return val
    if not conf.getattr(key, 'flags').get('enabled', True):
        return val
    d = ht*val
    n = conf.gete(prefix+'endTime')
    n['current'] = d
    conf.sete(prefix+'endTime', n)
    from misura.client.live import registry
    registry.force_redraw([n['kid']])
    registry.emit_client_changed(n['kid'])
    return val
    

ConfigurationProxy.callbacks_set.add(calc_halftimes_multiple)


def adjust_diameter_range(conf, key, old, val):
    """Set inner diameter as minimum for outer diameter 
    and outer diameter as maximum for inner diameter"""
    from misura.client.live import registry
    tol = 0.05
    
    # diameter was edited
    if key[-9:] == '_diameter':
        k0 = key[:-8]
        mx = val
        # Recursion-level sample diameter can be 0
        ks = (k0 + 'guessViewedOuter', k0 + 'guessIrradiatedOuter')
        for k in ks:
            old = conf.getattr(k, 'max')
            conf.setattr(k, 'max', min(mx, old))
            registry.force_redraw([conf.getattr(k, 'kid')])
    else:
        # Search for a specific section diameter set
        sec = key.split('_')[0]
        dia = search_diameter(conf, sec)
        if dia is not None and dia>0:
            old = conf.getattr(key, 'max')
            conf.setattr(key, 'max', min(dia, old))
        else:
            dia = 5.
            
    # one of inner/outer was edited
    if key[-5:] == 'Inner':
        nkey = key[:-5] + 'Outer'
        mn = min([val + val * tol, dia])
        old = conf.getattr(nkey, 'min')
        conf.setattr(nkey, 'min', max(mn,old))
        registry.force_redraw([conf.getattr(nkey, 'kid')])
    elif key[-5:] == 'Outer':
        nkey = key[:-5] + 'Inner'
        mx = max([val - val * tol, 0])
        old = conf.getattr(nkey, 'max')
        conf.setattr(nkey, 'max', min(old, mx))
        registry.force_redraw([conf.getattr(nkey, 'kid')])
    return val


ConfigurationProxy.callbacks_set.add(adjust_diameter_range)