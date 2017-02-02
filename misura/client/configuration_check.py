#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Check discrepancies between current values and saved ones."""
import tempfile
import os
import subprocess

def configuration_check(obj):
    print 'configuration_check ', obj['fullpath']
    output = []
    columns = ['***current***']
    desc = obj.describe()
    for k, opt in desc.iteritems():
        if k in ('log', 'preset', 'running', 'mro'):
            continue
        if 'Runtime' in opt['attr']:
            continue
        if opt['type'] == 'Button':
            continue
        comparison = None
        if obj.compare_presets:
            comparison = obj.compare_presets(k)
        if comparison is None:
            # TODO: manage server-side
            output.append((opt, 'MISSING'))
            continue
        for k in comparison.keys():
            if k not in columns:
                columns.append(k)
        vals = [repr(v) for v in comparison.values()]
        # No change in configurations
        if len(set(vals)) == 1:
            continue
        print opt['kid'], comparison
        output.append((opt, comparison))
    return output, columns


def render_configuration_check_txt(output, columns):
    render = ''
    for opt, comparison in output:
        render += '{}: {}\n'.format(opt['kid'], comparison)

    return render


def render_configuration_check(output, columns):
    render = '<table  border="1" cellpadding="4" font="Monospace">\n<tr><th>Path</th>'
    for col in columns:
        render += '<th>{}</th>'.format(col)
    render += '</tr>\n'
    for opt, comparison in output:
        if comparison is 'MISSING':
            continue
        render += '<tr><td>{}</td>\n'.format(opt['handle'])
        for col in columns:
            val = comparison.get(col, '')
            render += '<td><pre>{}</pre></td>\n'.format(val)
        render += '</tr>\n'
    render += '</table><br/>\n'
    return render


def object_header(obj):
    mro ='Unknown' if not len(obj['mro']) else obj['mro'][0]
    return '<h2>{}, <u>{}</u></h2><p>of type {}</p><br/>\n'.format(obj['fullpath'], obj['name'], mro,)


def recursive_configuration_check(obj, final=True):
    render = ''
    if final:
        render += '<html><body>\n'
        render = object_header(obj)
        output, columns = configuration_check(obj)
        render += render_configuration_check(output, columns)

    for child in obj.devices:
        output, columns = configuration_check(child)
        if len(output) > 0:
            render += object_header(child)
            render += render_configuration_check(output, columns)
        render += recursive_configuration_check(child, final=False)

    if final:
        render += '\n</body></html>'
    return render


def render_wiring(dot):
    """Render wiring dot graph to temporary svg file.
    Return rendered file path"""
    print 'GRAPH:\n',dot
    handle, filename = tempfile.mkstemp()
    print 'tmpfile',handle, filename
    os.write(handle, dot)
    os.close(handle)
    out = subprocess.check_output('dot -O -T svg {}'.format(filename), shell=True)
    print 'dot call:', out
    svg_filename = filename+'.svg'
    os.remove(filename)
    return svg_filename

        

if __name__ == '__main__':
    from misura.client import from_argv
    m = from_argv()
    output = configuration_check(m)
    print '\nOUTPUT\n\n'
    print render_configuration_check_txt(*output)
