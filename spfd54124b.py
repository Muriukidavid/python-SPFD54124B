#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time 

# Color modes:
colorModes = {
	"12-bit":0x03, 		# 12-bits/pixel (RGB 4-4-4-bits input), 4K-colours
	"16-bit":0x05, 		# 16-bits/pixel (RGB 5-6-5-bits input), 65K-colours
	"18-bit":0x06, 		# 18-bits/pixel (RGB 6-6-6-bits input), 262K-colours
}

#Start up parameters:
SWRESET = 0x01 			# 01h Software reset command
COLMOD = 0x3A 			# 3Ah Color mode command
#switching on
SLPOUT = 0x11 			# SLPOUT (11h): Sleep Out
DISPON = 0x29 			# DISPON - Display on

# Display paramerters:
NVCTR = 0xB4
NVCTR_NLA = 4 			#(1 << 2) display inversion in normal full color mode: 0=line 1=frame
NVCTR_NLB = 2 			#(1 << 1) in idle mode
NVCTR_NLC = 1 			#(1 << 0) in full colours partial mode

#MADCTR: Memory AdDress ConTrolleR
MADCTR = 0x36 			# MADCTR command code
MADCTR_RGB = (1 << 3) 	# RGB-BGR order bit: ‘0’ =RGB color filter panel, ‘1’ =BGR color filter panel)
MADCTR_ML = (1 << 4) 	# Vertical refresh order:LCD vertical refresh direction control,
								# ‘0’ = LCD vertical refresh Top to Bottom,
								# ‘1’ = LCD vertical refresh Bottom to Top
MADCTR_MV = (1 << 5) 	# Row/Column Exchange	|
MADCTR_MX = (1 << 6) 	# Column Address Order	|--> Controls MCU to memory write/read direction.
MADCTR_MY = (1 << 7) 	# Row Address Order	|		Used to change screen orientation

RAMWR = 0x2C			#RAMWR (2Ch): Memory Write unlock
CASET = 0x2A 			# Column Address Set. 
RASET = 0x2B 			# Row Address Set
SLPOUT = 0x11 			# Sleep Out
DISPON = 0x29 			# Display on

orientations = {
	"_0": 0,
	"_90": 1,
	"_180": 2,
	"_270": 3,
}

class Color(object):
	"""
	A 3 byte RGB color and 16-bit 5-red, 6-green, 5-blue color representations class
	"""

	def __init__(self, r, g, b):
		self.r = r
		self.g = g
		self.b = b

	def __enter__(self): # for use in "with"
		return self.packColor()

	def packColor(self):
		"""
		Pack RGB pixel data into a single 16-bit value of 5 red bits, 6 green bits and 5 blue bits
		"""
		return ((self.r << 11) & 0xf800 | (self.g << 5) & 0x07e0 | (self.b & 0x001f))

