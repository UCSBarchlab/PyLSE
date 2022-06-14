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

#from lexer import *
import lexer
from node import Node
from parser import *

import ply.yacc as yacc
import os

class SystemDeclarationParser(Parser):

    def __init__(self, data, typedefDict=None):
        #priority counter for system decs, lower number == higher priority
        self.prioritycounter = 0

        super(SystemDeclarationParser, self).__init__(data, lexer, typedefDict)

        self.AST.type = 'SystemDec'
    
    def parseCurrentStatement(self):
        if self.currentToken.type in ('SYSTEM',):
            self.accept('SYSTEM')
            systemslist = self.parseSystemList()
            return Node("System", systemslist)
        elif self.currentToken.type == 'IDENTIFIER':
            #look ahead to check if this is a Process Instantiation Assignment, e.g.
            # P1 = Process(5, true);
            # Note: Partial instantiation is NOT supported
            lookahead = self.lexer.clone()
            nextToken = lookahead.token()
            if nextToken.type in ('EQUALS', 'ASSIGN'):
                #P1
                ident = self.parseIdentifier()

                # =
                assert self.currentToken.type in ('EQUALS', 'ASSIGN')
                self.accept(self.currentToken.type)

                # Process(5, true)
                templateident = self.parseIdentifier()
                inst = self.parseTemplateInstantiation(templateident)

                # ;
                self.accept('SEMI')

                return Node("ProcessAssignment", [inst], ident, 
                        ident=ident, instantiation=inst)
            else:
                return super(SystemDeclarationParser, self).parseCurrentStatement()
        else:
            return super(SystemDeclarationParser, self).parseCurrentStatement()

    def parseTemplateInstantiation(self, templateident):
        # Process(5, true)
        #        ^
        self.accept('LPAREN')
        
        parameters = []
        while self.currentToken.type != 'RPAREN':
            expr = self.parseExpression()
            if self.currentToken.type == 'COMMA':
                self.accept('COMMA')
            parameters += [expr]
        self.accept('RPAREN')

        return Node("TemplateInstantiation", parameters, templateident,
                parameters=parameters, ident=templateident)

    def parseSystemList(self):
        systemslist = []
        while self.currentToken.type in ('IDENTIFIER'):
            identifier = self.parseIdentifier()

            #EXTENSION of UPPAAL language: instantiation on system line
            #e.g. system Template(0), Template(1);
            if self.currentToken.type == 'LPAREN':
                # Process(5, true)
                #        ^
                inst = self.parseTemplateInstantiation(identifier)
            else:
                # Process
                params = []
                inst = Node("TemplateInstantiation", params, identifier,
                        ident=identifier, parameters=params)

            inst.priority = self.prioritycounter

            if self.currentToken.type == 'COMMA':            
                self.accept('COMMA') 
            elif self.currentToken.type == 'LESS':
                self.accept('LESS') 
                self.prioritycounter += 1

            systemslist.append( inst )

            if self.currentToken.type == 'SEMI':
                self.accept('SEMI')
                break
        return systemslist
