import serial
import struct
import signal
from threading import Thread,Event
from Queue import Queue,Empty
from warnings import *

PARITY_NONE, PARITY_EVEN, PARITY_ODD = 'N', 'E', 'O'
STOPBITS_ONE, STOPBITS_TWO = (1, 2)
FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS = (5,6,7,8)

GENERAL, DEVICE, MALFORMED = (0x00,0x01,0x02)

class serial_connection():
    """serial_connection (default = None, data_block_format = '<2Bi', packet_q = None)

    Class to provide a high level concept of a serial port, suitable for
    interfacing with serial device. The class should
    be initialised with a valid serial port number or device string.

    This class interfaces with the async_serial class to acquire its data.
    The data is passed around in a Queue object, which is designed to
    provide a thread safe interface to the packets.

    This queue is generally writable as a way of thread safe communication
    with the device and its associated functions.
    
    On calling serial_connection.open(), this class will block until data is 
    available to be read on the Queue, at which point, the packets will be 
    inspected and dispatched to a suitable destination, which may be another 
    queue.
    
    Handlers should register with instances of this class by calling the
    serial_connection.register(handler) method. With an optional id argument. See
    the documentation for this function for its full interface.
    
    We have a concept of two kinds of packets. 
    
    The first packet type is for handling packets from the serial bus.
    
    This packet is a single tuple, with entries that are set by the unpacking 
    of the binary data from the serial link (using struct.struct). All 
    packets of this type get dispatched to the handler assigned to the device 
    given by the tuple's first element. Such a device handler can be registered 
    through serial_connection.register() or at a later stage through 
    connection.register_device().
    
    The binary data format should be given during initialisation. See the python
    documentation for struct to see what form this format string should take. The
    default format is 2 unsigned bytes followed by an signed integer, all in 
    little endian form.


    The second packet type is for general interthread communication. The packet 
    format is a pair of tuples (inside a tuple):
    * The first tuple is the of the form:
    (source, destination), where source and destination are valid handler IDs.
    * The second tuple contains the arbitrary payload.

    The optional packet_q argument is to force this class to use a pre-existing
    instance of Queue if that is desired.

    Overwrite test_for_general_packet(), test_for_device_packet(), 
    get_handler_id_from_general_packet() and get_device_id_from_device_packet()
    as needed in order that your packets are handled correctly.

    Arguments:
    serial_connection (default = None, data_block_format = '<2Bi', packet_q = None)
    """

    def __init__(self, port=None, data_block_format = '<2Bi', packet_q = None):
        
        # Initialise the notification queue if necessary        
        if packet_q == None:
            self.packet_q = Queue()
        else:
            self.packet_q = packet_q

        self.should_exit = False

        self.running = Event()

        # Initialise serial port
        self.io = async_serial(port, data_block_format, self.packet_q)
        
        # Find what the format of the data_block is
        data_block_size_bytes = self.io.struct.size
        sample_data_block = self.io.struct.unpack(" "*data_block_size_bytes)
        self.data_block_types = []

        for each_value in sample_data_block:
            self.data_block_types.append(type(each_value))

        self.data_block_types = tuple(self.data_block_types)

        # We allow open the serial port immediately so we don't lose
        # replies during hardware initialisation
        self.io.open()

        # Initialise handler dictionary.
        self.handler_list = {}

        # Initialise device dictionary. This stores the association between
        # device IDs and handler IDs.
        self.device_list = {}

        self.default_handler_id = 1

    def __del__(self):

        # Exit tidily, shutting down connections etc
        self.close()

    def send_command(self, device_id, command, data = 0):
        """ serial_connection.send_command(device_id, command, data = 0)
        Send a command to the specified device ID. No check is made on
        the validity of the device ID as the topology of network is not
        necessarily known.
        """
        self.io.write((device_id, command, data))
         
        return 0

    def register_device(self, handler_id, device_id):
        """ serial_connection.register_device(handler_id, device_id)
        Attempt to register the the device given by device_id
        with the handler given by handler_id. handler_id need not
        be registererd before calling this function.
        """
        # Check we have a unique handler for each device
        if self.device_list.has_key(device_id):
            warn('Device %s cannot be registered with handler %s because it\
                    has already been registered with handler %s.'\
                    %(str(device_id),str(handler_id),str(self.device_list[device_id])))
        else:
            self.device_list[device_id] = handler_id

    
    def register(self, handler, handler_id = None, device_id = None):
        """ serial_connection.register(handler, handler_id = None, device_id = None)
        Register a handler with this connection.
        The caller should pass a data handler and optionally a
        unique handler ID. If no handler ID is passed, a unique integer ID
        will be assigned.

        An optional argument, device_id, is used to register a handler with
        a Zaber device ID.
        
        The data handler can be a method or a queue (for multithreaded
        goodness).

        This function returns the assigned device ID.
        """

        # If no handler id was passed 
        if handler_id == None:
            # Find a unique id
            while self.handler_list.has_key(self.default_handler_id):
                self.default_handler_id = self.default_handler_id + 1

            handler_id = self.default_handler_id
            self.default_handler_id = self.default_handler_id + 1

        
        # This will overwrite a previously registered handler function
        self.handler_list[handler_id] = handler

        # If no device id was passed
        if not device_id == None:
            # Attempt to register it
            self.register_device(handler_id, device_id)

        return handler_id
    
    def inspect_packet(self, packet):
        """ serial_connection.inspect_packet(packet)
        Function that inspects the packet and returns a tuple containing
        the packet type, either GENERAL or DEVICE, and the destination id 
        (which is either the handler id or the device id for GENERAL and
        DEVICE packets respectively).

        If the packet is determined to be malformed, the packet type
        returned will be MALFORMED.
        
        This is the function that should be overwritten if the format of
        the packets change. This base class tests initially for a GENERAL
        packet initially, which is of the form:
        ((source, destination), (arbitrary payload))
        
        The destination is returned as the id in this case.

        On failing the test for a general packet, we test for a DEVICE
        packet, of the form described at initialisation. This is necessarily
        different to the GENERAL packet described above (as the first entry in
        the tuple cannot be itself a tuple - see the python documentation for 
        struct)
        
        In this case, we assume that the first entry in the packet is the
        device id, and hence becomes the destination.

        If the packet formats are different then the methods 
        test_for_device_packet() or test_for_general_packet() should be
        overridden.

        If the device ID in the DEVICE packets or the handler id in the GENERAL
        packets are given some other way than the first entry in the 
        device packet or the second entry in the first tuple of the general
        packet respectively, then .
        """
        if self.test_for_general_packet(packet):
            return (GENERAL,\
                    self.get_handler_id_from_general_packet(packet),\
                    self.get_source_handler_id_from_general_packet(packet))

        elif self.test_for_device_packet(packet):
            return (DEVICE, self.get_device_id_from_device_packet(packet))

        else:
            return (MALFORMED, )


    def test_for_general_packet(self, packet):
        """serial_connection.test_for_general_packet(packet)
        Check to see if the packet sent is of the form of a general packet.
        Return True of it is and False if not.
        """
        if  (type(packet) == tuple and
                len(packet) == 2 and 
                type(packet[0]) == tuple and
                len(packet[0]) == 2):

            return True
        else:
            return False
                
    
    def test_for_device_packet(self, packet):
        """ serial_connection.test_for_device_packet(packet)
        Check to see if the packet sent is of the form of a device packet.
        Return True of it is and False if not.
        """
        # Test to see if we have a tuple of the correct length
        if (type(packet) == tuple and
                len(packet) == len(self.data_block_types)):

            # If we do, check each entry is of the expected typ/
            n = 0
            for each_entry in packet:
                if not type(each_entry) == self.data_block_types[n]:
                    # if not, return False
                    return False
                n = n+1

            return True

        else:
            return False
    
    def get_handler_id_from_general_packet(self, packet):
        """ serial_connection.get_handler_id_from_general_packet(packet)
        Return the handler id from the general packet.
        It assumes the second entry of the first tuple is the handler id
        """
        return packet[0][1]

    def get_source_handler_id_from_general_packet(self, packet):
        """serial_connection.get_source_handler_id_from_general_packet(packet)
        Return the handler id of the source from the general packet.
        It assumes the first entry of the first tuple is the handler id
        """
        return packet[0][0]

    def get_device_id_from_device_packet(self, packet):
        """ serial_connection.get_device_id_from_device_packet(packet)
        Return the device id from the device packet.
        It assumes the first entry in the packet tuple is the device id.
        """
        return packet[0]
    
    def build_packet(self, data_block):
        """ serial_connection.build_packet(self, data_block)
        Build a packet beginning with data_block. The default state
        is the packet *is* the data block. This is to allow easy 
        inheritance for classes with more complicated packets.
        """
        return data_block

    def queue_handler(self, packets_to_handle=None):
        """ serial_connection.queue_handler()
        Function to handle the queue. This is the function that blocks
        until data is available on the queue. It inspects packets as they
        arrive, attempts to ignore malformed packets, and then sends the
        rest on accordingly.
        """
        if packets_to_handle == None:
            block = True
        else:
            block = False

        try:
            while block or packets_to_handle > 0 :
                
                try:
                    if self.should_exit:
                        break
                    
                    # Drop out of the queue check every half a second to check
                    # we shouldn't be exiting
                    data_block = self.packet_q.get(True, 0.5)

                    if not block:
                        packets_to_handle = packets_to_handle - 1
                
                except Empty:
                    if self.should_exit:
                        break
                    else:
                        continue

                packet = self.build_packet(data_block)

                packet_details = self.inspect_packet(data_block)
                if packet_details[0] == GENERAL:
                    # We seem to have a general packet
                    destination = packet_details[1]
                    source = packet_details[2]
                    self.dispatch_packets(destination, packet, source)

                elif packet_details[0] == DEVICE:
                    # We seem to have a device packet 
                    device_id = packet_details[1]
                    
                    # Call the device handler functions
                    if self.device_list.has_key(device_id):
                        destination = self.device_list[device_id]
                        self.dispatch_packets(destination, packet)

                    else:
                        warn('Data returned from unregistered device ' \
                                + str(device_id) + ': ' + str(packet))
                
                else:
                    # We seem to have a malformed packet
                    warn('Malformed packet received. Ignoring it...')

        except KeyboardInterrupt:
            self.close()
            # Pass on the interrupt to the calling function
            raise KeyboardInterrupt
            return None

        return None


            
    def dispatch_packets(self, destination, packet, source=None):
        """ serial_connection.dispatch_packets(destination, packet)
        Attempt to dispatch the packet to the destination (a handler ID)
        """
        if self.handler_list.has_key(destination):

            # See whether we have a queue of a function on which to act
            # This uses the big evil that is 'isinstance' to negate the 
            # need for a separate queue handler class. Perhaps there is 
            # a better way to do this...?
            if isinstance(self.handler_list[destination], Queue):
                # we have a handler queue
                self.handler_list[destination].put(packet)
            else:
                # We have something else
                self.handler_list[destination](packet)

        else:
            warn('No handler ID: %s is registered.' % (str(destination)))
            if not source == None:
                self.handler_list[source](('destination_not_registered', packet))


    
    def open(self):
        """ serial_connection.open()
        Method to open the connection
        """
        self.queue_handler()
        self.running.set()

    def close(self):
        """ serial_connection.close()
        Shutdown the connection IO connection
        """
        self.should_exit = True
        self.io.close()
        self.running.clear()
        print '\nGoodbye from the serial connection!'

