#!/usr/bin/python

# Simple program for summer camp rover information reader
# Stoupa, 05/2016
# My first script in Python

# Event handling copy&paste from:
# http://stackoverflow.com/questions/5060710/format-of-dev-input-event/16682549

import atexit
import coder
import glob
import os
import struct
import sys
import select
import random
import threading
import time

event_path = "/dev/input/event2"
lcd_path = "/dev/lcd0"
line_width = 16
virus_path = '/etc/rover_virus'
broken_path = '/etc/rover_broken'

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

class LCD:
	_message = ''
	_repaint = None
	_running = True
	_thread = None
	_lcd = None

	def __init__(self):
		LCD._thread = threading.Thread(target=LCD._worker)
		LCD._lcd = open(lcd_path, 'w')
		LCD._repaint = threading.Event()
		LCD._thread.start()

	@staticmethod
	def _worker():
		while(LCD._running):
			LCD._repaint.wait()
			LCD._repaint.clear()
			print 'Repainting LCD'
			LCD._lcd.write(' ' if LCD._message == '' else LCD._message)
			LCD._lcd.flush()
		print 'Finishing LCD handler'

	@staticmethod
	def set_message(message):
		LCD._message = message
		LCD._repaint.set()

	@staticmethod
	def get_message():
		return LCD._message

	@staticmethod
	def stop(msg):
		LCD._message = msg
		LCD._repaint.set()
		LCD._running = False
		LCD._repaint.set()
		LCD._thread.join()
		LCD._lcd.close()

class IdleOutput:
	def __init__(self, text):
		self.text = text
		LCD.set_message(text[0:32])

	def get_text(self):
		return self.text

	def direction_handler(self, direction):
		return

class CardOutput:
	def __init__(self, text):
		self.line = 0
		self.text = text
		self.event_file = None
		LCD.set_message(self.get_text_buffer())

	def scroll(self, direction):
		if (direction == Dir.DOWN):
			if (len(self.text) > self.line * line_width + 2 * line_width):
				self.line = self.line + 1;
		elif (direction == Dir.UP):
			self.line = max(self.line - 1, 0);

	def get_text(self):
		return self.text

	def direction_handler(self, direction):
		self.scroll(direction)
		LCD.set_message(self.get_text_buffer())

	def get_text_buffer(self):
		output = self.text[self.line * line_width:self.line * line_width + 2 * line_width]
		output = list(output.ljust(2 * line_width))
		if Rover.virus:
			output[04] = chr(0x07)
			output[05] = chr(0x07)
			output[12] = chr(0x07)
			output[18] = chr(0x07)
			output[22] = chr(0x07)
			output[27] = chr(0x07)
			output[30] = chr(0x07)
		return "".join(output)

class ProgressbarOutput:
	def __init__(self, text):
		self.text = self.first_line('Preparing...') + self.second_line(0)
		LCD.set_message(self.text)
		time.sleep(2.5)
		self.text = self.first_line(text) + self.second_line(0)
		LCD.set_message(self.text)
		time.sleep(1)
		for percent in range(0, 101):
			self.text = self.first_line(text) + self.second_line(percent)
			LCD.set_message(self.text)
			time.sleep(0.1)
		time.sleep(2)
		self.text = self.first_line(text) + 'Done.'
		LCD.set_message(self.text)
		time.sleep(4)
		return

	def get_text(self):
		return self.text

	def first_line(self, text):
		return text[0:16].ljust(16)

	def second_line(self, percent):
		percent = min(100, max(percent, 0))
		return '[{!s:10}]{:>3}%'.format('=' * (percent/10), percent)

	def direction_handler(self, direction):
		return

class BrokenOutput:
	def __init__(self, text):
		self.garbage = list(text)
		self.garbage.extend([' '] * (line_width * 2 - len(self.garbage)))
		self.chars = [
				chr(0x00), chr(0x03), chr(0x07), chr(0x16), chr(0x18), chr(0x19), chr(0x22),
				'S', 't', 'o', 'u', 'p', 'a',
				'0', '1',
				'x', '@', '&', '%', '!', ':', ',', '-',
				]
		LCD.set_message("".join(self.garbage[0:32]))

	def randomize(self, garbage):
		for i in range(4):
			garbage[random.randint(0, line_width * 2 - 1)] = self.chars[random.randint(0, len(self.chars) - 1)] 
		return garbage

	def get_text(self):
		return self.garbage

	def direction_handler(self, direction):
		self.garbage = self.randomize(self.garbage)
		LCD.set_message("".join(self.garbage))
		return

