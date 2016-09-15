#!/usr/bin/env python3

import magicbot
import wpilib

from robotpy_ext.control.button_debouncer import ButtonDebouncer
from components import drive, intake, winch, light
from automations import shootBall, portcullis, lightOff, targetGoal
from common import driveEncoders
from networktables.util import ntproperty


from robotpy_ext.common_drivers import navx, distance_sensors

from networktables.networktable import NetworkTable


class MyRobot(magicbot.MagicRobot):
    # Shorten a bunch of things
    targetGoal = targetGoal.TargetGoal
    shootBall = shootBall.ShootBall
    winch = winch.Winch
    light = light.Light
    lightSwitch = lightOff.LightSwitch
    intake = intake.Arm
    drive = drive.Drive

    enable_camera_logging = ntproperty('/camera/logging_enabled', True)
    auto_aim_button = ntproperty('/SmartDashboard/Drive/autoAim', False, writeDefault = False)

    """Create basic components (motor controllers, joysticks, etc.)"""
    def createObjects(self):
        self.joystick1 = wpilib.Joystick(0)
        self.joystick2 = wpilib.Joystick(1)

        self.lf_motor = wpilib.CANTalon(5)
        self.lr_motor = wpilib.CANTalon(10)
        self.rf_motor = wpilib.CANTalon(15)
        self.rr_motor = wpilib.CANTalon(20)

        self.robot_drive = wpilib.RobotDrive(self.lf_motor, self.lr_motor, self.rf_motor, self.rr_motor)

        self.leftArm = wpilib.CANTalon(25)
        self.rightArm = wpilib.CANTalon(30)

        self.leftBall = wpilib.Talon(9)

        self.winchMotor = wpilib.Talon(0)
        self.kickMotor = wpilib.Talon(1)

        self.flashlight = wpilib.Relay(0)
        self.lightTimer = wpilib.Timer()
        self.turningOffState = 0
        self.lastState = False

        self.rf_encoder = driveEncoders.DriveEncoders(self.robot_drive.frontRightMotor, True)
        self.lf_encoder = driveEncoders.DriveEncoders(self.robot_drive.frontLeftMotor)

        self.back_sensor = distance_sensors.SharpIRGP2Y0A41SK0F(0)
        self.ultrasonic = wpilib.AnalogInput(1)

        self.navX = navx.AHRS.create_spi()

        self.sd = NetworkTable.getTable('SmartDashboard')

        self.control_loop_wait_time = 0.025
        self.reverseButton = ButtonDebouncer(self.joystick1, 1)

        self.shoot = ButtonDebouncer(self.joystick2, 1)
        self.raiseButton = ButtonDebouncer(self.joystick2, 3)
        self.lowerButton = ButtonDebouncer(self.joystick2, 2)
        self.lightButton = ButtonDebouncer(self.joystick1, 6)

    def autonomous(self):
        self.drive.reset_gyro_angle()
        magicbot.MagicRobot.autonomous(self)

    def disabledPeriodic(self):
        """Repeat periodically while robot is disabled. Usually emptied. Sometimes used to easily test sensors and other things."""
        pass

    def disabledInit(self):
        """Do once right away when robot is disabled."""
        self.enable_camera_logging = True
        self.drive.disable_camera_tracking()

    def teleopInit(self):
        """Do when teleoperated mode is started."""
        self.drive.reset_drive_encoders()
        self.sd.putValue('startTheTimer', True)
        self.intake.target_position = None
        self.intake.target_index = None

        self.drive.disable_camera_tracking()
        self.enable_camera_logging = False

    def teleopPeriodic(self):
        """Do periodically while robot is in teleoperated mode."""

        self.drive.move(-self.joystick1.getY(), self.joystick2.getX())

        if self.reverseButton.get():
            self.drive.switch_direction()

        if self.joystick2.getRawButton(5):
            self.intake.outtake()
        elif self.joystick2.getRawButton(4):
            self.intake.intake()

        if self.shoot.get():
            self.shootBall.shoot()

        """There's two sets of arm buttons. The first automatically raises and lowers the arm the proper amount, whereas the second will let you manually raise and lower it more precise amounts."""
        if self.raiseButton.get():
            self.intake.raise_arm()
        elif self.lowerButton.get():
            self.intake.lower_arm()

        if self.joystick1.getRawButton(3):
            self.intake.set_manual(-1)
        if self.joystick1.getRawButton(2):
            self.intake.set_manual(1)

        lightButton = False
        uiButton = self.sd.getValue('LightBulb', False)
        if uiButton != self.lastState:
            lightButton = True
        self.lastState = uiButton
        if (self.lightButton.get() or lightButton) and self.turningOffState == 0:
            self.lightSwitch.switch()
        if self.joystick1.getRawButton(5) or self.auto_aim_button:
            self.targetGoal.target()


        if self.joystick1.getRawButton(7):
            self.winch.deploy_winch()
        if self.joystick1.getRawButton(8):
            self.winch.winch()

        if self.joystick1.getRawButton(9) and self.drive.isTheRobotBackwards:
            self.drive.move(.5, 0)

        if not self.ds.isFMSAttached():
            if self.joystick1.getRawButton(10):
                self.drive.angle_rotation(35)
            elif self.joystick1.getRawButton(9): # Could be problematic if robot is backwards
                self.drive.angle_rotation(0)
            elif self.joystick2.getRawButton(10):
                self.drive.enable_camera_tracking()
                self.drive.align_to_tower()

if __name__ == '__main__':
    wpilib.run(MyRobot)
