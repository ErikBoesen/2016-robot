import wpilib

from robotpy_ext.common_drivers import navx, distance_sensors
from networktables import NetworkTable
from networktables.util import ntproperty
from common import driveEncoders
from . import winch
import math

# Define constants. This way if we need to change something we don't have to change it 50 times.
ENCODER_ROTATION = 1023
WHEEL_DIAMETER = 7.639

class Drive:
    """
        The sole interaction between the robot and its driving system
        occurs here. Anything that wants to drive the robot must go
        through this class.
    """
    robot_drive = wpilib.RobotDrive
    navX = navx.AHRS
    rf_encoder = driveEncoders.DriveEncoders
    lf_encoder = driveEncoders.DriveEncoders
    ultrasonic = wpilib.AnalogInput
    sd = NetworkTable
    back_sensor = distance_sensors.SharpIRGP2Y0A41SK0F
    winch = winch.Winch

    target_angle = ntproperty('/components/autoaim/target_angle', 0)
    enable_camera = ntproperty('/camera/enabled', False)
    align_angle_nt = ntproperty('/components/drive/align_angle', 0)


    def __init__(self):
        self.sd = NetworkTable.getTable('/SmartDashboard')
        self.angle_P = self.sd.getAutoUpdateValue('Drive/Angle_P', .055)
        self.angle_I = self.sd.getAutoUpdateValue('Drive/Angle_I', 0)
        self.drive_constant = self.sd.getAutoUpdateValue('Drive/Drive_Constant', .0001)
        self.rotate_max = self.sd.getAutoUpdateValue('Drive/Max Gyro Rotate Speed', .37)

        self.enabled = False
        self.align_angle = None
        self.align_print_timer = wpilib.Timer()
        self.align_print_timer.start()

    def on_enable(self):
        """
            Constructor.

            :param robotDrive: a `wpilib.RobotDrive` object
            :type rf_encoder: DriveEncoders()
            :type lf_encoder: DriveEncoders()

        """

        # Hack for one-time initialization because magicbot doesn't support it
        if not self.enabled:
            nt = NetworkTable.getTable('components/autoaim')
            nt.addTableListener(self._align_angle_updated, True, 'target_angle')

        self.isTheRobotBackwards = False
        self.iErr = 0
        # set defaults here
        self.y = 0
        self.rotation = 0
        self.squaredInputs = False

        self.halfRotation = 1

        self.gyro_enabled = True

        self.align_angle = None

    # Verb functions -- these functions do NOT talk to motors directly. This
    # allows multiple callers in the loop to call our functions without
    # conflicts.

    def move(self, y, rotation, squaredInputs=False):
        """
            Causes the robot to move

            :param x: The speed that the robot should drive in the X direction. 1 is right [-1.0..1.0]
            :param y: The speed that the robot should drive in the Y direction. -1 is forward. [-1.0..1.0]
            :param rotation:  The rate of rotation for the robot that is completely independent of the translation. 1 is rotate to the right [-1.0..1.0]
            :param squaredInputs: If True, the x and y values will be squared, allowing for more gradual speed.
        """
        self.y = max(min(y, 1), -1)
        self.rotation = max(min(1.0, rotation), -1)
        self.squaredInputs = squaredInputs


    def set_gyro_enabled(self, value):
        """
            Enables the gyro
            :param value: Whether or not the gyro is enabled
            :type value: Boolean
        """
        self.gyro_enabled = value

    def return_gyro_angle(self):
        return self.navX.getYaw()

    def reset_gyro_angle(self):
        self.navX.reset()

    def set_angle_constant(self, constant):
        self.angle_constant = constant

    def reset_drive_encoders(self):
        self.lf_encoder.zero()
        self.rf_encoder.zero()


    def return_drive_encoder_position(self):
        return self.lf_encoder.get()

    def _get_inches_to_ticks(self, inches):

        gear_ratio = 50 / 12
        target_position = (gear_ratio * ENCODER_ROTATION * inches) / (math.pi*WHEEL_DIAMETER)
        return target_position

    def drive_distance(self, inches, max_speed=.9):

        return self.encoder_drive(self._get_inches_to_ticks(inches), max_speed)

    def encoder_drive(self, target_position, max_speed):
        target_offset = target_position - self.return_drive_encoder_position()

        if abs(target_offset)> 1000:
            self.y = target_offset * self.drive_constant.value
            self.y = max(min(max_speed, self.y), -max_speed)
            return False
        return True


    def angle_rotation(self, target_angle):
        """
            Adjusts the robot so that it points at a particular angle. Returns True
            if the robot is near the target angle, False otherwise

            :param target_angle: Angle to point at, in degrees

            :returns: True if near angle, False if gyro is not enabled or not within 1º of target
        """
        if not self.gyro_enabled:
            return False

        angleOffset = target_angle - self.return_gyro_angle()
        if abs(angleOffset) > 3:
            self.iErr += angleOffset
            self.rotation = angleOffset * self.angle_P.value + self.angle_I.value * self.iErr
            self.rotation = max(min(self.rotate_max.value, self.rotation), -self.rotate_max.value)

            return False
        self.iErr = 0
        return True

    def enable_camera_tracking(self):
        self.enable_camera = True

    def disable_camera_tracking(self):
        self.enable_camera = False
        self.align_angle = None
        self.align_angle_nt = 0

    def align_to_tower(self):
        if self.align_angle is not None:
            return self.angle_rotation(self.align_angle)
        else:
            return False

    def _align_angle_updated(self, source, key, value, isNew):
        self.align_angle = value + self.return_gyro_angle()
        self.align_angle_nt = self.align_angle

    def wall_goto(self):
        y = (self.back_sensor.getDistance() - 16.0)/35
        y = max(min(.6, y), -.6)

        self.y = y
        return y

    def set_direction(self, direction):
        self.isTheRobotBackwards = bool(direction)

    def switch_direction(self):
        self.isTheRobotBackwards = not self.isTheRobotBackwards

    def halveRotation(self):
        self.halfRotation = .5

    def normalRotation(self):
        self.halfRotation = 1

    def execute(self):
        """Actually makes the robot drive"""
        backwards = -1 if self.isTheRobotBackwards else 1

        if(self.winch.isExtended and self.isTheRobotBackwards):
            self.robot_drive.arcadeDrive(-self.y, -self.rotation / 2, self.squaredInputs)
        else:
            self.robot_drive.arcadeDrive(backwards * self.y, -self.rotation * self.halfRotation, self.squaredInputs)


        # by default, the robot shouldn't move
        self.y = 0
        self.rotation = 0
        self.update_sd()

    def update_sd(self):
        self.sd.putValue('Drive/NavX | Yaw', self. navX.getYaw())
        self.sd.putValue('Drive/Encoder', self.return_drive_encoder_position())
        self.sd.putValue('Drive/backCamera', self.isTheRobotBackwards)
        self.sd.putValue('Drive/Ultrasonic', self.ultrasonic.getVoltage())