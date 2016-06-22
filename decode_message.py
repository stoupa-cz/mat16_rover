#!/usr/bin/env python

import coder
import sys

msg = ''

for line in sys.stdin:
    msg += line

print coder.decode(msg)