class async_serial(Thread):
    def __init__(self,
                 port = None,           #Number of device, numbering starts at
                                        # zero.
                 data_block_format = 'b',
                 read_q = None,         #The queue on which to place the packets
                                        # as they are read in. No argument implies
                                        # that we need to initialise a new queue
                 packet_timeout=1,      #Timeout waiting for packets to arrive.
                                        # This is so we don't block permanently 
                                        # while nothing ever arrives.
                 baudrate=9600,         #baudrate
                 bytesize=EIGHTBITS,    #number of databits
                 parity=PARITY_NONE,    #enable parity checking
                 stopbits=STOPBITS_ONE, #number of stopbits
                 xonxoff=0,             #enable software flow control
                 rtscts=0,              #enable RTS/CTS flow control
                 writeTimeout=None,     #set a timeout for writes
                 dsrdtr=None            #None: use rtscts setting, dsrdtr override if true or false
                 ):

        '''Initialise the asynchronous serial object
        '''
        
        Thread.__init__(self)
        self.serial = serial.Serial( port,
                                baudrate,
                                bytesize,
                                parity,
                                stopbits,
                                packet_timeout,
                                xonxoff,
                                rtscts,
                                writeTimeout,
                                dsrdtr)
        
        self.running = Event()

        self.buffer = ''
        
        try:
            self.struct = struct.Struct(data_block_format)
        except:
            raise StandardError('Problem encountered loading struct with ' +data_block_format)
        
        self.packet_size = self.struct.size
        
        if read_q == None:
            self.read_q = Queue()
        else:
            self.read_q = read_q
        
    def open(self):
        '''Open the serial serial bus to be read. This starts the listening
        thread.
        '''
        self.serial.flushInput()
        self.running.set()
        self.start()
    
    def write(self, data):
        '''Write a packet to the serial bus.
        '''
        self.serial.write(apply(self.struct.pack, data))

    def close(self):
        '''Close the listening thread.
        '''
        self.running.clear()

    def run(self):
        '''Run is the function that runs in the new thread and is called by
        start(), inherited from the Thread class
        '''
        try:
            while(self.running.isSet()):
                new_data = self.serial.read(self.packet_size-len(self.buffer))
                self.buffer = self.buffer + new_data
                if (len(self.buffer) == self.packet_size):
                    # Put the unpacked data onto the read queue
                    self.read_q.put(self.struct.unpack(self.buffer))

                    # Clear the buffer
                    self.buffer = ''

        except KeyboardInterrupt:
            self.interrupt_main()
            self.close()
            return None

