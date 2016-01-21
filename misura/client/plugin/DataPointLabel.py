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
        datapoint = self.parent

        text_values = {'xlabel': datapoint.xAx.settings.label,
                       'ylabel': datapoint.yAx.settings.label,
                       'x': datapoint.x,
                       'y': datapoint.y}
        datapoint.toset(self, 'label', datapoint.settings.labelText % text_values)
        datapoint.toset(self, 'positioning', 'axes')
        datapoint.cpset(datapoint, self, 'xAxis')
        datapoint.cpset(datapoint, self, 'yAxis')
        xsig = 5
        if datapoint.x / datapoint.xRange > 0.7:
            xsig = -15
        ysig = 2
        if datapoint.y / datapoint.yRange > 0.7:
            ysig = -4
        datapoint.toset(self, 'xPos', datapoint.x + xsig * datapoint.xRange / 100)
        datapoint.toset(self, 'yPos', datapoint.y)
        # Styling
        datapoint.toset(self, 'Text/color', datapoint.xy.settings.PlotLine.color)

document.thefactory.register(DataPointLabel)
