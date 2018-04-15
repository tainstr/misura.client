#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import multiprocessing

from misura.client.bin.acquisition import run_acquisition_app
from misura.client.bin.graphics import run_graphics_app
from misura.client.bin.conf import run_conf_app
from misura.client.bin.browser import run_browser_app


#TODO: add --console for command line environment
app_map = {'--acquisition': run_acquisition_app,
           '--live': run_acquisition_app,
           '--graphics': run_graphics_app,
           '--browser': run_browser_app}


def run_misura_app():
    for a in sys.argv:
        if a in app_map:
            app = app_map[a]
            sys.argv.remove(a)
            app()
            return
    # if no argument can be recogize, just run the browser        
    run_browser_app()
    
    
if __name__ == '__main__':
    multiprocessing.freeze_support()
    run_misura_app()