#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Programmatic interface construction utilities"""
from misura.canon.logger import Log as logging
import functools
import os
import collections

from misura.canon import option
from misura.canon.option import sorter, prop_sorter

from .. import _
from .. import widgets
from ..configuration_check import recursive_configuration_check, render_wiring

from PyQt4 import QtGui, QtCore, QtSvg


def desc2html(desc):
    """Crea una rappresentazione HTML del dizionario di descrizione."""
    logging.debug('%s', 'show details')
    t = '<h1> Properties for: %s </h1>' % desc.get(
        'name', {'current': 'Object'})['current']
    items = desc.items()
    items.sort(sorter)
    t += '<table border="1" cellpadding="4" font="Monospace">'
    t += '<tr> <td>Property</td> <td>Current Value</td> <td>Factory Default</td>'
    for prop, val in items:
        if val['type'] == 'Section':
            continue
        if prop != 'controls':
            t += '<tr> <td><big><u>%s</u>  </big></td> <td>  <b>%r</b></td> <td>  %r</td> </tr>' % (prop, val['current'],
                                                                                                    desc[prop].get('factory_default'))
    t += '</table>'
    t = t.replace('\\n', '<br/>')
    return t


def sort_children(prop_dict):
    for handle in prop_dict.keys():
        prop = prop_dict[handle]
        children = prop['children']
        sorted_keys = sorted(children.values(), option.prop_sorter)
        sorted_keys = [p['handle'] for p in sorted_keys]
        children = collections.OrderedDict(
            (k, children[k]) for k in sorted_keys)
        children = sort_children(children)
        prop['children'] = children
        prop_dict[handle] = prop
    return prop_dict
            

def orgSections(prop_dict, configuration_level=5):
    """Riordina le chiavi a seconda delle sezioni cui appartengono."""
    # Move children options into their parent's "children" key
    prop_dict = prop_dict.copy()
    for handle in prop_dict.keys():
        prop = prop_dict.get(handle, False)
        if prop is False:
            continue
        # Add the children key to any option (simplifies further processing)
        if not prop.has_key('children') or isinstance(prop['children'],list):
            prop['children'] = collections.OrderedDict()
            prop_dict[handle] = prop
        
        parent = prop.get('parent', False)
        if parent is False:
            continue
        parentopt = prop_dict.get(parent, False)
        if parentopt is False:
            logging.debug(
                '%s %s %s', 'Non-existent parent for ', handle, prop['parent'])
            continue
        # Create the children list on the parent option
        if not parentopt.has_key('children') or isinstance(parentopt['children'], list):
            parentopt['children'] = collections.OrderedDict()
        # Append the child to the parent
        parentopt['children'][handle] = prop 
        # Delete the child from the main dictionary
        del prop_dict[handle]
        # Update the parent on the main dictionary
        prop_dict[parent] = parentopt

    # Sorting
    prop_dict = sort_children(prop_dict)
    # Sectioning
    sections = {'Main': []}
    for handle, prop in prop_dict.iteritems():
        if not prop.has_key('readLevel'):
            prop['readLevel'] = -1
        if prop['readLevel'] > configuration_level:
            continue
        if ':' in handle:
            spl = ':'
        elif '_' in handle:
            spl = '_'
        else:
            sections['Main'].append(prop)
            continue
        spl = handle.split(spl)
        if not sections.has_key(spl[0]):
            sections[spl[0]] = []
        sections[spl[0]].append(prop)
    return sections


class Section(QtGui.QWidget):

    def __init__(self, server, remObj, prop_list, parent=None, context='Option'):
        QtGui.QWidget.__init__(self, parent)
        prop_list.sort(prop_sorter)
        self.p = []
        self.server = server
        self.remObj = remObj
        self.path = remObj._Method__name

        self.lay = QtGui.QFormLayout()
        self.lay.setLabelAlignment(QtCore.Qt.AlignRight)
        self.lay.setRowWrapPolicy(QtGui.QFormLayout.WrapLongRows)
        self.widgetsMap = {}
        for prop in prop_list:
            self.build(prop)

        self.setLayout(self.lay)

    def hide_show(self, children, button):
        """Hide or show option's children"""
        if children.isVisible():
            children.hide()
            button.setText('+')
        else:
            children.show()
            button.setText('-')

    def expandable_row(self, wg, children):
        more = QtGui.QPushButton("+")
        more.setMaximumWidth(50)
        p = functools.partial(self.hide_show, children, more)
        self.p.append(p)
        self.connect(more, QtCore.SIGNAL('clicked()'), p)
        out = QtGui.QWidget()
        lay = QtGui.QHBoxLayout()
        lay.addWidget(wg)
        lay.addWidget(more)
        out.setLayout(lay)
        return out
    
    def add_children(self, parent_layout, prop):
        parent_widget = widgets.build(self.server, self.remObj, prop, parent=self)
        if parent_widget is False:
            return False
        self.widgetsMap[prop['handle']] = parent_widget
        # No children: just add the option and return
        if len(prop.get('children', [])) == 0:
            parent_layout.addRow(parent_widget.label_widget, parent_widget)
            return True
        # Widget hosting the children form
        children = QtGui.QWidget()
        children_lay = QtGui.QFormLayout()
        children.setLayout(children_lay)
        # Add the parent option plus the expansion button
        parent_layout.addRow(parent_widget.label_widget, 
                             self.expandable_row(parent_widget, children))

        for handle, child in prop['children'].iteritems():
            if handle == prop['handle']:
                logging.error('Option parenthood loop detected', handle, prop['children'].keys())
                continue
            self.add_children(children_lay, child)

        parent_layout.addRow(children)
        children.hide()
        
    def build(self, prop):
        self.add_children(self.lay, prop)
        return True


