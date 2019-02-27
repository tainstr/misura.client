#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.document as document
from veusz.widgets.textlabel import TextLabel
from veusz import widgets


class LineLabel(TextLabel):
    typename = 'linelabel'
    description = "Label for OptionLines"

    def __init__(self, *args, **kwargs):
        TextLabel.__init__(self, *args, **kwargs)
        if type(self) == LineLabel:
            self.readDefaults()

    @classmethod
    def allowedParentTypes(klass):
        """Get types of widgets this can be a child of."""
        from misura.client.plugin.OptionLine import OptionLine
        return (OptionLine, widgets.Line)
    
    @classmethod
    def addSettings(klass, s):
        """Construct list of settings."""
        widgets.TextLabel.addSettings(s)
        pos = s.get('positioning')
        pos.default = 'axes'
        pos.set('axes')
        pos.hidden = True
        
        s.Text.size = '6pt'
        
        s.get('xAxis').hidden = True
        s.get('yAxis').hidden = True
        s.get('xPos').hidden = True
        s.get('yPos').hidden = True

    def update(self):
        """Update output label with the coordinates of the point."""
        line = self.parent
        self.settings.xAxis = line.settings.xAxis
        self.settings.yAxis = line.settings.yAxis
        
        x = line.settings.xPos[0]
        x2 = line.settings.xPos2[0]  
        y = line.settings.yPos[0]
        y2 = line.settings.yPos2[0]
            
        self.settings.xPos = (x+x2)/2.
        self.settings.yPos = (y+y2)/2.
        
        # Styling
        self.settings.Text.color = line.settings.Line.color

document.thefactory.register(LineLabel)