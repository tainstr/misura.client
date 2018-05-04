#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Programmatic interface construction utilities"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import functools
import os
import collections
import threading

from misura.canon import option
from misura.canon.option import sorter, prop_sorter
from misura.canon.csutil import lockme

from .. import _
from .. import widgets
from ..configuration_check import recursive_configuration_check, render_wiring
from .. import iutils

from PyQt4 import QtGui, QtCore, QtSvg


def desc2html(desc):
    """Crea una rappresentazione HTML del dizionario di descrizione."""
    logging.debug('show details')
    t = '<h1> Properties for: %s </h1>' % desc.get(
        'name', {'current': 'Object'})['current']
    items = desc.items()
    items.sort(sorter)
    t += '<table border="1" cellpadding="4" font="Monospace">'
    t += '<tr> <td>Property</td> <td>Current Value</td> <td>Factory Default</td> <td> ... </td></tr>'
    for prop, val in items:
        if val['type'] == 'Section':
            continue
        if prop != 'controls':
            more = 'type: %r <br/> attr: %r' % (val['type'], val['attr'])
            t += '<tr> <td><big><u>%s</u>  </big></td> <td>  <b>%r</b></td> <td>  %r</td> <td>  %s</td></tr>' % (prop, val['current'],
                                                                                                    val.get('factory_default', ''),
                                                                                                    more)
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
        if not prop.has_key('children') or isinstance(prop['children'], list):
            prop['children'] = collections.OrderedDict()
            prop_dict[handle] = prop

        parent = prop.get('parent', False)
        if parent is False:
            continue
        parentopt = prop_dict.get(parent, False)
        if parentopt is False:
            logging.debug('Non-existent parent for ', handle, prop['parent'])
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
    sections = collections.defaultdict(list)
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
        sections[spl[0]].append(prop)
    return sections

class ClickableLabel(QtGui.QPushButton):
    clicked = QtCore.pyqtSignal()
    right_clicked = QtCore.pyqtSignal()
        
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        else: 
            self.right_clicked.emit()
        return QtGui.QPushButton.mousePressEvent(self, event)


class OptionsGroup(QtGui.QGroupBox):
    def __init__(self, wg, children, parent=None):
        QtGui.QGroupBox.__init__(self, parent=parent)
        self.wg = wg
        self.children = children
        
        self.more = ClickableLabel()
        self.more.setIcon(iutils.theme_icon('add'))
        self.more.setMaximumWidth(30)
        self.more.clicked.connect(self.hide_show)
        self.more.right_clicked.connect(self.show_menu)
        self.menu = QtGui.QMenu()
        self.compare_menu = self.menu.addMenu(_('Compare'))
        self.compare_menu.aboutToShow.connect(self.build_compare_menu)
        self.setFlat(False)
        title = wg.prop.get('group', False)
        if title:
            self.setTitle(title)
            self.setStyleSheet("""QGroupBox { background-color: transparent; border: 1px solid gray; border-radius: 0px; }
        QGroupBox::title { subcontrol-position: top center; padding: 0 5px; }""")
        else:
            self.setStyleSheet("""QGroupBox { background-color: transparent; border: 0px solid gray; border-radius: 0px; }
        QGroupBox::title { subcontrol-position: top center; padding: 0 0px; }""")
        out = QtGui.QWidget(self)
        lay = QtGui.QHBoxLayout()
        lay.addWidget(wg.label_widget)
        lay.addWidget(wg)
        lay.addWidget(self.more)
        out.setLayout(lay)
        
        glay = QtGui.QVBoxLayout()
        glay.addWidget(out)
        glay.addWidget(children)
        self.setLayout(glay)
    
    def mousePressEvent(self, event):
        if not self.title():
            return
        # only active near the title bar
        if event.pos().y()>10:
            return 
        button = event.button()
        if button==QtCore.Qt.LeftButton:
            self.hide_show()
        elif button==QtCore.Qt.RightButton:
            self.show_menu(event.pos())
        
    def expand(self):
        self.children.show()
        self.more.setIcon(iutils.theme_icon('list-remove'))
        self.setChecked(True)
        
    def collapse(self):
        self.children.hide()
        self.more.setIcon(iutils.theme_icon('add'))
        self.setChecked(False)                         
        
    def hide_show(self):
        """Hide or show option's children"""
        if self.children.isVisible():
            self.collapse()
        else:
            self.expand()
            
    def show_menu(self, pos=False):
        if not pos:
            pos = self.more.pos()
        self.menu.popup(self.mapToGlobal(pos))
        
    def build_compare_menu(self):
        self.comparisons = {}
        self.compare_menu.clear()
        wm = self.children.widgetsMap.copy()
        wm[self.wg.handle] = self.wg
        comparison = self.wg.remObj.compare_option(*wm.keys())
        set_func = lambda keyvals: [wm[k].set_raw(v) for k,v in keyvals]
        widgets.active.build_option_menu(comparison, self.comparisons, self.compare_menu, set_func)
        
