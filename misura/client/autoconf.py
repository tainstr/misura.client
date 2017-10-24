#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Auto configuration script for standard Misura4 full-optional"""
from traceback import print_exc
from time import time, sleep

##################
# Configuration
##################

# Camera serials
left_cam_serial = 's61608502'
right_cam_serial = 's61546509'
flex_cam_serial = 's61628526'
micro_cam_serial = 's191628501'

# Motor boards
# DEBUG SEQUENCE
board_microfocus_path = 'idx0'
# board_left_xy_path = 'idx0/board1'
# board_left_angk_path = 'idx0/board2'
# board_right_xy_path = 'idx0/board3'
# board_right_ang_path = 'idx0/board4'

# REAL SEQUENCE
board_right_ang_path = 'idx0/board1'
board_right_xy_path = 'idx0/board2'
board_left_xy_path = 'idx0/board3'
board_left_angk_path = 'idx0/board4'


tacontroller = '192.1.200.20:2020'  # False

##################
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from exceptions import RuntimeError


def jlog(*a):
    logging.debug('job', *a)

def speed(motor):
    if motor['sloPe'] <= 8000:
        motor['sloPe'] = 8000
    if motor['Rate'] <= 3000:
        motor['Rate'] = 3000

def toPath(parent, path):
    r = parent.toPath(path)
    if not r:
        msg = logging.critical('Path was not found:', path)
        raise RuntimeError(msg)
    return r