class SPFD54124B(object):
	"""
	An SPFD54124B class object for controlling the Nokia 1616 LCD
	"""

	def __init__(self, spidevice, gpio, pins, foreground, background, COLORMODE="16-bit"):
		"""
		Initialize the SPFD54124B object:
		:param spidevice: The hardware SPI device if available
		:type spidevice: object
		:param pins: The data and clock gpio pins to be used. Necessary because 9-bit mode hack inevitable, SPI hardware is 8-bit only
		"""
		if spidevice:# pass a zero to disable hw spi
			self.spi = spidevice.open("/dev/spidev2.0", mode=0, delay=0, bits_per_word=9, speed=12000) # 12Mhz speed
		else:
			self.spi = 0
		self.gpio = gpio
		self.pins = pins
		#bit-banging pins
		if self.spi:
			self.RESET = pins[0]
			self.BACKLIGHT = pins[1]
		else:
			self.CS = pins[0]
			self.SCK = pins[1]
			self.MOSI = pins[2]
			self.RESET = pins[3]# MISO isn't required so we can repurpose it here
			self.BACKLIGHT = pins[4]
		#LCD properties
		self.width = 130 #width of display in pixels
		self.height = 161 #height of display in pixels
		self.rows = self.height/9
		self.columns = self.width/6
		self.orientation = orientations.get("_0")
		self.COLORMODE = colorModes.get("16-bit")	# a 16 bit color mode default
		self.foreground = foreground.packColor()  	# a foreground Color in 16-bit format
		self.background = background.packColor()	# a background Color in 16-bit format

		# initialize the display
		self.initGpio()
		self.start(self.background)

	def __enter__(self):
		return self

	def __exit__(self):
		if self.autocleanup:
			self.close

	def close(self):
		if self.spi:
			self.spi.close()

	def initGpio(self):
		self.gpio.init() # Always initialize the A20 gpio first
		for pin in self.pins:
			self.gpio.setcfg(pin, 1) # configure as an output

	def send(self, byte):
		"""
		Sends one byte of data(9-bits long) to the SPI display
		"""
		if self.spi==0:
			#enable write
			self.gpio.output(self.CS,0)
			for i in range(0, 9):
				if(byte & (256 >> i)):
					self.gpio.output(self.MOSI, 1)
				else:
					self.gpio.output(self.MOSI, 0)
				#toggle the clock to transmit 1 bit
				self.gpio.output(self.SCK, 0)
				self.gpio.output(self.SCK, 1)
			#disable write
			self.gpio.output(self.CS, 1)
		else:
			# requires an initialized 9-bit hardware SPI device 
			self.spi.send(byte & 0x1FF) # preserve only 9-bits during send

	def start(self, color):
		"""
		Resets and clears the LCD using the color passed
		"""
		self.gpio.output(self.BACKLIGHT, 1) # enable backlight LED
		self.reset()				# hardware reset
		self.sendCommand(SWRESET)	# software reset
		self.waitms(200)			# wait 200ms
		self.sendCommand(COLMOD)	# select color mode
		self.sendData(self.COLORMODE)
		self.sendCommand(SLPOUT)	# sleep out
		self.sendCommand(DISPON)	# display on
		self.setOrientation(self.orientation)
		self.clear(color)			# clear

	def sendCommand(self, command):
		command = command & 0xFF
		#print("command: ",command, "\n")
		self.send(command) # clear 9th bit

	def sendData(self, data):
		data = data | 0x100
		self.send(data) # set 9th bit

	def sendPixel(self, color):
		if self.COLORMODE == colorModes.get("16-bit"):
			self.sendData((color >> 8));
			self.sendData(color & 0xFF);
		elif self.COLORMODE == colorModes.get("18-bit"):
			self.sendData(color >> 24  & 0xFF)
			self.sendData((color >>16) & 0xFF)
			self.sendData(color & 0xFF)
		elif self.COLORMODE == colorModes.get("12-bit"):
			pass#TODO: implement 12 bit color mode sending
 
	def setWindow(self, x, y, w, h):
		"""
		Sets the window to be updated
		Takes two points that define the rectangle: (x1, y1), (x1, y2)
		"""
		#choosing a range of columns
		self.sendCommand(CASET);# set column address 
		self.sendData(0);		# the second byte is always zero, because sending 2 bytes
		self.sendData(2+x);		# left corner - x
		self.sendData(0);
		self.sendData(2+x+w-1);	# right angle - x

		self.sendCommand(RASET);# set row address
		self.sendData(0);
		self.sendData(1+y);		# Left corner - y
		self.sendData(0);
		self.sendData(1+y+h);	# Right angle - y

		self.sendCommand(RAMWR)	#unlock memory write

		
	def clear(self, color):
		"""
		Paints the background color in the entire display
		"""
		self.setWindow(0, 0, self.width, self.height)
		for i in range(0,self.width*self.height):
			self.sendPixel(color)
	
	def reset(self):
		self.gpio.output(self.CS, 0) # hold CS low
		self.gpio.output(self.RESET, 0) # hold RESET low
		self.waitms(200); # wait 100ms
		self.gpio.output(self.CS, 1) # release CS
		self.gpio.output(self.RESET, 1) # release RESET
		self.waitms(200) # wait 100ms
		self.gpio.output(self.MOSI, 0) # hold output low
		self.gpio.output(self.SCK, 1) # hold clock high
	
	def setOrientation(self, orientation):
		self.sendCommand(MADCTR)
		if orientation == orientations.get("_0"):
			self.sendData(0)
		elif orientation == orientations.get("_90"):
			self.sendData((MADCTR_MV | MADCTR_MX))
		elif orientation == orientations.get("_180"):
			self.sendData(MADCTR_MY | MADCTR_MX)
		elif orientation == orientations.get("_270"):
			self.sendData(MADCTR_MV | MADCTR_MY)

	def waitms(self, ms):
		time.sleep(ms/1000)