class ChildSection(QtGui.QWidget):
    def __init__(self, *a, **k):
        super(QtGui.QWidget, self).__init__(*a, **k)
        self.widgetsMap={}
        
class Section(QtGui.QGroupBox):
    """Form builder for a list of options"""
    def __init__(self, server, remObj, prop_list, title='Group', color='gray', parent=None, context='Option'):
        QtGui.QGroupBox.__init__(self, parent)
        self.setTitle(title)
        prop_list.sort(prop_sorter)
        self.p = []
        self.server = server
        self.remObj = remObj
        self.path = remObj._Method__name
        self.setStyleSheet("""QGroupBox { background-color: transparent; 
        border: 1px solid %s; border-radius: 5px; 
        margin-top: 10px; margin-bottom: 10px; }
        QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0px 5px; }""" % (color, ))
        self.setCheckable(True)
        self.clicked.connect(self.enable_disable)
        self.lay = QtGui.QFormLayout()
        self.lay.setLabelAlignment(QtCore.Qt.AlignRight)
        self.lay.setRowWrapPolicy(QtGui.QFormLayout.WrapLongRows)
        self.setLayout(self.lay)
        self.widgetsMap = {}
        self.parentsMap = {}
        self.groupsMap = {}
        for prop in prop_list:
            self.build(prop)
            
    def hide_frame(self):
        self.setStyleSheet("""QGroupBox { background-color: transparent; 
        border: 0px solid gray; border-radius: 0px; 
        margin-top: 0px; margin-bottom: 0px; }
        """)
        self.setTitle('')
        self.setChecked(True)
        self.setCheckable(False)

    def enable_disable(self, status=True):
        if status:
            self.expand()
        else:
            self.collapse()

    def expand(self):
        for w in self.groupsMap.itervalues():
            w.show()
        for w in self.widgetsMap.itervalues():
            w.show()
            w.label_widget.show()
        self.setMaximumHeight(16777215)
        self.setChecked(True)

    def collapse(self):
        if not self.isCheckable():
            return False
        for w in self.groupsMap.itervalues():
            w.hide()
        for w in self.widgetsMap.itervalues():
            w.hide()
            w.label_widget.hide()
        self.setMaximumHeight(40)
        self.setChecked(False)
        return True

            
    def expand_children(self):
        for group in self.groupsMap.itervalues():
            group.expand()

    def collapse_children(self):
        for group in self.groupsMap.itervalues():
            group.collapse()

    def add_children(self, main_widget, prop):
        parent_layout = main_widget.layout()
        parent_widget = widgets.build(
            self.server, self.remObj, prop, parent=main_widget)
        if parent_widget is False:
            return False
        self.widgetsMap[prop['handle']] = parent_widget
        if main_widget!=self:
            main_widget.widgetsMap[prop['handle']] = parent_widget
            
        # No children: just add the option and return
        if len(prop.get('children', [])) == 0:
            parent_layout.addRow(parent_widget.label_widget, parent_widget)
            return True
        # Widget hosting the children form
        children = ChildSection(parent_widget)
        children_lay = QtGui.QFormLayout()
        children.setLayout(children_lay)
        # Add the parent option plus the expansion button
        group = OptionsGroup(parent_widget, children, parent=self)
        self.groupsMap[parent_widget.handle] = group
        parent_layout.addRow(group)
        for handle, child in prop['children'].iteritems():
            if handle == prop['handle']:
                logging.error(
                    'Option parenthood loop detected', handle, prop['children'].keys())
                continue
            self.add_children(children, child)
            self.parentsMap[handle] = children
        children.hide()

    def build(self, prop):
        self.add_children(self, prop)
        return True

    def highlight_option(self, handle):
        self.show()
        wg = self.widgetsMap.get(handle, False)
        if wg is False:
            logging.error('Section.highlight_option: not found', handle)
            return False
        parent = self.groupsMap.get(handle, False)
        if parent is not False:
            parent.expand()
        wg.label_widget.setStyleSheet(
            'QWidget { font-weight: bold; color: red; }')
        self.expand()
        return wg

