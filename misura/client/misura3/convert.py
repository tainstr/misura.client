#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
"""Converts from Misura 3 to Misura 4 database formats"""
import tables
import numpy as np
from copy import deepcopy
import os
import StringIO
from traceback import format_exc
from datetime import datetime
from time import time, mktime
import string
import hashlib

from PIL import Image

from misura.canon import bitmap, option, reference, indexer
from misura.canon.option import ao
from misura.canon.plugin import dataimport

import m3db

logging = dataimport.SelectLogging()

valid_chars = "-_. %s%s" % (string.ascii_letters, string.digits)

# Heating curve point
HeatingCyclePoint = {
    't': tables.Float32Col(pos=1),
    'T': tables.Float32Col(pos=2),
    'chk': tables.BoolCol(pos=3)
}

base_dict = dataimport.base_dict()

measure_dict = dataimport.measure_dict()
ao(measure_dict, 'maxT', 'Meta', name='Maximum temperature')
ao(measure_dict, 'end', 'Meta', name='End of test')
ao(measure_dict, 'maxHeatingRate', 'Meta', name='Max heating rate')
ao(measure_dict, 'coolingDuration', 'Meta', name='Cooling duration')
ao(measure_dict, 'maxCoolingRate', 'Meta', name='Max cooling rate')

ao(measure_dict, 'scrEnd', 'Script', "mi.Point(idx=-1)", parent='end')
ao(measure_dict, 'scrMaxT', 'Script', """i,t,T=mi.Max('T')
mi.t(t)
mi.T(T)
""", parent='maxT')
ao(measure_dict, 'scrMaxHeatingRate', 'Script', """
print 'scrMaxHeatingRate'
T1=kiln.TimeDerivative('T')
if len(T1)<10: mi.Exit()
rate=max(T1)
w=mi.Where(T1==rate)
if w<0: mi.Exit()
print 'scrMaxHeatingRate',w
mi.Point(idx=w+1)
mi.Value(rate/60)
""", 'Max Heating Rate', parent='maxHeatingRate')

ao(measure_dict, 'scrCoolingDuration', 'Script', """
if not mi.SelectCooling():
    mi.Exit()
t,T=mi.xy('T')
dT=T[0]-T[-1]
dt=t[-1]-t[0]
mi.T(dT)
mi.t(dt)
""", 'Total cooling duration', parent='coolingDuration')

ao(measure_dict, 'scrMaxCoolingRate', 'Script', """
if not mi.SelectCooling():
    mi.Exit()
T1=mi.TimeDerivative('T')
if len(T1)<10: mi.Exit()
rate=min(T1)
w=mi.Where(T1==rate)
if w<0: mi.Exit()
mi.Value(-rate/60)
mi.Point(idx=w)
""", 'Maximum Cooling Rate', parent='maxCoolingRate')

smp_dict = dataimport.base_dict()
smp_dict['name']['current'] = 'Sample'
ao(smp_dict, 'idx', 'Integer', attr=['Hidden'])
ao(smp_dict, 'ii', 'Integer', attr=['Hidden'])
ao(smp_dict, 'initialDimension', 'Float', 3000., name='Initial dimension')
ao(smp_dict, 'initialWidth', 'Float', 2000., name='Initial width')
ao(smp_dict, 'roi', 'Rect', [0, 0, 640, 480], attr=['Hidden'])
ao(smp_dict, 'profile', 'Profile', attr=['Hidden'])
ao(smp_dict, 'frame', 'Image', attr=['Hidden'])
# frame?

hsm_smp_dict = deepcopy(smp_dict)
ao(hsm_smp_dict, 'Sintering', 'Meta')
ao(hsm_smp_dict, 'Softening', 'Meta')
ao(hsm_smp_dict, 'Sphere', 'Meta')
ao(hsm_smp_dict, 'HalfSphere', 'Meta')
ao(hsm_smp_dict, 'Melting', 'Meta')


