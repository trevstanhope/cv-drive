import serial # Electro-hydraulic controller
import time
SERIAL_DEVICE = '/dev/ttyACM0'
SERIAL_BAUD = 9600
INTERVAL = 1
PWM_MIN = 2
PWM_MAX = 255

try:
    arduino = serial.Serial(SERIAL_DEVICE, SERIAL_BAUD)
except Exception as error:
    print('ERROR: %s' % str(error))

pwm = raw_input('Enter PWM: ')
while True:
    try:
        arduino.write(pwm + '\n')
    except KeyboardInterrupt:
        try:
            pwm = raw_input('Enter PWM: ')
            print('Writing %s to Arduino...' % pwm)
        except KeyboardInterrupt:
            break
    except NameError:
        break
        