class FirstSetupWizard(object):
    def __init__(self, server, left_cam_serial=left_cam_serial,
                 right_cam_serial=right_cam_serial,
                 flex_cam_serial=flex_cam_serial,
                 micro_cam_serial=micro_cam_serial,
                 board_microfocus_path=board_microfocus_path,
                 board_left_xy_path=board_left_xy_path,
                 board_left_angk_path=board_left_angk_path,
                 board_right_xy_path=board_right_xy_path,
                 board_right_ang_path=board_right_ang_path,
                 jobs=lambda *a: jlog(a),
                 job=lambda *a: jlog(a),
                 done=lambda *a: jlog(a)):
        self.aborted = False
        
        self.tc_hitemp = None
        self.tc_termostat = None
        self.power_out = None

        self.left_cam_serial = left_cam_serial
        self.right_cam_serial = right_cam_serial
        self.flex_cam_serial = flex_cam_serial
        self.micro_cam_serial = micro_cam_serial

        self.board_microfocus_path = board_microfocus_path
        self.board_left_xy_path = board_left_xy_path
        self.board_left_angk_path = board_left_angk_path
        self.board_right_xy_path = board_right_xy_path
        self.board_right_ang_path = board_right_ang_path

        self.server = server
        m = server
        self.board_main = m.morla.idx0

        self.jobs = jobs
        self.job = job
        self.done = done

    def set_objects(self):
        mo = self.server.morla
        self.board_microfocus = toPath(mo, self.board_microfocus_path)
        self.board_left_xy = toPath(mo, self.board_left_xy_path)
        self.board_left_angk = toPath(mo, self.board_left_angk_path)
        self.board_right_xy = toPath(mo, self.board_right_xy_path)
        self.board_right_ang = toPath(mo, self.board_right_ang_path)

        self.m_focus = self.board_microfocus.X
        self.m_micro = self.board_microfocus.Y
        self.left_x = self.board_left_xy.X
        self.left_y = self.board_left_xy.Y
        self.left_ang = self.board_left_angk.X
        self.m_flash = self.board_left_angk.Y
        self.right_x = self.board_right_xy.X
        self.right_y = self.board_right_xy.Y
        self.right_ang = self.board_right_ang.X

    def read_serials(self):
        m = self.server

        for cam in m.beholder.devices:
            dp = cam['devpath']
            cn = cam['name'].lower()
            if 'left' in cn:
                self.left_cam_serial = dp
                self.board_left_xy_path = '/'.join(
                    cam.encoder.x['motor'][0].split('/')[2:-2])
                self.board_left_angk_path = '/'.join(
                    cam.encoder.angle['motor'][0].split('/')[2:-2])

            elif 'right' in cn:
                self.right_cam_serial = dp
                self.board_right_xy_path = '/'.join(
                    cam.encoder.x['motor'][0].split('/')[2:-2])
                self.board_right_ang_path = '/'.join(
                    cam.encoder.angle['motor'][0].split('/')[2:-2])

            elif 'flex' in cn:
                self.flex_cam_serial = dp
                self.board_microfocus_path = '/'.join(
                    cam.encoder.y['motor'][0].split('/')[2:-2])

            elif 'micro' in cn:
                self.micro_cam_serial = dp
                self.board_microfocus_path = '/'.join(
                    cam.encoder.focus['motor'][0].split('/')[2:-2])

        logging.debug('Read serials:\n', self.__dict__)
        # Check configured roles
        # if m.hsm['camera'][0] not in ('None', None, ''):
        #   if not m.hsm['camera'][0].endswith(self.micro_cam_serial):

    def camera_names(self):
        m = self.server
        # Camera names
        try:
            self.left_cam = toPath(m.beholder, self.left_cam_serial)
            self.left_cam['name'] = 'Left'
            self.left_cam['autocrop'] = 'Never'
            self.left_cam['clock'] = 26
            self.left_cam.save('default')
        except:
            print_exc()

        try:
            self.right_cam = toPath(m.beholder, self.right_cam_serial)
            self.right_cam['name'] = 'Right'
            self.right_cam['autocrop'] = 'Never'
            self.right_cam['clock'] = 26
            self.right_cam.save('default')
        except:
            print_exc()
        try:
            self.flex_cam = toPath(m.beholder, self.flex_cam_serial)
            self.flex_cam['name'] = 'Flex'
            self.flex_cam['autocrop'] = 'Never'
            self.flex_cam['clock'] = 26
            self.flex_cam.save('default')
        except:
            print_exc()
        try:
            self.micro_cam = toPath(m.beholder, self.micro_cam_serial)
            self.micro_cam['name'] = 'Microscope'
            self.micro_cam['clock'] = 92
            self.micro_cam.save('default')
        except:
            print_exc()
            
    def wait(self, timeout, m):
        jn = 'Waiting motor {}, {}'.format(m['name'], m['fullpath'])
        self.jobs(100, jn)
        t = time()
        while m['moving'] and not self.aborted:
            dt = time()-t
            if dt > timeout:
                logging.error('Motor timed out')
                break
            p = m['position']
            sleep(0.1)
            logging.debug('waiting', p)
            self.job(int(100*dt/timeout), jn)
        m.wait(0.1)
        r = not m['moving']
        if not r:
            logging.error('Timed out while waiting for', m['fullpath'])
        self.done(jn)
        return r
    
    def send_to_zero(self, motor):
        print 'sending to zero:', motor['fullpath'], motor['sloPe'], motor['Rate']
        speed(motor)
        motor['micro'] = 'lower step'
        print motor['limits']
    
        if not self.wait(60, motor):
            return False
        if motor['goingTo'] != 0:
            logging.error('goingTo!=0 after send_to_zero', motor['goingTo'])
            return False
        if motor['position'] == 0:
            logging.error('position!=0 after send_to_zero', motor['goingTo'])
            return False
        return True
    
    def motor_find_limits(self, motor, name):
        print 'motor_find_limits', motor['fullpath'], name, motor['sloPe'], motor['Rate']
        speed(motor)
        motor['name'] = name
        motor['micro'] = 'both ends'
        print name, motor['limits']
        if not self.wait(60, motor):
            return False
        logging.error('found steps: {}'.format(motor['steps']))
        self.send_to_zero(motor)
        motor.save('default')
        return True

    def board_send_to_zero(self, board):
        motors = board['motors']
        print 'board_send_to_zero', motors, board.list()
        for dev in board.devices:
            if self.aborted:
                return False
            if dev['devpath'] in motors:
                self.send_to_zero(dev)
                continue
            elif dev['devpath'] in ['X', 'Y']:
                print 'skipping disabled motor', dev['fullpath']
            else:
                print 'send_to_zero child board', dev['fullpath']
                self.board_send_to_zero(dev)
        return False


    def configure_motors(self):
        assert len(self.server.morla.list()
                   ) == 1, 'Motion board detection failed'
        assert len(self.server.morla.idx0.list()
                   ) == 6,  'Wrong daisy chain detection'

        self.board_main.maxDaisy = 5
        # High speed motors
        self.m_micro['Rate'] = 3000
        self.m_micro['sloPe'] = 8000
        self.m_micro.save('default')
        self.m_flash['Rate'] = 2000
        self.m_flash['sloPe'] = 10000
        self.m_flash.save('default')
        
        # Angulars  in full power
        self.left_ang['mOde'] = 2
        self.left_x['mOde'] = 2
        self.right_ang['mOde'] = 2
        self.right_x['mOde'] = 2

        print 'Initialization Order'

        order = lambda *lst: '\n'.join([dev['fullpath'][:-1]
                                        for dev in lst] + ['#END'])
        m = self.server.morla

        orderZero = order(self.m_micro, self.m_focus,
                          self.left_x, self.right_x,
                          self.left_y, self.right_y,
                          self.left_ang, self.right_ang)

        m['orderZero'] = orderZero
        m['order'] = orderZero

        m.save('default')

        orderHsm = order(self.left_ang, self.right_ang,
                         self.left_x, self.right_x,
                         self.left_y, self.right_y,
                         self.m_micro, self.m_focus,
                         )
        m['order'] = orderHsm
        m.save('hsm')
        
    def board_find_limits(self, board, xname=False, yname=False):
        if self.aborted:
            logging.debug('Aborted: skipping board_find_limits', xname, yname)
        motors = []
        names = []
        if xname:
            motors.append('X')
            names.append(xname)
        if yname:
            motors.append('Y')
            names.append(yname)
        board.name = '/'.join(names)
        board.motors = ', '.join(motors)
        board.save('default')
        if xname and not self.aborted:
            self.motor_find_limits(board.X, xname)
        if yname and not self.aborted:
            self.motor_find_limits(board.Y, yname)
        return not self.aborted

    def configure_limits(self):
        # Safety zero positioning
        jn = 'Configuring motor limits'
        self.jobs(7, jn)

        self.board_microfocus['motors'] = 'X,Y'
        self.board_left_xy['motors'] = 'X,Y'
        self.board_left_angk['motors'] = 'X,Y'
        self.board_right_xy['motors'] = 'X,Y'
        self.board_right_ang['motors'] = 'X'

        self.job(1, jn, 'Sending to zero all motors')
        self.board_send_to_zero(self.board_microfocus)
        self.job(2, jn, 'Finding Focus and HSM limits')
        self.board_find_limits(self.board_microfocus, 'Focus M1', 'HSM-Flex M2')
        self.job(3, jn, 'Finding Left X/Y limits')
        self.board_find_limits(self.board_left_xy, 'Left X M7', 'Left Y M8')
        self.job(4, jn, 'Finding Right Angle limits')
        self.board_find_limits(self.board_right_ang, 'Right Angle M4')
        self.job(5, jn, 'Finding Right X/Y limits')
        self.board_find_limits(self.board_right_xy, 'Right X M5', 'Right Y M6')
        self.job(6, jn, 'Finding Left Angle/Kiln limits')
        self.board_find_limits(self.board_left_angk, 'Left Angle M9', 'Kiln M3')
        self.done(jn)

    def starting_position(self, motor, steps, config_name, job=1, jobname='Starting position'):
        if self.aborted:
            logging.error('Aborted: skipping starting_position', motor['fullpath'], config_name)
        self.job(job, jobname, 'Starting position', motor['fullpath'], config_name)
        print 'starting_position', motor['sloPe'], motor['Rate']
        speed(motor)
        motor['goingTo'] = steps
        self.wait(60, motor)
        if motor['position'] != steps:
            logging.error('starting_position: steps mismatch',
                          motor['position'], steps)
        motor.save(config_name)
        motor['goingTo'] = 0
        self.wait(60, motor)

    def configure_starting_positions(self):
        jn = 'Configuring starting positions'
        self.jobs(12, jn)
        logging.debug('Microscope motors')
        self.starting_position(
            self.m_micro, self.m_micro['steps'] * 3 / 4., 'hsm', 1, jn)

        logging.debug('Horizontal motors')
        self.starting_position(
            self.left_x, self.left_x['steps'] / 2, 'horizontal', 2, jn)
        self.starting_position(
            self.right_x, self.right_x['steps'] / 2, 'horizontal', 3, jn)
        self.starting_position(
            self.left_y, self.left_y['steps'] / 10, 'horizontal')
        self.starting_position(
            self.right_y, self.right_y['steps'] / 4, 'horizontal', 4, jn)

        logging.debug('Vertical motors')
        self.starting_position(
            self.left_x, self.left_x['steps'], 'vertical', 5, jn)
        self.starting_position(
            self.left_ang, self.left_ang['steps'], 'vertical', 6, jn)
        self.starting_position(
            self.right_x, self.right_x['steps'], 'vertical', 7, jn)
        self.starting_position(
            self.right_ang, self.right_ang['steps'], 'vertical', 8, jn)
        self.starting_position(
            self.left_y, self.left_y['steps'] * 9 / 10, 'vertical', 9, jn)
        self.starting_position(
            self.right_y, self.right_y['steps'] / 6, 'vertical', 10, jn)

        logging.debug('Flex motors')
        self.starting_position(
            self.m_micro, self.m_micro['steps'] / 2, 'flex', 11, jn)

        self.done(jn)

    def configure_baudrates(self):
        b0 = self.server.morla.idx0
        b0.raw("{0000}115200b")      # sets baudrate to 115200 for board 4
        b0.raw("{000}115200b")       # sets baudrate to 115200 for board 3
        b0.raw("{00}115200b")        # sets baudrate to 115200 for board 2
        b0.raw("{0}115200b")         # sets baudrate to 115200 for board 1
        b0.raw("{}115200b")          # sets baudrate to 115200 for board 0

        b0.baudrate = 115200         # tells the server the new baudrate

        b0.raw("{0000}123456789e")   # saves eeprom for board 4
        b0.raw("{000}123456789e")    # saves eeprom for board 3
        b0.raw("{00}123456789e")     # saves eeprom for board 2
        b0.raw("{0}123456789e")      # saves eeprom for board 1
        b0.raw("{}123456789e")       # saves eeprom for board 0

        b0.save('default')

    ######
    # CAMERAS
    ######
    def configure_cameras(self):
        print 'Configure cameras'
        self.camera_names()
        m = self.server
        m.beholder['servedClasses'] = ['']
        m.beholder.save('default')
        # Instruments association
        m.hsm['camera'] = self.micro_cam
        m.hsm.save('default')

        m.horizontal['cameraLeft'] = self.left_cam
        m.horizontal['cameraRight'] = self.right_cam
        m.horizontal.save('default')

        m.vertical['cameraBase'] = self.right_cam
        m.vertical['cameraHeight'] = self.left_cam
        m.vertical.save('default')

        m.flex['camera'] = self.flex_cam
        m.flex['cameraLeft'] = self.left_cam
        m.flex['cameraRight'] = self.right_cam
        m.flex.save('default')

        # Samples association
        # Microscope camera
        m.hsm['nSamples'] = 1
        self.micro_cam['name'] = 'Left'
        self.micro_cam['smp0'] = [m.hsm.sample0['fullpath'], 'default']
        self.micro_cam.save('default')

        # Horizontal left/right
        m.horizontal['nSamples'] = 1
        self.left_cam['smp0'] = m.horizontal.sample0.Left
        self.left_cam.save('horizontal')
        self.right_cam['smp0'] = m.horizontal.sample0.Right
        self.right_cam.save('horizontal')

        # Vertical
        m.vertical['nSamples'] = 1
        self.left_cam['name'] = 'Height'
        self.left_cam['smp0'] = m.vertical.sample0.Base
        self.left_cam.save('vertical')
        self.right_cam['name'] = 'Base'
        self.right_cam['smp0'] = m.vertical.sample0.Height
        self.right_cam.save('vertical')

    def configure_encoders(self):
        print 'Configure encoders'
        self.camera_names()
        for cam in self.server.beholder.devices:
            cam.encoder.focus.motor = self.m_focus
            cam.encoder.focus.save('default')

        try:
            self.micro_cam.encoder.y.motor = self.m_micro
            self.micro_cam.encoder.y.save('default')
        except:
            print_exc()

        try:
            self.flex_cam.encoder.y.motor = self.m_micro
            self.flex_cam.encoder.y.save('default')
        except:
            print_exc()

        try:
            self.left_cam.encoder.x.motor = self.left_x
            self.left_cam.encoder.x.align = -2
            self.left_cam.encoder.x.save('default')
            self.left_cam.encoder.y.motor = self.left_y
            self.left_cam.encoder.y.save('default')

            self.left_cam.encoder.angle.motor = self.left_ang
            self.left_cam.encoder.angle.save('default')
        except:
            print_exc()

        try:
            self.right_cam.encoder.x.motor = self.right_x
            self.right_cam.encoder.x.align = 2
            self.right_cam.encoder.x.save('default')

            self.right_cam.encoder.y.motor = self.right_y
            self.right_cam.encoder.y.save('default')

            self.right_cam.encoder.angle.motor = self.right_ang
            self.right_cam.encoder.angle.save('default')
        except:
            print_exc()

    def process_tc_reader(self, dev):
        """Identify TC Reader device"""
        if dev['model'] == '3016':
            dev['name'] = 'High Temperature'
            dev['inputch0'] = 13
            dev['inputch1'] = 13
            dev['inputch2'] = 14
            dev['inputch3'] = 14
            dev.save('default')
            self.tc_hitemp = dev
        elif dev['model'] == '3014':
            dev['name'] = 'Termostat'
            dev['input'] = 23
            dev.save('default')
            self.tc_termostat = dev

    def configure_epack(self):
        """Configure the system for ePack device"""
        m = self.server
        assert len(m.smaug.list()
                   ) == 3, 'Wrong number of thermal control devices'
        m.smaug['epack'] = '10.0.8.88:502'
        m.smaug['rescan']
        m.smaug.save('default')

        for dev in m.smaug.devices:
            if dev['mro'][0] == 'DatExel':
                self.process_tc_reader(dev)
            if dev['mro'][0] == 'Eurotherm_ePack':
                self.power_out = dev

        assert self.tc_hitemp != None, 'High temperature thermocouple reader not found'
        assert self.tc_termostat != None, 'Low temperature thermocouple reader not found'
        assert self.power_out != None, 'Power controller not found'

        ht = self.tc_hitemp['fullpath']
        ts = self.tc_termostat['fullpath']
        pw = self.power_out['fullpath']
        m.kiln.setattr('Ts', 'options', [ht, 'default', 'ch0'])
        m.kiln.setattr('Ts2', 'options', [ht, 'default', 'ch1'])
        m.kiln.setattr('Tk', 'options', [ht, 'default', 'ch2'])
        m.kiln.setattr('Th', 'options', [ht, 'default', 'ch3'])

        m.kiln.setattr('Te', 'options', [ts, 'default', 'ch1'])

        m.kiln.setattr('P', 'options', [pw, 'default', 'power'])
        m.kiln.setattr('powerSwitch', 'options', [pw, 'default', 'enabled'])

    def configure_tacontroller(self):
        """Configure system for TAController device"""
        m.smaug['socket'] = tacontroller
        m.smaug['rescan']
        m.smaug.save('default')
        ta = getattr(m.smaug, tacontroller.replace('.', '').replace(':', ''))
        ta['name'] = 'TAController'
        ta.save('default')
        ta = ta['fullpath']
        m.kiln.setattr('customRegulator', 'options', [ta, 'default'])
        m.kiln.setattr('Ts', 'options', [ta, 'default', 'T'])
        m.kiln.setattr('Tk', 'options', [ta, 'default', 'TFurnace'])
        m.kiln.setattr('Te', 'options', [ta, 'default', 'RT'])
        m.kiln.setattr('P', 'options', [ta, 'default', 'power'])

    def configure_kiln(self):
        print 'Configure kiln'
        m = self.server
        m.kiln.motor = self.m_flash
        m.kiln['motorStatus'] = 2

        if not tacontroller:
            self.configure_epack()
        else:
            self.configure_tacontroller()
        m.kiln.save('default')
        
    def abort(self):
        self.aborted = True

    def do(self, argv=False):
        """Full setup"""
        self.aborted = False
        if not argv:
            argv = 'mcek'
        logging.debug('DO', argv)

        argv = set(argv)
        if 's' in argv:
            self.read_serials()
            argv.remove('s')
        self.set_objects()

        jn = 'Setting up: {}'.format(argv)
        self.jobs(jn, len(argv))
        i = 0

        if 'm' in argv:
            self.configure_motors()
            i += 1
            self.job(i, jn, 'Configured motors')
        if self.aborted:
            return
        if 'l' in argv:
            self.configure_limits()
            i += 1
            self.job(i, jn, 'Configured limits')
        if self.aborted:
            return
        if 'p' in argv:
            self.configure_starting_positions()
            i += 1
            self.job(i, jn, 'Configured positions')
        if self.aborted:
            return
        if 'b' in argv:
            self.configure_baudrates()
            i += 1
            self.job(i, jn, 'Configured baudrates')
        if self.aborted:
            return
        if 'c' in argv:
            self.configure_cameras()
            i += 1
            self.job(i, jn, 'Configured cameras')
        if self.aborted:
            return
        if 'e' in argv:
            self.configure_encoders()
            i += 1
            self.job(i, jn, 'Configured encoders')
        if self.aborted:
            return
        if 'k' in argv:
            self.configure_kiln()
            i += 1
            self.job(i, jn, 'Configured kiln')
        if self.aborted:
            return
        self.done(jn)


if __name__ == '__main__':
    from sys import argv
    from misura.client import from_argv
    print """
    s - keep serials
    m - motors
    l - limits
    p - positions
    b - baudrates
    c - cameras
    e - encoders
    k - kiln
    Default: mcek
    All: mlbcek
    """
    m = from_argv()
    fsw = FirstSetupWizard(m)
    fsw.do(argv[-1])
