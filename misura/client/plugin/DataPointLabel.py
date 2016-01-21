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

    def update(self):
        """Update output label with the coordinates of the point."""
        s = self.parent.settings
        txt = s.labelText
        var = {'xlabel': self.parent.xAx.settings.label,
               'ylabel': self.parent.yAx.settings.label,
               'x': self.parent.x,	'y': self.parent.y}
        txt = txt % var
        self.parent.toset(self, 'label', txt)
        self.parent.toset(self, 'positioning', 'axes')
        self.parent.cpset(self.parent, self, 'xAxis')
        self.parent.cpset(self.parent, self, 'yAxis')
        xsig = 5
        if self.parent.x / self.parent.xRange > 0.7:
            xsig = -15
        ysig = 2
        if self.parent.y / self.parent.yRange > 0.7:
            ysig = -4
        self.parent.toset(self, 'xPos', self.parent.x + xsig * self.parent.xRange / 100)
        self.parent.toset(self, 'yPos', self.parent.y)
        # Styling
        self.parent.toset(self, 'Text/color', self.parent.xy.settings.PlotLine.color)

document.thefactory.register(DataPointLabel)
