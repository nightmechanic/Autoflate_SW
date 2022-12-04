import time
import board
import digitalio
import analogio
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn as adsAnalogIn


class AutoFlate:
    # Some constants
    VBatRatio = 6  # (10+2)/2
    PressRatio = 1.5  # (2+1)/2
    PressMinV = 0.5
    PressMaxV = 4.5
    PressMinP = 0  # [psi]
    PressMaxP = 72.5189  # [psi]
    PressSlope = (PressMaxP - PressMinP) / (PressMaxV - PressMinV)  # [psi/V]

    PressureHyst = 0.5  # psi
    InitialDeflateTime = 10000  # msec
    InitialInflateTime = 10000  # msec
    MaxInflateTime = 60000  # msec
    MaxDeflateTime = 60000  # msec
    minDiff = 4  # psi
    minTimePsi = 2500  # msec
    switchToValveDelay = 0.1 #sec
    class Tasks:
        NONE = "NONE"
        MEASURING = "MEASURING"
        INFLATING = "INFLATING"
        DEFLATING = "DEFLATING"
        DONE = "DONE"

    def __init__(self):
        # Digital IO setup
        self.DOInflate = digitalio.DigitalInOut(board.IO33)
        self.DOInflate.direction = digitalio.Direction.OUTPUT
        self.DODeflate = digitalio.DigitalInOut(board.IO34)
        self.DODeflate.direction = digitalio.Direction.OUTPUT
        self.DODrySW = digitalio.DigitalInOut(board.IO42)
        self.DODrySW.direction = digitalio.Direction.OUTPUT

        # internal ADC setup
        self.AIVref = analogio.AnalogIn(board.IO1)
        self.AIVbat = analogio.AnalogIn(board.IO2)
        self.AIPressure = analogio.AnalogIn(board.IO3)

        # ADS1115 (ext ADC) setup
        self.ADS_I2C = busio.I2C(board.IO18, board.IO17, frequency=400000)
        self.ads = ADS.ADS1115(self.ADS_I2C)
        self.adsVref = adsAnalogIn(self.ads, ADS.P0)
        self.adsExt = adsAnalogIn(self.ads, ADS.P1)
        self.adsVbat = adsAnalogIn(self.ads, ADS.P2)
        self.adsPressure = adsAnalogIn(self.ads, ADS.P3)

        #Others
        self.currentTask = self.Tasks.DONE
        self.last_pressure = 0
        self.last_time = 0
        self.slowRate = 0
        self.Timer = 0
        self.Message = "OK"

    def get_VBat(self):
        vbat = (self.adsVbat.voltage * self.VBatRatio)
        return round(vbat,1)

    def get_pressure(self):
        pressureV = self.adsPressure.voltage * self.PressRatio
        pressure = (pressureV - self.PressMinV) * self.PressSlope
        pressure = pressure + self.PressMinP
        return round(pressure,1)

    def get_pressure_avg(self):
        pressure = 0
        for x in range(4):
            time.sleep(0.1)
            pressure += self.get_pressure()
            pressure = pressure / 4
        return round(pressure,1)

    def stop(self):
        self.DOInflate.value = False
        self.DODeflate.value = False
        self.DODrySW.value = False

    def deflate(self):
        self.DODrySW.value = False
        self.DOInflate.value = False
        self.DODeflate.value = True

    def inflate(self):
        self.DODrySW.value = True
        time.sleep(self.switchToValveDelay)
        self.DOInflate.value = True
        self.DODeflate.value = False

    def timer_calc(self, rate, P_diff):
        if self.currentTask == self.Tasks.INFLATING:
            if rate <= 0:
                timer = max(self.InitialInflateTime, P_diff * self.minTimePsi)
            else:
                timer = min(self.MaxInflateTime, rate * P_diff)
        else:
            if rate >= 0:
                timer = max(self.InitialDeflateTime, P_diff * self.minTimePsi)
            else:
                timer = min(self.MaxDeflateTime, abs(rate * P_diff))

        return timer

    def inflate_deflate(self,setPressure):
        if self.currentTask == self.Tasks.DONE:
            self.Message = "OK"
            self.slowRate = 0
            air_rate = 0
            start_time = time.monotonic()
            current_pressure = self.get_pressure_avg()
            pressure_diff = abs(current_pressure - setPressure)
            self.last_pressure = current_pressure
            self.last_time = start_time
            if current_pressure > (setPressure + self.PressureHyst):
                self.currentTask = self.Tasks.DEFLATING
                self.Timer = self.timer_calc(air_rate, pressure_diff)
                self.deflate()
            elif setPressure > (current_pressure + self.PressureHyst):
                self.currentTask = self.Tasks.INFLATING
                self.Timer = self.timer_calc(air_rate, pressure_diff)
                self.inflate()
            else:
                self.currentTask = self.Tasks.DONE
        if self.currentTask == self.Tasks.INFLATING or self.currentTask == self.Tasks.DEFLATING:
            current_time = time.monotonic()

            if (current_time - self.start_time) < self.Timer:
                pass
            else:
                self.stop()
                current_pressure = self.get_pressure_avg()
                if abs(current_pressure - self.last_pressure) < 0.5:
                    air_rate = 0
                    self.slowRate += 1
                else:
                    air_rate = (current_time - self.last_time) / (current_pressure - self.last_pressure)

                pressure_diff = abs(current_pressure - setPressure)
                self.last_pressure = current_pressure
                if self.slowRate > 2:
                    self.Message="Slow/No pressure change!"
                    self.currentTask = self.Tasks.DONE
                elif current_pressure > (setPressure + self.PressureHyst):
                    self.currentTask = self.Tasks.DEFLATING
                    self.Timer = self.timer_calc(air_rate, pressure_diff)
                    self.deflate()
                elif setPressure > (current_pressure + self.PressureHyst):
                    self.currentTask = self.Tasks.INFLATING
                    self.Timer = self.timer_calc(air_rate, pressure_diff)
                    self.inflate()
                else:
                    self.currentTask = self.Tasks.DONE
                    self.Message = "OK"

                return self.last_pressure, self.currentTask, self.Message