CONTINUOUS, STEP = (0,1)

# Command format:
# 'command_name': command
base_commands = {
        'reset':                    0,
        'home':                     1,
        'renumber':                 2 ,
        'store_current_position':   16,
        'return_stored_position':   17,
        'read_or_write_memory':     35,
        'restore_settings':         36,
        'return_setting':           53,
        'echo_data':                55,
        'return_current_position':  60,
        }

move_commands = {
        'stored_position':          18,
        'absolute':                 20,
        'relative':                 21,
        'constant_speed':           22,
        'stop':                     23,
        }

setting_commands = {
        'microstep_resolution':     37,
        'running_current':          38,
        'hold_current':             39,
        'device_mode':              40,
        'target_speed':             42,
        'acceleration':             43,
        'maximum_range':            44,
        'current_position':         45,
        'max_relative_move':        46,
        'home_offset':              47,
        'alias_number':             48,
        'lock_state':               49,
        }

extra_error_codes = {
        'busy':                      255,
        'save_position_invalid':    1600,
        'save_position_not_homed':  1601,
        'return_position_invalid':  1700,
        'move_position_invalid':    1800,
        'move_position_not_homed':  1801,
        'relative_position_limited':2146,
        'settings_locked':          3600,
        'disable_auto_home_invalid':4008,
        'bit_10_invalid':           4010,
        'home_switch_invalid':      4012,
        'bit_13_invalid':           4013,
        }

