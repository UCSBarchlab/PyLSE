"""
    Copyright (C) 2009 
    Andreas Engelbredt Dalsgaard <andreas.dalsgaard@gmail.com>
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

"""This file contains the lexer rules and the list of valid tokens."""
import ply.lex as lex
import sys
import re

reserved = {
'void' : 'VOID',
'int' : 'INT',
'bool' : 'BOOL',
'chan' : 'CHANNEL',
'clock' : 'CLOCK',
'urgent' : 'URGENT',
'broadcast' : 'BROADCAST',
'const' : 'CONST',
'if' : 'IF',
'else' : 'ELSE',
'while' : 'WHILE',
'for' : 'FOR',
'struct' : 'STRUCT',
'true' : 'TRUE',
'false' : 'FALSE',
'True' : 'TRUE',
'False' : 'FALSE',
'not' : 'NOT',
'and' : 'AND',
'or' : 'OR',
'imply' : 'IMPLY',
'return' : 'RETURN',
'do' : 'DO',
'system' : 'SYSTEM',
'typedef' : 'TYPEDEF',
'extern' : 'EXTERN', #opaal specific!
}
#TODO add <? and ?>

# This is the list of token names.
tokens = [
    'IDENTIFIER',
    'NUMBER',
# Operators
    'PLUS',
    'MINUS',
    'TIMES',
    'DIVIDE',
    'MODULO',
    'BITAND',
    'BITOR',
    'XOR',
    'LSHIFT',
    'RSHIFT',
    'LOR',
    'LAND',
    'LNOT',
    'LESS',
    'GREATER',
    'LESSEQ',
    'GREATEREQ',
    'EQUAL',
    'NOTEQUAL',
    'PLUSPLUS',
    'MINUSMINUS',
    'CONDITIONAL',
# Assignments
    'EQUALS',
    'ASSIGN',
    'TIMESEQUAL',
    'DIVEQUAL',
    'MODEQUAL',
    'PLUSEQUAL',
    'MINUSEQUAL',
    'LSHIFTEQUAL',
    'RSHIFTEQUAL',
    'ANDEQUAL',
    'OREQUAL',
    'XOREQUAL',
#Delimeters
    'SEMI',
    'COMMA',
    'DOT',
    'COLON',
    'LPAREN',
    'RPAREN',
    'LCURLYPAREN',
    'RCURLYPAREN',
    'LBRACKET',
    'RBRACKET',
#Miscellaneous
    'APOSTROPHE',
    ] +list(reserved.values())
 
# These are regular expression rules for simple tokens.
# Operators (The following sections is inspired by c_lexer.py)
t_PLUS        = r'\+'
t_MINUS       = r'-'
t_TIMES       = r'\*'
t_DIVIDE      = r'/'
t_MODULO      = r'%'
t_BITAND      = r'&'
t_BITOR       = r'\|'
t_XOR         = r'\^'
t_LSHIFT      = r'<<'
t_RSHIFT      = r'>>'
t_LOR         = r'\|\|'
t_LAND        = r'&&'
t_LNOT        = r'!'
t_LESS        = r'<'
t_GREATER     = r'>'
t_LESSEQ      = r'<='
t_GREATEREQ   = r'>='
t_EQUAL       = r'=='
t_NOTEQUAL    = r'!='
t_PLUSPLUS    = r'\+\+'
t_MINUSMINUS  = r'--'
t_CONDITIONAL = r'\?'

# Assignments
t_EQUALS      = r'='
t_ASSIGN      = r':='
t_TIMESEQUAL  = r'\*='
t_DIVEQUAL    = r'/='
t_MODEQUAL    = r'%='
t_PLUSEQUAL   = r'\+='
t_MINUSEQUAL  = r'-='
t_LSHIFTEQUAL = r'<<='
t_RSHIFTEQUAL = r'>>='
t_ANDEQUAL    = r'&='
t_OREQUAL     = r'\|='
t_XOREQUAL    = r'^='

# Delimeters
t_SEMI        = r';'
t_COMMA       = r','
t_DOT         = r'\.'
t_COLON       = r':'
t_LPAREN      = r'\('
t_RPAREN      = r'\)'
t_LCURLYPAREN = r'\{'
t_RCURLYPAREN = r'\}'
t_LBRACKET    = r'\['
t_RBRACKET    = r'\]'

#Miscellaneous
t_APOSTROPHE  = r"'"


def t_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value,'IDENTIFIER')    # Check for reserved words
    return t

# Read in an int.
def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

# Ignore comments. 
def t_COMMENT(t):
    r'//.*\n'
    t.lineno += t.value.count('\n')

def t_MCOMMENT(t):
    r'/\*(.|\n)*?\*/'
    t.lineno += t.value.count('\n')

# Track line numbers.
def t_NEWLINE(t):
    r'\n+'
    t.lineno += len(t.value)

# These are the things that should be ignored.
t_ignore = ' \t'

# Handle errors.
def t_error(t):
    raise SyntaxError("syntax error on line %d near '%s'" %
        (t.lineno, t.value))
# Build the lexer.
lexer = lex.lex()

# vim:ts=4:sw=4:expandtab