CONFIG_SEC = 0
STATUS_SEC = 1
RESULT_SEC = 2
class SectionBox(QtGui.QWidget):
    """Divide section into Status, Configuration and Results toolboxes."""
    sigScrollTo = QtCore.pyqtSignal(int, int)
    
    def __init__(self, server, remObj, prop_list, parent=None, context='Option'):
        QtGui.QWidget.__init__(self, parent=parent)
        self.lay = QtGui.QVBoxLayout()
        self.setLayout(self.lay)
        self.server = server
        self.remObj = remObj
        status_list = []
        results_list = []
        config_list = []

        for opt in prop_list:
            attr = opt.get('attr', False)
            if ('Config' in attr):
                config_list.append(opt)
            if not attr and opt['type'] == 'Meta':
                results_list.append(opt)
            elif ('History' in attr and 'Runtime' not in attr) or ('Result' in attr):
                results_list.append(opt)
            elif ('Runtime' in attr) or ('ReadOnly' in attr) or opt['type'] == 'ReadOnly' or ('Status' in attr):
                status_list.append(opt)
            else:
                config_list.append(opt)

        self.status_section = Section(server, remObj, status_list,  title=_('Status'), color='red',
                                      parent=None, context=context)
        self.results_section = Section(server, remObj, results_list, title=_('Results'), color='green',
                                       parent=None, context=context)
        self.config_section = Section(server, remObj, config_list, title=_('Configuration'), color='gray',
                                      parent=None, context=context)
        
        self.sections = [self.config_section, self.status_section, self.results_section]

        self.widgetsMap = {}
        self.widgetsMap.update(self.status_section.widgetsMap)
        self.widgetsMap.update(self.results_section.widgetsMap)
        self.widgetsMap.update(self.config_section.widgetsMap)

        lens = [len(sec.widgetsMap) > 0 for sec in self.sections]
        # None active!
        if sum(lens) < 1:
            return
        # Just one active section:
        if sum(lens) == 1:
            i = lens.index(True)
            sec = self.sections[i]
            self.lay.addWidget(sec)
            sec.hide_frame()
            return

        def add_section(sec):
            """Add section only if has widgets to show"""
            if not sec.widgetsMap:
                sec.hide()
            else:
                self.lay.addWidget(sec)

        # Prioritize sections
        add_section(self.config_section)

        if not getattr(remObj, 'remObj', False):
            add_section(self.results_section)
            add_section(self.status_section)
        else:
            add_section(self.status_section)
            add_section(self.results_section)

        self.lay.addStretch(1)
        self.reorder()
        
    def expand(self):
        for s in self.sections:
            s.expand()
            
    def collapse(self):
        for s in self.sections:
            s.collapse()

    def get_status(self):
        status = [True,True,True]
        # Hide everything
        for i,w in enumerate(self.sections):
            status[i] = w.isChecked() and len(w.widgetsMap)>0
        return status
    
    def set_status(self, status):
        for i, st in enumerate(status):
            w = self.sections[i]
            if st and len(w.widgetsMap)>0:
                w.expand()
                self.sigScrollTo.emit(w.pos().x(), w.pos().y() + 50)
            else:
                w.collapse()

    def reorder(self):
        # return
        w = None
        isRunning = self.server.has_key('isRunning') and self.server['isRunning']
        status = self.get_status()
        # Select what to show
        if isRunning:
            status[CONFIG_SEC] = False
            status[STATUS_SEC] = True
            status[RESULT_SEC] = True
        else:
            status[CONFIG_SEC] = True
            status[RESULT_SEC] = True
            status[STATUS_SEC] = False
        self.set_status(status)

    def highlight_option(self, handle):
        for sec in [self.config_section, self.status_section, self.results_section]:
            if handle in sec.widgetsMap:
                break
            else:
                sec = False
        if not sec:
            logging.debug(
                'SectionBox.highlight_option: not visible/found', handle)
            return False
        wg = sec.highlight_option(handle)
        x = sec.x()
        y = sec.y()
        parent = wg
        while parent != sec:
            y += parent.y()
            x += parent.x()
            parent = parent.parent()
        self.sigScrollTo.emit(x, y)
        return wg


