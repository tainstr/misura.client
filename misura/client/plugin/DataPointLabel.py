#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.document as document
from veusz.widgets.textlabel import TextLabel
from veusz import widgets

class DataPointLabel(TextLabel):
    typename = 'datapointlabel'
    description = "Label for datapoints"

    def __init__(self, *args, **kwargs):
        TextLabel.__init__(self, *args, **kwargs)
        if type(self) == DataPointLabel:
            self.readDefaults()



    @classmethod
    def allowedParentTypes(klass):
        """Get types of widgets this can be a child of."""
        from misura.client.plugin.datapoint import DataPoint
        return (DataPoint,)
    
    @classmethod
    def addSettings(klass, s):
        """Construct list of settings."""
        widgets.TextLabel.addSettings(s)
        pos = s.get('positioning')
        pos.default = 'axes'
        pos.set('axes')
        pos.hidden = True

    def update(self):
        """Update output label with the coordinates of the point."""
        datapoint = self.parent
        from misura.client import axis_selection as axsel
        data = self.document.data
        text_values = {'xlabel': datapoint.xAx.settings.label,
                       'ylabel': datapoint.yAx.settings.label,
                       'x': datapoint.x,
                       'y': datapoint.y,
                       }
        
        y = datapoint.parent.settings.yData
        linked = data[y].linked
        text = datapoint.settings.labelText
        if linked and linked.prefix:
            tname = axsel.get_best_x_for(y, linked.prefix, data, '_t')
            Tname = axsel.get_best_x_for(y, linked.prefix, data, '_T')
            text_values.update({'t': data[tname].data[datapoint.point_index],
                       'T': data[Tname].data[datapoint.point_index],})
        else:
            # Purge time/temperature labels
            text1 =[]
            for line in text.split('\\\\'):
                if '%(t)' in line or '%(T)' in line:
                    continue
                text1.append(line)
            text = '\\\\'.join(text1)
        
        # Add to parent's operations queue   
        datapoint.toset(self, 'label', text % text_values)
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
        datapoint.toset(self, 'Text/color', datapoint.parent.settings.PlotLine.color)

document.thefactory.register(DataPointLabel)