# SCRIPTS
ao(hsm_smp_dict, 'scrSintering', 'Script', """
factor=script.Opt('param_sint')/100.
threshold=obj.At('h',0)*factor
r=obj.Drops('h', threshold)
if r is False: mi.Exit()
i,ti,val = r
if ti<0: mi.Exit()
mi.t(ti)
mi.T(obj.At('T',ti))
mi.Value(obj.At('h',ti))""", parent='Sintering')
ao(hsm_smp_dict, 'param_sint', 'Integer', 95,
   'Height shrinking for Sintering', parent='Sintering')

# ao(std_hsm,'Softening','Script',"""
# min_decrease=script.Opt('param_soft')
# ratio=mi.Ratio('Sint','Width')*obj.Opt('initialDimension')/obj.Opt('initialWidth')
# ratio=(ratio/ratio[0])
# i=mi.Drops(ratio,min_decrease/100.)
# if i<0: mi.Exit()
# v=ratio[i]
# mi.Point(i)
# mi.Value(v)""")
# ao(std_hsm,'param_soft','Integer',5,'Minimum % decrease in h/w ratio for Softening',parent='Softening')

ao(hsm_smp_dict, 'scrSoftening', 'Script', """
threshold=script.Opt('param_soft')
method=script.Opt('param_softMethod')
backward=script.Opt('param_softBackward')
if method=='Relative':
	threshold+=mi.At('soft',0)
if backward:
	#... ricerca del massimo e poi all'indietro!
	r=obj.Drops('soft',threshold)
else:
	r=obj.Raises('soft',threshold)
if r is False: mi.Exit()
i,ti,val = r
mi.t(ti)
mi.T(obj.At('T',ti))
mi.Value(obj.At('soft',ti))""", parent='Softening')

ao(hsm_smp_dict, 'param_soft', 'Float', 2.5,
   'Softening parameter threshold', parent='Softening')
ao(hsm_smp_dict, 'param_softMethod', 'Chooser', 'Absolute',
   'Method for softening thresholding', options=['Absolute', 'Relative'], parent='Softening')
ao(hsm_smp_dict, 'param_softBackward', 'Boolean', False,
   'Search threshold starting from the maximum softening value', parent='Softening')

ao(hsm_smp_dict, 'scrSphere', 'Script', """
threshold=script.Opt('param_sphere')
ratio=obj.Ratio('h','w')*obj.Opt('initialDimension')/obj.Opt('initialWidth')
ti=mi.Where(ratio<threshold)
if i<0: mi.Exit()
mi.Point(i)
mi.Value(ratio[i])""", parent='Sphere')
ao(hsm_smp_dict, 'param_sphere', 'Float', 1.,
   'Ratio h/w for Sphere', parent='Sphere')

ao(hsm_smp_dict, 'scrHalfSphere', 'Script', """
threshold=script.Opt('param_hsphere')
tol=script.Opt('param_hsphereTol')
ratio=obj.Ratio('h','w')*obj.Opt('initialDimension')/obj.Opt('initialWidth')
i=mi.Where(ratio<threshold)
if i<0: mi.Exit()
v=ratio[i]
if abs(threshold-v)>tol:
	mi.Exit()
mi.Point(i)
mi.Value(v)""", parent='HalfSphere')
ao(hsm_smp_dict, 'param_hsphere', 'Float', 0.5,
   'Ratio h/w for HalfSphere', parent='HalfSphere')
ao(hsm_smp_dict, 'param_hsphereTol', 'Float', 0.2,
   'Tolerance for HalfSphere', parent='HalfSphere')

ao(hsm_smp_dict, 'scrMelting', 'Script', """
threshold=script.Opt('param_melt')
ratio=obj.Ratio('h','w')*obj.Opt('initialDimension')/obj.Opt('initialWidth')
i=mi.Where(ratio<threshold)
if i<0:
	mi.Exit()
mi.Point(i)
mi.Value(ratio[i])""", parent='Melting')
ao(hsm_smp_dict, 'param_melt', 'Float', 0.333,
   'Ratio h/w for Melting', parent='Melting')

kiln_dict = dataimport.kiln_dict()
kiln_dict['name']['current'] = 'Kiln'
ao(kiln_dict, 'Regulation_Kp', 'Float', 0, 'Proportional Factor')
ao(kiln_dict, 'Regulation_Ki', 'Float', 0, 'Integral Factor')
ao(kiln_dict, 'Regulation_Kd', 'Float', 0, 'Derivative Factor')

