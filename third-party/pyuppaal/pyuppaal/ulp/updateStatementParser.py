""" 
    Copyright (C) 2009
    Andreas Engelbredt Dalsgaard <andreas.dalsgaard@gmail.com>
    Martin Toft <mt@martintoft.dk>
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

from lexer import *
import expressionParser
import parser
from node import Node


class updateStatementParser(parser.Parser):

    def __init__(self, data, lexerArg=None, typedefDict={}):
        if lexerArg is None:
            lexerArg = lexer

        self.lexer = lexerArg
        self.lexer.input(data+";")
        self.currentToken = self.lexer.token()
        self.typedefDict = typedefDict


    def parseUpdateStatements(self):
        statements = []

        while 1:
            if self.currentToken:
                if self.currentToken.type == 'IDENTIFIER':
                    identifier = self.parseIdentifierComplex()
                    if self.currentToken.type != 'LPAREN':
                        statements.append(self.parseAssignment(identifier))
                    else:
                        statements.append(self.parseFunctionCall(identifier))
                    
                    if self.currentToken.type == 'SEMI':
                        self.accept('SEMI')
                    elif self.currentToken.type == 'COMMA':
                        self.accept('COMMA')
                elif self.currentToken.type == 'NUMBER':
                    statements.append(self.parseExpression())
                elif self.currentToken.type == 'SEMI':
                    self.accept('SEMI')
                else:
                    self.error("failed to parse updateStatements - unexpected token type: "+self.currentToken.type) 
                    break
            else:
                break

        if self.currentToken != None:
            self.error('at token "%s" on line %d: Did not expect any token, but found token of type %s' % (self.currentToken.value, self.currentToken.lineno, self.currentToken.type))

        return Node('RootNode', statements)
    
# vim:ts=4:sw=4:expandtab