class Interface(QtGui.QTabWidget):

    """Interfaccia grafica ad un dizionario di configurazione."""

    def __init__(self, server, remObj=False, prop_dict=False, parent=None, context='Option'):
        QtGui.QTabWidget.__init__(self, parent)
        self.server = server
        if remObj is False:
            remObj = server
        self.remObj = remObj
        if not prop_dict:
            self.remObj.connect()
            prop_dict = self.remObj.describe()
        if not prop_dict:
            logging.critical(
                'Impossible to get object description %s', self.remObj._Method__name)
            return
        self.sections = orgSections(prop_dict, remObj._readLevel)
        self.prop_dict = prop_dict
        self.name = ''
        if prop_dict.has_key('name'):
            self.name = prop_dict['name']['current']
            self.setWindowTitle('Configuring: ' + self.name)
        self.sectionsMap = False
        self.widgetsMap = {}
        self.redraw()
        if self.sectionsMap['Main'].widgetsMap.has_key('preset'):
            self.connect(self.sectionsMap['Main'].widgetsMap[
                         'preset'], QtCore.SIGNAL('changed'), self.update)
            self.scSave = QtGui.QShortcut(
                QtGui.QKeySequence(_('Ctrl+S')), self)
            self.connect(self.scSave, QtCore.SIGNAL('activated()'), self.sectionsMap[
                         'Main'].widgetsMap['preset'].save_current)

        self.menu = QtGui.QMenu(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)

    def redraw(self, foo=0):
        self.close()
        wg = Section(
            self.server, self.remObj, self.sections['Main'], parent=self)
        self.sectionsMap = {'Main': wg}
        area = QtGui.QScrollArea(self)
        area.setWidget(wg)
        area.setWidgetResizable(True)
        sname = 'Main'
        if self.prop_dict.has_key(sname):
            if self.prop_dict[sname]['type'] == 'Section':
                sname = self.prop_dict[sname]['name']
        self.addTab(area, _('Main'))

        for section, prop_list in self.sections.iteritems():
            if section == 'Main':
                continue
            wg = Section(self.server, self.remObj, prop_list, parent=self)
            # Ignore empty sections
            if not len(wg.widgetsMap):
                continue
            self.sectionsMap[section] = wg
            area = QtGui.QScrollArea(self)
            area.setWidget(wg)
            area.setWidgetResizable(True)
            sname = section
            if self.prop_dict.has_key(sname):
                if self.prop_dict[sname]['type'] == 'Section':
                    sname = self.prop_dict[sname]['name']
            self.addTab(area, _(sname))

        # se c'è solo una sezione, nascondo la tabBar
        if len(self.sections.keys()) == 1:
            self.tabBar().setVisible(False)

        for sec in self.sectionsMap.itervalues():
            self.widgetsMap.update(sec.widgetsMap)

    def close(self):
        if not self.sectionsMap:
            return
        for wg in self.sectionsMap.itervalues():
            wg.close()
            wg.destroy()
        for i in range(self.count()):
            logging.debug('%s', 'remove tab')
            self.removeTab(self.currentIndex())

    def update(self):
        """Cause all widgets to re-register for an update"""
        for s, sec in self.sectionsMap.iteritems():
            for w, wg in sec.widgetsMap.iteritems():
                if wg.type == 'Button':
                    continue
                wg.register()
#                logging.debug('%s %s %s %s', 'updating:', s, w, wg.async_get())

    def showMenu(self, pt):
        self.menu.popup(self.mapToGlobal(pt))

    def show_details(self):
        """Show full configuration as HTML table"""
        self.desc = self.remObj.describe()
        widgets.info_dialog(desc2html(self.desc), 'Details for Object: %s' % self.desc.get(
            'name', {'current': 'Object'})['current'], parent=self)

    def presets_table(self):
        self.desc = self.remObj.describe()
        output = recursive_configuration_check(self.remObj)
        widgets.info_dialog(output, 'Presets Comparison, %s' % self.desc.get(
            'name', {'current': 'Object'})['current'], parent=self)

    _wiring = False

    def wiring_graph(self):
        if self._wiring:
            self._wiring.hide()
            self._wiring.close()
            self._wiring = False
        # Temp file
        svg_filename = render_wiring(self.remObj.wiring())

        # Scene
        scene = QtGui.QGraphicsScene()
        view = QtGui.QGraphicsView()
        view.setScene(scene)
        svg = QtSvg.QGraphicsSvgItem(svg_filename)
        scene.addItem(svg)
        # Display widget
        wg = QtGui.QWidget()
        lay = QtGui.QVBoxLayout()
        wg.setLayout(lay)
        lay.addWidget(view)
        wg.show()
        self._wiring = wg
        # Cleanup
        os.remove(svg_filename)


class InterfaceDialog(QtGui.QDialog):

    def __init__(self, server, remObj=False, prop_dict=False, parent=None):
        QtGui.QDialog.__init__(self, parent=parent)
        self.interface = Interface(server, remObj, prop_dict, self)
        lay = QtGui.QVBoxLayout()
        self.setLayout(lay)
        lay.addWidget(self.interface)
        self.ok = QtGui.QPushButton('Ok')
        self.ok.setDefault(True)
        lay.addWidget(self.ok)

        self.connect(self.ok, QtCore.SIGNAL('clicked()'), self.accept)
