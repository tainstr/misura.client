#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Simple plotting for archive and live acquisition."""
from misura.canon.logger import Log as logging
import veusz.plugins
import veusz.document as document
import utils


class MakeDefaultDoc(utils.OperationWrapper, veusz.plugins.ToolsPlugin):

    def __init__(self):
        """Make list of fields."""

        self.fields = [veusz.plugins.FieldBool("title", descr="Make title label", default=False)
                       ]

    def apply(self, cmd, fields={'title': False}):
        self.ops = []
        doc = cmd.document
        self.doc = doc
        self.doc.wipe()
        self.ops.append(
            (document.OperationWidgetAdd(doc.basewidget, 'page', name='temperature')))
        self.ops.append(
            (document.OperationWidgetAdd(doc.basewidget, 'page', name='time')))
        self.apply_ops(descr='MakeDefaultPlot: Pages')
        temp = doc.basewidget.getChild('temperature')
        time = doc.basewidget.getChild('time')
        self.ops.append(
            (document.OperationWidgetAdd(temp, 'graph', name='temp')))
        self.ops.append(
            (document.OperationWidgetAdd(time, 'graph', name='time')))
        self.apply_ops(descr='MakeDefaultPlot: Graphs')
        gtemp = temp.getChild('temp')
        gtime = time.getChild('time')

        if fields['title']:
            self.ops.append(
                (document.OperationWidgetAdd(time, 'label', name='title')))
            self.ops.append(
                (document.OperationWidgetAdd(temp, 'label', name='title')))
            self.apply_ops(descr='MakeDefaultPlot: Labels')

        self.dict_toset(doc.basewidget, {'width': '20cm', 'height': '20cm'})
        labels = ['Time (s)', u'Temperature (°C)']
        for i, g in enumerate([gtime, gtemp]):
            y = g.getChild('y')
            if y is not None:
                self.ops.append(document.OperationWidgetDelete(y))
            props = {'rightMargin': '1.5cm', 'leftMargin': '1.5cm',
                     'bottomMargin': '1.5cm', 'topMargin': '1.5cm'}
            self.dict_toset(g, props)
            self.toset(g.getChild('x'), 'label', labels[i])
            if not fields['title']:
                logging.debug('%s', 'Skipping title creation')
                continue
            self.toset(g, 'topMargin', '1.5cm')
            props = {'xPos': 0.1, 'yPos': 0.96, 'label': 'Title'}
            self.dict_toset(g.parent.getChild('title'), props)
        self.apply_ops('MakeDefaultDoc: Custom')
#		doc.setModified(True)
#		doc.setModified(False)


def makeDefaultDoc(cmd, title=False):
    """Make default temperature/time pages"""
    p = MakeDefaultDoc()
    p.apply(cmd, {'title': title})

# INTENTIONALLY NOT PUBLISHED
# plugins.toolspluginregistry.append(MakeDefaultDoc)
