#!/usr/bin/python
# -*- coding: utf-8 -*-

import veusz.document as document
from veusz.widgets import Line

class DataPointLine(Line):
    typename = 'datapointline'
    description = "Line for datapoints"

    def __init__(self, *args, **kwargs):
        Line.__init__(self, *args, **kwargs)
        if type(self) == DataPointLine:
            self.readDefaults()


    @classmethod
    def allowedParentTypes(klass):
        """Get types of widgets this can be a child of."""
        from misura.client.plugin.datapoint import DataPoint
        return (DataPoint,)


document.thefactory.register(DataPointLine)
