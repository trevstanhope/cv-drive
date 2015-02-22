# Short function that sets the software endstops for the device.
# Standalone, it is designed to be used by positioning the device manually
# or otherwise into its limit and then running this program.
# 

from zaber_device import zaber_device
from serial_connection import serial_connection
import time

def set_endstops(argv):
    '''A short example program that moves stuff around
    '''
    io = serial_connection('/dev/ttyUSB0', '<2Bi')
    
    device_ids = range(1,4)
    devices = []
    for device_id in device_ids:
        devices.append(zaber_device(io, device_id))

    for device in devices:
        device.restore_settings()

    io.close()



if __name__ == "__main__":
    import sys
    set_endstops(sys.argv)
