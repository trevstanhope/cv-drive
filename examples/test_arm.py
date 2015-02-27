#!/usr/bin/env python
"""
MOTOR ATTRIBUTES
    CURRENT: 1.7A (Max), 0.26 (Min)
    TORQUE: 777
    ACCELERATION: 600000 1/16th steps/sec^2 (Max)
    VELOCITY: 250000 (Max)
"""

__author__ = 'Trevor Stanhope'
__version__ = '0.1'
__date__ = 'Nov 4 2014'

# Imports
from ctypes import *
import sys
from time import sleep
from Phidgets.PhidgetException import PhidgetErrorCodes, PhidgetException
from Phidgets.Events.Events import AttachEventArgs, DetachEventArgs, ErrorEventArgs, InputChangeEventArgs, CurrentChangeEventArgs, StepperPositionChangeEventArgs, VelocityChangeEventArgs
from Phidgets.Devices.Stepper import Stepper

class Agrivision_Arm:
    
    def __init__(self, acceleration=30000, velocity=30000, current=4.0, position=50000):
        try:
            self.stepper = Stepper()
        except RuntimeError as e:
            print("Runtime Exception: %s" % e.details)
        try:
            self.stepper.setOnAttachHandler(self.StepperAttached)
            self.stepper.setOnDetachHandler(self.StepperDetached)
            self.stepper.setOnErrorhandler(self.StepperError)
            self.stepper.setOnCurrentChangeHandler(self.StepperCurrentChanged)
            self.stepper.setOnInputChangeHandler(self.StepperInputChanged)
            self.stepper.setOnPositionChangeHandler(self.StepperPositionChanged)
            self.stepper.setOnVelocityChangeHandler(self.StepperVelocityChanged)
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))

        try:
            self.stepper.openPhidget()
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))
            
        print("Waiting for attach....")
        try:
            self.stepper.waitForAttach(10000)
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))
            try:
                self.stepper.closePhidget()
            except PhidgetException as e:
                print("Phidget Exception %i: %s" % (e.code, e.details))
        self.SetParameters(acceleration, velocity, current, position)
    
    def SetParameters(self, acceleration=30000, velocity=30000, current=4.0, position=50000):
        try:
            self.stepper.setCurrentPosition(0, 50000)
            self.stepper.setEngaged(0, True) #! INTERESTING
            self.stepper.setAcceleration(0, acceleration) #! INTERESTING
            self.stepper.setVelocityLimit(0, velocity) #! INTERESTING
            self.stepper.setCurrentLimit(0, current) #! INTERESTING
            sleep(2)
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))
    
    ## PID STYLE CONTROL SYSTEM
    def AdjustPosition(self, position):
        try:
            print("Will now move to position %d..." % position)
            self.stepper.setTargetPosition(0, position)
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))
    
    def close(self):
        try:
            self.stepper.setEngaged(0, False)
            sleep(1)
            self.stepper.closePhidget()
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))
             
    def DisplayDeviceInfo(self):
        print("%8s, %30s, %10d, %8d" % (stepper.isAttached(), stepper.getDeviceName(), stepper.getSerialNum(), stepper.getDeviceVersion()))
        print("Number of Motors: %i" % (stepper.getMotorCount()))

    def StepperAttached(self, e):
        attached = e.device
        print("Stepper %i Attached!" % (attached.getSerialNum()))

    def StepperDetached(self, e):
        detached = e.device
        print("Stepper %i Detached!" % (detached.getSerialNum()))

    def StepperError(self, e):
        try:
            source = e.device
            print("Stepper %i: Phidget Error %i: %s" % (source.getSerialNum(), e.eCode, e.description))
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))

    def StepperCurrentChanged(self, e):
        source = e.device
        print("Stepper %i: Motor %i -- Current Draw: %6f" % (source.getSerialNum(), e.index, e.current))

    def StepperInputChanged(self, e):
        source = e.device
        print("Stepper %i: Input %i -- State: %s" % (source.getSerialNum(), e.index, e.state))

    def StepperPositionChanged(self, e):
        source = e.device
        print("Stepper %i: Motor %i -- Position: %f" % (source.getSerialNum(), e.index, e.position))

    def StepperVelocityChanged(self, e):
        source = e.device
        print("Stepper %i: Motor %i -- Velocity: %f" % (source.getSerialNum(), e.index, e.velocity))

if __name__ == '__main__':
    try:
        arm = Agrivision_Arm(acceleration=30000, velocity=30000, current=4.0, position=50000)
        arm.AdjustPosition(0)
        sleep(3)
        arm.AdjustPosition(100000)
        sleep(3)
        arm.close()
    except Exception:
        arm.close()
