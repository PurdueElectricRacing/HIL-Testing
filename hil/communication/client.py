import socket
from queue import Queue
import queue
from queue import Empty as QueueEmpty
from threading import Thread
import can
from time import sleep
import hil.utils as utils
import datetime

# modification of:
# https://github.com/teebr/socketsocketcan
# switched raspi to be the server instead of a client


# ---------------------------------------------------------------------------- #
class TCPBus(can.BusABC):

    RECV_FRAME_SZ = 29
    CAN_EFF_FLAG = 0x80000000
    CAN_RTR_FLAG = 0x40000000
    CAN_ERR_FLAG = 0x20000000

    def __init__(self, ip: str, port: int, can_filters: can.typechecking.CanFilters | None = None,**kwargs):
        super().__init__("whatever", can_filters)
        self.port: int = port
        self._is_connected: bool = False
        self.recv_buffer: Queue = Queue() # Queue[can.Message]
        self.send_buffer: Queue = Queue() # Queue[can.Message]
        self._shutdown_flag: bool = False#Queue()

        print(f"IP: {ip}, port: {port}")

        #open socket and wait for connection to establish.
        socket.setdefaulttimeout(3) # seconds
        utils.log("attempting to connect to tcp")
        self._conn: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        utils.log("Connecting...")
        self._conn.connect((ip, port))
        utils.log("connected")
        self._is_connected: bool = True
        self._conn.settimeout(0.5) #blocking makes exiting an infinite loop hard

        self.start_threads()


    def start_threads(self) -> bool:
        # self._conn.sendall(password.encode())
        # data_raw = self._conn.recv(1)
        # data = int.from_bytes(data_raw,"little")
        # print(f"recieved: {data}")
        # if data == 0x00:
        #     print("returning false")
        #     return False
        # print("returing true")
        #now we're connected, kick off other threads.
        self._tcp_listener = Thread(target=self._poll_socket)
        self._tcp_listener.start()

        self._tcp_writer = Thread(target=self._poll_send)
        self._tcp_writer.start()

        self.send_time_sync()
        return True
    
    def send_time_sync(self) -> None:
        # Sends the current time to update RTC
        self.send_buffer.put(4)
        t = datetime.datetime.now() 
        v = bytes([0,0,0,0,0,t.second, t.minute, t.hour, 
                   t.day, t.month, (t.year-2000), 0, 0])
        self.send_buffer.put(v)

    def _recv_internal(self,timeout: float | None = None) -> tuple[can.Message | None, bool]:
        #TODO: filtering
        try:
            return (self.recv_buffer.get(timeout=timeout), True)
        except queue.Empty:
            return None, True

    def send(self, msg: can.Message) -> None:
        if msg.is_extended_id:
            msg.arbitration_id |= self.CAN_EFF_FLAG
        if msg.is_remote_frame:
            msg.arbitration_id |= self.CAN_RTR_FLAG
        if msg.is_error_frame:
            msg.arbitration_id |= self.CAN_ERR_FLAG
        self.send_buffer.put(0)
        self.send_buffer.put(msg)

    def start_logging(self) -> None:
        self.send_buffer.put(1)
        self.send_buffer.put(0xFFFFFFFF)

    def stop_logging(self) -> None:
        self.send_buffer.put(3)
        self.send_buffer.put(0xFFFFFFFF)

    def _stop_threads(self) -> None:
        #self._shutdown_flag.put(True)
        self._shutdown_flag = True
        self._is_connected = False
        utils.log_warning("Bus Client Shutdown (TCP)")

    def shutdown(self, handshake: int) -> None:
        """gracefully close TCP connection and exit threads"""
        #handshake: 0: Currently in handshake mode, 1: In regular send mode
        if handshake == 0:
            msg = "exit"
            self._conn.sendall(msg.encode())
        else:
            msg = 4
            self._conn.sendall(msg.to_bytes(1, "little"))
        if self.is_connected:
            self._stop_threads()
        #can't join threads because this might be called from that thread, so just wait...
        while handshake == 1 and (self._tcp_listener.is_alive() or self._tcp_writer.is_alive()):
            sleep(0.005)
        self._conn.close() #shutdown might be faster but can be ugly and raise an exception

    def close(self) -> None:
        self._conn.close()

    @property
    def is_connected(self) -> bool:
        """check that a TCP connection is active"""
        return self._is_connected

    def _msg_to_bytes(self, msg: can.Message) -> bytes:
        """convert Message object to bytes to be put on TCP socket"""
        # print(msg)
        arb_id = msg.arbitration_id.to_bytes(4,"little") #TODO: masks
        dlc = msg.dlc.to_bytes(1,"little")
        data = msg.data + bytes(8-msg.dlc)
        # print(arb_id + dlc + data)
        return arb_id+dlc+data

    def _bytes_to_message(self, b: bytes) -> can.Message:
        """convert raw TCP bytes to can.Message object"""
        #ts = int.from_bytes(b[:4],"little") + int.from_bytes(b[4:8],"little")/1e6
        ts = int.from_bytes(b[:8],"little") + int.from_bytes(b[8:16],"little")/1e6
        #print(f"len: {len(b)}, time: {ts}, data: {b}")
        #can_id = int.from_bytes(b[8:12],"little")
        can_id = int.from_bytes(b[16:20],"little")
        dlc = b[20] #TODO: sanity check on these values in case of corrupted messages.

        #decompose ID
        is_extended = bool(can_id & self.CAN_EFF_FLAG) #CAN_EFF_FLAG
        if is_extended:
            arb_id = can_id & 0x1FFFFFFF
        else:
            arb_id = can_id & 0x000007FF

        return can.Message(
            timestamp = ts,
            arbitration_id = arb_id,
            is_extended_id = is_extended,
            is_error_frame = bool(can_id & self.CAN_ERR_FLAG), #CAN_ERR_FLAG
            is_remote_frame = bool(can_id & self.CAN_RTR_FLAG), #CAN_RTR_FLAG
            dlc=dlc,
            #data=b[13:13+dlc]
            data=b[21:21+dlc]
        )

    def _poll_socket(self) -> None:
        """background thread to check for new CAN messages on the TCP socket"""
        part_formed_message = bytearray() # TCP transfer might off part way through sending a message
        #with self._conn as conn:
        conn = self._conn
        while not self._shutdown_flag: #self._shutdown_flag.empty():
            try:
                data = conn.recv(self.RECV_FRAME_SZ * 20)
            except socket.timeout:
                #no data, just try again.
                continue
            except OSError as e:
                # socket's been closed.
                utils.log_error(f"ERROR: connection closed (1): {e}")
                self._stop_threads()
                break

            if len(data):
                # process the 1 or more messages we just received

                if len(part_formed_message):
                    data = part_formed_message + data #add on the previous remainder

                #check how many whole and incomplete messages we got through.
                num_incomplete_bytes = len(data) % self.RECV_FRAME_SZ
                num_frames = len(data) // self.RECV_FRAME_SZ

                #to pre-pend next time:
                if num_incomplete_bytes:
                    part_formed_message = data[-num_incomplete_bytes:]
                else:
                    part_formed_message = bytearray()

                c = 0
                for _ in range(num_frames):
                    self.recv_buffer.put(self._bytes_to_message(data[c:c+self.RECV_FRAME_SZ]))
                    c += self.RECV_FRAME_SZ
            else:
                #socket's been closed at the other end.
                utils.log_error(f"ERROR: connection closed (2)")
                self._stop_threads()
                break
        # utils.log("Exited poll socket")

    def _poll_send(self) -> None:
        """background thread to send messages when they are put in the queue"""
        #with self._conn as s:
        s = self._conn
        while not self._shutdown_flag: #self._shutdown_flag.empty():
            try:
                cmd = self.send_buffer.get(timeout=0.002)
                msg = self.send_buffer.get(timeout=0.002)
                data = cmd.to_bytes(1,"little")
                if (cmd == 0):
                    data += self._msg_to_bytes(msg)
                elif (cmd == 4):
                    data += msg
                else:
                    data += bytearray(13)
                    #data += msg.to_bytes(4, "little")
                while not self.send_buffer.empty(): #we know there's one message, might be more.
                    data += self.send_buffer.get().to_bytes(1,"little")
                    data += self._msg_to_bytes(self.send_buffer.get())
                try:
                    s.sendall(data)
                    #print(f"sent {data}")
                except OSError as e:
                    # socket's been closed.
                    utils.log_error(f"ERROR: connection closed (3): {e}")
                    self._stop_threads()
                    break
            except QueueEmpty:
                pass #NBD, just means nothing to send.
        # utils.log("Exited poll send")
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
class UDPBus(can.BusABC):
    #RECV_FRAME_SZ = 29
    RECV_FRAME_SZ = 18
    CAN_EFF_FLAG = 0x80000000
    CAN_RTR_FLAG = 0x40000000
    CAN_ERR_FLAG = 0x20000000

    def __init__(self, ip: str, port: int, can_filters: can.typechecking.CanFilters | None = None, **kwargs):
        super().__init__("whatever",can_filters)
        self.port: int = port
        self._is_connected: bool = False
        self.recv_buffer: Queue = Queue()
        self._shutdown_flag: bool = False#Queue()

        #open socket and wait for connection to establish.
        socket.setdefaulttimeout(3) # seconds
        utils.log("attempting to connect to udp")
        self._conn: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        self._conn.bind(("", 5005))
        utils.log("Listening to UDP Port")
        self._is_connected: bool = True
        self._conn.settimeout(0.5) #blocking makes exiting an infinite loop hard

        #now we're connected, kick off other threads.
        self._udp_listener: Thread = Thread(target=self._poll_udp_socket)
        self._udp_listener.start()

    def _bytes_to_message(self, b: bytes) -> can.Message:
        """convert raw TCP bytes to can.Message object"""
        #ts = int.from_bytes(b[:4],"little") + int.from_bytes(b[4:8],"little")/ e6
        # ts = int.from_bytes(b[:8],"little") + int.from_bytes(b[8:16],"little")/1e6
        ts = int.from_bytes(b[:4], "little")/1000.0
        #print(f"len: {len(b)}, time: {ts}, data: {b}")
        #can_id = int.from_bytes(b[8:12],"little")
        # can_id = int.from_bytes(b[16:20],"little")
        can_id = int.from_bytes(b[4:8], 'little')
        #dlc = b[20] #TODO: sanity check on these values in case of corrupted messages.
        bus_id = b[8]
        dlc = b[9]

        #decompose ID
        is_extended = bool(can_id & self.CAN_EFF_FLAG) #CAN_EFF_FLAG
        if is_extended:
            arb_id = can_id & 0x1FFFFFFF
        else:
            arb_id = can_id & 0x000007FF

        return can.Message(
            timestamp = ts,
            arbitration_id = arb_id,
            is_extended_id = is_extended,
            is_error_frame = bool(can_id & self.CAN_ERR_FLAG), #CAN_ERR_FLAG
            is_remote_frame = bool(can_id & self.CAN_RTR_FLAG), #CAN_RTR_FLAG
            dlc=dlc,
            channel=bus_id,
            #data=b[13:13+dlc]
            #data=b[21:21+dlc]
            data=b[10:10+dlc]
        )

    def send(self, msg: can.Message) -> None:
        if msg.is_extended_id:
            msg.arbitration_id |= self.CAN_EFF_FLAG
        if msg.is_remote_frame:
            msg.arbitration_id |= self.CAN_RTR_FLAG
        if msg.is_error_frame:
            msg.arbitration_id |= self.CAN_ERR_FLAG
        self.send_buffer.put(msg)

    def _recv_internal(self, timeout: float | None = None) -> tuple[can.Message | None, bool]:
        #TODO: filtering
        try:
            return (self.recv_buffer.get(timeout=timeout), True)
        except queue.Empty:
            return None, True

    def _poll_udp_socket(self) -> None:
        """background thread to check for new CAN messages on the UDP socket"""
        part_formed_message = bytearray() # UDP transfer might off part way through sending a message
        conn = self._conn
        while not self._shutdown_flag: #self._shutdown_flag.empty():
            try:
                data = conn.recv(self.RECV_FRAME_SZ * 20)
            except socket.timeout:
                #no data, just try again.
                continue
            except OSError as e:
                # socket's been closed.
                utils.log_error(f"ERROR: connection closed (1): {e}")
                self._stop_threads()
                break

            if len(data):
                # process the 1 or more messages we just received

                if len(part_formed_message):
                    data = part_formed_message + data #add on the previous remainder

                #check how many whole and incomplete messages we got through.
                num_incomplete_bytes = len(data) % self.RECV_FRAME_SZ
                num_frames = len(data) // self.RECV_FRAME_SZ

                #to pre-pend next time:
                if num_incomplete_bytes:
                    part_formed_message = data[-num_incomplete_bytes:]
                else:
                    part_formed_message = bytearray()

                c = 0
                for _ in range(num_frames):
                    self.recv_buffer.put(self._bytes_to_message(data[c:c+self.RECV_FRAME_SZ]))
                    c += self.RECV_FRAME_SZ
            else:
                #socket's been closed at the other end.
                utils.log_error(f"ERROR: connection closed (2)")
                self._stop_threads()
                break

    def _stop_threads(self) -> None:
        #self._shutdown_flag.put(True)
        self._shutdown_flag = True
        self._is_connected = False
        utils.log_warning("Bus Client Shutdown (UDP)")

    def shutdown(self) -> None:
        """gracefully close UDP connection and exit threads"""
        if self._is_connected:
            self._stop_threads()
        #can't join threads because this might be called from that thread, so just wait...
        while self._udp_listener.is_alive():
            sleep(0.005)
        self._conn.close() #shutdown might be faster but can be ugly and raise an exception
# ---------------------------------------------------------------------------- #