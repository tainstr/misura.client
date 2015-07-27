#!/usr/bin/python
# -*- coding: utf-8 -*-
"""A point connected to an xy plot."""
from misura.canon.logger import Log as logging
import veusz.widgets
import veusz.document as document
import veusz.setting as setting
import numpy as np
import utils


def translateCoord(ax, vc):
    return [ax.plottedrange[0] + c * (ax.plottedrange[1] - ax.plottedrange[0]) for c in vc]


class Intercept(utils.OperationWrapper, veusz.widgets.Line):
    typename = 'intercept'
    description = 'Intercept Line'
    allowusercreation = True

    def __init__(self, parent, name=None):
        veusz.widgets.Line.__init__(self, parent, name=name)

        self.addAction(veusz.widgets.widget.Action('up', self.actionUp,
                                                   descr='Update Intercept Line',
                                                   usertext='Update Intercept Line'))

        self.settings.positioning = 'relative'
        self.settings.mode = 'point-to-point'

        # xy : {idx:dp1, idx:dp2, ...}
        self.crossings = {}

    @classmethod
    def addSettings(klass, s):
        """Construct list of settings."""
        veusz.widgets.Line.addSettings(s)

        s.add(setting.Bool('showLabels', True,
                           descr='Show Labels',
                           usertext='Show datapoint labels',
                           formatting=True),
              1)
        s.add(setting.Str(
            'labelText', '%(xlabel)s=%(x)i \\\\%(ylabel)s=%(y)E',
            descr='Output labels text',
            usertext='Output labels text'),
            2)

    def intercept_xy(self, obj):
        """Intercept obj xy for all line length"""
        doc = self.document
        self.doc = doc

        # Translate end points coords
        xax = self.parent.getChild(obj.settings.xAxis)
        ox, ox2 = translateCoord(xax, [self.x, self.x2])
        yax = self.parent.getChild(obj.settings.yAxis)
        oy, oy2 = translateCoord(yax, [self.y, self.y2])

        logging.debug('%s %s %s %s %s', 'limits', ox, oy2, ox2, oy2)

        # Get the data from the plot obj
        vx = doc.data[obj.settings.xData].data
        vy = doc.data[obj.settings.yData].data
        # Line angle
        ang = np.arctan((oy2 - oy) / (ox2 - ox))
        logging.debug('%s %s', 'Angle', ang * 180 / np.pi)
        # Rotation matrix
        rot = np.matrix([
            [np.cos(ang), np.sin(ang)],
            [-np.sin(ang), np.cos(ang)]
        ])
        # Rotate the data
        r = np.asarray(rot * np.array([vx, vy]))
        # Rotate the points
        rp = np.asarray(rot * np.array([[ox], [oy]]))
        rox = rp[0][0]
        roy = rp[1][0]
        # Find where the rotated array crosses the x axis
        crossing = np.diff(np.sign(r[1] - roy))
#		print 'Diff sign',crossing,np.abs(crossing).sum()
        crossings = np.where(crossing != 0)[0]
        logging.debug('%s %s', 'Crossings', crossings)
        # Find valid crossing
        cx = []
        found = {obj: {}}
        for c in crossings:
            if not (min(ox, ox2) < vx[c] < max(ox, ox2) or min(oy, oy2) < vy[c] < max(oy, oy2)):
                logging.debug(
                    '%s %s %s %s', 'ignoring crossing', c, vx[c], vy[c])
                continue
            # Avoid very similar entries
            if c + 1 in cx or c - 1 in cx:
                logging.debug(
                    '%s %s %s %s', 'Ignoring too near crossing', c, vx[c], vy[c])
                continue
            cx.append(c)
            # Must create a new DataPoint widget for this crossing
            name = 'intercept_%s_%s_%i' % (self.name, obj.name, c)
            dpset = {'name': name, 'xy': obj.name,
                     'xAxis': obj.settings.xAxis, 'yAxis': obj.settings.yAxis,
                     'xPos': float(vx[c]), 'yPos': float(vy[c]), 'coordLabel': '', 'showLabel': False}
            if self.settings.showLabels == True:
                lblname = 'lbl_' + name
                dpset['showLabel'] = True
                dpset['coordLabel'] = lblname
                self.ops.append(
                    document.OperationWidgetAdd(self.parent, 'label', name=lblname))
            self.ops.append(
                document.OperationWidgetAdd(self.parent, 'datapoint', **dpset))
            found[obj][c] = (name, vx[c], vy[c])
        # Update crossings dictionary
        self.crossings.update(found)
        return True

    def actionUp(self, x=None, y=None, x2=None, y2=None):
        logging.debug('%s', 'INTERCEPT LINE UP')
        doc = self.document
        s = self.settings
        self.ops = []

        # Settings coerence
        aligned = self.toset(self, 'positioning', 'relative')
        aligned = aligned and self.toset(self, 'mode', 'point-to-point')
        if not aligned:
            logging.debug('%s %s', 'Not aligned: apply ops', self.ops)
            doc.applyOperation(
                document.OperationMultiple(self.ops, descr='InterceptUp'))
            self.ops = []

        x = s.xPos[0] if x is None else x
        y = s.yPos[0] if y is None else y
        x2 = s.xPos2[0] if x2 is None else x2
        y2 = s.yPos2[0] if y2 is None else y2
        logging.debug('%s %s %s %s', x, y, x2, y2)
        self.x = x
        self.y = y
        self.x2 = x2
        self.y2 = y2

        # Delete old datapoints and their labels
        for xy, fd in self.crossings.iteritems():
            for c, (name, dpx, dpy) in fd.iteritems():
                dp = self.parent.getChild(name)
                if dp.labelwidget is not None:
                    self.ops.append(
                        document.OperationWidgetDelete(dp.labelwidget))
                self.ops.append(document.OperationWidgetDelete(dp))

        self.apply_ops('interceptDelete')

        # Iterate over all curves in the same graph
        self.crossings = {}  # xy : {idx1:dp1, idx2:dp2, ...}
        for obj in self.parent.children:
            if obj.typename != 'xy':
                continue
            self.intercept_xy(obj)

        # Create everything
        self.apply_ops('interceptCreate')

        # Then update current datapoints
        for xy, fd in self.crossings.copy().iteritems():
            for c, (name, dpx, dpy) in fd.iteritems():
                dp = self.parent.getChild(name)
                # Updata datapoint position
                if not self.settings.showLabels:
                    lbl = dp.labelwidget
                    if lbl is not None:
                        self.ops.append(document.OperationWidgetDelete(lbl))
                dp.actionUp(dpx, dpy)
        # Create everything
        self.apply_ops('interceptLabels')
        return True

    def updateControlItem(self, cgi, pt1, pt2):
        """If control items are moved, update line."""
        # Call the line method

        veusz.widgets.Line.updateControlItem(self, cgi, pt1, pt2)
        self.actionUp()


document.thefactory.register(Intercept)
