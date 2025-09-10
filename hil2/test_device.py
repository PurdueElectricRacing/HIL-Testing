from typing import Any, Optional

import json
import os
import threading

import cantools.database.can.database as cantools_db

from . import action
from . import can_helper
from . import commands
from . import dut_cons
from . import hil_errors
from . import serial_helper


# Peripheral configuration ------------------------------------------------------------#
class AdcConfig:
    """Configuration for an ADC (Analog-to-Digital Converter)."""

    def __init__(self, adc_config: dict):
        """
        :param adc_config: The ADC configuration dictionary
        """
        match adc_config:
            # PCB
            case {
                "bit_resolution": br,
                "adc_reference_v": ar,
                "5v_reference_v": v5r,
                "24v_reference_v": v24r,
            }:
                self.bit_resolution: int = br
                self.adc_reference_v: float = ar
                self.five_v_reference_v: Optional[float] = v5r
                self.twenty_four_v_reference_v: Optional[float] = v24r
            # Breadboard
            case {
                "bit_resolution": br,
                "adc_reference_v": ar,
            }:
                self.bit_resolution: int = br
                self.adc_reference_v: float = ar
                self.five_v_reference_v: Optional[float] = None
                self.twenty_four_v_reference_v: Optional[float] = None
            case _:
                raise hil_errors.ConfigurationError("Invalid ADC configuration")

    def raw_to_v(self, raw_value: int) -> float:
        """
        Convert a raw ADC value to a voltage.

        :param raw_value: The raw ADC value to convert
        :return: The converted voltage value
        """
        if raw_value < 0 or raw_value > (2**self.bit_resolution - 1):
            raise hil_errors.RangeError(f"ADC raw value {raw_value} out of range")
        return (raw_value / (2**self.bit_resolution - 1)) * self.adc_reference_v

    def raw_to_5v(self, raw_value: int) -> float:
        """
        Convert a raw ADC value to a voltage using the 5V reference.
        If on a PCB, AI5 means it when through a voltage divider.

        :param raw_value: The raw ADC value to convert
        :return: The converted voltage value
        """
        match self.five_v_reference_v:
            case None:
                error_msg = "5V reference voltage not configured"
                raise hil_errors.ConfigurationError(error_msg)
            case v5r:
                return (self.raw_to_v(raw_value) / v5r) * 5.0

    def raw_to_24v(self, raw_value: int) -> float:
        """
        Convert a raw ADC value to a voltage using the 24V reference.
        If on a PCB, AI24 means it when through a voltage divider.

        :param raw_value: The raw ADC value to convert
        :return: The converted voltage value
        """
        match self.twenty_four_v_reference_v:
            case None:
                error_msg = "24V reference voltage not configured"
                raise hil_errors.ConfigurationError(error_msg)
            case v24r:
                return (self.raw_to_v(raw_value) / v24r) * 24.0


class DacConfig:
    """Configuration for a DAC (Digital-to-Analog Converter)."""

    def __init__(self, dac_config: dict):
        """
        :param dac_config: The DAC configuration dictionary
        """
        match dac_config:
            case {"bit_resolution": br, "reference_v": rv}:
                self.bit_resolution = br
                self.reference_v = rv
            case _:
                raise hil_errors.ConfigurationError("Invalid DAC configuration")

    def v_to_raw(self, value: float) -> int:
        """
        Convert a voltage value to a raw DAC value.

        :param value: The voltage value to convert
        :return: The converted raw DAC value
        """
        if value < 0 or value > self.reference_v:
            raise hil_errors.RangeError(f"DAC value {value} out of range")
        return int((value / self.reference_v) * (2**self.bit_resolution - 1))