class Interface(QtGui.QTabWidget):

    """Tabbed interface builder for dictionary of options"""
    first_show = True
    
    def __init__(self, server, remObj=False, prop_dict=False, parent=None, context='Option', fixed=False):
        QtGui.QTabWidget.__init__(self, parent)
        self._lock = threading.Lock()
        self.server = server
        if remObj is False:
            remObj = server
        if remObj.doc:
            remObj.doc.sigConfProxyModified.connect(functools.partial(self.rebuild, False, True, True))
        self.remObj = remObj
        self.prop_dict = {}
        self.prop_keys = []
        self.sectionsMap = False
        self.fixed = fixed
        self.rebuild(prop_dict)
        self.menu = QtGui.QMenu(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)

    def show_section(self, name):
        sections = self.sectionsMap.keys()
        if name not in sections:
            logging.warning('No section named', name)
        i = sections.index(name)
        self.setCurrentIndex(i)

    def showEvent(self, event):
        if self.first_show:
            self.first_show = False
            return
        self.rebuild(force=True)

    _prev_section = False
    _prev_section_status = False
    _deleted  = False
    @lockme()
    def rebuild(self, prop_dict=False, force=False, redraw=False):
        """Rebuild the full widget"""
        if self._deleted:
            logging.debug('Interface.rebuild: deleted')
            return 
        if self.sectionsMap:
            i = self.currentIndex()
            self._prev_section = self.sectionsMap.keys()[i]
            self._prev_section_status = self.sectionsMap[self._prev_section].get_status() 
        if not prop_dict and self.fixed:
            prop_dict = self.prop_dict
        elif not prop_dict:
            self.remObj.connect()
            k = set(self.prop_keys)
            rk = set(self.remObj.keys())
            d = k.symmetric_difference(rk)
            if len(d) == 0 and not (force or redraw):
                logging.debug(
                    'Interface.rebuild not needed: options are equal.')
                return
            prop_dict = self.remObj.describe()
            # If a prop_dict was set, just pick currently defined options
            if len(k) and len(prop_dict) and not redraw:
                visible = set(prop_dict.keys()).intersection(k)
                prop_dict = {key: prop_dict[key] for key in visible}
        if not prop_dict:
            logging.critical('Impossible to get object description',
                             self.remObj._Method__name)
            return
        self.clear()
        self.sections = orgSections(prop_dict, self.remObj._readLevel)
        self.prop_dict = prop_dict
        self.prop_keys = self.prop_dict.keys()
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
            
        # Restore previous status
        if self._prev_section and self._prev_section in self.sectionsMap:
            self.show_section(self._prev_section)
            self.sectionsMap[self._prev_section].set_status(self._prev_section_status)

    def reorder(self):
        """Switch toolbox currentIndexes"""
        for sec in self.sectionsMap.itervalues():
            sec.reorder()

    def redraw(self, foo=0):
        self.close()
        wg = SectionBox(
            self.server, self.remObj, self.sections['Main'], parent=self)
        self.sectionsMap = collections.OrderedDict({'Main': wg})
        self._funcs = []
        area = QtGui.QScrollArea(self)
        area.setWidget(wg)
        area.setWidgetResizable(True)
        self.areasMap = collections.OrderedDict({'Main': area})
        f = functools.partial(self.scroll_to, area)
        wg.sigScrollTo.connect(f)
        self._funcs.append(f)
        sname = 'Main'
        if self.prop_dict.has_key(sname):
            if self.prop_dict[sname]['type'] == 'Section':
                sname = self.prop_dict[sname]['name']
        self.addTab(area, _('Main'))

        for section, prop_list in self.sections.iteritems():
            if section == 'Main':
                continue
            wg = SectionBox(self.server, self.remObj, prop_list, parent=self)
            # Ignore empty sections
            if not len(wg.widgetsMap):
                continue
            self.sectionsMap[section] = wg
            area = QtGui.QScrollArea(self)
            area.setWidget(wg)
            area.setWidgetResizable(True)
            self.areasMap[section] = area
            sname = section
            if self.prop_dict.has_key(sname):
                if self.prop_dict[sname]['type'] == 'Section':
                    sname = self.prop_dict[sname]['name']
            self.addTab(area, _(sname))

            f = functools.partial(self.scroll_to, area)
            wg.sigScrollTo.connect(f)
            self._funcs.append(f)

        # hide tabBar if just one section
        self.tabBar().setVisible(len(self.sections.keys()) > 1)

        for sec in self.sectionsMap.itervalues():
            self.widgetsMap.update(sec.widgetsMap)

    def highlight_option(self, handle):
        """Ensure `handle` widget is visible"""
        sec = 'Main'
        if '_' in handle and len(self.sectionsMap) > 1:
            sec = handle.split('_')[0]
        area = self.areasMap[sec]
        sec = self.sectionsMap[sec]
        self.setCurrentWidget(area)
        wg = sec.highlight_option(handle)
        logging.debug('HIGHLIGHT OPT', handle)
        return wg

    def scroll_to(self, area, x, y):
        area.ensureVisible(x, y - 50)

    def close(self):
        if not self.sectionsMap:
            return
        for wg in self.sectionsMap.itervalues():
            wg.close()
            wg.deleteLater()
        for i in range(self.count()):
            logging.debug('remove tab', i)
            self.removeTab(self.currentIndex())
        self.clear()
        self.sectionsMap = {}
        self._deleted = True
        self.blockSignals(True)

    def update(self):
        """Cause all widgets to re-register for an update"""
        for s, sec in self.sectionsMap.iteritems():
            for w, wg in sec.widgetsMap.iteritems():
                if wg.type == 'Button':
                    continue
                wg.register()

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

        self.connect(self.ok, QtCore.SIGNAL('clicked()'), self.ok_clicked)
        
    def ok_clicked(self):
        self.interface.close()
        self.interface.hide()
        self.interface.deleteLater()
        
        self.accept()
