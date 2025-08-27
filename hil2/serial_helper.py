from typing import Optional

import logging
import threading
import time

import serial
import serial.tools.list_ports

from . import commands
from . import hil_errors

SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1
SERIAL_RETRIES = 5

GET_TIMEOUT = 0.1
SLEEP_INTERVAL = 0.01


# Discover ----------------------------------------------------------------------------#
def discover_devices(hil_ids: list[int]) -> dict[int, serial.Serial]:
    """
    Attempts to find HIL devices by sending an identification command to each serial
    port.

    :param hil_ids: A list of expected HIL device IDs
    :return: A dictionary mapping discovered HIL device IDs to their serial connections
    """

    devices = {}

    com_ports = [
        port.device
        for port in serial.tools.list_ports.comports()
        if "USB Serial" in port.description
    ]

    # For every serial port, try to see if it is a HIL device
    for cp in com_ports:
        logging.debug(f"Trying to discover HIL device on port {cp}")
        serial_con = serial.Serial(
            cp,
            SERIAL_BAUDRATE,
            timeout=SERIAL_TIMEOUT,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=0,
            rtscts=0,
        )
        serial_con.dtr = False
        time.sleep(1)
        serial_con.reset_input_buffer()
        serial_con.dtr = True

        # Need to give a little time
        for _ in range(SERIAL_RETRIES):
            read_hil_id = commands.read_id(serial_con)
            if read_hil_id is not None and read_hil_id in hil_ids:
                devices[read_hil_id] = serial_con
                logging.info(
                    f"Discovered HIL device with ID {read_hil_id} on port {cp}"
                )
                break
            time.sleep(1)
        else:
            # If it is not a HIL device, close it
            serial_con.close()

    # Check we found all devices
    for hil_id in hil_ids:
        if hil_id not in devices:
            error_msg = f"Failed to discover HIL device with ID {hil_id} on any port"
            raise hil_errors.SerialError(error_msg)

    return devices


# Threaded serial ---------------------------------------------------------------------#
class ThreadedSerial:
    """
    A class that handles serial communication in a separate thread.
    This is needed because CAN messages are received asynchronously as opposed to
    command and response.
    """

    def __init__(self, serial_con: serial.Serial, stop_event: threading.Event):
        """
        :param serial_con: The serial connection to the HIL device
        :param stop_event: The event used to signal the thread to stop
        """
        self.serial_con: serial.Serial = serial_con
        self.stop_event: threading.Event = stop_event

        # Raw readings from the serial port
        self.readings: list[int] = []

        # Parsed readings. The key is the command (ex: READ_GPIO) and the value is the
        # list of bytes
        self.parsed_readings: dict[int, list[int]] = {}
        # Parsed CAN messages. The key is the bus number, the value is a list of the
        # list of bytes for each message
        self.parsed_can_messages: dict[int, list[list[int]]] = {}

        # Lock for synchronizing access to shared resources
        self.lock = threading.Lock()

    def write(self, data: bytes) -> None:
        """
        Write data to the serial port. Safe to be called from another thread.

        :param data: The data to write to the serial port
        """
        self.serial_con.write(data)

    def _read(self):
        """
        Attempt to read a single byte from the serial port.
        """
        read_data = self.serial_con.read(1)
        if len(read_data) < 1:
            return
        value = int.from_bytes(read_data, "big")
        self.readings.append(value)

    def _process_readings(self):
        """
        Attempt to process read bytes.
        """
        processed = True
        while processed:
            # If something was processed, try to process again
            processed, self.readings = commands.parse_readings(
                self.readings, self.parsed_readings, self.parsed_can_messages
            )

    def _get_readings(self, command: int) -> Optional[list[int]]:
        """
        Get the readings for a specific command. Safe to be called from a different thread.

        :param command: The command to get readings for (used as key)
        :return: The readings for the command, or None if not found
        """
        with self.lock:
            val = self.parsed_readings.pop(command, None)
            return val

    def get_readings_with_timeout(
        self,
        command: int,
        timeout: float = GET_TIMEOUT,
        sleep_interval: float = SLEEP_INTERVAL,
    ) -> Optional[list[int]]:
        """
        Get the readings for a command, with a delay.
        Retries the reading at regular intervals until the timeout is reached.
        Safe to be called from a different thread.

        :param command: The command to get readings for (used as key)
        :param timeout: The maximum time to wait for readings (seconds)
        :param sleep_interval: The time to wait between retries (seconds)
        :return: The readings for the command, or None if not found
        """

        deadline = time.time() + timeout
        while time.time() < deadline:
            if (reading := self._get_readings(command)) is not None:
                return reading
            time.sleep(sleep_interval)
        return None

    def get_parsed_can_messages(self, bus: int) -> list[list[int]]:
        """
        Get the parsed CAN messages for a specific bus.
        Safe to be called from a different thread.

        :param bus: The bus number to get messages for
        :return: A list of parsed (but not decoded) CAN messages for the bus
        """
        with self.lock:
            return self.parsed_can_messages.pop(bus, [])

    def stop(self):
        """
        Stop the serial helper thread.
        Safe to be called from a different thread.
        """
        self.stop_event.set()

    def _close(self):
        """
        Close the serial connection.
        """
        self.serial_con.close()

    def run(self):
        """
        Run the serial helper thread.
        Constantly tries to read from the serial port and process the readings.
        Should be run in a separate thread.
        """
        while not self.stop_event.is_set():
            self._read()
            if len(self.readings) > 0:
                with self.lock:
                    self._process_readings()

        self._close()