meta_commands = {}

class device_base():
    '''
    device_base(connection, id, run_mode = CONTINUOUS, verbose = False)
    Implements the device base class. It doesn't do very much by itself.
    connection: Should be an instance of the serial_connection class.
    id: A user-defined string for this device. If no id is passed then 
        a string representation of the hash of this instance is used
    run_mode: Defines whether the device should run through every queue that gets placed
        on the command queue, or whether it should do one at a time and wait for step()
        to be called before running the next. The options are CONTINUOUS (the former mode)
        and STEP (the latter mode).
    verbose: Boolean representing whether to be verbose or not.
    '''

    def __init__(self, connection, id = None, run_mode = CONTINUOUS, verbose = False):
        # These have to be initialised immediately to prevent a potential infinite
        # recursion when the attribute handler can't find them.
        self.base_commands = {}
        self.meta_commands = {}
        self.user_meta_commands = {}
        self.setting_commands = {}
        self.move_commands = {}
        if id == None:
            id = str(hash(self))
        self.id = id
        self.connection = connection
        self.run_mode = run_mode
        self.awaiting_action = False
        self.last_packet_received = None
        self.last_packet_sent = None
        self.meta_command_depth = 0
        self.meta_command_pause_after = False
        self.pause_after = True
        # Register with the connection
        self.connection.register(self.packet_handler, id)
        self.base_commands = {}
        self.meta_commands = {}
        self.user_meta_commands = {}
        self.setting_commands = {}
        self.move_commands = {}
        self.action_state = False
        self.pending_responses = 0
        self.verbose = verbose
        # Create data structures to store the response lookups
        self.settings_lookup = {}
        self.command_lookup = {}
        self.move_lookup = {}
        self.extra_error_codes_lookup = {}

    def __getattr__(self, attr):
        if self.base_commands.has_key(attr):
            def base_function(data = 0):
                return self.enqueue_base_command(attr, data)
            return base_function
        elif attr[0:5] == 'move_' and self.move_commands.has_key(attr[5:]):
            def move_function(data = 0):
                return self.move(attr[5:], data)
            return move_function 
        elif attr[0:4] == 'set_' and self.setting_commands.has_key(attr[4:]):
            def set_function(data = 0):
                return self.set(attr[4:], data)
            return set_function
        elif attr[0:4] == 'get_' and self.setting_commands.has_key(attr[4:]):
            def get_function(blocking = False):
                return self.get(attr[4:], blocking = blocking)
            return get_function
        elif self.meta_commands.has_key(attr):
            def do_function(data = 0):
                return self.meta(attr, self.meta_commands[attr])
            return do_function
        elif self.user_meta_commands.has_key(attr):
            def do_function(data = 0):
                return self.meta(attr, self.user_meta_commands[attr])
            return do_function
        else:
            raise AttributeError
        return None
    
    def get_id(self):
        '''
        devive_base.get_id()
        Return the ID that this device has been assigned
        '''
        return self.id

    def step(self):
        '''
        device_base.step()
        This function executes the next command in the command queue.
        It blocks if the previous command has not finished and returns
        when it has and the next command has been sent.
        This function operates by pulling packets off the queue until
        we are in a position to execute the next command.
        '''
        self.awaiting_action = False
        if len(self.command_queue) == 0:
            # Nothing to do here cos there's nothing on the queue.
            if self.verbose:
                print 'Command queue empty for receive step command'
        elif self.in_action() and self.run_mode == STEP \
                and not self.connection.running.isSet():
            # Device is in the action state and the queue handler isn't running,
            # so we need to manually pull a packet off the queue 
            # (which will block until something is there)
            self.connection.queue_handler(1)
        elif self.in_action() and self.run_mode == STEP:
            # We need to do something when we're no longer in action
            # so notify the packet handler of this
            self.awaiting_action = True
        elif not self.in_action():
            # We should send the command now
            apply(self.do_now, self.command_queue.pop(0))
        elif self.run_mode == CONTINUOUS:
            # This is the state when we are in_action() but 
            # the queue handler should make things
            # work nicely when the time comes.
            pass
        return None

    def enqueue(self, command, data = 0, command_dictionary = None, pause_after = True):
        '''device_base.enqueue(command, data = 0, command_dictionary = None)
        enqueue a command for subsequent execution. If the queue is empty, the
        command is immediately executed.
        command should be a reference to an entry in command_dictionary. The default
        command dictionary is base_commands and is used if command_dictionary == None.
        data is the data that should be passed at execution.
        '''
        if command_dictionary == None:
            command_dictionary = self.base_commands
        if self.meta_command_depth > 0 and not self.meta_command_pause_after:
            pause_after = False
        else:
            if self.verbose:
                for n in range(0,self.meta_command_depth):
                    print '\t',
                print 'pause'
        if not self.in_action() and len(self.command_queue) == 0 and not self.responses_pending()\
            and not self.run_mode == STEP:
            # Execute immediately
            apply(self.do_now, (command_dictionary[command], data, pause_after))
        else:
            self.command_queue.append((command_dictionary[command], data, pause_after))
        return None
    
    def enqueue_base_command(self, command, argument):
        '''
        device_base.base_command(command, argument)
        Called when a base command is to be dealt with.
        Just enqueues the command.
        '''
        if self.verbose:
            for n in range(0,self.meta_command_depth):
                print '\t',
            print 'enqueuing: %s, %s (%i): %i' % \
                    (self.id, command, self.base_commands[command], argument)
        self.enqueue(command, argument, self.base_commands)

    def on_base_command_error(self, error):
        '''
        device_base.on_base_command_error(error)
        This is the base command error handling function.
        This function will just print out that an error was received and
        then blithely move on.
        '''
        if error > 1000:
            print 'error   : %s' % self.extra_error_codes_lookup[error]
        elif self.base_commands.has_key(error):
            print 'error   : invalid %s' % self.base_commands[error]
        else:
            print 'error   : unknown device error, zaber code: %s' % str(error)
        return None
    
    def get(self, setting, blocking = False):
        '''
        device_base.get(setting, blocking = False)
        Exit quietly. This attribute should be overwritten in child classes.
        Any calls to self.get_SOMETHING end up here with the setting string
        SOMETHING.
        '''
        return None

    def set(self, setting, value):
        '''
        device_base.set(setting, value)
        Exit quietly. This attribute should be overwritten in child classes.
        Any calls to self.set_SOMETHING end up here with the setting string
        SOMETHING.
        '''
        return None

    def on_settings_error(self, error):
        '''
        device_base.on_settings_error(error)
        This is the settings error handling function.
        This function will just print out that an error was received and
        then blithely move on.
        '''
        if error > 1000:
            print 'error   : %s' % self.extra_error_codes_lookup[error]
        else:
            print 'error   : invalid %s' % self.setting_commands[error]
        return None

    def move(self, move_command, argument):
        '''
        device_base.move(move_command, argument)
        Exit quietly. This attribute should be overwritten in child classes.
        Any calls to self.move_SOMETHING end up here with the move_command string
        SOMETHING.
        '''
        return None
    
    def on_move_error(self, error):
        '''
        device_base.on_move_error(error)
        This is the move error handling function.
        This function will just print out that an error was received and
        then blithely move on.
        '''
        if error > 1000:
            print 'error   : %s' % self.extra_error_codes_lookup[error]
        else:
            print 'error   : invalid %s' % self.move_commands[error]
        return None

    def on_busy_error(self):
        '''
        device_base.on_busy_error()
        This function resends the last command until it goes through.
        '''
        print 'error   : Busy error received, resending the last command'
        self.do_now(self.last_packet_sent[1], self.last_packet_sent[2])

    def meta(self, name, meta_command):
        '''
        device_base.meta(meta_command)
        Execute the supplied meta command. At this stage it is
        expanded out and the relevant functions are called to handle it.
        meta commands that are part of the meta_command recursively
        call this function.
        '''
        if self.verbose:
            for n in range(0,self.meta_command_depth):
                print '\t',
            print 'metacommand: %s' % (name)
        self.meta_command_depth = self.meta_command_depth + 1
        last_command = None
        for idx in range(0,len(meta_command)):
            each_command = meta_command[idx]
            if idx+1 < len(meta_command) and meta_command[idx+1][0] == 'pause':
                next_command_pause = True
            else:
                next_command_pause = False
            if each_command[0] == 'pause':
                # We considered pause on the last loop
                continue
            elif self.base_commands.has_key(each_command[0]) or \
                   self.move_commands.has_key(each_command[0][5:]) or \
                   self.meta_commands.has_key(each_command[0]) or \
                   self.user_meta_commands.has_key(each_command[0]):
                if next_command_pause:
                    self.meta_command_pause_after = True
                else:
                    self.meta_command_pause_after = False
                apply(getattr(self,each_command[0]), each_command[1:])
                last_command = each_command
            elif each_command[0] == 'repeat':
                # Special case of repeat
                if not last_command == None:
                    n = 0
                    if len(each_command) == 1:
                        # ie, no argument sent
                        iterations = 1
                    else:
                        iterations = each_command[1] - 1
                    while n < iterations:
                        if n == iterations - 1 and next_command_pause == True:
                            self.meta_command_pause_after = True
                        apply(getattr(self,last_command[0]), last_command[1:])
                        n = n+1
        self.meta_command_pause_after = False
        self.meta_command_depth = self.meta_command_depth - 1
        return None
                
    def new_meta_command(self, name, command_list):
        '''
        device_base.new_meta_command(name, command_list)
        Define a new meta command (a command sequence) that can then
        be called like an existing command.
        This function allows the special command 'repeat', with an argument
        as the number of times to repeat.
        A meta command can consist of move commands, base commands and
        other meta commands, as well as repeats.
        command_list should be a tuple of commands, with each command itself
        a tuple, of the form (command, argument)
        '''
        # Check that all the commands are valid.
        for each_command in command_list:
            if not self.base_commands.has_key(each_command[0]) and \
               not self.move_commands.has_key(each_command[0][5:]) and \
               not self.meta_commands.has_key(each_command[0]) and \
               not self.user_meta_commands.has_key(each_command[0]) and \
               not each_command[0] == 'repeat' and \
               not each_command[0] == 'pause':
                raise LookupError, 'Command in the supplied command list that is not valid'
                return None
        self.user_meta_commands[name] = command_list
        return None

    def do_now(self, command, data = None, pause_after = True, blocking = False, release_command = None):
        '''
        device_base.do_now(command, data = None, pause_after = True, blocking = False, release_command = None)
        Place holder function that should be overwritten in child classes.
        This function is called when a packet is wanted to be sent immediately 
        to the device.
        '''

        return None

    def get_all_settings(self, blocking = False):
        '''
        device_base.get_all_settings(blocking = False)
        Iterate over all the settings in self.setting_commands and call 
        self.get(setting, blocking) for each setting.
        '''
        for each_setting in self.setting_commands:
            self.get(each_setting, blocking=blocking)
        return None

    def in_action(self):
        '''
        device_base.in_action()
        Return the action state of the current device. This is fairly loosely
        defined and is dependant on the class implementation. It is basically
        used as a test as to whether the next command in the queue should be sent.
        '''
        return self.action_state

    def responses_pending(self):
        '''
        device_base.responses_pending()
        Return whether we are still awaiting a packet from the device.
        '''
        return self.pending_responses > 0

    def handle_device_packet(self, source, command, data):
        '''
        device_base.handle_device_packets(source, command, data)
        Place holder function that should be overwritten in child classes.
        This function should handle a packet that originated at the device
        with the id given by source. command is normally an echo of the 
        sent command with data being whatever the response is.
        '''
        return None

    def handle_general_packet(self, source, data):
        '''
        device_base.handle_general_packet(source, data)
        Any general packets put on the device queue destined for the device
        id assigned to this device end up here.
        All packets are assumed to be command packets and are interpreted as 
        such. The data packet is assumed to be of the following form:
        ('method', argument1, argument2, ...)
        All methods defined in the instance of the class are available to be
        called in this way. Any value returned from the method is placed on the
        queue with "source" as the destination (ie, replies are sent back).
        '''
        try: 
            reply = apply(getattr(self,data[0]), data[1:])
            if not reply == None:
                self.connection.packet_q.put(((self.id, source),(reply)))
        except:
            if self.verbose:
                print 'Packet received from %s for which nothing can be done: %s' % \
                        (source, str(data))

    def packet_handler(self, packet):
        '''
        device_base.packet_handler(packet)
        Interpret packets that have been placed on the queue and destined for this
        class instance.
        It attempts to interpret whether we have a device packet (a packet originating
        at the device) or a general packet (anything other data placed on the queue).
        It then dispatches the packet to the either self.handle_device_packet() or
        self.handle_general_packet()
        '''
        if len(packet) == 2:
            # We have a usual packet
            try:
                source = packet[0][0]
                destination = packet[0][1]
                data = packet[1]
                if not destination == self.id:
                    raise StandardError
            except:
                warn('Malformed packet received. Ignoring it...')
                return -1
            self.handle_general_packet(source, data)
        else:
            try:
                source = packet[0]
                command = packet[1]
                data = packet[2]
            except:
                warn('Malformed device packet received. Ignoring it...')
                return -1
            self.handle_device_packet(source, command, data) 

