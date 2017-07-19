#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Simple plotting for browser and live acquisition."""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon import version as canon_version
from misura.client import version as client_version
import veusz.plugins
import veusz.document as document
import utils


class MakeDefaultDoc(utils.OperationWrapper, veusz.plugins.ToolsPlugin):

    def __init__(self, page='', title='', time=True, temp=True, grid=False):
        """Make list of fields."""

        self.fields = [
            veusz.plugins.FieldText(
                "page", descr="Base page name", default=page),
            veusz.plugins.FieldText(
                "title", descr="Make title label", default=title),
            veusz.plugins.FieldBool(
                "time", descr="Create time page", default=time),
           veusz.plugins.FieldBool(
                "temp", descr="Create temperature page", default=temp),
           veusz.plugins.FieldBool(
                "grid", descr="Host graphs in a grid", default=grid)
        ]

    def adjust_graph(self, g, label):
        y = g.getChild('y')
        if y is not None:
            self.ops.append(document.OperationWidgetDelete(y))
        props = {'rightMargin': '1.5cm', 'leftMargin': '1.5cm',
                 'bottomMargin': '1.5cm', 'topMargin': '16pt'}
        self.dict_toset(g, props)
        self.toset(g.getChild('x'), 'label', label)
        self.toset(g, 'topMargin', '16pt')

    
    def create_page_and_grid(self, page):
        self.ops.append(
                            (document.OperationWidgetAdd(self.doc.basewidget, 'page', name=page)))
        self.apply_ops(descr='MakeDefaultPlot: Page '+page)
        wg = self.doc.basewidget.getChild(page)
        if self.fields.get('grid', False):
            self.ops.append(document.OperationWidgetAdd(wg, 'grid', name='grid'))
            self.apply_ops(descr='MakeDefaultPlot: Grid')
            wg = wg.getChild('grid')
            self.toset(wg, 'topMargin', '16pt')
        return wg 
    
    def make_title(self, page_wg, title):
        if self.fields.get('grid', False):
            page_wg = page_wg.parent
        self.ops.append(
                (document.OperationWidgetAdd(page_wg, 'label', name='title')))
        self.apply_ops(descr='MakeDefaultPlot: Title')
        props = {'xPos': 0.1, 'yPos': 1, 'label': title, 'alignVert': 'top'}
        label=page_wg.getChild('title')
        self.dict_toset(label, props)
        self.dict_toset(page_wg, {'notes': title})
        self.ops.append(document.OperationWidgetMove(label.path,page_wg.path,0))
        return True

    def create_page_temperature(self, page):
        wg = self.create_page_and_grid(page)
        self.ops.append(document.OperationWidgetAdd(wg, 'graph', name='temp'))
        self.apply_ops(descr='MakeDefaultPlot: Graph Temperature')
        title = self.fields.get('title', False) or 'By Temperature'
        self.make_title(wg, title)
        graph = wg.getChild('temp')
        self.adjust_graph(graph, u'Temperature (°C)')

    def create_page_time(self, page):
        wg = self.create_page_and_grid(page)
        self.ops.append(
            (document.OperationWidgetAdd(wg, 'graph', name='time')))
        self.apply_ops(descr='MakeDefaultPlot: Graph Time')
        title = self.fields.get('title', False) or 'By time'
        self.make_title(wg, title)
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
            self.wipe_doc_preserving_filename()
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

    def wipe_doc_preserving_filename(self):
        name = self.doc.filename
        pname = self.doc.proxy_filename
        self.doc.wipe()
        self.doc.filename = name
        self.doc.proxy_filename = pname

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


def makeDefaultDoc(cmd, title=''):
    """Make default temperature/time pages"""
    p = MakeDefaultDoc()
    p.apply(cmd, {'title': title})

# INTENTIONALLY NOT PUBLISHED
# plugins.toolspluginregistry.append(MakeDefaultDoc)
