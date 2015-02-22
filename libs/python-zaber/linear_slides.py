from zaber_device import *
from zaber_multidevice import *

# Units are all with respect to 1 mm 
linear_units = {
        'mm':                       1,
        'um':                       1e-3,
        'inches':                   25.4,
        'thou':                     25.4e-3,
        'mil':                      25.4e-3,
        }

class linear_slide(zaber_device):
    ''' linear_slide(connection, 
                 device_number,
                 id, 
                 steps_per_rev = 200, 
                 mm_per_rev = 6.35, 
                 units = 'mm',
                 run_mode = CONTINUOUS,
                 action_handler = None,
                 verbose = False):
    
    Modified zaber_device with support for more meaningful linear units.

    steps_per_rev is the number of steps per revolution of the stepper.
    mm_per_rev is the number of linear mm that corresponds to each revolution of the stepper.


    See the documentation for zaber_device for the full usage.
    '''
    def __init__(self, 
                 connection, 
                 device_number, 
                 id = None,
                 steps_per_rev = 200, 
                 mm_per_rev = 6.35, 
                 units = 'mm',
                 run_mode = CONTINUOUS,
                 action_handler = None,
                 verbose = False):

        mm_per_step = float(mm_per_rev)/float(steps_per_rev)
        self.move_units = units
        
        zaber_device.__init__(self, connection, device_number, id = id,
                units_per_step = mm_per_step*linear_units[self.move_units],
                run_mode = run_mode,
                action_handler = action_handler,
                verbose = verbose)
        

class multiaxis_linear_slides(zaber_multidevice):
    '''multiaxis_linear_slides(connection, 
                               id, 
                               devices, 
                               steps_per_rev = 200, 
                               mm_per_rev = 6.35, 
                               units = 'mm',
                               run_mode = CONTINUOUS,
                               action_handler = None,
                               verbose = False)

    Modified zaber_multidevice with support for more meaningful linear units.
    
    steps_per_rev is the number of steps per revolution of the stepper.
    mm_per_rev is the number of linear mm that corresponds to each revolution of the stepper.

    See the documentation for zaber_multidevice for the full usage.
    '''

    def __init__(self, 
                 connection,  
                 devices, 
                 id = None,
                 steps_per_rev = 200, 
                 mm_per_rev = 6.35, 
                 units = 'mm',
                 run_mode = CONTINUOUS,
                 action_handler = None,
                 verbose = False):

        mm_per_step = float(mm_per_rev)/float(steps_per_rev)
        
        zaber_multidevice.__init__(self,
                                   connection, 
                                   devices,
                                   id = id,
                                   units_per_step = mm_per_step,
                                   move_units = units,
                                   run_mode = run_mode,
                                   action_handler = action_handler, 
                                   verbose=verbose)        
        

def linear_slide_example(io):
    
    x_axis = linear_slide(io, 1, id = 'x_axis', verbose = True)
    y_axis = linear_slide(io, 2, id = 'y_axis')
    z_axis = linear_slide(io, 3, id = 'z_axis', verbose = True)
    
    x_axis.home()
    y_axis.home()
    z_axis.home()
    
    x_axis.move_relative(10)
    y_axis.move_absolute(100)
    y_axis.home()
    y_axis.move_absolute(0)
    x_axis.move_absolute(20)
    z_axis.move_relative(10)
    z_axis.move_absolute(50)
    z_axis.move_relative(-10)
    
    # Will block
    io.open()

def multiaxis_example(io):
    
    axes = {'x':1, 'y':2, 'z':3}
    
    gantry_system = multiaxis_linear_slides(io, axes, 'gantry', verbose = True)
    gantry_system.home()
    gantry_system.move_relative({'x':100, 'y':200, 'z':0})
    gantry_system.move_absolute({'x':50, 'y':150, 'z':0})
    
    gantry_system.new_meta_command('zigzag', (('move_relative',{'x':10, 'y':10}),\
                                              ('move_relative',{'x':20, 'y':-20}),\
                                              ('move_relative',{'x':10, 'y':10})))

    gantry_system.new_meta_command('two_zigzags', (('zigzag',),('repeat',2)))
    
    gantry_system.two_zigzags()

    gantry_system.home()

    # The alternative, thread safe way of calling the move commands
    io.packet_q.put((('','gantry'),('move_relative',{'x':75, 'z':20})))
    io.packet_q.put((('','gantry'),('move_relative',{'x':75, 'y':200, 'z':20})))
    
    try:
        io.open()
    except:
        io.close()

def examples(argv):
    '''A short example program that moves stuff around
    '''
    io = serial_connection('/dev/ttyUSB0', '<2Bi')
    #linear_slide_example(io)
    multiaxis_example(io)

if __name__ == "__main__":
    import sys
    examples(sys.argv)
