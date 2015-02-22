from zaber_device import *
from copy import copy

class zaber_multidevice(zaber_device):
    '''zaber_multidevice(connection, 
                     id, 
                     devices, 
                     units_per_step = None,
                     move_units = 'microsteps',
                     run_mode = CONTINUOUS,
                     action_handler = None,
                     verbose = False)
    
    Class to handle collections of Zaber devices. The class talks to the devices
    over an instance of the serial_connection class passed as connection.

    Commands are sent to all devices in the devices dictionary unless the data
    only specifies a subset of the devices. Data for the command should be in a 
    dictionary with a key for each device that is to be called.

    id: A user defined string that is used as the identifier for this class instance.
        It is used to allow a more human readable reference to the device in question.

    devices: This is a dictionary linking user defined ids and their corresponding zaber id.
             e.g. {'device_1':1, 'device_2':2}

    units_per_step: This is the how many "units" correspond to one step of the stepper motor.

    move_units: A string identifier for the current unit. The default is microsteps. One 
        microstep is a quantity defined by the device and is found at initialisation.
    
    run_mode: Defines whether the device should run through every queue that gets placed
        on the command queue, or whether it should do one at a time and wait for step()
        to be called before running the next. The options are CONTINUOUS (the former mode)
        and STEP (the latter mode).

    action_handler: This is the function that is called when the device is ready for its
        next action.

    verbose: A boolean flag to define the verbosity of the output.
    '''

    def __init__(self, 
                 connection, 
                 devices,
                 id = None,
                 units_per_step = None,
                 move_units = 'microsteps',
                 run_mode = CONTINUOUS,
                 action_handler = None,
                 verbose = False):
        
        device_base.__init__(self, connection, id = id, run_mode = run_mode, verbose=verbose)        
        
        self.move_units = move_units
        
        self.action_handler = action_handler 

        self.devices = {}
        self.device_lookup = {}
        for each_device in devices:
            self.device_lookup[devices[each_device]] = each_device
            self.devices[each_device] = zaber_device(connection,
                                            devices[each_device],
                                            each_device,
                                            units_per_step = units_per_step,
                                            move_units = self.move_units,
                                            run_mode = run_mode,
                                            action_handler = self.handle_action,
                                            verbose = False)
        
        self.base_commands = base_commands
        self.move_commands = move_commands
        self.meta_commands = {}
        self.user_meta_commands = {}

        self.command_queue = []
        self.mode = CONTINUOUS
        
        # Set up the empty data case
        self.zero_data = {}
        for each_device in devices:
            self.zero_data[each_device] = 0
        
    def in_action(self):
        ''' zaber_multidevice.in_action()
        Return whether any of the individual devices making up this multidevice
        are doing anything.
        '''
        action_state = False
        for each_device in self.devices:
            action_state = action_state or self.devices[each_device].in_action()

        return action_state
    
    def enqueue_base_command(self, command, argument=None):
        '''device_base.base_command(command, argument)

        Called when a base command is to be dealt with.
        Just enqueues the command.
        '''
        if argument == None:
            argument = copy(self.zero_data)

        if not type(argument) == dict:
            temp = copy(self.zero_data)
            for each_device in temp:
                temp[each_device] = argument
        
        argument = temp

        if self.verbose:
            for n in range(0,self.meta_command_depth):
                print '\t',

            print 'enqueuing: %s, %s (%i): %s' % \
                    (self.id, command, self.base_commands[command], str(argument))

        self.enqueue(command, argument, self.base_commands)

    def move(self, move_command, argument=None):
        ''' zaber_multidevice.move(move_command, argument=None)

        This function enqueues a move command
        '''
        if argument == None:
            argument = copy(self.zero_data)

        if not type(argument) == dict:
            temp = copy(self.zero_data)
            for each_device in temp:
                temp[each_device] = argument

            argument = temp

        if move_command == 'stored_position':
            
            if self.verbose:
                for n in range(0,self.meta_command_depth):
                    print '\t',
                print 'enqueuing: %s, move %s (%i): addresses  %s' % \
                        (self.id, move_command, \
                        self.move_commands[move_command], str(argument))
            
            self.enqueue(move_command, argument, self.move_commands)
        else:
            if self.verbose:
                for n in range(0,self.meta_command_depth):
                    print '\t',
                print 'enqueuing: %s, move %s (%i): %s %s' % \
                        (self.id, move_command, self.move_commands[move_command],\
                        str(argument), self.move_units)
            
            microstep_movements = copy(argument)
            for each_device in argument:
                microstep_movements[each_device] = int(float(argument[each_device])\
                                                        * self.devices[each_device].microsteps_per_unit)

            self.enqueue(move_command, microstep_movements, self.move_commands)

        return None

    def get(self, setting, blocking = False):
        '''zaber_multidevice.get(setting, blocking = False)

        Currently doesn't do very much
        '''
        return None

    def set(self, setting, value):
        '''zaber_multidevice.set(setting)

        Currently doesn't do very much
        '''
        return None

    def do_now(self, command, data = None, pause_after = None, 
            blocking = False, release_command = None):
        '''zaber_multidevice.do_now(command, data = None, pause_after = None, 
                blocking = False, release_command = None)

        Send the each device in the device list the command given by command 
        with the supplied data.

        data should be a dictionary with an entry per device that needs to be called.
        It need not be every device that is part of this multidevice, in which 
        case only those devices that are included in the dictionary are called.

        If no data is given, then 0 is sent to each device

        The paused flag tells the function whether this command should raise
        the self.pause_after flag. This is only maintained until the next packet is
        sent, at which point it is preempted by the next packet. The
        self.pause_after flag tells the action_handler to pause after execution
        of this command. The next command is initiated with the step() method.
        CONTINUOUS mode is equivalent to pause_after always equal to false. By
        default, every command will cause a pause.

        If the blocking flag is set to True, then this function will block on 
        each device_call which will not return until release_command gets put on the queue
        or we run out of pending responses (probably implying an error occurred).

        If release_command is not passed or is None, then then command is used
        as the release command (ie an echo is expected)
        '''

        if data == None or data == 0:
            data = copy(self.zero_data)
        
        if self.verbose:
            print 'sending:   %s, command %i: %s' % \
                        (self.id, command, \
                        str(data))

        for each_device in data:
            try:
                self.devices[each_device].do_now(command, data[each_device], \
                        pause_after, blocking, release_command)
            except KeyError:
                # ignore invalid keys
                pass

def zaber_multidevice_example(io):
    devices = {'1':1, '2':2, '3':3}

    multidevice_system = zaber_multidevice(io, devices, 'multidevice_system', verbose = True)
    
    multidevice_system.home()
    multidevice_system.move_relative({'1':100000, '2':200000, '3':0})

    # The alternative, thread safe way of calling the move commands
    io.packet_q.put((('','multidevice_system'),('move_relative',{'1':75000, '3':20000})))

    io.open()

def step_example(io):
    devices = {'1':1, '2':2, '3':3}

    multidevice_system = zaber_multidevice(io, devices, 'multidevice_system', run_mode = STEP, verbose = True)
    
    multidevice_system.home()
    multidevice_system.move_relative({'1':100000, '2':200000, '3':0})
    
    while len(multidevice_system.command_queue) > 0:
        multidevice_system.step()

    io.close()

def examples(argv):
    '''A short example program that moves stuff around
    '''
    io = serial_connection('/dev/ttyUSB0', '<2Bi')
    zaber_multidevice_example(io)
    #step_example(io)

if __name__ == "__main__":
    import sys
    examples(sys.argv)
