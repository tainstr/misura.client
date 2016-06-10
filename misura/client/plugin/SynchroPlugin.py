#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Synchronize two curves."""
import veusz.plugins as plugins
import veusz.document as document
import numpy as np
from PyQt4 import QtGui, QtCore
import copy
import utils
from misura.client.plugin.cuvrve_label import CurveLabel

def get_nearest_index(data, value):
    dst = np.abs(data - value)
    return np.where(dst == dst.min())[0][0]



def check_consistency(reference_curve, translating_curve):
    if reference_curve.parent != translating_curve.parent:
        raise plugins.ToolsPluginException(
            'The selected curves must belong to the same graph.')
    if reference_curve.settings.yAxis != translating_curve.settings.yAxis or reference_curve.settings.xAxis != translating_curve.settings.xAxis:
        raise plugins.ToolsPluginException(
            'The selected curves must share the same x, y axes.')

def add_label_to(curve, message, label_name, doc, toset):
    doc.applyOperation(document.OperationWidgetAdd(curve,
                                                   'curvelabel', name=label_name))
    label = curve.getChild(label_name)
    toset(label, 'label', message)
    toset(label, 'xPos', 0.1)
    toset(label, 'yPos', 0.9)

class SynchroPlugin(utils.OperationWrapper, plugins.ToolsPlugin):

    """Translate curves so that they equal a reference curve at a known x-point"""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', 'Synchronize two curves')
    # unique name for plugin
    name = 'Synchro'
    # name to appear on status tool bar
    description_short = 'Synchronize'
    # text to appear in dialog box
    description_full = 'Synchronize two or more curves so they equals to a reference curve at the requested x-point.'

    def __init__(self, reference_curve_full_path='/', translating_curve_full_path='/'):
        """Make list of fields."""

        self.fields = [
            plugins.FieldWidget(
                "ref", descr="Reference curve:", widgettypes=set(['xy']), default=reference_curve_full_path),
            plugins.FieldWidget(
                "trans", descr="Translating curve:", widgettypes=set(['xy']), default=translating_curve_full_path),
            plugins.FieldFloat("matching_x_value", descr="Matching X Value", default=0.),
            #			plugins.FieldDatasetMulti('dslist','')
            plugins.FieldCombo("mode", descr="Translation Mode:", items=[
                               'Translate Values', 'Translate Axes'], default="Translate Values")
        ]

    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.ops = []
        doc = cmd.document
        self.doc = doc
        reference_curve = doc.resolveFullWidgetPath(fields['ref'])
        translating_curve = doc.resolveFullWidgetPath(fields['trans'])

        check_consistency(reference_curve, translating_curve)

        # TODO: selezionare l'asse anziché due curve.
        # Altrimenti, altre curve riferentesi all'asse originario verrebbero
        # sfalsate quando le sue dimensioni si aggiornano!


        reference_curve_nearest_value_index = get_nearest_index(
            doc.data[reference_curve.settings.xData].data,
            fields['matching_x_value']
        )

        translating_curve_nearest_value_index = get_nearest_index(
            doc.data[translating_curve.settings.xData].data,
            fields['matching_x_value']
        )

        translating_dataset_name = translating_curve.settings.yData
        translating_dataset = doc.data[translating_dataset_name]

        reference_dataset = doc.data[reference_curve.settings.yData]

        delta = translating_dataset.data[translating_curve_nearest_value_index] - reference_dataset.data[reference_curve_nearest_value_index]

        message = {
            'Translate Values': "Translated curve '%s' by %E %s." % (translating_dataset_name, delta, translating_dataset.unit),
            'Translate Axes': "Translated Y axis by %E %s." % (delta, translating_dataset.unit)
        }[fields['mode']]

        translate = {
            'Translate Values': lambda: self.translate_values(
                translating_dataset,
                translating_dataset_name,
                delta,
                doc,
                message
            ),
            'Translate Axes': lambda: self.translate_axis(
                cmd,
                reference_curve.parent.getChild(reference_curve.settings.yAxis),
                translating_curve,
                delta,
                doc,
                message
            )
        }[fields['mode']]

        label_name = 'sync_info_' + translating_dataset_name.replace('/', ':')
        add_label_to(translating_curve, message, label_name, doc, self.toset)

        return translate()

    def translate_axis(self, cmd, dataset, translating_curve, delta, doc, message):
        # Create a new Y axis
        ypath = cmd.CloneWidget(dataset.path,
                                translating_curve.parent.path,
                                newname='Trans_' + dataset.name)
        new_y_axis = doc.resolveFullWidgetPath(ypath)
        self.toset(new_y_axis, 'label', 'Trans: ' + dataset.settings.label)
        self.toset(new_y_axis, 'Line/transparency', 30)
        self.toset(new_y_axis, 'MajorTicks/transparency', 30)
        self.toset(new_y_axis, 'MinorTicks/transparency', 30)
        self.toset(new_y_axis, 'Label/italic', True)

        newmin, newmax = dataset.getPlottedRange()
        # Remove Auto ranges from reference axis
        self.toset(dataset, 'max', float(newmax))
        self.toset(dataset, 'min', float(newmin))
        self.toset(new_y_axis, 'max', float(newmax + delta))
        self.toset(new_y_axis, 'min', float(newmin + delta))
        self.toset(translating_curve, 'yAxis', new_y_axis.name)

        self.apply_ops()
        return True

    def translate_values(self, dataset, dataset_name, delta, doc, message):
        translated_data = dataset.data - delta
        translated_dataset = copy.copy(dataset)
        translated_dataset.data = translated_data
        op = document.OperationDatasetSet(dataset_name, translated_dataset)
        self.ops.append(op)

        self.apply_ops()
        return True



plugins.toolspluginregistry.append(SynchroPlugin)