class PotConfig:
    """Configuration for a POT (Potentiometer)."""

    def __init__(self, pot_config: dict):
        """
        :param pot_config: The POT configuration dictionary
        """
        match pot_config:
            case {"bit_resolution": br, "reference_ohms": r, "wiper_ohms": w}:
                self.bit_resolution = br
                self.reference_ohms = r
                self.wiper_ohms = w
            case _:
                raise hil_errors.ConfigurationError("Invalid POT configuration")

    def ohms_to_raw(self, value: float) -> int:
        """
        Convert an ohm value to a raw POT value.

        :param value: The ohm value to convert
        :return: The converted raw POT value
        """
        if value < self.wiper_ohms or value > self.reference_ohms + self.wiper_ohms:
            raise hil_errors.RangeError(f"POT value {value} out of range")
        steps = self.bit_resolution**2 - 1
        return int((steps * (value - self.wiper_ohms)) / self.reference_ohms)


# Interface configuration -------------------------------------------------------------#
class Port:
    """Configuration for a port."""

    def __init__(self, port: dict):
        """
        :param port: The port configuration dictionary
        """
        match port:
            case {"name": name, "port": port, "mode": mode}:
                self.name: str = name
                self.port: int = port
                self.mode: str = mode
            case _:
                raise hil_errors.ConfigurationError("Invalid Port configuration")


class Mux:
    """Configuration for a MUX (Multiplexer)."""

    def __init__(self, mux: dict):
        """
        :param mux: The MUX configuration dictionary
        """
        match mux:
            case {
                "name": name,
                "mode": mode,
                "select_ports": select_ports,
                "port": port,
            }:
                self.name: str = name
                self.mode: str = mode
                self.select_ports: list[int] = select_ports
                self.port: int = port
            case _:
                raise hil_errors.ConfigurationError("Invalid Mux configuration")

    def select_from_name(self, name: str) -> Optional["MuxSelect"]:
        """
        Attempt to see if self is the base mux that is being referenced.
        For example: DMUX_6 means DMUX is the base mux and 6 is the select line.

        :param name: The name of the MUX select line (ex: DMUX_6)
        :return: The MuxSelect instance if found, None otherwise
        """
        name_parts = name.rsplit("_", 1)
        if len(name_parts) < 2:
            return None
        if name_parts[0] != self.name:
            return None
        try:
            return MuxSelect(self, int(name_parts[1]))
        except ValueError:
            return None


class MuxSelect:
    """Represents a selected MUX (Multiplexer) line."""

    def __init__(self, mux: Mux, select: int):
        """
        :param mux: The MUX instance
        :param select: The selected line number (0 indexed)
        """
        self.mux: Mux = mux
        self.select: int = select


class CanBus:
    """Configuration for a CAN (Controller Area Network) bus."""

    def __init__(self, can_bus: dict):
        """
        :param can_bus: The CAN bus configuration dictionary
        """
        match can_bus:
            case {"name": name, "bus": bus}:
                self.name: str = name
                self.bus: int = bus
            case _:
                raise hil_errors.ConfigurationError("Invalid CAN Bus configuration")


