#!/usr/bin/python
# -*- coding: utf-8 -*-

import veusz.document as document
from veusz.widgets.textlabel import TextLabel

class DataPointLabel(TextLabel):
    typename = 'datapointlabel'
    description = "Label for datapoints"

    @classmethod
    def allowedParentTypes(klass):
        """Get types of widgets this can be a child of."""
        from misura.client.plugin.datapoint import DataPoint
        return (DataPoint,)

document.thefactory.register(DataPointLabel)
