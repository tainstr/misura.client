#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import tempfile 
from traceback import format_exc
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon import option

from . import _
from . import conf
from . import widgets
from .confwidget import ClientConf
from .live import registry
from .clientconf import confdb
from misura.canon.version import __version__ as canon_version
from . import parameters
from version import __version__ as client_version
from .autoupdate import check_server_updates, check_client_updates
from PyQt4 import QtGui, QtCore, uic






about="""
<h1> Misura &trade;</h1>
<p>misura.client version: {}<br/>
misura.canon version: {}</p>
<p>Copyright TA Instruments / Waters LLC</p>
<p><small>See public source code repository page for licensing information</small></p>
""".format(client_version, canon_version)

def showAbout():
    dialog = QtGui.QDialog()
    uic.loadUi(os.path.join(parameters.pathUi, 'about_misura.ui'), dialog)
    dialog.logo_label.setScaledContents(True)
    dialog.label_client_version.setText('client: ' + client_version)
    dialog.label_canon_version.setText('canon: ' + canon_version)

    dialog.logo_label.setPixmap(QtGui.QPixmap(os.path.join(parameters.pathArt, 'logo.png')))
    dialog.setWindowIcon(QtGui.QIcon(os.path.join(parameters.pathArt, 'icon.svg')))

    dialog.exec_()
    


class HelpMenu():
    def add_help_menu(self, menu_bar):
        self.menu_bar = menu_bar
        self.help = menu_bar.addMenu('Help')
        self.help.aboutToShow.connect(self.update_menu)
        
    @property
    def server(self):
        return getattr(self.menu_bar, 'server', False)
        
    def update_menu(self):
        self.help.clear()
        self.help.addAction(_('Client configuration'), self.showClientConf)
        self.help.addAction(_('Documentation'), self.showDocSite)
        self.help.addAction(_('Pending operations'), self.showTasks)
        self.help.addAction(_('Bug report'), self.bug_report)
        if self.server:
            self.help.addAction(_('Check server updates'), self.check_server_updates)
        self.help.addAction(_('Check client updates'), self.check_client_updates)
        self.help.addAction(_('About'), showAbout)

    def showClientConf(self):
        """Show client configuration panel"""
        self.cc = ClientConf()
        self.cc.show()

    def showDocSite(self):
        url = 'http://misura.readthedocs.io'
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def showTasks(self):
        registry.taskswg.user_show = True
        registry.taskswg.show()
        
    def bug_report(self):
        report = {}
        option.ao(
            report, 'title', 'String', name=_("Short title"))
        option.ao(report, 'type', 'Chooser', name=_("Type"), options=[_("Bug"),_("Improvement"),_("New feature")])
        option.ao(report, 'severity', 'Chooser', name=_("Severity"), options=[_("Lowest"),
                                                                              _("Low"),
                                                                              _("Mean"),
                                                                              _("High"),
                                                                              _("Highest"),])
        option.ao(report, 'steps', 'TextArea', name=_("Steps to reproduce"))
        option.ao(report, 'problem', 'TextArea', name=_("Description"))

        cp = option.ConfigurationProxy({'self': report})
        dia = conf.InterfaceDialog(cp, cp, report)
        dia.setWindowTitle(_('Bug report'))
        
        if not dia.exec_():
            logging.debug('Bug report was aborted')
            return False
        
        # Create a temporary directory, to ensrue the path is available    
        self._debug_dir = tempfile.mkdtemp()
        # Delete it
        os.removedirs(self._debug_dir)
        logging.debug('Creating bug report archive in', self._debug_dir)
        # Copy all available client logs 
        shutil.copytree(confdb['logdir'], self._debug_dir)
        
        # Write report
        s = option.CsvStore()
        s.desc = cp.desc 
        s.write_file(os.path.join(self._debug_dir, 'report.csv'))

        
        self._backupFileTransfer = False
        self._logsFileTransfer = False
        if self.server:
            # Update debug values
            self.server.support['libs']
            self.server.support['env']
            self.server.support['dmesg']
            self.server.support.save('default')
            # Create configuration backup
            self.server.support['doBackup']
            self._backupFileTransfer = widgets.aFileList(self.server, self.server.support, 
                          self.server.support.gete('backups'))
            # Create logs backup
            self.server.support['doLogs']
            self._logsFileTransfer = widgets.aFileList(self.server, self.server.support, 
                          self.server.support.gete('logs'))
            # Download them
            for wg in [self._backupFileTransfer, self._logsFileTransfer]:
                wg.hide()
                wg.get()
                if wg.download(os.path.join(self._debug_dir, wg.handle+'.tar.bz2')): 
                    wg.transfer.dlFinished.connect(self._make_debug_archive)
        else:
            self._make_debug_archive()
                    
    def _make_debug_archive(self, url=False, outfile=False):
        """Create the final debug archive"""
        if self._backupFileTransfer and url and '/logs/' in url:
                logging.debug('Backup file transfer finished')
                self._backupFileTransfer = False
        elif self._logsFileTransfer and url and '/backups/' in url:
                logging.debug('Logs file transfer finished')
                self._logsFileTransfer = False
        if self._logsFileTransfer != False or self._backupFileTransfer != False:
            logging.debug('Waiting for file transfers to finish')
            return False
            
        filename = QtGui.QFileDialog.getSaveFileName(None, 
                                                     _('Choose a filename where to archive the report'), 
                                                     '', 'ZIP (*.zip *.ZIP)')
        if not filename:
            logging.debug('Bug report aborted')
            return False
        if filename.lower().endswith('.zip'):
            filename = filename[:-4]
        if os.name!='nt':
            from commands import getstatusoutput as go
            go('dmesg > "{}/dmesg.log"'.format(self._debug_dir))
        shutil.make_archive(filename, 'zip', self._debug_dir)
        logging.debug('Created archive', filename, self._debug_dir)
        shutil.rmtree(self._debug_dir)
        logging.debug('Removed temporary debug dir', self._debug_dir)
        
    def check_client_updates(self):
        try:
            r = check_client_updates()
            if not r:
                QtGui.QMessageBox.information(self.menu_bar, 'Up to date', 'Misura Client is up to date.\nNo newer version was found.')
                return True
            if r is True:
                QtGui.QMessageBox.information(self.menu_bar, 'Updated', 'Misura Client sources were updated.')
                return True
            self._client_updater = r  
            return
        except:
            QtGui.QMessageBox.warning(self.menu_bar, 'Misura Client update error', format_exc())
    
    def check_server_updates(self):
        try:
            r = check_server_updates(self.server, self.menu_bar)
            if not r:
                QtGui.QMessageBox.information(self.menu_bar, 'Up to date', 'Misura Server is up to date.\nNo newer version was found.')
                return True
            self._server_updater = r
        except: 
            QtGui.QMessageBox.warning(self.menu_bar, 'Misura Server update error', format_exc())
            
        
        
