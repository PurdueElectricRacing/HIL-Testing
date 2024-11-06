from collections.abc import Callable
import hil.utils as utils
# from hil.hil import HIL

class Component():
    """ 
    Generalized component of system 
    Can operate in NC, Measure, Emulate, or Hardware modes
    When in measurement or emulation, a source must be specified.
    """

    def __init__(self, name: str, hil_con: tuple[str, str], mode: str, hil):
    # def __init__(self, name: str, hil_con: tuple[str, str], mode: str, hil: HIL):
        self.name: str = name

        self._state = 0
        self.inv_meas: bool = False
        self.inv_emul: bool = False
        self.read_func: Callable[[], int] = None
        self.write_func: Callable[[int], None] = None
        self.hiZ_func: Callable[[], None] = None

        # TODO: allow both measure and emulation source

        # if "measure_source" in config:
        #     me_src = config['measure_source']
        #     self.me = hil.get_hil_device(me_src['device'])
        #     if "inv" in me_src:
        #         self.inv_meas = me_src["inv"]
            
        #     if (me_src['mode'] == "DI"):
        #         self.read_port = self.me.get_port_number(me_src['port'], me_src['mode'])
        #         if self.inv_meas:
        #             self.read_func = lambda : not self.me.read_gpio(self.read_port)
        #         else:
        #             self.read_func = lambda : self.me.read_gpio(self.read_port)
        #     elif (me_src['mode'] == "AI"):
        #         self.read_port = self.me.get_port_number(me_src['port'], me_src['mode'])
        #         self.read_func = lambda : self.me.read_analog(self.read_port)
        #     else:
        #         utils.log_error(f"Unrecognized measure mode {me_src['mode']} for component {self.name}")

        # if "emulation_source" in config:
        #     em_src = config['emulation_source']
        #     self.em = hil.get_hil_device(em_src['device'])

        #     if "inv" in em_src:
        #         self.inv_emul = em_src["inv"]

        #     if (em_src['mode'] == "DO"):
        #         self.write_port = self.em.get_port_number(em_src['port'], em_src['mode'])
        #         if self.inv_emul:
        #             self.write_func = lambda s: self.em.write_gpio(self.write_port, not s)
        #         else:
        #             self.write_func = lambda s: self.em.write_gpio(self.write_port, s)
        #         self.state = self._state
        #     elif(em_src['mode'] == "AO"):
        #         self.write_port = self.em.get_port_number(em_src['port'], em_src['mode'])
        #         self.write_func = lambda s: self.em.write_dac(self.write_port, s)
        #     else:
        #         utils.log_error(f"Unrecognized emulation mode {em_src['mode']} for component {self.name}")

        dev = hil.get_hil_device(hil_con[0])
        hil_port_num = dev.get_port_number(hil_con[1], mode)
        if (hil_port_num >= 0):
            print(f"Creating new component '{self.name}' of type {mode} on {hil_con}")
            if (mode == "DI"):
                if self.inv_meas:
                    self.read_func = lambda : not dev.read_gpio(hil_port_num)
                else:
                    self.read_func = lambda : dev.read_gpio(hil_port_num)
            elif (mode == "AI"):
                self.read_func = lambda : dev.read_analog(hil_port_num)
            elif (mode == "DO"):
                if self.inv_emul:
                    self.write_func = lambda s: dev.write_gpio(hil_port_num, not s)
                else:
                    self.write_func = lambda s: dev.write_gpio(hil_port_num, s)
                self.state = self._state
                self.hiZ_func = lambda : dev.read_gpio(hil_port_num)
                # TODO: check if hil port also has DI capability (i.e. relay can't hiZ)
            elif(mode == "AO"):
                self.write_func = lambda s: dev.write_dac(hil_port_num, s)
                self.hiZ_func = lambda : dev.read_gpio(hil_port_num)
            elif(mode == "POT"):
                self.write_func = lambda s: dev.write_pot(hil_port_num, s)
            else:
                utils.log_error(f"Unrecognized emulation/measurement mode {mode} for component {self.name}")
        else:
            utils.log_error(f"Failed to get hil port for component {self.name}")

        self.hil = hil

    @property
    def state(self) -> int:
        if self.read_func:
            self._state = self.read_func()
        elif self.write_func == None:
            utils.log_warning(f"Read from {self.name}, but no measurement source or emulation source was found")
        return self._state

    @state.setter
    def state(self, s: int) -> None:
        if self.read_func == None:
            self._state = s
        if self.write_func:
            self.write_func(s)
        else:
            utils.log_warning(f"Wrote to {self.name}, but no emulation source was found")
    
    def hiZ(self) -> None:
        if (self.hiZ_func):
            self.hiZ_func()
        else:
            utils.log_warning(f"hiZ is not supported for {self.name}")
    
    def shutdown(self) -> None:
        if (self.hiZ_func):
            self.hiZ_func()
        elif self.write_func:
            self.state = 0

