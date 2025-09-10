from typing import Callable, Optional

from . import can_helper


# Shutdownable component interface ----------------------------------------------------#
class ShutdownableComponent:
    """Interface for components that need to be 'shutdown' when HIL is stopped"""

    def shutdown(self) -> None:
        raise NotImplementedError()


# DO ----------------------------------------------------------------------------------#
class DO(ShutdownableComponent):
    """Digital Output"""

    def __init__(self, set_fn: Callable[[bool], None], hiZ_fn: Callable[[], None]):
        """
        :param set_fn: Function to set the digital output value
        :param hiZ_fn: Function to set the digital output to high impedance (HiZ)
        """
        self._set_fn: Callable[[bool], None] = set_fn
        self._hiZ_fn: Callable[[], None] = hiZ_fn

    def set(self, value: bool) -> None:
        """
        Sets the digital output value.

        :param value: The value to set the digital output to (low = false, high = true)
        """
        self._set_fn(value)

    def hiZ(self) -> None:
        """
        Sets the digital output to high impedance (HiZ) mode.
        """
        self._hiZ_fn()

    def shutdown(self) -> None:
        """
        Shuts down the digital output by setting it to high impedance (HiZ) mode.
        """
        self._hiZ_fn()


# DI ----------------------------------------------------------------------------------#
class DI:
    """Digital Input"""

    def __init__(self, get_fn: Callable[[], bool]):
        """
        :param get_fn: Function to get the digital input value
        """
        self._get_fn: Callable[[], bool] = get_fn

    def get(self) -> bool:
        """
        Gets the digital input value.

        :return: The digital input value
        """
        return self._get_fn()


# AO ----------------------------------------------------------------------------------#
class AO(ShutdownableComponent):
    """Analog Output"""

    def __init__(self, set_fn: Callable[[float], None], hiZ_fn: Callable[[], None]):
        """
        :param set_fn: Function to set the analog output value
        :param hiZ_fn: Function to set the analog output to high impedance (HiZ)
        """
        self._set_fn: Callable[[float], None] = set_fn
        self._hiZ_fn: Callable[[], None] = hiZ_fn

    def set(self, value: float) -> None:
        """
        Sets the analog output value.

        :param value: The value to set the analog output to in volts
        """
        self._set_fn(value)

    def hiZ(self) -> None:
        """
        Sets the analog output to high impedance (HiZ) mode.
        """
        self._hiZ_fn()

    def shutdown(self) -> None:
        """
        Shuts down the analog output by setting it to high impedance (HiZ) mode.
        """
        self._hiZ_fn()


# AI ----------------------------------------------------------------------------------#
class AI:
    """Analog Input"""

    def __init__(self, get_fn: Callable[[], float]):
        """
        :param get_fn: Function to get the analog input value
        """
        self._get_fn: Callable[[], float] = get_fn

    def get(self) -> float:
        """
        Gets the analog input value.

        :return: The analog input value in volts.
        """
        return self._get_fn()


# POT ---------------------------------------------------------------------------------#
class POT:
    """Potentiometer"""

    def __init__(self, set_fn: Callable[[float], None]):
        """
        :param set_fn: Function to set the potentiometer value
        """
        self._set_fn: Callable[[float], None] = set_fn

    def set(self, value: float) -> None:
        """
        Sets the potentiometer value.

        :param value: The value to set the potentiometer to in ohms
        """
        self._set_fn(value)


# CAN ---------------------------------------------------------------------------------#
class CAN:
    """CAN Bus Interface"""

    def __init__(
        self,
        send_fn: Callable[[str | int, dict], None],
        get_last_fn: Callable[[Optional[str | int]], Optional[can_helper.CanMessage]],
        get_all_fn: Callable[[Optional[str | int]], list[can_helper.CanMessage]],
        clear_fn: Callable[[Optional[str | int]], None],
    ):
        """
        :param send_fn: Function to send CAN messages
        :param get_last_fn: Function to get the last received CAN message
        :param get_all_fn: Function to get all received CAN messages
        :param clear_fn: Function to clear CAN messages
        """
        self._send_fn: Callable[[str | int, dict], None] = send_fn
        self._get_last_fn: Callable[[Optional[str | int]], Optional[dict]] = get_last_fn
        self._get_all_fn: Callable[[Optional[str | int]], list[dict]] = get_all_fn
        self._clear_fn: Callable[[Optional[str | int]], None] = clear_fn

    def send(self, signal: str | int, data: dict) -> None:
        """
        Sends a CAN message.

        :param signal: The signal identifier or message id
        :param data: The data to send. Will later be encoded to raw bytes
        """
        self._send_fn(signal, data)

    def get_last(
        self, signal: Optional[str | int] = None
    ) -> Optional[can_helper.CanMessage]:
        """
        Gets the last received CAN message.

        :param signal: The signal identifier or message id. If not specified, the last
                       message for any signal will be returned.
        :return: The last received CAN message or None if not found
        """
        return self._get_last_fn(signal)

    def get_all(
        self, signal: Optional[str | int] = None
    ) -> list[can_helper.CanMessage]:
        """
        Gets all received CAN messages.

        :param signal: The signal identifier or message id. If not specified, all
                       messages for any signal will be returned.
        :return: A list of all received CAN messages
        """
        return self._get_all_fn(signal)

    def clear(self, signal: Optional[str | int] = None) -> None:
        """
        Clears the received CAN messages.

        :param signal: The signal identifier or message id. If not specified, all
                       messages for any signal will be cleared.
        """
        self._clear_fn(signal)