# Test device -------------------------------------------------------------------------#
class TestDevice:
    # Init ----------------------------------------------------------------------------#
    def __init__(
        self,
        hil_id: int,
        name: str,
        ports: dict[str, Port],
        muxs: dict[str, Mux],
        can_busses: dict[str, CanBus],
        adc_config: AdcConfig,
        dac_config: Optional[DacConfig],
        pot_config: Optional[PotConfig],
    ):
        """
        :param hil_id: The HIL ID of the device
        :param name: The name of the device
        :param ports: The port configurations
        :param muxs: The MUX configurations
        :param can_busses: The CAN bus configurations
        :param adc_config: The ADC configuration
        :param dac_config: The DAC configuration
        :param pot_config: The potentiometer configuration
        """
        self.hil_id: int = hil_id
        self._name: str = name
        self._ports: dict[str, Port] = ports
        self._muxs: dict[str, Mux] = muxs
        self._can_busses: dict[str, CanBus] = can_busses
        self._adc_config: AdcConfig = adc_config
        self._dac_config: Optional[DacConfig] = dac_config
        self._pot_config: Optional[PotConfig] = pot_config

        # Please use set_serial() to set the serial!
        self._ser: Optional[serial_helper.ThreadedSerial] = None

        self.device_can_busses: dict[int, can_helper.CanMessageManager] = dict(
            map(
                lambda c: (c.bus, can_helper.CanMessageManager()),
                self._can_busses.values(),
            )
        )

    @classmethod
    def from_json(cls, hil_id: int, name: str, device_config_path: str):
        """
        Create a TestDevice instance from a JSON configuration file.

        :param hil_id: The HIL ID of the device
        :param name: The name of the device
        :param device_config_path: The path to the device configuration JSON file
        """
        with open(device_config_path, "r") as device_config_path:
            device_config = json.load(device_config_path)

        ports = dict(
            map(lambda p: (p.get("name"), Port(p)), device_config.get("ports", []))
        )
        muxs = dict(
            map(lambda m: (m.get("name"), Mux(m)), device_config.get("muxs", []))
        )
        can_busses = dict(
            map(lambda c: (c.get("name"), CanBus(c)), device_config.get("can", []))
        )

        match device_config:
            case {"adc_config": adc_config_data}:
                adc_config = AdcConfig(adc_config_data)
            case _:
                error_msg = f"ADC configuration missing for device {name}"
                raise hil_errors.ConfigurationError(error_msg)

        match device_config:
            case {"dac_config": dac_config_data}:
                dac_config = DacConfig(dac_config_data)
            case _:
                dac_config = None

        match device_config:
            case {"pot_config": pot_config_data}:
                pot_config = PotConfig(pot_config_data)
            case _:
                pot_config = None

        return cls(
            hil_id,
            name,
            ports,
            muxs,
            can_busses,
            adc_config,
            dac_config,
            pot_config,
        )

    def set_serial(self, ser: serial_helper.ThreadedSerial) -> None:
        """
        Set the serial connection for the TestDevice.
        The caller is responsible for starting the serial connection's thread.

        :param ser: The serial connection to set
        """
        self._ser = ser

    def close(self) -> None:
        """
        Close the serial connection for the TestDevice.
        """
        match self._ser:
            case None:
                error_msg = f"Cannot close TestDevice {self._name}: serial not set"
                raise hil_errors.EngineError(error_msg)
            case ser:
                ser.stop()

    # Command handling ----------------------------------------------------------------#
    def _select_mux(self, mux_select: MuxSelect) -> None:
        """
        Select a MUX (Multiplexer) line.

        :param mux_select: The MUX selection information
        """
        for i, p in enumerate(mux_select.mux.select_ports):
            select_bit = True if (mux_select.select & (1 << i)) else False
            self._set_do(p, select_bit)

    def _set_do(self, pin: int, value: bool) -> None:
        """
        Set a digital output (DO) pin.

        :param pin: The pin number to set
        :param value: The value to set the pin to (low = False, high = True)
        """
        match self._ser:
            case None:
                error_msg = f"Cannot set DO on TestDevice {self._name}: serial not set"
                raise hil_errors.EngineError(error_msg)
            case ser:
                commands.write_gpio(ser, pin, value)

    def _hiZ_do(self, pin: int) -> None:
        """
        Set a digital output (DO) pin to high impedance (HiZ).

        :param pin: The pin number to set
        """
        match self._ser:
            case None:
                error_msg = (
                    f"Cannot set HiZ DO on TestDevice {self._name}: serial not set"
                )
                raise hil_errors.EngineError(error_msg)
            case ser:
                commands.hiZ_gpio(ser, pin)

    def _get_di(self, pin: int) -> bool:
        """
        Get the digital input (DI) state of a pin.

        :param pin: The pin number to read
        :return: The state of the pin (True for high, False for low)
        """
        match self._ser:
            case None:
                error_msg = f"Cannot get DI on TestDevice {self._name}: serial not set"
                raise hil_errors.EngineError(error_msg)
            case ser:
                return commands.read_gpio(ser, pin)

    def _set_ao(self, pin: int, value: float) -> None:
        """
        Set an analog output (AO) pin after converting the volts value to raw.

        :param pin: The pin/offset number to set
        :param value: The voltage value to set the pin to
        """
        match (self._ser, self._dac_config):
            case (ser, dac_config) if ser is not None and dac_config is not None:
                raw_value = dac_config.v_to_raw(value)
                commands.write_dac(ser, pin, raw_value)
            case _:
                error_msg = f"Cannot set AO on TestDevice {self._name}: serial or DAC config not set"
                raise hil_errors.EngineError(error_msg)

    def _hiZ_ao(self, pin: int) -> None:
        """
        Set an analog output (AO) pin to high impedance (HiZ).

        :param pin: The pin/offset number to set
        """
        match self._ser:
            case None:
                error_msg = (
                    f"Cannot set HiZ AO on TestDevice {self._name}: serial not set"
                )
                raise hil_errors.EngineError(error_msg)
            case ser:
                commands.hiZ_dac(ser, pin)

    def _get_ai(self, pin: int, mode: str) -> float:
        """
        Get an analog input (AI) reading from a pin and convert the reading to volts.

        :param pin: The pin number to read
        :param mode: The mode to use for the reading (AI5, AI24, or AI)
        :return: The voltage value read from the pin
        """
        match self._ser:
            case None:
                error_msg = f"Cannot get AI on TestDevice {self._name}: serial not set"
                raise hil_errors.EngineError(error_msg)
            case ser:
                raw_value = commands.read_adc(ser, pin)

        if mode == "AI5":
            return self._adc_config.raw_to_5v(raw_value)
        elif mode == "AI24":
            return self._adc_config.raw_to_24v(raw_value)
        elif mode == "AI":
            return self._adc_config.raw_to_v(raw_value)
        else:
            raise ValueError(f"Unsupported AI mode: {mode}")

    def _set_pot(self, pin: int, value: float) -> None:
        """
        Set a potentiometer (POT) pin after converting the ohms value to raw.

        :param pin: The pin/offset to set
        :param value: The resistance value to set the pin to (in ohms)
        """
        match (self._ser, self._pot_config):
            case (ser, pot_config) if ser is not None and pot_config is not None:
                raw_value = pot_config.ohms_to_raw(value)
                commands.write_pot(ser, pin, raw_value)
            case _:
                error_msg = f"Cannot set POT on TestDevice {self._name}: serial not set"
                raise hil_errors.EngineError(error_msg)

    def _update_can_messages(self, bus: int, can_dbc: cantools_db.Database) -> None:
        """
        Update the CAN message store by decoding the saved parsed can messages from the Serial.

        :param bus: The CAN bus to update
        :param can_dbc: The CAN database to use for decoding
        """
        match self._ser:
            case None:
                error_msg = (
                    f"Cannot update CAN messages on TestDevice {self._name}: "
                    "serial not set"
                )
                raise hil_errors.EngineError(error_msg)
            case ser:
                self.device_can_busses[bus].add_multiple(
                    commands.parse_can_messages(ser, bus, can_dbc)
                )

    def _send_can(
        self, bus: int, signal: str | int, data: dict, can_dbc: cantools_db.Database
    ) -> None:
        """
        Send a CAN message on the specified bus.

        :param bus: The CAN bus to send the message on
        :param signal: The CAN signal to send
        :param data: The data to include in the CAN message
        :param can_dbc: The CAN database to use for encoding
        """
        raw_data = list(can_dbc.encode_message(signal, data))
        msg_id = can_dbc.get_message_by_name(signal).frame_id

        match self._ser:
            case None:
                error_msg = (
                    f"Cannot send CAN message on TestDevice {self._name}: "
                    "serial not set"
                )
                raise hil_errors.EngineError(error_msg)
            case ser:
                commands.send_can(ser, bus, msg_id, raw_data)

    # Action --------------------------------------------------------------------------#
    def do_action(self, action_type: action.ActionType, port: str) -> Any:
        """
        Perform a HIL action on a specific port.

        :param action_type: The type of action to perform (+ includes all needed info)
        :param port: The HIL port to perform the action on
        :return: depends on the action type
        """

        maybe_port = self._ports.get(port, None)
        maybe_mux_select = next(
            (
                val
                for m in self._muxs.values()
                if (val := m.select_from_name(port)) is not None
            ),
            None,
        )
        maybe_can_bus = self._can_busses.get(port, None)

        match (action_type, maybe_port, maybe_mux_select, maybe_can_bus):
            # Set DO + direct port
            case (action.SetDo(value), mp, _, _) if mp is not None and mp.mode == "DO":
                self._set_do(mp.port, value)
            # Set DO + mux select
            case (action.SetDo(value), _, mms, _) if (
                mms is not None and mms.mux.mode == "DO"
            ):
                self._select_mux(mms)
                self._set_do(mms.mux.port, value)
            # HiZ DO + direct port
            case (action.HiZDo(), mp, _, _) if mp is not None and mp.mode == "DO":
                self._hiZ_do(mp.port)
            # HiZ DO + mux select
            case (action.HiZDo(), _, mms, _) if (
                mms is not None and mms.mux.mode == "DO"
            ):
                self._select_mux(mms)
                self._hiZ_do(mms.mux.port)
            # Get DI + direct port
            case (action.GetDi(), mp, _, _) if mp is not None and mp.mode == "DI":
                return self._get_di(mp.port)
            # Get DI + mux select
            case (action.GetDi(), _, mms, _) if (
                mms is not None and mms.mux.mode == "DI"
            ):
                self._select_mux(mms)
                return self._get_di(mms.mux.port)
            # Set AO + direct port
            case (action.SetAo(value), mp, _, _) if mp is not None and mp.mode == "AO":
                self._set_ao(mp.port, value)
            # HiZ AO + direct port
            case (action.HiZAo(), mp, _, _) if mp is not None and mp.mode == "AO":
                self._hiZ_ao(mp.port)
            # Get AI + direct port
            case (action.GetAi(), mp, _, _) if mp is not None and mp.mode.startswith(
                "AI"
            ):
                return self._get_ai(mp.port, mp.mode)
            # Get AI + mux select
            case (
                action.GetAi(),
                _,
                mms,
                _,
            ) if mms is not None and mms.mux.mode.startswith("AI"):
                self._select_mux(mms)
                return self._get_ai(mms.mux.port, mms.mux.mode)
            # Set Pot + direct port
            case (action.SetPot(value), mp, _, _) if (
                mp is not None and mp.mode == "POT"
            ):
                self._set_pot(mp.port, value)
            # Send CAN msg + can bus name
            case (action.SendCan(signal, data, can_dbc), _, _, mcb) if mcb is not None:
                self._update_can_messages(mcb.bus, can_dbc)
                self._send_can(mcb.bus, signal, data, can_dbc)
            # Get last CAN msg + can bus name
            case (action.GetLastCan(signal, can_dbc), _, _, mcb) if mcb is not None:
                self._update_can_messages(mcb.bus, can_dbc)
                return self.device_can_busses[mcb.bus].get_last(signal)
            # Get all CAN msgs + can bus name
            case (action.GetAllCan(signal, can_dbc), _, _, mcb) if mcb is not None:
                self._update_can_messages(mcb.bus, can_dbc)
                return self.device_can_busses[mcb.bus].get_all(signal)
            # Clear CAN msgs + can bus name
            case (action.ClearCan(signal, can_dbc), _, _, mcb) if mcb is not None:
                self._update_can_messages(mcb.bus, can_dbc)
                self.device_can_busses[mcb.bus].clear(signal)
            # Unsupported action
            case _:
                error_msg = (
                    f"Action {type(action)} not supported for "
                    f"port {port} on device {self._name}"
                )
                raise hil_errors.EngineError(error_msg)