instr_dict = dataimport.instr_dict()
ao(instr_dict, 'camera', 'Role', ['camerapath', 'default'])

camera_dict = dataimport.instr_dict()
camera_dict['name']['current'] = 'camera'
camera_dict['devpath']['current'] = 'camerapath'
camera_dict['dev']['current'] = 'camera'
ao(camera_dict, 'last_frame', 'Image', [], attr=['Hidden'])
ao(camera_dict, 'size', 'List', [640, 480], attr=['Hidden'])
ao(camera_dict, 'Analysis_umpx', 'Integer', 1, name='Micron to pixel conversion')
ao(camera_dict, 'nSamples', 'Integer', 1, attr=['Hidden'])
ao(camera_dict, 'Analysis_instrument', 'String', 'hsm', attr=['Hidden'])
ao(camera_dict, 'Analysis_Simulation', 'Boolean', True, attr=['Hidden'])


anl_dict = dataimport.base_dict()
ao(anl_dict, 'blackWhite', 'Boolean', True, attr=['Hidden'])
ao(anl_dict, 'adaptiveThreshold', 'Boolean', False, attr=['Hidden'])
ao(anl_dict, 'autoregion', 'Boolean', False, attr=['Hidden'])

server_dict = dataimport.server_dict()

empty = {'self': deepcopy(camera_dict)}

# Tree for generical sample
smp_tree = {'self': smp_dict,
                'analyzer': {'self': anl_dict },
}

# Tree for hsm sample
hsm_smp_tree = {'self': hsm_smp_dict,
                'analyzer': {'self': anl_dict },
}

# Tree for generical instrument
instr_tree = {'self': instr_dict,
                     'measure': {'self': measure_dict},
}

# Main tree
tree_dict = {'self': server_dict,
             'kiln': {'self': kiln_dict},
             'beholder': {'self': deepcopy(dataimport.base_dict()),
                          'idx0': {'self': camera_dict}
                          }

             }

def create_tree(outFile, tree, path='/'):
    """Recursive tree structure creation"""
    for key, foo in tree.list():
        if outFile.has_node(path, key):
            logging.debug('Path already found:', path, key)
            continue
        logging.debug('Creating group:', path, key)
        outFile.create_group(path, key, key)
        dest = path + key + '/'
        if outFile.has_node(dest):
            continue
        create_tree(outFile, tree.child(key), dest)


