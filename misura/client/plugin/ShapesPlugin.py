#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Place datapoints on the characteristic shapes."""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.plugins as plugins
import veusz.document as document

from FieldMisuraNavigator import FieldMisuraNavigator
from InterceptPlugin import InterceptPlugin
import utils

# TODO: Estendere a tutte le opzioni di tipo Meta.
m4shapes = ['Sintering', 'Softening', 'Sphere', 'HalfSphere', 'Melting']

standards = {'Misura4': '', 'Misura3': 'm3_', 'CEN/TS': 'cen_'}

standard_filtering_predicates = {
    'Misura4': lambda shape_name: not '_' in shape_name,
    'Misura3': lambda shape_name: shape_name.startswith('m3_'),
    'CEN/TS': lambda shape_name: shape_name.startswith('cen_'),
}

def remove_prefix(shape_name):
    prefix = shape_name.split('_')[0]

    if prefix == shape_name:
        return shape_name

    return shape_name.replace('_', '').replace(prefix, '')

class ShapesPlugin(utils.OperationWrapper, plugins.ToolsPlugin):

    """Show Misura Microscope shapes in graphics"""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', 'Show characteristic shapes')
    # unique name for plugin
    name = 'Shapes'
    # name to appear on status tool bar
    description_short = 'Show characteristic shapes'
    # text to appear in dialog box
    description_full = 'Draw characteristic shapes on temperature and time graphs'

    def __init__(self, sample=None, temp=True, time=True, text='$shape$'):
        """Make list of fields."""
        #\\\\%(xlabel)s=%(x)i
        self.fields = [
            FieldMisuraNavigator("sample",
                                 descr="Target sample:",
                                 depth='sample',
                                 default=sample),
            plugins.FieldText('text', 'Label text', default=text),
            plugins.FieldCombo('characteristic_shape_standard',
                               descr='Standard',
                               default='Misura4',
                               items=standards.keys())
        ]

    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.ops = []
        self.doc = cmd.document
        smpe = fields['sample']
        p = smpe.path
        if '/sample' not in p:
            raise plugins.ToolsPluginException(
                'The target must be a sample or a sample dataset, found: ' + p)
        cur = fields['currentwidget']
        g = self.doc.resolveFullWidgetPath(cur)
        g = utils.searchFirstOccurrence(g, 'graph')
        if g is None or g.typename != 'graph':
            logging.debug('Found graph:', g)
            raise plugins.ToolsPluginException(
                'You should run this tool on a graph')
        logging.debug('ShapesPlugin searching', p)
        cur = g.path
        conf = False
        vds = []
        for k, ent in smpe.children.iteritems():
            conf = getattr(ent.ds, 'm_conf', False)
            if not conf:
                continue
            if len(ent.ds) > 0:
                vds.append(ent.path)
        if not conf or len(vds) == 0:
            raise plugins.ToolsPluginException('No metadata found for ' + p)
        logging.debug('Found datasets', vds)
        smpp = smpe.path.split(':')[-1]
        # Detect if a sample dataset was selected and go up one level
        if smpp.split('/')[-2].startswith('sample'):
            smpp = smpe.parent.path
        smpp = smpp.replace('summary', '')
        logging.debug('Found sample path', smpp, p)
        smp = conf.toPath(smpp)
        logging.debug('config', smp)

        all_items = smp.describe().iteritems()
        sample_shapes = filter(lambda item: item[1]['type'] == 'Meta', all_items)

        required_shapes_filter = standard_filtering_predicates[fields['characteristic_shape_standard']]
        required_sample_shapes = filter(lambda item: required_shapes_filter(item[0]), sample_shapes)

        for shape, opt in required_sample_shapes:
            pt = opt['current']
            t = pt['time']
            T = pt['temp']
            shape_name = str(fields['text']).replace('$shape$', remove_prefix(shape))
            txt = u'%s - %s °C' % (shape_name, pt['temp'])
            if t in [0, None, 'None'] or T in [0, None, 'None']:
                logging.debug('Shape not found:', shape)
                continue
            # Absolute time translations
            if t > conf['zerotime'] / 2:
                logging.debug('Absolute time translation', t, conf['zerotime'])
                t -= conf['zerotime']
            # Temperature plotting
            basename = smpe.path.replace('/', ':') + '_'
            val = T if 'temp' in cur.split('/') else t
            val = round(val, 0)
            logging.debug('Selected value based on ', shape, cur, val, pt,t, T)
            f = {'currentwidget': cur,
                 'axis': 'X',
                 'val': val,
                 'text': txt,
                 'basename': basename + shape,
                 'target': vds,
                 'search': 'Nearest (Fixed X)',
                 'searchRange': 5
                 }
            self.ops.append(
                document.OperationToolsPlugin(InterceptPlugin(), f))

        logging.debug('ShapesPlugin ops', self.ops)
        self.apply_ops()


plugins.toolspluginregistry.append(ShapesPlugin)
