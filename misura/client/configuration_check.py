#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Check discrepancies between current values and saved ones."""

def configuration_check(obj, output=False, columns=False, iterate=True):
    print 'configuration_check ',obj['fullpath']
    if output is False:
        output = []
    if columns is False:
        columns = []
    desc = obj.describe()
    for k, opt in desc.iteritems():
        if k in ('log', 'preset','running'):
            continue
        if 'Runtime' in opt['attr']:
            continue
        comparison = obj.compare_presets(k)
        if comparison is None:
            #TODO: manage server-side
            output.append((opt, 'MISSING'))
            continue
        for k in comparison.keys():
            if k not in columns: columns.append(k)
        vals = [repr(v) for v in comparison.values()]
        # No change in configurations
        if len(set(vals)) == 1:
            continue
        print opt['kid'], comparison
        output.append((opt, comparison))

    if iterate:
        for obj in obj.devices:
            configuration_check(obj, output, columns, iterate)

    return output, columns

def render_configuration_check_txt(output, columns):
    render = ''
    for opt, comparison in output:
        render += '{}: {}\n'.format(opt['kid'], comparison)
        
    return render

def render_configuration_check(output, columns):
    render = '<html><body><table  border="1" cellpadding="4" font="Monospace"><tr><th>Path</th>'
    for col in columns:
        render += '<th>{}</th>'.format(col)
    render += '</tr>\n'
    for opt,comparison in output:
        render += '<tr><td>{}</td>\n'.format(opt['handle'])
        for col in columns:
            val = comparison.get(col, '')
            render += '<td>{}</td>\n'.format(val)
        render += '</tr>\n'
    render += '</table></body></html>'
    print render
    return render
    

if __name__ == '__main__':
    from misura.client import from_argv
    m = from_argv()
    output = configuration_check(m)
    print '\nOUTPUT\n\n'
    print render_configuration_check_txt(*output)