class Converter(dataimport.Converter):
    name = 'Misura3'
    file_pattern = '*.mdb'
    outpath = ''
    interrupt = False
    progress = 0
    outFile = False

    def __init__(self, dbpath, outdir=False):
        self.dbpath = dbpath

        if not outdir:
            outdir = os.path.dirname(dbpath)
            outdir = os.path.join(outdir, 'm4')
            if not os.path.exists(outdir):
                os.mkdir(outdir)
        self.outdir = outdir
        self.m4db = os.path.join(outdir, 'database.sqlite')

    def get_outpath(self, tcode=False, img=True, force=True, keep_img=True):
        # Open DB and import test data
        if not tcode:
            self.dbpath, tcode = self.dbpath.split('|')
        self.outFile = False
        self.outpath = False
        self.tcode = tcode
        conn, cursor = m3db.getConnectionCursor(self.dbpath)
        cursor.execute("select * from PROVE where IDProve = '%s'" % tcode)
        tests = cursor.fetchall()
        if len(tests) != 1:
            logging.debug( 'Wrong number of tests found', tests)
            conn.close()
            return False
        test = tests[0]
        self.test = test
        self.icode = m3db.getImageCode(tcode)
        cursor.execute(
            "select * from IMMAGINI where [IDProve] = '%s' order by Tempo" % self.icode)
        self.rows = cursor.fetchall()
        logging.debug('CONVERT GOT', len(self.rows))
        if len(self.rows) < 1:
            logging.debug('No points', self.rows)
            conn.close()
            return False
        conn.close()
        # ##
        # Open Output File

        safeName = ''.join(
            c for c in self.test[m3db.fprv.Desc_Prova] if c in valid_chars)
        self.outpath = os.path.join(self.outdir, safeName + '_' + tcode + '.h5')
        self.img = True
        # Manage overwriting options
        if os.path.exists(self.outpath):
            # If I am forcing overwriting and not caring about current images:
            # create new file
            self.outFile = False
            try: 
                self.outFile = indexer.SharedFile(self.outpath, mode='a')
                # Keep images only if they exist
                keep_img = keep_img and self.outFile.has_node('/hsm/sample0/frame')
            except:
                logging.error('Error opening existing file:', format_exc())
                force = True
                keep_img = False
            
            if not force:
                logging.debug('Already exported path:', self.outpath)
                self.outFile.close()
                return False
            elif force and not keep_img:
                if self.outFile:
                    self.outFile.close()
                os.remove(self.outpath)
                self.outFile = indexer.SharedFile(self.outpath, mode='w')
            # Keep current images
            elif keep_img:
                self.img = False
        # If it does not exist, create!
        else:
            self.outFile = indexer.SharedFile(self.outpath, mode='w')
        self.keep_img = keep_img
        self.force = force
        return self.outpath


    def convert(self, frm='ImageM3', max_num_images=-1):
        """Extract a Misura 3 test and export into a Misura 4 test file"""
        conn, cursor = m3db.getConnectionCursor(self.dbpath)
        outFile = self.outFile
        zt = time()
        log_ref = reference.Log(outFile, '/', server_dict['log'])

        def log(msg, priority=10):
            # TODO: check zerotime
            log_ref.commit([[time() - zt, (priority, msg)]])

        log('Importing from %s, id %s' % (self.dbpath, self.tcode))
        log('Conversion Started at ' + 
            datetime.now().strftime("%H:%M:%S, %d/%m/%Y"))
        log('Conversion Parameters: \n\tImages: %r, \n\tUpdate: %r, \n\tKeep Images: %r, \n\tImage Format: %r' % (
            self.img, self.force, self.keep_img, frm))

        self.progress = 11
        # Heating cycle table
        cycle = m3db.getHeatingCycle(self.test)
        self.progress = 12

        # ##
        # CONFIGURATION
        serial = hashlib.md5(self.dbpath).hexdigest()[:8]
        tree = deepcopy(tree_dict)
        # Create instrument dict
        instr = m3db.getInstrumentName(self.test[m3db.fprv.Tipo_Prova])
        tree[instr] = deepcopy(instr_tree)
        if instr == 'hsm':
            tree[instr]['sample0'] = deepcopy(hsm_smp_tree)
        else:
            tree[instr]['sample0'] = deepcopy(smp_tree)
        # Get a configuration proxy
        tree = option.ConfigurationProxy(tree, readLevel=5, writeLevel=5)
        instrobj = getattr(tree, instr)
        tree['runningInstrument'] = instr
        tree['lastInstrument'] = instr
        tree['eq_sn'] = serial
        instrobj['name'] = instr
        # Sample
        smp = instrobj.sample0
        smp['name'] = self.test[m3db.fprv.Desc_Prova]

        # Set ROI
        roi = [0, 0, 640, 480]
        if self.tcode.endswith('L'):
            roi[2] = 320.
        elif self.tcode.endswith('R'):
            roi[0] = 320.
            roi[2] = 320.
        smp['roi'] = roi

        # Measure
        tid = self.dbpath + '|' + self.tcode
        tdate0 = self.test[m3db.fprv.Data]
        zerotime = mktime(tdate0.timetuple())
        tdate = tdate0.strftime("%H:%M:%S, %d/%m/%Y")
        logging.debug(self.test[m3db.fprv.Data].strftime("%H:%M:%S, %d/%m/%Y"))
        instrobj.measure['zerotime'] = zerotime
        instrobj.measure['name'] = self.test[m3db.fprv.Desc_Prova]
        instrobj.measure['comment'] = self.test[m3db.fprv.Note]
        instrobj.measure['date'] = tdate
        instrobj.measure['id'] = tid
        uid = hashlib.md5(self.dbpath + '|' + self.tcode).hexdigest()
        instrobj.measure['uid'] = uid
        instrobj['zerotime'] = zerotime

        # Kiln
        tree.kiln['curve'] = cycle
        tree.kiln['Regulation_Kp'] = self.test[m3db.fprv.Pb]
        tree.kiln['Regulation_Ki'] = self.test[m3db.fprv.ti]
        tree.kiln['Regulation_Kd'] = self.test[m3db.fprv.td]
        tree.kiln['ksn'] = serial
        # Create the hierarchy
        create_tree(outFile, tree)

        # ##
        # GET THE ACTUAL DATA
        header, columns = m3db.getHeaderCols(self.test[m3db.fprv.Tipo_Prova], self.tcode)
        rows = np.array(self.rows)
        self.rows = rows
        logging.debug(header, columns, len(rows[0]), instr)
        instr_path = '/' + instr
        smp_path = instr_path + '/sample0'
        smp_path_T = smp_path+'/T'

        # TODO: Check conf node (???)
    # 	if not hasattr(outFile.root,'conf'):
    # 		outFile.close()
    # 		os.remove(outpath)
    # 		return convert(dbpath, tcode, outdir, img,force, keep_img,frm)

        self.progress = 13

        arrayRef = {}
        timecol = rows[:, m3db.fimg.Tempo].astype('float')
        timecol, unidx = np.unique(timecol, return_index=True)
        # Set first point as zero time
        timecol -= timecol[0]
        ini_area = 0.0
        dim = set(['d', 'h', 'w', 'camA', 'camB']).intersection(
            set(header))
        ini0 = self.test[m3db.fprv.Inizio_Sint]
        initialDimension = 0
        # Convert data points
        for i, col in enumerate(header):
            if self.interrupt:
                self.cancel()
                return False
            if col == 't':
                data = timecol
                continue
            if columns[i] >= rows.shape[1]:
                logging.debug("Skipping undefined column. Old db?", columns[i])
                continue
            data = rows[:, columns[i]].astype('float')[unidx]
            # Skip invalid data
            if np.isnan(data).all():
                continue
            data[~np.isfinite(data)] = 0.0
             
            # Unit and client-side unit
            if col == 'h':
                ini1 = 3000.
            elif col == 'A':
                ini1 = -data[0]
            elif col == 'w':
                ini1 = 2000.
            elif col in ['d', 'camA', 'camB']:
                ini1 = ini0 * 100.                

            unit = False
            csunit = False
            if col == 'd' or 'Percorso' in col:
                data = ini1*data / 1000./100.
                unit = 'micron'
            elif 'Percorso' in col:
                data = data / 1000.
                unit = 'percent'
            elif col == 'h':
                data = ini1*data / 100./100.
                unit = 'micron'
            elif col == 'soft':
                data = data / 100.
                unit = 'percent'
            elif col == 'A':
                data = -data
                unit = 'micron^2'
            elif col == 'P':
                data = data / 10.
                unit = 'micron'
            elif col == 'w':
                logging.debug(data)
                data = data / 200.
                unit = 'micron'
            if col in ['T', 'P', 'S']:
                arrayRef[col] = reference.Array(outFile, '/summary/kiln', kiln_dict[col])
            else:
                opt = ao({}, col, 'Float', 0, col, attr=['History', 'Hidden'])[col]
                if col in dim:
                    opt['percent'] = col not in ['camA', 'camB', 'w']
                if col in ['d', 'h']:
                    opt['initialDimension'] = ini1
                    initialDimension = ini1
                if unit:
                    opt['unit'] = unit
                if csunit:
                    opt['csunit'] = csunit
                instrobj.sample0.sete(col, opt)
                arrayRef[col] = reference.Array(outFile, '/summary' + smp_path, opt)
            # Recreate the reference so the data is clean
            arrayRef[col].dump()
            path = arrayRef[col].path
            base_path = path[8:]
            # Create hard links
            if not outFile.has_node(base_path):
                outFile.link(base_path, path)
            ref = arrayRef[col]
            ref.append(np.array([timecol, data]).transpose())
            
        # Create sample0/T links
        for pre in ['','/summary']:
            if not outFile.has_node(pre+smp_path_T):
                outFile.link(pre+smp_path_T, '/kiln/T')
            
        outFile.flush()

        self.progress = 20
        # ##
        # ASSIGN INITIAL DIMENSION
        smp['initialDimension'] = initialDimension
        outFile.flush()

        self.progress = 21
        log('Converted Points: %i\n' % (len(rows) - 1) * len(header))
        ######
        # Final configuration adjustment and writeout
        ######
        elapsed = float(timecol[-1])
        instrobj.measure['elapsed'] = elapsed
        print 'final timecol', timecol[0], timecol[-1]
        # Get characteristic shapes
        if instr == 'hsm':
            sh = m3db.getCharacteristicShapes(self.test, rows.transpose())
            print 'got characteristic shapes', sh
            instrobj.sample0.desc.update(sh)

        # ##
        # IMAGES
        imgdir = os.path.join(os.path.dirname(self.dbpath), self.icode)
        if os.path.exists(imgdir) and self.img and (instr in ['hsm', 'drop', 'post']):
            omg = self.append_images(imgdir, frm, max_num_images)
            if not omg:
                if self.interrupt:
                    return False
                else:
                    log('ERROR Appending images')


        # Write conf tree
        outFile.save_conf(tree.tree())
        outFile.set_attributes('/conf', attrs={'version': '3.0.0',
                                'zerotime': zerotime,
                                'elapsed': elapsed,
                                'instrument': instr,
                                'date': tdate,
                                'serial': serial,
                                'uid': uid })
        self.progress = 99
        log('Appending to Misura database: '+ self.outpath)
        outFile.close()
        indexer.Indexer.append_file_to_database(self.m4db, self.outpath)
        log('Conversion ended: '+ self.outpath)
        self.progress = 100

        return self.outpath



    def append_images(self, imgdir, frm, max_num_images=-1):
        refClass = getattr(reference, frm)
        ref = refClass(self.outFile, '/hsm/sample0', smp_dict['frame'])
        a = self.outFile.get_attributes(ref.path)
        self.outFile.set_attributes(ref.path, attrs=a)
        sjob = self.progress
        job = (98. - sjob) / len(self.rows)
        oi = 0
        esz = 0
        t0 = float(self.rows[0, m3db.fimg.Tempo])
        for i, r in enumerate(self.rows):
            if self.interrupt:
                self.cancel()
                break
            if i >= max_num_images and max_num_images >= 0:
                break
            nj = sjob + i * job
            self.progress = int(nj)

            num = int(r[m3db.fimg.Numero_Immagine])
            img = '%sH.%03i' % (self.icode, int(num))
            img = os.path.join(imgdir, img)
            if not os.path.exists(img):
                logging.debug('Skipping non-existent image', img)
                continue

            im, size = decompress(img, frm)

            sz = len(im)
            esz += sz
            t = float(self.rows[i, m3db.fimg.Tempo]) - t0
#            print 'append_images', t, t0, float(self.rows[i, m3db.fimg.Tempo])
            ref.commit([[t, im]])
            oi += 1
            self.outFile.flush()
        logging.debug('Included images:', oi)
        logging.debug('Expected size:', esz / 1000000.)
        return True


def decompress(img, frm):
    """Available formats (Storage):
            'Image': misura compression algorithm (Image)
            'ImageM3': legacy Misura3 compression algorithm (Binary)
            other: any PIL supported format (Binary)
    """
    fr = open(img, 'rb').read()
    if frm == 'ImageM3':
        return (fr, (640, 480))
    try:
        fr = bitmap.decompress(fr)
        if frm == 'ImageBMP':
            return fr
        fr = fr[::-1]
        im = Image.fromstring('L', (640, 480), fr)
        im = im.convert('L')
        if frm == 'Image':
            return (np.asarray(im), im.size)
        else:
            sio = StringIO.StringIO()
            im.save(sio, frm)
            im.save('debug.' + frm, frm)
            sio.seek(0)
            r = sio.read()
            return (r, im.size)
    except:
        logging.debug(format_exc())
        logging.debug('Error reading image', img)
        r = ('', (0, 0))
    return r

