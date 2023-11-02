
class Component():
    """ 
    Generalized component of system 
    Can operate in NC, Measure, Emulate, or Hardware modes
    When in measurement or emulation, a source must be specified.
    """

    class Mode():
        NC   = 0
        MEAS = 1
        EMUL = 2
        HARD = 3

    def __init__(self, config, hil):
        # self.mode = Component.Mode.NC
        self.name = config['name']
        print(f"Created new component {self.name} of type {config['type']}")
        self.hil = hil
