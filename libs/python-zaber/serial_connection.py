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

class basic_test:
    def __init__(self):
        self.async_serial = async_serial('/dev/ttyUSB0', '<2Bi')
        self.async_serial.open()

def main(argv):
    ''' Run some basic stuff to test it working
    '''
    meh = basic_test()
    meh.async_serial.write((1, 1, 0))
    meh.async_serial.write((2, 1, 0))
    meh.async_serial.write((3, 1, 0))
    meh.async_serial.close()

if __name__ == "__main__":
    import sys
    main(sys.argv)