# Test device manager -----------------------------------------------------------------#
class TestDeviceManager:
    """
    Manages test devices for HIL (Hardware-in-the-Loop) simulation.
    """

    def __init__(self, test_devices: dict[str, TestDevice]):
        """
        :param test_devices: A dictionary of test devices managed by this manager.
                             key = device name, value = TestDevice instance
        """
        self._test_devices: dict[str, TestDevice] = test_devices

    @classmethod
    def from_json(
        cls, test_config_path: str, device_config_fpath: str
    ) -> "TestDeviceManager":
        """
        Create a TestDeviceManager instance from JSON configuration files.
        Is responsible for starting all of the ThreadedSerial instances.

        :param test_config_path: The path to the test configuration JSON file.
        :param device_config_fpath: The file path to the directory containing device
                                    configuration files.
        :return: A TestDeviceManager instance.
        """

        with open(test_config_path, "r") as test_config_file:
            test_config = json.load(test_config_file)

        hil_ids = []
        stop_events = {}
        test_devices = {}
        match test_config:
            case {"hil_devices": hil_devices}:
                for device in hil_devices:
                    match device:
                        case {
                            "id": hil_id,
                            "name": name,
                            "config": config_file_name,
                        } if (
                            not hil_id in hil_ids
                        ):
                            hil_ids.append(hil_id)
                            stop_events[hil_id] = threading.Event()
                            test_devices[name] = TestDevice.from_json(
                                hil_id,
                                name,
                                os.path.join(device_config_fpath, config_file_name),
                            )
                        case {"id": hil_id}:
                            error_msg = f"Duplicate HIL device ID found: {hil_id}"
                            raise hil_errors.ConfigurationError(error_msg)
                        case _:
                            error_msg = f"Invalid HIL device configuration: {device}"
                            raise hil_errors.ConfigurationError(error_msg)
            case _:
                error_msg = "Invalid test configuration: missing 'hil_devices' key"
                raise hil_errors.ConfigurationError(error_msg)

        hil_devices = serial_helper.discover_devices(hil_ids)

        sers = dict(
            map(
                lambda hil_id: (
                    hil_id,
                    serial_helper.ThreadedSerial(
                        hil_devices[hil_id], stop_events[hil_id]
                    ),
                ),
                hil_ids,
            )
        )
        for test_device in test_devices.values():
            ser = sers[test_device.hil_id]
            t = threading.Thread(target=ser.run)
            t.start()
            test_device.set_serial(ser)

        return cls(test_devices)

    def maybe_hil_con_from_net(
        self, board: str, net: str
    ) -> Optional[dut_cons.HilDutCon]:
        """
        Check to see if a board is a HIL device.

        :param board: The name of the board to check.
        :param net: The network to use for the connection.
        :return: A HilDutCon instance if the board is a HIL device, None otherwise.
        """
        if board in self._test_devices:
            return dut_cons.HilDutCon(board, net)
        else:
            return None

    def do_action(
        self, action_type: action.ActionType, hil_dut_con: dut_cons.HilDutCon
    ) -> Any:
        """
        Perform an action on a HIL device.

        :param action_type: The type of action to perform.
        :param hil_dut_con: The HIL DUT connection information.
        :return: The result of the action (if any).
        """
        if hil_dut_con.device in self._test_devices:
            return self._test_devices[hil_dut_con.device].do_action(
                action_type, hil_dut_con.port
            )
        else:
            error_msg = f"Device {hil_dut_con.device} not found"
            raise hil_errors.ConnectionError(error_msg)

    def close(self) -> None:
        """
        Close all HIL devices.
        """
        for device in self._test_devices.values():
            device.close()
