from robotpy_ext.autonomous import state, timed_state
from .GenericAutonomous import LowBar, ChevalDeFrise, Portcullis, Charge, Default
from automations import targetGoal
from components import intake as Intake, drive as Drive
from networktables.networktable import NetworkTable
from networktables.util import ntproperty
from magicbot.magic_tunable import tunable
import math

class ModularAutonomous(LowBar, ChevalDeFrise, Portcullis, Charge, Default):
    MODE_NAME = 'Modular_Autonomous'
    DEFAULT = False

    sd = NetworkTable
    intake = Intake.Arm
    drive = Drive.Drive
    targetGoal = targetGoal.TargetGoal
    present = ntproperty('/components/autoaim/present', False)

    opposite = tunable(120)
    Ramp_Distance = tunable(6)

    def initialize(self):
        LowBar.initialize(self)
        Portcullis.initialize(self)

    @state(first=True)
    def startModularAutonomous(self):
        print(self.sd.getValue('robotDefense', 'Default') + 'Start')
        self.intake.manualZero()
        self.drive.reset_gyro_angle()
        self.next_state(self.sd.getValue('robotDefense', 'LowBar') + 'Start')
        self.position = int(self.sd.getValue('robotPosition', '1'))

    @state
    def transition(self):
        if self.position == 3:
            self.angleConst = 1
        elif self.position == 2 :
            self.angleConst = -1
        self.rotateAngle = math.degrees(math.atan(self.opposite/50)) * self.angleConst
        self.drive_distance = math.sqrt(2500 + self.opposite**2)
        if self.position == 1 or self.position == 4:
            self.next_state('drive_to_wall')
        else:
            self.next_state('rotate')

    @state
    def rotate(self):
        if self.drive.angle_rotation(self.rotateAngle):
            self.drive.reset_drive_encoders()
            self.next_state('drive_to_position')

    @state
    def drive_to_position(self):
        if self.drive.drive_distance(self.drive_distance):
            self.next_state('rotate_back')

    @state
    def rotate_back(self):
        if self.drive.angle_rotation(-45*self.angleConst):
            self.drive.reset_gyro_angle()
            self.drive.enable_camera_tracking()
            self.next_state('rotate_to_align')

    @timed_state(duration=1, next_state='target')
    def rotate_to_align(self, initial_call):
        if initial_call:
            self.drive.reset_gyro_angle()

        if self.drive.align_to_tower():
            self.next_state('target')

    @state
    def target(self):
        self.targetGoal.target()

class BallModularAutonomous(ModularAutonomous):
    MODE_NAME = 'Ball_Modular_Autonomous'
    DEFAULT = False

    sd = NetworkTable
    intake = Intake.Arm
    drive = Drive.Drive

    def initialize(self):
        LowBar.initialize(self)
        Portcullis.initialize(self)

        self.register_sd_var('Drive_Distance', -5)
        self.register_sd_var('Rotate_Angle', 180)
        self.register_sd_var('Collect_Distance', 0.5)

    @state(first=True)
    def startModularAutonomous(self):
        print(self.sd.getValue('robotDefense', 'Default') + 'Start')
        self.intake.manualZero()
        self.drive.reset_gyro_angle()
        self.next_state('drive_to_ball')

    @timed_state(duration = 4, next_state='lower_arms')
    def drive_to_ball(self, initial_call):
        if initial_call:
            self.drive.reset_drive_encoders()
            self.intake.set_arm_middle()

        if self.drive.drive_distance(self.Drive_Distance) and self.intake.on_target():
            self.next_state('collect')

    @state
    def collect(self, initial_call):
        if initial_call:
            self.drive.reset_drive_encoders()

        self.intake.intake()
        if self.drive.drive_distance(self.Collect_Distance):
            self.next_state('back_up')

    @state
    def back_up(self,initial_call):
        if initial_call:
            self.drive.reset_drive_encoders()

        if self.drive.drive_distance(-(self.Collect_Distance+self.Drive_Distance)):
            self.next_state('turn_around')

    @state
    def turn_around(self,initial_call):
        if initial_call:
            self.drive.reset_gyro_angle()

        if self.drive.angle_rotation(self.Rotate_Angle):
            self.next_state(self.sd.getValue('robotDefense', 'LowBar') + 'Start')
            self.position = int(self.sd.getValue('robotPosition', '1'))
            print('test '+(self.sd.getValue('robotDefense', 'LowBar') + 'Start'))
            print('test '+self.sd.getValue('robotPosition', '1'))
