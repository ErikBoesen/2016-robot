from magicbot import StateMachine, timed_state, state
from components import light, intake as Intake

class LightSwitch(StateMachine):
    light = light.Light
    intake = Intake.Arm

    def on_enable(self):
        self.counter = 0

    def switch(self):
        self.counter = 0
        self.engage()

    @state(first=True, must_finish=True)
    def firstState(self):
        if self.light.on:
            self.next_state('off')
        else:
            self.light.turnOn()
            self.done()

    @timed_state(duration = .25, next_state='on', must_finish = True)
    def off(self, initial_call):
        if initial_call:
            self.counter += 1

        self.light.turnOff()
        if self.counter > 2:
            self.done()

    @timed_state(duration = .25, next_state = 'off', must_finish = True)
    def on(self):
        self.light.turnOn()
