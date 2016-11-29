#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Auto configuration script for standard Misura4 full-optional"""


##################
# Configuration
##################

# Camera serials
left_cam_serial = 's61443500'
right_cam_serial = 's61443503'
flex_cam_serial = 's61450503'
micro_cam_serial = 's191447500'

# Motor boards
board_microfocus_path = 'idx0'
board_left_xy_path = 'idx0/board1'
board_left_angk_path = 'idx0/board2'
board_right_xy_path = 'idx0/board3'
board_right_ang_path = 'idx0/board4'

# TEST
left_cam_serial = 'simcam0'
right_cam_serial = 'simcam1'
flex_cam_serial = 'simcam2'
micro_cam_serial = 'simcam3'

##################
from misura.canon.logger import Log as logging
from exceptions import RuntimeError

def send_to_zero(motor):
    print 'sending to zero:', motor['fullpath']
    motor['micro'] = 'lower step'
    print motor['limits']
    motor.wait(60)
    if motor['goingTo']!=0:
        logging.error('goingTo!=0 after send_to_zero',motor['goingTo'])
        return False
    if motor['position']==0:
        logging.error('position!=0 after send_to_zero',motor['goingTo'])
        return False
    return True

def board_send_to_zero(board):
    motors = board['motors']
    for dev in board.devices:
        if dev['devpath'] in motors:
            send_to_zero(dev)
            continue
        board_send_to_zero(dev)
    return False


def motor_find_limits(motor, name):
    if motor['sloPe'] == 8000:
        motor['sloPe'] = 3000
    if motor['Rate'] == 800:
        motor['Rate'] = 2000
    motor['name'] = name
    motor['micro'] = 'both ends'
    print motor['limits']
    motor.wait(60)
    logging.error('found steps: {}'.format(motor['steps']))
    send_to_zero(motor)
    motor.save('default')
    return True


def board_find_limits(board, xname=False, yname=False):
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
    if xname:
        motor_find_limits(board.X, xname)
    if yname:
        motor_find_limits(board.Y, yname)
    return True


def starting_position(motor, steps, config_name):
    motor['goingTo'] = steps
    motor.wait(60)
    if motor['position']!=steps:
        logging.error('starting_position: steps mismatch',motor['position'], steps)
    motor.save(config_name)
    motor['goingTo'] = 0
    motor.wait(60)
    
def toPath(parent, path):
    r = parent.toPath(path)
    if not r:
        msg = logging.critical('Path was not found:', path)
        raise RuntimeError(msg)
    return r

