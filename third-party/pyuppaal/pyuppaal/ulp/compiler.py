#!/usr/bin/python

"""
    Copyright (C) 2008 Andreas Engelbredt Dalsgaard <andreas.dalsgaard@gmail.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>. """

from parser import *
from lexer import *
  
if len(sys.argv) == 1:
    print "usage : ./compile.py inputfile"
    raise SystemExit

if len(sys.argv) >= 2:
    filename = sys.argv[1]

lexer = lex.lex()
p = Parser(open(filename).read(), lexer)

p.AST.visit()

# vim:ts=4:sw=4:expandtab
