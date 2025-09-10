from typing import Optional

import logging
import os

import cantools.database.can.database as cantools_db

from . import action
from . import can_helper
from . import component
from . import dut_cons
from . import hil_errors
from . import net_map
from . import test_device


class Hil2:
    # Init ----------------------------------------------------------------------------#
    def __init__(
        self,
        test_config_path: str,
        device_config_fpath: str,
        net_map_path: Optional[str] = None,
        can_dbc_fpath: Optional[str] = None,
    ):
        """
        :param test_config_path: The path to the test configuration JSON file
        :param device_config_fpath: The path to the device configuration JSON folder
        :param net_map_path: The path to the net map (exported from Altium) file
                             (optional)
        :param can_dbc_path: The path to the CAN DBC folder (optional)
        """
        self._test_device_manager: test_device.TestDeviceManager = (
            test_device.TestDeviceManager.from_json(
                test_config_path, device_config_fpath
            )
        )
        self._dut_cons: dut_cons.DutCons = dut_cons.DutCons.from_json(test_config_path)
        self._maybe_net_map: Optional[net_map.NetMap] = (
            None if net_map_path is None else net_map.NetMap.from_csv(net_map_path)
        )
        self._can_dbc: Optional[cantools_db.Database] = (
            None
            if can_dbc_fpath is None
            else can_helper.load_can_dbcs(os.path.join(can_dbc_fpath))
        )
        # Components that need to be "shutdown" when HIL2 exits
        self._shutdown_components: dict[
            net_map.BoardNet, component.ShutdownableComponent
        ] = {}

    # Context -------------------------------------------------------------------------#
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, _traceback):
        if exc_type is not None:
            logging.critical(f"Hil2 exiting due to exception: {exc_value}")

        self.close()
        self._test_device_manager.close()
        return False

    # Soft close ----------------------------------------------------------------------#
    def close(self) -> None:
        """
        'Shutdown' all the componets (hiZ currently configured outputs)
        """
        for comp in self._shutdown_components.values():
            comp.shutdown()
        self._shutdown_components.clear()

    # Map -----------------------------------------------------------------------------#
    def _map_to_hil_device_con(self, board: str, net: str) -> dut_cons.HilDutCon:
        """
        Map a DUT connection (board/net or hil device/port) to a HIL device connection.
        If the board is a hil device (ex: 'RearTester'), return the corresponding HIL
        device connection.
        Otherwise, try to map from the test board and net name ('Dashboard'/'BRK_STAT')
        to the HIL device/port it is connected to.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        :return: The corresponding HIL device connection
        """
        maybe_hil_dut_con = self._test_device_manager.maybe_hil_con_from_net(board, net)
        match (self._maybe_net_map, maybe_hil_dut_con):
            case (None, None):
                error_msg = (
                    "No HIL device connection found for board/net, and no "
                    "net map available to resolve: "
                    f"({board}, {net})"
                )
                raise hil_errors.ConnectionError(error_msg)
            case (net_map, None):
                net_map_entry = net_map.get_entry(board, net)
                dut_con = dut_cons.DutCon(
                    net_map_entry.component, net_map_entry.designator
                )
                return self._dut_cons.get_hil_device_connection(board, dut_con)
            case (None, hil_dut_con):
                return hil_dut_con
            case _:
                error_msg = (
                    "Multiple methods to resolve HIL device connection for "
                    "board/net found; ambiguous: "
                    f"({board}, {net})"
                )
                raise hil_errors.ConnectionError(error_msg)

    # DO ------------------------------------------------------------------------------#
    def set_do(self, board: str, net: str, value: bool) -> None:
        """
        Sets the digital output value.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        :param value: The value to set the digital output to (low = false, high = true)
        """
        _ = self.do(board, net)  # Ensure component is registered to shutdown
        self._test_device_manager.do_action(
            action.SetDo(value), self._map_to_hil_device_con(board, net)
        )

    def hiZ_do(self, board: str, net: str) -> None:
        """
        Sets the digital output to high impedance (HiZ) mode.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        """
        _ = self.do(board, net)  # Ensure component is registered to shutdown
        self._test_device_manager.do_action(
            action.HiZDo(), self._map_to_hil_device_con(board, net)
        )

    def do(self, board: str, net: str) -> component.DO:
        """
        Create a DO component which has shortcuts to the set and HiZ functions.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        :return: The corresponding DO component
        """
        comp = component.DO(
            set_fn=lambda value: self.set_do(board, net, value),
            hiZ_fn=lambda: self.hiZ_do(board, net),
        )
        self._shutdown_components[net_map.BoardNet(board, net)] = comp
        return comp

    # DI ------------------------------------------------------------------------------#
    def get_di(self, board: str, net: str) -> bool:
        """
        Gets the digital input value.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        :return: The digital input value
        """
        return self._test_device_manager.do_action(
            action.GetDi(), self._map_to_hil_device_con(board, net)
        )

    def di(self, board: str, net: str) -> component.DI:
        """
        Create a DI component which has shortcuts to the get function.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        :return: The corresponding DI component
        """
        return component.DI(get_fn=lambda: self.get_di(board, net))

    # AO ------------------------------------------------------------------------------#
    def set_ao(self, board: str, net: str, value: float) -> None:
        """
        Sets the analog output value.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        :param value: The value to set the analog output to in volts
        """
        _ = self.ao(board, net)  # Ensure component is registered to shutdown
        self._test_device_manager.do_action(
            action.SetAo(value), self._map_to_hil_device_con(board, net)
        )

    def hiZ_ao(self, board: str, net: str) -> None:
        """
        Sets the analog output to high impedance (HiZ) mode.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        """
        _ = self.ao(board, net)  # Ensure component is registered to shutdown
        self._test_device_manager.do_action(
            action.HiZAo(), self._map_to_hil_device_con(board, net)
        )

    def ao(self, board: str, net: str) -> component.AO:
        """
        Create an AO component which has shortcuts to the set and HiZ functions.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        :return: The corresponding AO component
        """
        comp = component.AO(
            set_fn=lambda value: self.set_ao(board, net, value),
            hiZ_fn=lambda: self.hiZ_ao(board, net),
        )
        self._shutdown_components[net_map.BoardNet(board, net)] = comp
        return comp

    # AI ------------------------------------------------------------------------------#
    def get_ai(self, board: str, net: str) -> float:
        """
        Gets the analog input value.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        :return: The analog input value in volts.
        """
        return self._test_device_manager.do_action(
            action.GetAi(), self._map_to_hil_device_con(board, net)
        )

    def ai(self, board: str, net: str) -> component.AI:
        """
        Create an AI component which has shortcuts to the get function.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        """
        return component.AI(get_fn=lambda: self.get_ai(board, net))

    # POT -----------------------------------------------------------------------------#
    def set_pot(self, board: str, net: str, value: float) -> None:
        """
        Sets the potentiometer value.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        :param value: The value to set the potentiometer to in ohms
        """
        self._test_device_manager.do_action(
            action.SetPot(value), self._map_to_hil_device_con(board, net)
        )

    def pot(self, board: str, net: str) -> component.POT:
        """
        Create a POT component which has shortcuts to the set function.

        :param board: The name of the board (DUT board or HIL device)
        :param net: The name of the net (DUT net name or HIL device port)
        :return: The corresponding POT component
        """
        return component.POT(set_fn=lambda value: self.set_pot(board, net, value))

    # CAN -----------------------------------------------------------------------------#
    def send_can(
        self, hil_board: str, can_bus: str, signal: str | int, data: dict
    ) -> None:
        """
        Send a CAN message out from a HIL device/can bus.

        :param hil_board: The name of the HIL board
        :param can_bus: The name of the CAN bus (ex: 'VCAN')
        :param signal: The signal identifier or message id
        :param data: The data to send. Will be encoded to raw bytes
        """
        match self._can_dbc:
            case None:
                raise hil_errors.ConfigurationError("CAN DBC not configured")
            case can_dbc:
                self._test_device_manager.do_action(
                    action.SendCan(signal, data, can_dbc),
                    self._test_device_manager.maybe_hil_con_from_net(
                        hil_board, can_bus
                    ),
                )

    def get_last_can(
        self, hil_board: str, can_bus: str, signal: Optional[str | int] = None
    ) -> Optional[can_helper.CanMessage]:
        """
        Gets the last received CAN message on a HIL device/can bus.

        :param hil_board: The name of the HIL board
        :param can_bus: The name of the CAN bus (ex: 'VCAN')
        :param signal: The signal identifier or message id. If not specified, the last
                       message for any signal will be returned.
        :return: The last received CAN message or None if not found
        """
        match self._can_dbc:
            case None:
                raise hil_errors.ConfigurationError("CAN DBC not configured")
            case can_dbc:
                return self._test_device_manager.do_action(
                    action.GetLastCan(signal, can_dbc),
                    self._test_device_manager.maybe_hil_con_from_net(
                        hil_board, can_bus
                    ),
                )

    def get_all_can(
        self, hil_board: str, can_bus: str, signal: Optional[str | int] = None
    ) -> list[can_helper.CanMessage]:
        """
        Gets all received CAN messages on a HIL device/can bus.

        :param hil_board: The name of the HIL board
        :param can_bus: The name of the CAN bus (ex: 'VCAN')
        :param signal: The signal identifier or message id. If not specified, all
                       messages for any signal will be returned.
        :return: A list of all received CAN messages
        """
        match self._can_dbc:
            case None:
                raise hil_errors.ConfigurationError("CAN DBC not configured")
            case can_dbc:
                return self._test_device_manager.do_action(
                    action.GetAllCan(signal, can_dbc),
                    self._test_device_manager.maybe_hil_con_from_net(
                        hil_board, can_bus
                    ),
                )

    def clear_can(
        self, hil_board: str, can_bus: str, signal: Optional[str | int] = None
    ) -> None:
        """
        Clears the received CAN messages on a HIL device/can bus.

        :param hil_board: The name of the HIL board
        :param can_bus: The name of the CAN bus (ex: 'VCAN')
        :param signal: The signal identifier or message id. If not specified, all
                       messages for any signal will be cleared.
        """
        match self._can_dbc:
            case None:
                raise hil_errors.ConfigurationError("CAN DBC not configured")
            case can_dbc:
                self._test_device_manager.do_action(
                    action.ClearCan(signal, can_dbc),
                    self._test_device_manager.maybe_hil_con_from_net(
                        hil_board, can_bus
                    ),
                )

    def can(self, hil_board: str, can_bus: str) -> component.CAN:
        """
        Gets the CAN component for a specific HIL board and CAN bus which has shortcuts
        to the send, get last, get all, and clear functions.

        :param hil_board: The name of the HIL board
        :param can_bus: The name of the CAN bus (ex: 'VCAN')
        :return: The corresponding CAN component
        """
        return component.CAN(
            lambda signal, data: self.send_can(hil_board, can_bus, signal, data),
            lambda signal: self.get_last_can(hil_board, can_bus, signal),
            lambda signal: self.get_all_can(hil_board, can_bus, signal),
            lambda signal: self.clear_can(hil_board, can_bus, signal),
        )
