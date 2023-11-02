
from components.component import Component

class SdcNode(Component):

    def __init__(self, config, hil):
        super(SdcNode, self).__init__(config, hil)
        # if (_mode != Component.EMUL): print("INVALID SDC COMPONENT MODE")
        self.state = 0

        # TODO: register output with emulator
        em_src = config['emulation_source']
        self.em = hil.get_emulator(em_src['device'])
        self.em.register_output(em_src['port'], em_src['type'])

    # @state.setter
    # def state(self, s):
    #     # TODO: actually trigger pin
    #     self.state = s



