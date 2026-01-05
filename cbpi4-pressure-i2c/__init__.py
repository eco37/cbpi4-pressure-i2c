
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


logger = logging.getLogger(__name__)

@parameters([Property.Select("Channel", options=["0", "1", "2", "3"], default_value = 0,
                            description="Select hardware channel-number of ADS1x15 (Default is 0x48)"),
             Property.Select("Address", options=["0x48", "0x49", "0x4A", "0x4B"], default_value = "0x48",
                             description="Select hardware address-number of ADS1x15 (Default is 0x48)"),
             Property.Number(label="Max PSI",configurable = True, default_value = 80,
                             description="Sensor Max PSI (Default is 80)"),
             Property.Number(label="Offset",configurable = True, default_value = 0,
                             description="Sensor Offset (Default is 0)")])
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
        voltage_min = 0.527
        voltage_max = 4.5

        socket_nr = int(self.props.get("Socket", 0))
        self.foo = socket_nr
        bar = socket_nr

        psi_max = int(self.props.get("Max PSI", 80))
        channel = int(self.props.get("Channel",0))
        address = int(self.props.get("Address","0x48"), 16)
        self.offset = float(self.props.get("Offset",0))
        self.unit = self.cbpi.config.get("PRESSURE_UNIT", "kPa")
        if self.unit is None or self.unit == "" or not self.unit:
            self.unit = "kPa"
            self.cbpi.notify("Pressure Sensor Init Problem","Cant read config value: PRESSURE_UNIT. Unit set to {}".format(self.unit), NotificationType.WARNING)

        self.scale = psi_max/(voltage_max - voltage_min)
        t = voltage_max * self.scale
        self.calc_offset = psi_max - t

        i2c = busio.I2C(board.SCL, board.SDA)

        # Create the ADS object and specify the gain
        try:
            ads = ADS1115(i2c, address=address)
            ads.gain = 1
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
                    self.value = psi + self.offset
                if self.unit == "kPa":
                    self.value = round(psi * 6.89476) + self.offset

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
