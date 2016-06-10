#!/usr/bin/python
# -*- coding: utf-8 -*-

import veusz.document as document
from veusz.widgets.textlabel import TextLabel

class CurveLabel(TextLabel):
    typename = 'curvelabel'
    description = "Label for curves"

    def __init__(self, *args, **kwargs):
        TextLabel.__init__(self, *args, **kwargs)
        if type(self) == CurveLabel:
            self.readDefaults()

    @classmethod
    def allowedParentTypes(klass):
        """Get types of widgets this can be a child of."""
        from veusz.widgets.point import PointPlotter
        return (PointPlotter,)

    def setText(self, text):
        self.label = text


document.thefactory.register(CurveLabel)