class InputHandler:
	def __init__(self):
		self.subscribers = []
		self.running = True
		self.thread = threading.Thread(target=self.event_handler)
		self.thread.start()

	# XXX Dtor is never called
	def __del__(self):
		print "InputHandler destructor called"
		self.running = False
		self.thread.join()
		if self.event_file is not None and not self.event_file.closed:
			self.event_file.close()

	def subscribe(self, obj):
		self.subscribers.append(obj)

	def unsubscribe(self, obj):
		try:
			self.subscribers.remove(obj)
		except ValueError:
			return

	def event_handler(self):
		self.event_file = open(event_path, "rb")

		while self.event_file and self.running:
			r, w, e = select.select([ self.event_file ], [], [], 1)
			if self.event_file in r:
				event = self.event_file.read(EVENT_SIZE)
			else:
				continue

			(tv_sec, tv_usec, type, code, value) = struct.unpack(FORMAT, event)

			direction = Dir.UNKNOWN

			if (type != 0 or code != 0) and value != 0:
				if code == 113:
					print("pushed")
					direction = Dir.STOP
				elif code == 114:
					print("vol down (=up)")
					direction = Dir.UP
				elif code == 115:
					print("vol up (=down)")
					direction = Dir.DOWN
				else:
					print("unsupported code")

			if (direction != Dir.UNKNOWN):
				for subscriber in self.subscribers:
					subscriber.direction_handler(direction)

class Rover:
	virus = None
	broken = None

	def __init__(self):
		Rover.virus = os.path.isfile(virus_path)
		Rover.broken = os.path.isfile(broken_path)
		return

	@staticmethod
	def infect():
		Rover.virus = True
		open(virus_path, 'w').close()
		os.system('sync')

	@staticmethod
	def aid():
		Rover.virus = False
		os.remove(virus_path)
		os.system('sync')

	@staticmethod
	def corrupt():
		Rover.broken = True
		open(broken_path, 'w').close()
		os.system('sync')

	@staticmethod
	def fix():
		Rover.broken = False
		os.remove(broken_path)
		os.system('sync')

def goodbye ():
	print "Cleaning up"
	LCD.stop('{:16s}{:16s}'.format('System was', 'stopped.'))

def main ():
	atexit.register(goodbye)

	rover = Rover()
	lcd = LCD()

	card_idle_msg = 'Please insert a memory card.'
	output = IdleOutput(card_idle_msg)
	input = InputHandler()
	message = LCD.get_message()

	while (True):
		message_old = message
		files = glob.glob('/media/*/rover.bin')
		if (len(files) > 0):
			try:
				with open(files[0]) as f:
						message = coder.decode(f.read()).strip().replace("\n", chr(0x17))
						if message == '*FIX*':
							if Rover.broken:
								Rover.fix()
								input.unsubscribe(output)
								output = ProgressbarOutput('Updating...')
								output = IdleOutput('Firmware has    been updated.')
						elif Rover.broken:
							pass
						elif message == '*INFECT*':
							if not Rover.virus:
								Rover.infect()
								input.unsubscribe(output)
								output = ProgressbarOutput('Infecting...')
								output = IdleOutput('System has been infected.')
						elif message == '*AID*':
							if Rover.virus:
								Rover.aid()
								input.unsubscribe(output)
								output = ProgressbarOutput('Cleaning virus..')
								output = IdleOutput('Virus has been  cleaned.')
						elif message == '*BREAK*':
							if not Rover.broken:
								Rover.corrupt()
								input.unsubscribe(output)
								output = BrokenOutput('Firmware has    been corrupted.')
								input.subscribe(output)
						elif message != message_old or not isinstance(output, CardOutput):
							print 'Switching to card output'
							input.unsubscribe(output)
							output = CardOutput(message)
							input.subscribe(output)
			except:
				message = ''
				continue
		elif Rover.broken:
			if not isinstance(output, BrokenOutput):
				print 'Going to the broken mode'
				input.unsubscribe(output)
				output = BrokenOutput('System is broken')
				input.subscribe(output)
		elif (not isinstance(output, IdleOutput) or message != card_idle_msg):
			print 'Going to idle'
			input.unsubscribe(output)
			output = IdleOutput(card_idle_msg)
			message = output.get_text()
		time.sleep(0.1)

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print 'Interrupted'
        try:
		goodbye()
		sys.exit(0)
	except SystemExit:
		os._exit(0)
