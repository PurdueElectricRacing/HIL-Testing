from components.component import Component

class BrakeTransducer(Component):

    def __init__(self, config, hil):
        super(BrakeTransducer, self).__init__(config, hil)

        self.vcc = 5.0
        self.min_out = self.vcc * 0.1
        self.max_out = self.vcc * 0.9
        self.delta = self.max_out - self.min_out

    def set_percent(self, p):
        if (p > 1.0): p = 1.0
        if (p < 0.0): p = 0.0
        self.state = self.min_out + self.delta * p

    def set_short_gnd(self):
        self.state = 0.0

    def set_short_vcc(self):
        self.state = self.vcc

