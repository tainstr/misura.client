#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Import a single FlashLine shot"""
import numpy as np
from veusz import plugins
from misura.client import _

from misura.client.flash.flashline import dataparser

class FlashShotImportPlugin(plugins.ImportPlugin):
    """An example plugin for reading a set of unformatted numbers
    from a file."""

    name = "FlashShot"
    author = "Daniele Paganelli"
    description = "Imports a single FlashLine shot (.fw<n>)"

    # Uncomment this line for the plugin to get its own tab
    promote_tab='FlashShot'

    file_extensions = set(['.fw1', '.fw0'])

    def __init__(self):
        plugins.ImportPlugin.__init__(self)
        self.fields = [
            plugins.ImportFieldText("name", descr="Dataset name", default="shot"),
            ]

    def doImport(self, params):
        """Actually import data
        params is a ImportPluginParams object.
        Return a list of ImportDataset1D, ImportDataset2D objects
        """
        data, header = dataparser.channel(params.filename)
        data = data[:-3]
        t = np.arange(len(data), dtype='float')/header['frequency']
        name = params.field_results["name"]
        return [plugins.ImportDataset1D(name, data),
                plugins.ImportDataset1D(name+'_t', t)]

# add the class to the registry. An instance also works, but is deprecated
plugins.importpluginregistry.append(FlashShotImportPlugin)
