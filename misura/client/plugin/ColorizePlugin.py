#!/usr/bin/python
"""Set curve color markers"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.plugins as plugins

import utils


class ColorizePlugin(utils.OperationWrapper, plugins.ToolsPlugin):

    """Set color markers"""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', 'Colorize')
    # unique name for plugin
    name = 'Colorize'
    # name to appear on status tool bar
    description_short = 'Set color markers'
    # text to appear in dialog box
    description_full = 'Set color markers according to the "other" x coordinate (time or temperature).'
    preserve = True

    def __init__(self, curve='', x=''):
        """Make list of fields."""

        self.fields = [
            plugins.FieldWidget(
                "curve", descr="Curve:", widgettypes=set(['xy']), default=curve),
            plugins.FieldDataset("x", descr="Colorize by:", default=x),
        ]

    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.ops = []
        self.doc = cmd.document

        c = self.doc.resolveFullWidgetPath(fields['curve'])
        if c is None:
            c = self.doc.resolveFullWidgetPath(fields['currentwidget'])
            if c is None:
                raise plugins.ToolsPluginException(
                    'You should run this tool on a curve')

        g = utils.searchFirstOccurrence(c, 'graph', -1)
        if g is None or g.typename != 'graph':
            logging.debug('found', g, c)
            raise plugins.ToolsPluginException(
                'Error: Curve is not contained in a graph.')
        pts = fields['x']
        ds = self.doc.data.get(pts, False)
        if not ds:
            xds = self.doc.data.get(c.settings.xData, False)
            x = False
            if not xds or not xds.linked:
                pass
            elif c.settings.xData.endswith('T'):
                x = 't'
            elif c.settings.xData.endswith('t'):
                x = 'kiln/T'
            if x:
                if len(xds.linked.prefix):
                    x = xds.linked.prefix + ':' + x
                ds = self.doc.data.get(x, False)
                pts = x

        if not ds:
            raise plugins.ToolsPluginException(
                'Error: Cannot find a proper coloring dataset.')
        # Undo
        if c.settings.Color.points == pts:
            self.toset(c, 'Color/points', '')
            if c.settings.marker == u'circle':
                self.toset(c, 'marker', u'none')
        # Do
        else:
            self.toset(c, 'Color/points', pts)
            if c.settings.marker == u'none':
                self.toset(c, 'marker', u'circle')

        # Ranges
        self.toset(c, 'Color/min', min(ds.data))
        self.toset(c, 'Color/max', max(ds.data))
        self.toset(c, 'MarkerFill/colorMap', 'transblack')
        self.toset(c, 'MarkerFill/transparency', 10)
        self.toset(c, 'MarkerLine/hide', True)

        self.apply_ops()


plugins.toolspluginregistry.append(ColorizePlugin)
