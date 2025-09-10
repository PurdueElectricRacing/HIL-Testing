from typing import Optional, Union

import cantools.database.can.database as cantools_db


# Union type representing all possible actions ----------------------------------------#
ActionType = Union[
    "SetDo",
    "HiZDo",
    "GetDi",
    "SetAo",
    "HiZAo",
    "GetAi",
    "SetPot",
    "SendCan",
    "GetLastCan",
    "GetAllCan",
    "ClearCan",
]


# DO actions --------------------------------------------------------------------------#
class SetDo:
    """Action to set a digital output"""

    __match_args__ = ("value",)

    def __init__(self, value: bool):
        """
        :param value: The value to set the digital output to (low = false, high = true)
        """
        self.value: bool = value


class HiZDo:
    """Action to set a digital output to high impedance (HiZ)"""

    def __init__(self):
        pass


# DI actions --------------------------------------------------------------------------#
class GetDi:
    """Action to get a digital input"""

    def __init__(self):
        pass


# AO actions --------------------------------------------------------------------------#
class SetAo:
    """Action to set an analog output"""

    __match_args__ = ("value",)

    def __init__(self, value: float):
        """
        :param value: The value (in volts) to set the analog output to
        """
        self.value: float = value


class HiZAo:
    """Action to set an analog output to high impedance (HiZ)"""

    def __init__(self):
        pass


class GetAi:
    """Action to get an analog input"""

    def __init__(self):
        pass


# POT actions -------------------------------------------------------------------------#
class SetPot:
    """Action to set a potentiometer"""

    __match_args__ = ("value",)

    def __init__(self, value: float):
        """
        :param value: The value (in ohms) to set the potentiometer to
        """
        self.value: float = value


# CAN actions -------------------------------------------------------------------------#
class SendCan:
    """Action to send a CAN message"""

    __match_args__ = ("signal", "data", "can_dbc")

    def __init__(self, signal: str | int, data: dict, can_dbc: cantools_db.Database):
        """
        :param signal: The signal name or message ID to send
        :param data: The data to include in the CAN message. Will be encoded to bytes
        :param can_dbc: The CAN database to use for encoding the message
        """
        self.signal: str | int = signal
        self.data: dict = data
        self.can_dbc: cantools_db.Database = can_dbc


class GetLastCan:
    """Action to get the last received CAN message"""

    __match_args__ = ("signal", "can_dbc")

    def __init__(self, signal: Optional[str | int], can_dbc: cantools_db.Database):
        """
        :param signal: The signal name or message ID to get. If not specified, the last
                       message will be returned (if any) regardless of the signal/id
        :param can_dbc: The CAN database to use for decoding the message
        """
        self.signal: Optional[str | int] = signal
        self.can_dbc: cantools_db.Database = can_dbc


class GetAllCan:
    """Action to get all received CAN messages"""

    __match_args__ = ("signal", "can_dbc")

    def __init__(self, signal: Optional[str | int], can_dbc: cantools_db.Database):
        """
        :param signal: The signal name or message ID to get. If not specified, all
                       messages will be returned (if any) regardless of the signal/id
        :param can_dbc: The CAN database to use for decoding the messages
        """
        self.signal: Optional[str | int] = signal
        self.can_dbc: cantools_db.Database = can_dbc


class ClearCan:
    """Action to clear a CAN message"""

    __match_args__ = ("signal", "can_dbc")

    def __init__(self, signal: Optional[str | int], can_dbc: cantools_db.Database):
        """
        :param signal: The signal name or message ID to clear. If not specified, all
                       messages will be cleared (if any) regardless of the signal/id
        :param can_dbc: The CAN database to use for decoding the messages
        """
        self.signal: Optional[str | int] = signal
        self.can_dbc: cantools_db.Database = can_dbc
