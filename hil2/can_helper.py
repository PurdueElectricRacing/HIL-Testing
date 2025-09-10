from typing import Optional

import os

import cantools.database.can.database as cantools_db


# Helper functions --------------------------------------------------------------------#
def load_can_dbcs(dbc_fpath: str, recursive: bool = False) -> cantools_db.Database:
    """
    Scans a folder (and optionally all subfolders) for DBC files and loads them into a
    single CAN database.

    :param dbc_fpath: The path to the CAN DBC folder
    :param recursive: Whether to search subdirectories recursively (default: False)
    :return: The loaded CAN database
    """
    db = cantools_db.Database()

    if not dbc_fpath or not os.path.isdir(dbc_fpath):
        return db

    if recursive:
        for root, _, files in os.walk(dbc_fpath):
            for file in files:
                if file.endswith(".dbc"):
                    db.add_dbc_file(os.path.join(root, file))
    else:
        for file in os.listdir(dbc_fpath):
            if file.endswith(".dbc"):
                db.add_dbc_file(os.path.join(dbc_fpath, file))

    return db


# CAN Message struct ------------------------------------------------------------------#
class CanMessage:
    """Represents a parsed/decoded CAN message"""

    def __init__(self, signal: str | int, data: dict):
        """
        :param signal: The signal name or message ID
        :param data: The data contained in the CAN message
        """

        self.signal: str | int = signal
        self.data: dict = data


# CAN Message Manager class -----------------------------------------------------------#
class CanMessageManager:
    """Manages a collection of CAN messages"""

    def __init__(self):
        self._messages: list[CanMessage] = []

    def add_multiple(self, messages: list[CanMessage]) -> None:
        """
        :param messages: The list of CAN messages to add
        """
        self._messages.extend(messages)

    def get_last(self, signal: Optional[str | int]) -> Optional[CanMessage]:
        """
        :param signal: The signal name or message ID to get. If None, the last message
                       will be returned (if any) regardless of the signal/id
        :return: The last CAN message with the specified signal, or None if not found
        """
        if signal is None:
            return self._messages[-1] if self._messages else None
        for msg in reversed(self._messages):
            if msg.signal == signal:
                return msg
        return None

    def get_all(self, signal: Optional[str | int] = None) -> list[CanMessage]:
        """
        :param signal: The signal name or message ID to get. If None, all messages will
                       be returned (if any) regardless of the signal/id
        :return: A list of all CAN messages with the specified signal (or all)
        """
        return list(
            filter(lambda msg: signal is None or msg.signal == signal, self._messages)
        )

    def clear(self, signal: Optional[str | int] = None) -> None:
        """
        :param signal: The signal name or message ID to clear. If None, all messages
                       will be cleared (if any) regardless of the signal/id
        """
        if signal is None:
            self._messages.clear()
        else:
            self._messages = list(
                filter(lambda msg: msg.signal != signal, self._messages)
            )
