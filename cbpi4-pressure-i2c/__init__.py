
# -*- coding: utf-8 -*-
import os
from aiohttp import web
import logging
from unittest.mock import MagicMock, patch
import asyncio
import random
from cbpi.api import *
from cbpi.api.dataclasses import NotificationType

import time
import board
import busio

from adafruit_ads1x15 import ADS1115, AnalogIn, ads1x15

import numpy as np


logger = logging.getLogger(__name__)


def add_calibration_point(x, y, field):
    if isinstance(field, str) and field:
        x1, y1 = field.split("=")
        x = np.append(x, float(x1))
        y = np.append(y, float(y1))
    return x, y

def calibrate(value, equation):
    return eval(equation)


@parameters([Property.Select("Channel", options=["0", "1", "2", "3"], default_value = 0,
                            description="Select hardware channel-number of ADS1x15 (Default is 0x48)"),
             Property.Select("Address", options=["0x48", "0x49", "0x4A", "0x4B"], default_value = "0x48",
                             description="Select hardware address-number of ADS1x15 (Default is 0x48)"),
             Property.Number(label="Max PSI",configurable = True, default_value = 80,
                             description="Sensor Max PSI (Default is 80)"),
             Property.Number(label="Min Volt",configurable = True, default_value = 0.5,
                             description="Lowest Volt Value (Default is 0.5)"),
             Property.Number(label="Max Volt",configurable = True, default_value = 4.5,
                             description="Maximum Volt Value (Default is 4.5)"),
             Property.Select("Gain", options=["0.6666", "1", "2", "4", "8", "16"], default_value = "1",
                             description="2/3: +/-6.144V, 1: +/-4.096V, 2: +/-2.048V, 4: +/-1.024V, 8: +/-0.512V, 16: +/-0.256V (Default is 1)"),
             Property.Text(label="Calibration Point 1", configurable=True, default_value="", description="Optional field for calibrating your Tilt. Enter data in the format uncalibrated=actual"),
             Property.Text(label="Calibration Point 2", configurable=True, default_value="", description="Optional field for calibrating your Tilt. Enter data in the format uncalibrated=actual"),
             Property.Text(label="Calibration Point 3", configurable=True, default_value="", description="Optional field for calibrating your Tilt. Enter data in the format uncalibrated=actual")])
class PressureSensori2c(CBPiSensor):
    scale = None
    calc_offset = None
    chan = None
    foo = 23
    offset = 0
    unit = "kPa"

    def __init__(self, cbpi, id, props):
        super(PressureSensori2c, self).__init__(cbpi, id, props)
        print("Init Pressure Sensor i2c Start")

        self.value = 0
        offset2 = 0.527
        #voltage_min = 0.527
        #voltage_max = 4.5
        
        self.calibration_equ = ""
        self.x_cal_1=self.props.get("Calibration Point 1","")
        self.x_cal_2=self.props.get("Calibration Point 2","")
        self.x_cal_3=self.props.get("Calibration Point 3","")
        
        # Load calibration data from plugin
        x = np.empty([0])
        y = np.empty([0])
        x, y = add_calibration_point(x, y, self.x_cal_1)
        x, y = add_calibration_point(x, y, self.x_cal_2)
        x, y = add_calibration_point(x, y, self.x_cal_3)

        # Create calibration equation
        if len(x) < 1:
            self.calibration_equ = "value"
        if len(x) == 1:
            self.calibration_equ = 'value + {0}'.format(y[0] - x[0])
        if len(x) > 1:
            A = np.vstack([x, np.ones(len(x))]).T
            m, c = np.linalg.lstsq(A, y, rcond=None)[0]
            self.calibration_equ = '{0}*value + {1}'.format(m, c)

        socket_nr = int(self.props.get("Socket", 0))
        self.foo = socket_nr
        bar = socket_nr

        psi_max = int(self.props.get("Max PSI", 80))
        channel = int(self.props.get("Channel",0))
        address = int(self.props.get("Address","0x48"), 16)
        self.voltage_max = float(self.props.get("Max Volt",0.5))
        self.voltage_min = float(self.props.get("Min Volt",4.5))
        gain = round(float(self.props.get("Gain",1)),1)
        self.unit = self.cbpi.config.get("PRESSURE_UNIT", "kPa")
        if self.unit is None or self.unit == "" or not self.unit:
            self.unit = "kPa"
            self.cbpi.notify("Pressure Sensor Init Problem","Cant read config value: PRESSURE_UNIT. Unit set to {}".format(self.unit), NotificationType.WARNING)

        self.scale = psi_max/(self.voltage_max - self.voltage_min)
        t = self.voltage_max * self.scale
        self.calc_offset = psi_max - t

        i2c = busio.I2C(board.SCL, board.SDA)

        # Create the ADS object and specify the gain
        try:
            ads = ADS1115(i2c, address=address)
            ads.gain = gain
            self.chan = AnalogIn(ads, channel)
        except Exception as e:
            self.cbpi.notify("Pressure Sensor Init Error","Cant read from input, Address: {}, Pin: {}, Error: {}".format(address, channel, e), NotificationType.ERROR)
            return

        print("Init Pressure Sensor i2c Done")

    async def run(self):
        while self.running is True:
            #self.value = self.value

            try:
                psi = (self.scale * self.chan.voltage) + self.calc_offset
                #psi = 7
                if self.unit == "PSI":
                    self.value = psi #+ self.offset
                if self.unit == "kPa":
                    self.value = round(psi * 6.89476) #+ self.offset

                self.value = calibrate(self.value, self.calibration_equ)
            except Exception as e:
                logger.warning("Error reading voltage: {} {}".format(e, self.foo))
                #await asyncio.sleep(self.interval)
                #continue

            #print(f"MQ-135 Voltage: {chan.voltage}V , {chan.value}, {P}, {psi} PSI, {bar} BAR")
            self.push_update(self.value)
            self.log_data(self.value)

            await asyncio.sleep(2)

    def get_state(self):
        return dict(value=self.value)

def setup(cbpi):
    cbpi.plugin.register("Pressure Sensor i2c", PressureSensori2c)
    pass
