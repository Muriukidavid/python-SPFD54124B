#pip install pyA20
from pyA20.gpio import port
from pyA20.gpio import gpio
from pyA20.spi import spi
from spfd54124b import SPFD54124B
from spfd54124b import Color
import time

HWSPI = False #whether to use hardware SPI, else bitbanging

# we need data and clock, if no other pins
if HWSPI:
	pins = [port.PH0, port.PI2] # backlight and RESET
else:
	pins = [port.PC19, port.PC20, port.PC21, port.PC22, port.PH0, port.PI2]
	#C19: CS
	#C20: CLK
	#C21: MOSI
	#C22: MISO -> RESET, needs changing to PI2
	#H0: BACKLIGHT
	#I2: RESET

white = Color(255, 255, 255)
black = Color(0, 0, 0)
yellow = Color(0, 255, 0)
red = Color(255, 0, 0)
lcd = SPFD54124B(spi, gpio, pins, white, black) 
lcd.setOrientation("_90")
lcd.clear(white)
lcd.waitms(200)
lcd.setOrientation("_180")
lcd.clear(yellow)
lcd.waitms(200)
lcd.setOrientation("_270")
lcd.clear(red)
lcd.waitms(200)
lcd.setOrientation("_0")
lcd.clear(white)
lcd.waitms(200)
lcd.setOrientation("_90")
lcd.clear(red)
