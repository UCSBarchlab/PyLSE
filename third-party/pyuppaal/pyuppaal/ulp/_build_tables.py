""" 
    Copyright (C) 2011
    Mads Chr. Olesen <mchro@cs.aau.dk>

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

#-----------------------------------------------------------------
# Based on pycparser: _build_tables.py, Copyright (C) 2008-2011, Eli Bendersky
#
# A dummy for generating the lexing/parsing tables and and 
# compiling them into .pyc for faster execution in optimized mode.
# Should be called from the installation directory.
#
#-----------------------------------------------------------------

# Generate c_ast.py
#

#from pyuppaal.ulp 
import systemdec_parser

# Generates the tables
#
systemdec_parser.SystemDeclarationParser('',
    lex_optimize=True, 
    yacc_debug=False, 
    yacc_optimize=True)

# Load to compile into .pyc
#
#import lextab
import systemdec_parser_yacctab
