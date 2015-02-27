"""
control.py
"""

#from zaber import zaber
import serial # Electro-hydraulic controller
import ast

class PID:
	
	def __init__(self):
        if self.VERBOSE: print('[Initializing Arduino] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        try:
            if self.VERBOSE: print('\tDevice: %s' % str(self.SERIAL_DEVICE))
            if self.VERBOSE: print('\tBaud Rate: %s' % str(self.SERIAL_BAUD))
            self.arduino = serial.Serial(self.SERIAL_DEVICE, self.SERIAL_BAUD)
        except Exception as error:
            print('\tERROR in __init__(): %s' % str(error))

    ## Estimate Average Position
    """
    1. Takes the current assumed offset and number of averages
    2. Calculate weights of previous offsets
    3. Estimate the weighted position of the crop row (in pixels)
    """
    def average_row(self, offset):
        if self.VERBOSE: print('[Estimating Row Position] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        self.offset_history.append(offset)
        while len(self.offset_history) > self.NUM_AVERAGES:
            self.offset_history.pop(0)
        average = int(numpy.mean(self.offset_history)) #!TODO
        print('\tMoving Average: %s' % str(average)) 
        return average

    ## Control Hydraulics
    """
    1. Get PWM response corresponding to average offset
    2. Send PWM response over serial to controller
    """
    def control_hydraulics(self, estimate, average):
        if self.VERBOSE: print('[Controlling Hydraulics] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        adjusted = self.P_COEF * estimate + self.I_COEF * average
        pwm = self.PWM_MAX - int(self.PWM_PER_PIXEL * (adjusted + self.PIXEL_RANGE))
        if pwm < self.PWM_MIN:
            pwm = self.PWM_MIN
        elif pwm > self.PWM_MAX:
            pwm = self.PWM_MAX
        if self.ARDUINO_ENABLED:
            try:
                self.arduino.write(str(pwm) + '\n')
            except Exception as error:
                print('\tERROR in control_hydraulics(): %s' % str(error))
        if self.ZABER_ENABLED:
            try:
                if len(self.zaber.command_queue) > 0:
                    self.zaber.step()
                else:
                    self.zaber.move_absolute(self.ZABER_CENTER + self.MICROSTEP_COEF * adjusted)
            except Exception as error:
                print('\tERROR in control_hydraulics(): %s' % str(error))
        print('\tAdjusted Offset: %d' % adjusted)
        print('\tPWM Output: %s' % str(pwm))
        return pwm

class Zaber:
	def __init__(self):
        if self.VERBOSE: print('[Initializing Zaber] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        if self.ZABER_ENABLED:
            io = zaber.serial_connection('/dev/ttyUSB0', '<2Bi')
            self.zaber = zaber.zaber_device(io, 1, 'zaber', run_mode = 1, verbose = True)