class zaber_device(device_base):
    ''' zaber_device(connection, 
                     device_number, 
                     id,
                     units_per_step = None,
                     move_units = 'microsteps',
                     run_mode = CONTINUOUS,
                     action_handler = None,
                     verbose = False)
    Class to handle the general Zaber devices. The class talks to the device
    over an instance of the serial_connection class passed as connection.
    id: A user defined string that is used as the identifier for this class instance.
        It is used to allow a more human readable reference to the device in question.
    device_number: This is the number that identifies the Zaber device on the serial chain.
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
                 device_number, 
                 id = None,
                 units_per_step = None,
                 move_units = 'microsteps',
                 run_mode = CONTINUOUS,
                 action_handler = None,
                 verbose = False):
        # These have to be initialised immediately to prevent a potential infinite
        # recursion when the attribute handler can't find them.
        self.base_commands = base_commands
        self.move_commands = move_commands
        self.meta_commands = {}
        self.user_meta_commands = {}
        self.setting_commands = setting_commands       
        self.action_handler = action_handler 
        # Define move units if not already done
        try: self.move_units
        except AttributeError:
            self.move_units = move_units
        if units_per_step == None:
            # If units_per_step has not been defined, then we
            # have to work with microsteps and ignore any predefined units
            self.move_units = 'microsteps'
        self.units_per_step = units_per_step
        self.initialised = False
        self.device_number = device_number
        device_base.__init__(self, connection, id, run_mode = run_mode, verbose = verbose)
        self.connection.register_device(self.id, self.device_number)
        self.base_commands = base_commands
        self.move_commands = move_commands
        self.extra_error_codes = extra_error_codes
        self.meta_commands = {}
        self.user_meta_commands = {}
        self.setting_commands = setting_commands
        self.command_queue = []
        self.last_command = None
        self.error_list = []
        self.blocking_retries = 3
        # Fill the data structures to store the response lookups
        for each_setting in self.setting_commands:
            self.settings_lookup[self.setting_commands[each_setting]] = each_setting
        for each_command in self.base_commands:
            self.command_lookup[self.base_commands[each_command]] = each_command
        for each_movement in self.move_commands:
            self.move_lookup[self.move_commands[each_movement]] = each_movement
        for each_error_code in self.extra_error_codes:
            self.extra_error_codes_lookup[self.extra_error_codes[each_error_code]] = \
                    each_error_code
        # Define a safe initialisation value of the usteps/unit
        self.microsteps_per_unit = 0
        # Initialisation has occurred when we have all the settings returned
        # from the device
        self.settings = {}
        self.get_all_settings(blocking = True)

    def get(self, setting, blocking = False):
        '''
        zaber_device.get(setting, blocking = False)
        Query the zaber device for the setting given by the setting string.
        See the setting_commands dictionary or consult the zaber documentation
        for valid settings.
        As with all device commands, this is returned asynchronously and so the return
        case should be handled properly by the device packet handler.
        It is possible to call this function with the blocking argument set to
        true. In this case, responses will be popped off the queue one by one
        (and dealt with appropriately) until the setting response arrives back,
        at which point normal execution will resume. In this case, the function will
        return the setting.
        Any calls to self.get_SOMETHING end up here with the setting string
        SOMETHING.
        '''
        if blocking:
            # Firstly we need to know how many errors are already on the
            # error list
            preexisting_errors = self.error_list.count(setting)
        attempt = 1
        while (not blocking and attempt == 1) or \
                (blocking and attempt < self.blocking_retries):
            # If we are blocking, keep trying until we don't
            # receive an error up to self.blocking_retries times
            self.do_now(self.base_commands['return_setting'],\
                    self.setting_commands[setting], blocking = blocking,\
                    release_command = setting)
            # See if we have received a satisfactory response and leave when we do            
            if self.error_list.count(setting) == preexisting_errors:
                return self.settings[setting]
            else:
                self.error_list.remove(command)
                attempt = attempt + 1
        return None

    def set(self, setting, value):
        '''
        zaber_device.set(setting, value)
        Set the device setting given by the setting string with 'value'.
        See the setting_commands dictionary or consult the zaber documentation
        for valid settings.
        Any calls to self.set_SOMETHING end up here with the setting string
        SOMETHING.
        '''
        self.do_now(self.setting_commands[setting], value)
        return None

    def move(self, move_command, argument):
        '''
        zaber_device.move(move_command, argument)
        Move the device using the command move_command with the supplied argument.
        Valid move commands are given in self.move_commands.
        Any calls to self.move_SOMETHING() end up here with the move_command string
        SOMETHING.
        '''
        if move_command == 'stored_position':
            if self.verbose:
                for n in range(0,self.meta_command_depth):
                    print '\t',
                print 'enqueuing: %s, move %s (%i): address %i' % \
                        (self.id, move_command, \
                        self.move_commands[move_command], data)
            self.enqueue(move_command, argument, self.move_commands)
        else:
            if self.verbose:
                for n in range(0,self.meta_command_depth):
                    print '\t',
                print 'enqueuing: %s, move %s (%i): %i %s' % \
                        (self.id, move_command, self.move_commands[move_command],\
                        argument, self.move_units)
            microstep_movement = int(float(argument) * self.microsteps_per_unit)
            self.enqueue(move_command, microstep_movement, self.move_commands)
        return None
    
    def do_now(self, command, data = None, pause_after = True, blocking = False, release_command = None):
        '''
        zaber_device.do_now(command, data = None, pause_after = True, blocking = False, release_command = None)
        Send the device the command given by command with the supplied data.
        If no data is given, then 0 is sent.
        The paused flag tells the function whether this command should raise
        the self.pause_after flag. This is only maintained until the next packet is
        sent, at which point it is preempted by the next packet. The
        self.pause_after flag tells the action_handler to pause after execution
        of this command. The next command is initiated with the step() method.
        CONTINUOUS mode is equivalent to pause_after always equal to false. By
        default, every command will cause a pause.
        If the blocking flag is set to True, then this function will not
        return until release_command gets put on the queue
        or we run out of pending responses (probably implying an error occurred).
        If release_command is not passed or is None, then then command is used
        as the release command (ie an echo is expected)
        '''
        if data == None:
            data = 0
        if release_command == None:
            release_command = command
        self.pause_after = pause_after
        command_tuple = (self.device_number, command, data)
        apply(self.connection.send_command, command_tuple)
        if self.in_action() and self.move_lookup.has_key(command):
            # This means the current command will preempt a previously sent command,
            # so we shouldn't do anything.
            if self.verbose:
                print "send:      %s, move %s (%i): %i" \
                            %(self.id, self.move_lookup[command], command, data)
        elif self.command_lookup.has_key(command):
            # if its not a base command, we trigger the action state
            self.action_state = True
            self.pending_responses = self.pending_responses + 1
            self.last_action_sent = self.command_lookup.has_key(command)
            if self.verbose:
                print "send:      %s, command %s (%i): %i" \
                        %(self.id, self.command_lookup[command], command, data)
        elif self.move_lookup.has_key(command):
            # if its not a move command, we trigger the action state
            self.action_state = True
            self.pending_responses = self.pending_responses + 1
            self.last_action_sent = self.move_lookup.has_key(command)
            if self.verbose:
                print "send:      %s, move %s (%i): %i" \
                        %(self.id, self.move_lookup[command], command, data)
        elif  self.settings_lookup.has_key(command):
            # Its a settings command
            self.pending_responses = self.pending_responses + 1
        else:
            # Don't know what to do with this...
            pass
        # If the blocking request was made, we take control of the
        # queue handler until our packet arrives. All other packets
        # arrive as usual and are handled in the same way. That is, 
        # the queue handler will do its usual thing, dispatching
        # packets, only it will be one at a time, initiated by this
        # loop. We drop out of the loop when a response is received for
        # the command we sent or no more responses are expected.
        if blocking:
            last_packet_sent_temp = self.last_packet_sent
            self.last_packet_sent = command_tuple
            while self.last_packet_received == None or \
                    not self.last_packet_received[1] == release_command:
                if self.responses_pending():
                    self.connection.queue_handler(1)
                else:
                    self.error_list.append(command)
                    break
            self.last_packet_sent = last_packet_sent_temp
        else:
            self.last_packet_sent = command_tuple
        return None

    def handle_device_packet(self, source, command, data):
        '''
        zaber_device.handle_device_packet(source, command, data)
        Handle a device packet that is received.
        Currently the function can only handle packets that are in the
        dictionaries: self.command_lookup, self.move_lookup and 
        self.settings_lookup.
        Command or move packets will trigger an action response, which is to call
        the action_handler function.
        TODO:   implement handling of the rest of the command set
        '''
        if command == 255:
            # We have received an error            
            if data == 255:
                # This means the device was busy during the last request
                self.pending_responses = self.pending_responses - 1
                if not self.responses_pending():
                    self.action_state = False
                self.on_busy_error()
            elif  self.command_lookup.has_key(data) \
                    or self.command_lookup.has_key(int(data/100)):
                self.pending_responses = self.pending_responses - 1
                self.on_base_command_error(data)
            elif self.move_lookup.has_key(data) \
                    or self.move_lookup.has_key(int(data/100)):
                self.pending_responses = self.pending_responses - 1
                self.on_move_error(data)
            elif self.settings_lookup.has_key(data) \
                    or self.settings_lookup.has_key(int(data/100)):
                self.pending_responses = self.pending_responses - 1
                self.on_settings_error(data)
        elif self.command_lookup.has_key(command):
            self.pending_responses = self.pending_responses - 1
            if self.verbose:
                print 'received:  %s, command %s (%i): %i' \
                        %(self.id, self.command_lookup[command], command, data)
        elif self.move_lookup.has_key(command):
            self.pending_responses = self.pending_responses - 1
            if self.verbose:
                print 'received:  %s, moved %s (%i): %i' \
                        %(self.id, self.move_lookup[command], command, data)
        elif self.settings_lookup.has_key(command):
            self.pending_responses = self.pending_responses - 1
            if self.verbose:
                print 'received:  %s, %s set (%i): %i' \
                        %(self.id, self.settings_lookup[command], command, data)
            self.settings[self.settings_lookup[command]] = data
            if self.settings_lookup[command] == 'microstep_resolution':
                if not self.move_units == 'microsteps':
                    self.microsteps_per_unit = float(data)/self.units_per_step
                else:
                    self.microsteps_per_unit = 1
            if len(self.settings) == len(self.settings_lookup):
                self.initialised = True
        else:
            # Ignore packets that we don't know how to handle
            # But still print out that we received them...
            if self.verbose:
                print 'received:  %s, %i: %i' \
                        %(self.id, command, data)
            return None
        if not self.responses_pending():
            self.action_state = False
        if (self.command_lookup.has_key(command) or self.move_lookup.has_key(command)):
            # If we have an action (rather than a setting) then pass over to the
            # action handler
            self.handle_action(source, command, data, self.pause_after)
        self.last_packet_received = (source, command, data)

    def handle_action(self, source, command, data, pause_after):
        if self.run_mode == STEP and \
                pause_after and \
                not self.awaiting_action:
            pass
        else:    
            if self.action_handler == None:
                self.step()
            else:
                self.action_handler(source, command, data, pause_after)
        return None

if __name__ == '__main__':
    pass 