class FirstSetupWizard(object):
    def __init__(self, server, left_cam_serial = left_cam_serial,
                            right_cam_serial = right_cam_serial,
                            flex_cam_serial = flex_cam_serial,
                            micro_cam_serial = micro_cam_serial,
                            board_microfocus_path = board_microfocus_path,
                            board_left_xy_path = board_left_xy_path,
                            board_left_angk_path = board_left_angk_path,
                            board_right_xy_path = board_right_xy_path,
                            board_right_ang_path = board_right_ang_path):
        
        self.tc_hitemp = None
        self.tc_termostat = None
        self.power_out = None
        
        self.server = server
        m = server
        self.board_main = m.morla.idx0 
        mo = m.morla
        self.board_microfocus = toPath(mo, board_microfocus_path)
        self.board_left_xy = toPath(mo, board_left_xy_path)
        self.board_left_angk = toPath(mo, board_left_angk_path)
        self.board_right_xy = toPath(mo, board_right_xy_path)
        self.board_right_ang = toPath(mo, board_right_ang_path)
        
        
        self.m_focus = self.board_microfocus.X
        self.m_micro = self.board_microfocus.Y
        self.left_x = self.board_left_xy.X
        self.left_y = self.board_left_xy.Y
        self.left_ang = self.board_left_angk.X
        self.m_flash = self.board_left_angk.Y
        self.right_x = self.board_right_xy.X
        self.right_y = self.board_right_xy.Y
        self.right_ang = self.board_right_ang.X
        
        
        # Camera names
        assert len(m.beholder.list()) == 4, 'Wrong camera identification'
        self.left_cam = toPath(m.beholder, left_cam_serial)
        self.left_cam['name'] = 'Left'
        self.left_cam['autocrop'] = 'Never'
        self.left_cam['clock'] = 26
        self.left_cam.save('default')
        self.right_cam = toPath(m.beholder, right_cam_serial)
        self.right_cam['name'] = 'Right'
        self.right_cam['autocrop'] = 'Never'
        self.right_cam['clock'] = 26
        self.right_cam.save('default')
        self.flex_cam = toPath(m.beholder, flex_cam_serial)
        self.flex_cam['name'] = 'Flex'
        self.flex_cam['autocrop'] = 'Never'
        self.flex_cam['clock'] = 26
        self.flex_cam.save('default')
        self.micro_cam = toPath(m.beholder, micro_cam_serial)
        self.micro_cam['name'] = 'Microscope'
        self.micro_cam['clock'] = 92
        self.micro_cam.save('default')
    
    def configure_motors(self):
        assert len(self.server.morla.list()) == 1, 'Motion board detection failed'
        assert len(self.server.morla.idx0.list()) == 6,  'Wrong daisy chain detection'
    
        self.board_main.maxDaisy = 5
        # High speed motors
        self.m_micro['Rate'] = 3000
        self.m_micro['sloPe'] = 8000
        self.m_flash['Rate'] = 3000
        self.m_flash['sloPe'] = 100000
    
        # Angulars  in full power
        self.left_ang['mOde'] = 2
        self.left_x['mOde'] = 2
        self.right_ang['mOde'] = 2
        self.right_x['mOde'] = 2
        
        print 'Initialization Order'
        
        order = lambda *lst: '\n'.join([dev['fullpath'][:-1] for dev in lst]+['#END'])
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
        
    def configure_limits(self):
        # Safety zero positioning
        board_send_to_zero(self.board_microfocus)
        board_find_limits(self.board_microfocus, 'Focus', 'Microscope')
    
        board_find_limits(self.board_left_xy, 'Left X', 'Left Y')
    
        board_find_limits(self.board_left_angk, 'Left Angle', 'Kiln')
    
        board_find_limits(self.board_right_xy, 'Right X', 'Right Y')
    
        board_find_limits(self.board_right_ang, 'Right Angle')
    
        # Starting positions....
        print 'Microscope motors'
        starting_position(self.m_micro, self.m_micro['steps'] * 3 / 4., 'hsm')
    
        print 'Horizontal motors'
        starting_position(self.left_x, self.left_x['steps'] / 2, 'horizontal')
        starting_position(self.right_x, self.right_x['steps'] / 2, 'horizontal')
        starting_position(self.left_y, self.left_y['steps'] / 10, 'horizontal')
        starting_position(self.right_y, self.right_y['steps'] / 4, 'horizontal')
    
        print 'Vertical motors'
        starting_position(self.left_x, self.left_x['steps'], 'vertical')
        starting_position(self.left_ang, self.left_ang['steps'], 'vertical')
        starting_position(self.right_x, self.right_x['steps'], 'vertical')
        starting_position(self.right_ang, self.right_ang['steps'], 'vertical')
        starting_position(self.left_y, self.left_y['steps'] * 9 / 10, 'vertical')
        starting_position(self.right_y, self.right_y['steps'] / 6, 'vertical')
    
        print 'Flex motors'
        starting_position(self.m_micro, self.m_micro['steps'] / 2, 'flex')
        

#END
        
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
        for cam in self.server.beholder.devices:
            cam.encoder.focus.motor = self.m_focus
            cam.encoder.focus.save('default')
    
        self.micro_cam.encoder.y.motor = self.m_micro
        self.micro_cam.encoder.y.save('default')
    
        self.flex_cam.encoder.y.motor = self.m_micro
        self.flex_cam.encoder.y.save('default')
    
        self.left_cam.encoder.x.motor = self.left_x
        self.left_cam.encoder.x.align = -2
        self.left_cam.encoder.x.save('default')
    
        self.left_cam.encoder.y.motor = self.left_y
        self.left_cam.encoder.y.save('default')
    
        self.left_cam.encoder.angle.motor = self.left_ang
        self.left_cam.encoder.angle.save('default')
    
        self.right_cam.encoder.x.motor = self.right_x
        self.right_cam.encoder.x.align = 2
        self.right_cam.encoder.x.save('default')
    
        self.right_cam.encoder.y.motor = self.right_y
        self.right_cam.encoder.y.save('default')
    
        self.right_cam.encoder.angle.motor = self.right_ang
        self.right_cam.encoder.angle.save('default')
    
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
    
    def configure_kiln(self):
        print 'Configure kiln'
        m = self.server
        assert len(m.smaug.list()) == 3, 'Wrong number of thermal control devices'
    #	m.smaug['servedClasses']=['Eurotherm_ePack', 'DatExel']
        m.smaug['epack'] = '10.0.8.88:502'
        m.smaug['rescan']
        m.smaug.save('default')
        m.kiln.motor = self.m_flash
        m.kiln['motorStatus'] = 2
        
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
    
        m.kiln.save('default')
        
    def do(self, argv=False):
        """Full setup"""
        if not argv:
            argv='mcek'
        if 'm' in argv:
            self.configure_motors()
        if 'l' in argv:
            self.configure_limits()
        if 'b' in argv:
            self.configure_baudrates()
        if 'c' in argv:
            self.configure_cameras()
        if 'e' in argv:
            self.configure_encoders()
        if 'k' in argv:
            self.configure_kiln()
        
if __name__ == '__main__':
    from sys import argv
    from misura.client import from_argv
    print """
    m - motors
    l - limits
    b - baudrates
    c - cameras
    e - encoders
    k - kiln
    Default: mcek
    All: mlbcek
    """
    m = from_argv()
    fsw = FirstSetupWizard(m)
    fsw.do(argv[1])
