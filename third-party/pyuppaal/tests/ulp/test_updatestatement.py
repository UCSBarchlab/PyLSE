#!/usr/bin/python
import sys
import os
import unittest
from pyuppaal.ulp import lexer, updateStatementParser, expressionParser, node

class TestUpdateStatementParsing(unittest.TestCase):

    def test_parse_assignment(self):
        pars = updateStatementParser.updateStatementParser("x = s")
        AST = pars.parseUpdateStatements()
        AST.visit()

        pars = updateStatementParser.updateStatementParser("x = s;")
        AST = pars.parseUpdateStatements()
        AST.visit()

    def test_parse_comma_separated_statements(self):
        pars = updateStatementParser.updateStatementParser("x = s, t= f();", lexer.lexer)
        AST = pars.parseUpdateStatements()
        AST.visit()

 
if __name__ == '__main__':
    unittest.main()
