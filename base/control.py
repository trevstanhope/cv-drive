"""
control.py
"""

import zaber
import serial # Electro-hydraulic controller
import ast
import numpy as np

class PID:
    
    def __init__(self):
        pass

    def calc_pid(self, vals):
        p = vals[-1]
        i = np.mean(vals)
        d = vals[-1] - vals[-2]
        return (p, i, d)

class Arduino:
    
    def __init__(self):
        try:
            self.arduino = serial.Serial(self.SERIAL_DEVICE, self.SERIAL_BAUD)
        except Exception as error:
            print('ERROR in __init__(): %s' % str(error))
            
    def write_output(self, estimate, average):
        try:
            self.arduino.write(str(pwm) + '\n')
        except Exception as err:
            print('ERROR in control_hydraulics(): %s' % str(error))
                
class Zaber:
    
    def __init__(self):
        try:
            io = zaber.serial_connection('/dev/ttyUSB0', '<2Bi')
            self.zaber = zaber.zaber_device(io, 1, 'zaber', run_mode = 1, verbose = True)
        except Exception as err:
            print str(err)
            
    def write_output(self):
        try:
            if len(self.zaber.command_queue) > 0:
                self.zaber.step()
            else:
                self.zaber.move_absolute(self.ZABER_CENTER + self.MICROSTEP_COEF * adjusted)
        except Exception as err:
            print('ERROR in control_hydraulics(): %s' % str(error))
