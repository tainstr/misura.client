#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Repeat image analysis"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon.reference import get_reference, get_node_reference
# TODO: move to morphometrix package
try:
    from misura.analyzer import PathShape, PathBorder
    enabled = True
except:
    enabled = False


def path_analysis(cls, x, y, analyzer, sample):
    mx = min(x)
    Mx = max(x)
    my = min(y)
    My = max(y)
    path = cls(roi=(mx, my, Mx - mx, My - my))
    path.x = x
    path.y = y
    return path.analyze(analyzer, sample)


def write_results(proxy, refs, out, t, fp, ver, sample, smp_def):
    undef = set()
    for key, val in out.items():
        if key in undef:
            continue
        # Import new definitions
        if not key in sample:
            found = False
            for d in smp_def:
                if d.has_key('handle') and d['handle'] == key:
                    d['kid'] = fp + key
                    logging.debug('Defining new result option', d)
                    sample.add_option(**d)
                    found = True
                    break
            if not found:
                logging.debug('Result is undefined', key)
                undef.add(key)
                continue

        ref = refs.get(key, False)
        if ref is False:
            opt = sample.gete(key)
            cls = get_reference(opt)
            folder = ver + fp
            ref = cls(proxy, folder=folder, opt=opt, with_summary=True)
            # Create summary dataset also
            logging.debug('Creating node reference', ref.folder)
            # Delete previous and recreate
            ref.dump()
            refs[key] = ref

        ref.commit([(t, val)])
        ref.interpolate()
    return refs


def postanalysis(proxy, analyzer, sample, dataset='profile',
                 aborted=[False],
                 jobs=lambda *x, **k: 0,
                 job=lambda *x, **k: 0,
                 done=lambda *x, **k: 0):
    fp = sample['fullpath']
    path_class = PathShape if fp.startswith('/hsm/sample') else PathBorder
    profile = get_node_reference(proxy, fp + dataset)
    N = len(profile)
    refs = {}
    ver = proxy.get_version()
    def abort():
        aborted[0] = True
    jobs(N, 'Post-analysis', abort=abort)
    for i in range(N):
        if aborted[0]:
            logging.debug('Post-analysis aborted')
            done('Post-analysis')
            return False
        print 'Analyze profile', round(100. * i / N, 2)
        job(i, 'Post-analysis')
        t, ((w, h), x, y) = profile[i]
        st, out = path_analysis(path_class, x, y, analyzer, sample)
        refs = write_results(proxy, refs, out, t, fp, ver,
                             sample, path_class.smp_def)
    logging.debug('Saving configuration')
    proxy.save_conf(sample.root.tree())
    proxy.flush()
    done('Post-analysis')
    return True

def deferred_postanalysis(*a, **k):
    from PyQt4 import QtCore
    from misura.client import widgets
    aborted = [False]
    k['aborted']=aborted
    def abort():
        aborted[0]=True
    thread = widgets.RunMethod(postanalysis, *a, **k)
    thread.pid = 'Post-analysis'
    thread.abort = abort
    QtCore.QThreadPool.globalInstance().start(thread)
    return thread

if __name__ == '__main__':
    #test_path = '/home/daniele/MisuraData/hsm/BORAX powder 10 C min.h5'
    #data_path = '/hsm/sample0'

    test_path = '/home/daniele/MisuraData/horizontal/profiles/System Interbau 80 1400.h5'
    data_path = '/horizontal/sample0/Right'
    from misura.canon.indexer import SharedFile
    f = SharedFile(test_path)
    f.load_conf()
    smp = f.conf.toPath(data_path)
    postanalysis(f, smp.analyzer, smp)
