#!/usr/bin/python

# Simple program for summer camp rover information reader
# Stoupa, 05/2016
# My first script in Python

# Event handling copy&paste from:
# http://stackoverflow.com/questions/5060710/format-of-dev-input-event/16682549

import struct
import time
import threading
import sys
import atexit

event_path = "/dev/input/event2"
lcd_path = "/dev/lcd0"
lcd_buffer = ''

# long int, long int, unsigned short, unsigned short, unsigned int
FORMAT = 'llHHI'
EVENT_SIZE = struct.calcsize(FORMAT)

# Direction of scrolling
class Dir:
	DOWN = 1
	UP = 2
	STOP = 3
	UNKNOWN = 10

	@staticmethod
	def get_string(direction):
		if direction == Dir.DOWN:
			return chr(0x19)
		elif direction == Dir.UP:
			return chr(0x18)
		elif direction == Dir.STOP:
			return chr(0x16)
		else:
			return '?'

def init_lcd ():
	global lcd_buffer
	lcd_buffer = '{:16s}'.format('')
	lcd_buffer += 'I {:c} Kamzici'.format(0x9d)

def update_lcd (amount, direction):
	global lcd_buffer, repaint_lcd
	bar = min(abs(amount / 3), 7);
	lcd_buffer = '{:12d} {:s} {:c}'.format(amount, Dir.get_string(direction), bar)
	lcd_buffer += 'I {:c} Kamzici'.format(0x9d)
	repaint_lcd.set()

def lcd_worker ():
	global lcd_buffer, repaint_lcd
	while (True):
		repaint_lcd.wait()
		repaint_lcd.clear()
		print "repainting"
		lcd = open(lcd_path, 'w')
		lcd.write(lcd_buffer)
		lcd.close()

def goodbye ():
	#t.join() # XXX
	event_file.close()

atexit.register(goodbye)

init_lcd ()

t = threading.Thread(target=lcd_worker)
t.daemon = True # XXX Do stopping in a better way
repaint_lcd = threading.Event()
t.start()
repaint_lcd.set()

output = 0

# open file in binary mode
event_file = open(event_path, "rb")
event = event_file.read(EVENT_SIZE)

while event_file:
	(tv_sec, tv_usec, type, code, value) = struct.unpack(FORMAT, event)

	direction = Dir.UNKNOWN

	if (type != 0 or code != 0) and value != 0:
		if code == 113:
			print("pushed")
			direction = Dir.STOP
			output = 0
		elif code == 114:
			print("down")
			direction = Dir.DOWN
			output -= 1
		elif code == 115:
			print("up")
			direction = Dir.UP
			output += 1
		else:
			print("unsupported code")

		update_lcd(output, direction)

	event = event_file.read(EVENT_SIZE)
