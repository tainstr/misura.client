#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Synchronize two curves."""
import veusz.plugins as plugins
import veusz.document as document
import numpy as np
import copy
import utils
from misura.client.plugin.curve_label import CurveLabel

from misura.canon.logger import get_module_logging
from veusz.plugins.datasetplugin import AddDatasetPlugin
logging = get_module_logging(__name__)


def get_nearest_index(data, value):
    dst = np.abs(data - value)
    return np.where(dst == dst.min())[0][0]



def check_consistency(reference_curve, translating_curve):
    if reference_curve.parent != translating_curve.parent:
        raise plugins.ToolsPluginException(
            'The selected curves must belong to the same graph.')
    #if reference_curve.settings.yAxis != translating_curve.settings.yAxis or reference_curve.settings.xAxis != translating_curve.settings.xAxis:
    #    raise plugins.ToolsPluginException(
    #        'The selected curves must share the same x, y axes.')

def add_label_to(curve, message, label_name, doc, toset):
    if not curve.hasChild(label_name):
        doc.applyOperation(document.OperationWidgetAdd(curve,
                                                       'curvelabel', name=label_name))

    label = curve.getChild(label_name)
    toset(label, 'label', message)
    toset(label, 'xPos', 0.1)
    toset(label, 'yPos', 0.9)

class SynchroPlugin(utils.OperationWrapper, plugins.ToolsPlugin):

    menu = ('Misura', 'Synchronize two curves')
    name = 'Synchro'
    description_short = 'Synchronize'
    description_full = 'Synchronize two or more curves so they equals to a reference curve at the requested x-point.'

    def __init__(self, *paths):
        
        logging.debug('SynchroPlugin init', paths)
        paths = list(paths)
        if len(paths)<2:
            paths += ['']*(2-len(paths))
        self.fields = [
            plugins.FieldWidget("reference_curve",
                                descr="Reference curve:",
                                widgettypes=set(['xy']),
                                default=paths.pop(0)),
            ]

        for i,p in enumerate(paths):
            self.fields.append(plugins.FieldWidget("translating_curve_{}".format(i+1),
                                                   descr="Translating curve {}:".format(i+1),
                                                   widgettypes=set(['xy']),
                                                   default=p))

        self.fields = self.fields + [
            plugins.FieldFloat("matching_x_value",
                               descr="Matching X Value",
                               default=0.),
            plugins.FieldCombo("mode",
                               descr="Translation Mode:",
                               items=['Translate Values', 'Create new datasets', 'Translate Axes'],
                               default="Create new datasets")
        ]

    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.ops = []
        self.cmd = cmd
        doc = cmd.document
        self.doc = doc
        reference_curve = doc.resolveFullWidgetPath(fields['reference_curve'])
        paths = []
        message = ''
        while True:
            i = len(paths)+1
            name = 'translating_curve_{}'.format(i)
            try:
                crv = doc.resolveFullWidgetPath(fields[name])
                paths.append( crv )
                check_consistency(reference_curve, crv)
                message += '\\\\' + self.synchronize_curves(reference_curve,
                                              crv,
                                              fields,
                                              doc)
            except:
                break

        message = message[2:]
        label_name = 'sync_info_' + reference_curve.settings.yData.replace('/', ':')
        add_label_to(reference_curve, message, label_name, doc, self.toset)
        self.apply_ops()

    def synchronize_curves(self, reference_curve, translating_curve, fields, doc):
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
        print 'MODE', fields['mode']
        if fields['mode'] in ('Translate Values', 'Create new datasets'):
            message = "Translated curve '%s' by %E %s." % (translating_dataset_name, delta, getattr(translating_dataset, 'unit', ''))
            if fields['mode'].startswith('Create'):
                self.translate_derived(translating_dataset_name, delta)
            else:
                self.translate_values(
                    translating_dataset,
                    translating_dataset_name,
                delta)
        else:
            message = "Translated Y axis by %E %s." % (delta, getattr(translating_dataset, 'unit', ''))
            self.translate_axis(
                self.cmd,
                reference_curve.parent.getChild(reference_curve.settings.yAxis),
                translating_curve,
                delta,
                reference_curve,
                doc)
        
        return message

    def translate_axis(self, cmd, dataset, translating_curve, delta, reference_curve, doc):
        # Create a new Y axis
        
        if reference_curve.settings.yAxis == translating_curve.settings.yAxis:
            logging.debug('Cloning ax for translating sync')
            ypath = cmd.CloneWidget(dataset.path,
                                    translating_curve.parent.path,
                                    newname='Trans_' + dataset.name)
            new_y_axis = doc.resolveFullWidgetPath(ypath)
            self.toset(new_y_axis, 'label', 'Trans: ' + dataset.settings.label)
            self.toset(new_y_axis, 'Line/transparency', 30)
            self.toset(new_y_axis, 'MajorTicks/transparency', 30)
            self.toset(new_y_axis, 'MinorTicks/transparency', 30)
            self.toset(new_y_axis, 'Label/italic', True)
            self.toset(translating_curve, 'yAxis', new_y_axis.name)
        else:
            logging.debug('Reusing ax for translating sync')
            new_y_axis = doc.resolveFullWidgetPath(translating_curve.parent.path+ '/'+ 
                                                   translating_curve.settings.yAxis)
            
        newmin, newmax = dataset.getPlottedRange()
        # Remove Auto ranges from reference axis
        self.toset(dataset, 'max', float(newmax))
        self.toset(dataset, 'min', float(newmin))
        self.toset(new_y_axis, 'max', float(newmax + delta))
        self.toset(new_y_axis, 'min', float(newmin + delta))
        
        return True

    def translate_values(self, dataset, dataset_name, delta):
        translated_data = dataset.data - delta
        translated_dataset = copy.copy(dataset)
        translated_dataset.data = translated_data
        op = document.OperationDatasetSet(dataset_name, translated_dataset)
        self.ops.append(op)
        return True
    
    def translate_derived(self, dataset_name, delta):
        op = document.OperationDatasetPlugin(AddDatasetPlugin(), {'ds_in': dataset_name, 
                                                                    'ds_out': dataset_name+'/sync',
                                                                    'value': -delta})
        self.ops.append(op)  
        return True



plugins.toolspluginregistry.append(SynchroPlugin)
