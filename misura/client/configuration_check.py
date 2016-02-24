#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Check discrepancies between current values and saved ones."""

def configuration_check(obj, output=False, iterate=True):
    print 'configuration_check ',obj['fullpath']
    if output is False:
        output = []
    desc = obj.describe()
    for k, opt in desc.iteritems():
        if k in ('log', 'preset'):
            continue
        if 'Runtime' in opt['attr']:
            continue
        print '...',k
        comparison = obj.compare_presets(k)
        if comparison is None:
            #TODO: manage server-side
            output.append((opt, 'MISSING'))
            continue
        vals = [repr(v) for v in comparison.values()]
        # No change in configurations
        if len(set(vals)) == 1:
            continue
        print opt['kid'], comparison
        output.append((opt, comparison))

    if iterate:
        for obj in obj.devices:
            configuration_check(obj, output, iterate)

    return output

def render_configuration_check(output):
    render = ''
    for opt, comparison in output:
        render += '{}: {}\n'.format(opt['kid'], comparison)
        
    return render

if __name__ == '__main__':
    from misura.client import from_argv
    m = from_argv()
    output = configuration_check(m)
    print '\nOUTPUT\n\n'
    print render_configuration_check(output)