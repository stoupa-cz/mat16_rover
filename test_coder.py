#!/usr/bin/python

import coder

msg = "abcdefghz09'/?"

print ">\n" + coder.encode(msg) + "<\n"

print ">\n" + coder.decode(coder.encode(msg)) + "<\n"
