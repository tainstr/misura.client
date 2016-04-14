#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Simple plotting for browser and live acquisition."""
from misura.canon.logger import Log as logging
from misura.canon import version as canon_version
from misura.client import version as client_version
import veusz.plugins
import veusz.document as document
import utils


class MakeDefaultDoc(utils.OperationWrapper, veusz.plugins.ToolsPlugin):

    def __init__(self, page='', title=False, time=True, temp=True):
        """Make list of fields."""

        self.fields = [
            veusz.plugins.FieldText(
                "page", descr="Base page name", default=page),
            veusz.plugins.FieldBool(
                "title", descr="Make title label", default=title),
            veusz.plugins.FieldBool(
                "time", descr="Create time page", default=time),
           veusz.plugins.FieldBool(
                "temp", descr="Create temperature page", default=temp)
        ]
        
    def adjust_graph(self, g, label):
        y = g.getChild('y')
        if y is not None:
            self.ops.append(document.OperationWidgetDelete(y))
        props = {'rightMargin': '1.5cm', 'leftMargin': '1.5cm',
                 'bottomMargin': '1.5cm', 'topMargin': '1.5cm'}
        self.dict_toset(g, props)
        self.toset(g.getChild('x'), 'label', label)
        self.toset(g, 'topMargin', '1.5cm')
        if self.fields.get('title', False):
            props = {'xPos': 0.1, 'yPos': 0.96, 'label': 'Title'}
            self.dict_toset(g.parent.getChild('title'), props)
        
    def create_page_temperature(self, page):
        self.ops.append(
                            (document.OperationWidgetAdd(self.doc.basewidget, 'page', name=page))) 
        self.apply_ops(descr='MakeDefaultPlot: Page '+page)
        wg = self.doc.basewidget.getChild(page)
        self.ops.append(
            (document.OperationWidgetAdd(wg, 'graph', name='temp')))
        self.apply_ops(descr='MakeDefaultPlot: Graph Temperature')
        if self.fields.get('title', False):
            self.ops.append(
                (document.OperationWidgetAdd(wg, 'label', name='title')))
            self.apply_ops(descr='MakeDefaultPlot: Temperature Title')
        graph = wg.getChild('temp')
        self.adjust_graph(graph, u'Temperature (°C)')
        
    def create_page_time(self, page):      
        self.ops.append(
            (document.OperationWidgetAdd(self.doc.basewidget, 'page', name=page)))
        self.apply_ops(descr='MakeDefaultPlot: Page '+page)
        wg = self.doc.basewidget.getChild(page)
        self.ops.append(
            (document.OperationWidgetAdd(wg, 'graph', name='time')))
        self.apply_ops(descr='MakeDefaultPlot: Graph Time')
        if self.fields.get('title', False):
            self.ops.append(
                (document.OperationWidgetAdd(wg, 'label', name='title')))
            self.apply_ops(descr='MakeDefaultPlot: Time Title')
        graph = wg.getChild('time')
        self.adjust_graph(graph, 'Time (s)')
        
        
    def apply(self, cmd, fields):
        self.ops = []
        self.fields = fields
        doc = cmd.document
        self.doc = doc
        # If no target page is specified, must wipe the doc
        page_T = 'temperature'
        page_t = 'time'
        base_page = fields.get('page','')
        if not base_page:
            self.doc.wipe()
        else:
            page_T = base_page + '_T'
            page_t = base_page + '_t' 
        
        self.dict_toset(doc.basewidget, {'width': '20cm', 'height': '20cm'})
        
        if fields.get('temp', True):
            self.create_page_temperature(page_T)
        if fields.get('time', True):
            self.create_page_time(page_t)  
        
        self.add_versions_to_file()
        self.apply_ops('MakeDefaultDoc: Done')
        return True

    def add_versions_to_file(self):
        command_interface = document.CommandInterface(self.doc)
        command_interface.AddCustom(u"constant",
                                    u"canon_version",
                                    canon_version.__version__.replace(".", "-"))
        command_interface.AddCustom(u"constant",
                                    u"client_version",
                                    client_version.__version__.replace(".", "-"))
        command_interface.AddCustom(u"constant",
                                    u"vsz_file_format_version",
                                    client_version.__vsz_file_format_version__)


def makeDefaultDoc(cmd, title=False):
    """Make default temperature/time pages"""
    p = MakeDefaultDoc()
    p.apply(cmd, {'title': title})

# INTENTIONALLY NOT PUBLISHED
# plugins.toolspluginregistry.append(MakeDefaultDoc)
