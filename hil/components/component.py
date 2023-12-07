import utils

class Component():
    """ 
    Generalized component of system 
    Can operate in NC, Measure, Emulate, or Hardware modes
    When in measurement or emulation, a source must be specified.
    """

    def __init__(self, config, hil):
        self.name = config['name']

        self._state = 0
        self.inv_meas = False
        self.inv_emul = False
        self.read_func  = None
        self.write_func = None

        if "measure_source" in config:
            me_src = config['measure_source']
            self.me = hil.get_hil_device(me_src['device'])
            if "inv" in me_src:
                self.inv_meas = me_src["inv"]
            
            if (me_src['mode'] == "DI"):
                self.read_port = self.me.get_port_number(me_src['port'], me_src['mode'])
                if self.inv_meas:
                    self.read_func = lambda : not self.me.read_gpio(self.read_port)
                else:
                    self.read_func = lambda : self.me.read_gpio(self.read_port)
            elif (me_src['mode'] == "AI"):
                self.read_port = self.me.get_port_number(me_src['port'], me_src['mode'])
                self.read_func = lambda : self.me.read_analog(self.read_port)
            else:
                utils.log_error(f"Unrecognized measure mode {me_src['mode']} for component {self.name}")


        if "emulation_source" in config:
            em_src = config['emulation_source']
            self.em = hil.get_hil_device(em_src['device'])

            if "inv" in em_src:
                self.inv_emul = em_src["inv"]

            if (em_src['mode'] == "DO"):
                self.write_port = self.em.get_port_number(em_src['port'], em_src['mode'])
                if self.inv_emul:
                    self.write_func = lambda s: self.em.write_gpio(self.write_port, not s)
                else:
                    self.write_func = lambda s: self.em.write_gpio(self.write_port, s)
                self.state = self._state
            elif(em_src['mode'] == "AO"):
                self.write_port = self.em.get_port_number(em_src['port'], em_src['mode'])
                self.write_func = lambda s: self.em.write_dac(self.write_port, s)
            else:
                utils.log_error(f"Unrecognized emulation mode {em_src['mode']} for component {self.name}")

        #print(f"Created new component {self.name} of type {config['type']}")
        self.hil = hil

    @property
    def state(self):
        if self.read_func:
            self._state = self.read_func()
        elif self.write_func == None:
            utils.log_warning(f"Read from {self.name}, but no measurement source or emulation source was found")
        return self._state

    @state.setter
    def state(self, s):
        if self.read_func == None:
            self._state = s
        if self.write_func:
            self.write_func(s)
        else:
            utils.log_warning(f"Wrote to {self.name}, but no emulation source was found")

    def shutdown(self):
        if self.write_func:
            self.state = 0

