class SerialError(Exception):
    """
    Error representing something going wrong relating to the serial
    connection/commands/responses
    """

    pass


class EngineError(Exception):
    """
    Error representing something going wrong relating to the HIL2 engine
    """

    pass


class ConfigurationError(Exception):
    """
    Error representing something wrong with the configuration
    """

    pass


class ConnectionError(Exception):
    """
    Error representing something going wrong when trying to map between HIL and DUT
    connections
    """

    pass


class RangeError(Exception):
    """
    Error representing a value is out of range
    """

    pass
