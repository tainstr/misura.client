#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Simple plotting for browser and live acquisition."""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from veusz import plugins
import veusz.document as document
import utils
from misura.canon import csutil 
from misura.client.clientconf import confdb
from misura.client.axis_selection import get_best_x_for

TIME_GRAPH = 0
TEMP_GRAPH = 1
graph_suffixes = {TIME_GRAPH:'_t', TEMP_GRAPH:'_T'}
graph_names = {TIME_GRAPH: 'time', TEMP_GRAPH:'temp'}
axis_labels = {TIME_GRAPH: 'Time', TEMP_GRAPH:'Temperature'}

class SwitchOrdinatePlugin(utils.OperationWrapper, plugins.ToolsPlugin):
    menu = ('Misura','Switch time/temperature')
    # unique name for plugin
    name = 'Switch ordinate'
    # name to appear on status tool bar
    description_short = 'Copy page and switch t/T ordinate'
    # text to appear in dialog box
    description_full = 'Copy current page and switch time/temperature ordinate for all elements'
    
    def __init__(self, source='', destination='/'):
        """Make list of fields."""

        self.fields = [
            plugins.FieldWidget(
                "source", descr="Source graph", widgettypes=set(['graph']), 
                default=source),
            plugins.FieldWidget(
                "destination", descr="Destination graph (empty to create)", 
                widgettypes=set(['graph', 'document']), 
                default=destination),
        ]
        
    def switch_xy(self, wg, dest_type):
        yData = wg.settings.yData
        xData = wg.settings.xData
        ds = self.doc.data[yData]
        prefix = '' if not ds.linked else ds.linked.prefix
        new_x = get_best_x_for(yData, prefix, self.doc.data, graph_suffixes[dest_type])
        if new_x == xData:
            logging.debug('No change', wg.path, xData)
            return False
        logging.debug('Switching', wg.path, xData, new_x)
        op = document.OperationSettingSet(wg.settings.get('xData'), new_x)
        self.ops.append(op)
        # Transform subordered datapoints
        for sub in wg.children:
            if not sub.typename=='datapoint':
                continue
            xpos = self.doc.data[new_x].data[sub.settings.pointIndex]
            logging.debug('Moved datapoint', sub.path, sub.point_index, sub.settings.xPos, xpos)
            op = document.OperationSettingSet(sub.settings.get('xPos'), xpos)
            self.ops.append(op)
            
    def switch_axis(self, wg, dest_type):
        if wg.settings.direction == 'vertical':
            return False
        op = document.OperationSettingSet(wg.settings.get('label'), axis_labels[dest_type])
        self.ops.append(op)
        
    def apply(self, cmd, fields):
        if fields['source']==fields['destination']:
            raise plugins.ToolsPluginException(
                'Destination cannot be equal to source')
        self.ops = []
        self.fields = fields
        doc = cmd.document
        self.doc = doc
        source_graph = self.doc.resolveFullWidgetPath(fields['source'])
        source_page = utils.searchFirstOccurrence(source_graph, 'page', -1)
        source_type = TIME_GRAPH
        sgp = source_graph.path
        spp = source_page.path
        
        if 'temperature' in (sgp[-11:], spp[-11:]) or '_T' in (sgp[-2:], spp[-2:]):
            source_type = TEMP_GRAPH
            
        dest_type = not source_type
        suffix = graph_suffixes[dest_type]
        
        destination_graph, destination_page = False, False
        destination_graph_path = False
        
        if fields['destination']!='/':
            destination_graph = self.doc.resolveFullWidgetPath(fields['destination'])
            destination_page = utils.searchFirstOccurrence(destination_graph, 'page', -1)
            destination_page_path = destination_page.path
            destination_graph_path = destination_graph.path
            # Delete destination graph
            op = document.OperationWidgetDelete(destination_graph)
            self.ops.append(op)
        # New destination page
        elif source_page.name in ('time', 'temperature'):
            destination_page_path = '/from_{}_to{}'.format(source_page.name, suffix)  
        else:
            # Remove previous suffix
            page = source_page.path
            if page[-2:] in ('_t', '_T'):
                page = page[:-2]
            destination_page_path = page+suffix
        
        # New destination graph path
        if not destination_graph_path:
            destination_graph_path = destination_page_path+'/'+graph_names[dest_type]
            
        # Create destination page if missing
        if not destination_page:
            op = document.OperationWidgetAdd(self.doc.basewidget, 'page', 
                                             name=destination_page_path[1:])
            self.ops.append(op)
            self.apply_ops()
            destination_page = self.doc.resolveFullWidgetPath(destination_page_path)
            
        # Clone source graph into destination page
        op = document.OperationWidgetClone(source_graph, destination_page, destination_graph_path.split('/')[-1])
        self.ops.append(op)
        self.apply_ops()
        
        destination_graph = self.doc.resolveFullWidgetPath(destination_graph_path)
        
        for wg in destination_graph.children:
            func = getattr(self, 'switch_'+wg.typename, False)
            if not func:
                continue
            func(wg, dest_type)
        self.apply_ops('Switch ordinates')


plugins.toolspluginregistry.append(SwitchOrdinatePlugin)