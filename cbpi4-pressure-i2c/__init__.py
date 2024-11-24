
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
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_tca9548a


logger = logging.getLogger(__name__)



@parameters([Property.Select(label="Socket", options=[0,1,2,3,4,5,6,7], description="Sensor socket"),
             Property.Select(label="Unit", options=["Bar","PSI"], description="Pressure Unit"),
             Property.Number(label="Max PSI",configurable = True, default_value = 80, description="Sensor Max PSI (Default is 80)"),
             Property.Number(label="Offset",configurable = True, default_value = 0, description="Sensor Offset (Default is 0)"),
             Property.Select(label="Interval", options=[1,5,10,30,60], description="Interval in Seconds")])
class PressureSensori2c(CBPiSensor):
    
    def __init__(self, cbpi, id, props):
        super(PressureSensori2c, self).__init__(cbpi, id, props)
        print("Init Pressure Sensor i2c Start")
        global scale, calc_offset, chan
        self.value = 0
        offset2 = 0.527
        voltage_min = 0.527
        voltage_max = 4.5

        socket_nr = int(self.props.get("Socket", 0))

        analog_pin = socket_nr
        ads_chip = 0
        if socket_nr > 4:
            analog_pin = socket_nr - 4
            ads_chip = 1

        psi_max = int(self.props.get("Max PSI", 80))

        scale = psi_max/(voltage_max - voltage_min)
        #print(scale)
        t = voltage_max * scale
        #print(t)
        calc_offset = psi_max - t
        #print(offset)

        i2c = busio.I2C(board.SCL, board.SDA)

        # Create the TCA9548A object and give it the I2C bus
        tca = adafruit_tca9548a.TCA9548A(i2c)

        chan = None

        # Create the ADS object and specify the gain
        try:
            ads = ADS.ADS1115(tca[ads_chip])
            ads.gain = 1
            chan = AnalogIn(ads, analog_pin)
        except Exception as e:
            self.cbpi.notify("Pressure Sensor Init Error","Cant read from input, ADS: {}, Pin: {}, Error: {}".format(ads_chip, analog_pin, e), NotificationType.ERROR)
            return

        #ads = ADS.ADS1115(i2c)
        #chan = AnalogIn(ads, ADS.P0)
        print("Init Pressure Sensor i2c Done")

    async def run(self):
        while self.running is True:
            global chan, calc_offset, scale
            interval = int(self.props.get("Interval",1))
            offset = int(self.props.get("Offset",0))
            unit = self.props.get("Unit","Bar")
            #self.value = random.randint(0,50)
            #self.push_update(self.value)
            
            psi = (scale * chan.voltage) + calc_offset

            if unit == "PSI":
                self.value = psi + offset
            if unit == "Bar":
                self.value = round(psi / 14.5038, 3) + offset
            
            #print(f"MQ-135 Voltage: {chan.voltage}V , {chan.value}, {P}, {psi} PSI, {bar} BAR")
            #print("RUN")
            self.push_update(self.value)
            await asyncio.sleep(interval)
    
    def get_state(self):
        return dict(value=self.value)

def setup(cbpi):
    #cbpi.plugin.register("MyCustomActor", CustomActor)
    cbpi.plugin.register("Pressure Sensor i2c", PressureSensori2c)
    #cbpi.plugin.register("MyustomWebExtension", CustomWebExtension)
    pass
