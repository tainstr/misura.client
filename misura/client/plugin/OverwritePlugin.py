#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tool to overwrite two datasets."""
import veusz.plugins as plugins
import veusz.document as document
import utils
from copy import copy
from compiler.ast import flatten


class OverwritePlugin(utils.OperationWrapper, plugins.ToolsPlugin):

    """Overwrite two datasets."""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', 'Overwrite datasets')
    # unique name for plugin
    name = 'Overwrite'
    # name to appear on status tool bar
    description_short = 'Overwrite one dataset with another one'
    # text to appear in dialog box
    description_full = ('Overwrite dataset A with dataset B.'
                        'Optionally delete B dataset after operation.')

    def __init__(self, a='', b='', delete=False):
        """Make list of fields."""

        self.fields = [
            plugins.FieldDataset(
                'a', 'Dataset to be overwritten (A)', default=a),
            plugins.FieldDataset('b', 'Source dataset (B)', default=b),
            plugins.FieldBool('delete', 'Delete B dataset', default=delete),
        ]

    def apply(self, cmd, fields):
        """Do the work of the plugin.
        cmd: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        self.ops = []
        self.doc = cmd.document
        if fields['a'] == fields['b']:
            raise plugins.ToolsPluginException('A and B datasets must differ.')
        delete = fields['delete']
        a = self.doc.data[fields['a']]
        a1 = copy(a)
        b = self.doc.data[fields['b']]
        pm = getattr(b, 'pluginmanager', False)

        # Overwrite data
        a1.data = b.data[:]
        # Substitute A with update version A1
        self.ops.append(document.OperationDatasetSet(fields['a'], a1))

        # Delete B dataset, if requested
        if delete:
            self.ops.append(document.OperationDatasetDelete(fields['b']))

        self.apply_ops()


plugins.toolspluginregistry.append(OverwritePlugin)
