#!/usr/bin/python

# Coding and decoding routines
# Stoupa, 07/2016

key = 0xcafe

def encode(text):
    output = ''
    # TODO add some random stuff
    for i, c in enumerate(text):
        output += str(bin((ord(c) + i + 42) ^ key)) + "\n"
    return output

def decode(text):
    output = ''
    # TODO remove some random stuff
    for i, line in enumerate(text.splitlines()):
        output += chr((int(line, 2) ^ key) - i - 42)
    return output
