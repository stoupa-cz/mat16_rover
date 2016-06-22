#!/usr/bin/python

# Coding and decoding routines
# Stoupa, 07/2016

key = 0xcafe

def encode(text):
    output = ''
    for i, c in enumerate(text):
        output += str(bin((ord(c) + i + 42) ^ key)) + "\n"
    return output

def decode(text):
    output = ''
    for i, line in enumerate(text.splitlines()):
        output += chr((int(line, 2) ^ key) - i - 42)
    return output
