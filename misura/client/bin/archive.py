#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from misura.client import iutils, archive, live

if __name__ == '__main__':
    iutils.initApp()
    live.registry.toggle_run(False)
    app = iutils.app

    mw = archive.MainWindow()
    if len(sys.argv) > 1:
        mw.open_file(sys.argv[1])
    mw.show()
    sys.exit(app.exec_())
