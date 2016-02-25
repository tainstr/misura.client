#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Check discrepancies between current values and saved ones."""


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
    return '<h2>{}, <u>{}</u></h2><p>of type {}</p><br/>\n'.format(obj['fullpath'], obj['name'], obj['mro'][0],)


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


def wiring(obj):
    """Render a dot file representing all RoleIO relations."""
    """
    digraph structs {
        node [shape=record];
        A[label="<out1> first out|<out2> second out|<out3> third out"]
        B[label="<role1> first role|<role2> second role|<role3> third role"]
        A:out1 -> B:role2;
    }
    """
    desc = obj.describe()
    for k, opt in desc:
        if not opt['type'] == 'RoleIO':
            continue
        

if __name__ == '__main__':
    from misura.client import from_argv
    m = from_argv()
    output = configuration_check(m)
    print '\nOUTPUT\n\n'
    print render_configuration_check_txt(*output)
