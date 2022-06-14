#!/usr/bin/python
import sys
import os
import unittest
from pyuppaal.ulp import lexer, parser, expressionParser, node
from pyuppaal.ulp.systemdec_parser import SystemDeclarationParser

class TestBasicParsing(unittest.TestCase):

    def test_comment_last_line(self):
        lex = lexer.lexer
        declaration = '// comment'
        pars = parser.Parser(declaration, lex)
    
    def test_error_upc_raise_exception(self):
        lex = lexer.lexer
        declaration = 'foo' #illegal statement
        self.assertRaises(Exception, parser.Parser, declaration, lex)
            
    def test_error_system_decl_raise_exception(self):
        declaration = 'foo' #illegal statement
        self.assertRaises(Exception, SystemDeclarationParser, declaration)
    
    def test_init_array(self):
        lex = lexer.lexer
        declaration = 'int myArray[10] = { 5, 5, 5, 5, 5, 5, 5, 5, 5, 5 };'
        pars = parser.Parser(declaration, lex)

    def test_parse_declarations(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_simple_declarations.txt'), "r")

        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        res = pars.AST.children

        #pars.AST.visit()

        declvisitor = parser.DeclVisitor(pars)
        declvisitor.visit(pars.AST)
        
        #print map(tuple, declvisitor.variables)
        #before declvisitor rewrite not all clocks were stored in variables
        #self.assertEqual(map(tuple, declvisitor.variables), [('a', 'TypeInt', [], None), ('b', 'TypeBool', [], None), ('b1', 'TypeBool', [], None), ('b2', 'TypeBool', [], None)])
        self.assertEqual(map(tuple, declvisitor.variables), [('a', 'TypeInt', [], None), ('b', 'TypeBool', [], None), ('b1', 'TypeBool', [], None), ('b2', 'TypeBool', [], None), ('c', 'TypeClock', [], None)])

        self.assertEqual(len(declvisitor.clocks), 1)
        self.assertEqual(declvisitor.clocks[0][0], 'c')

        self.assertEqual(declvisitor.channels, [('d', [])])
        self.assertEqual(declvisitor.urgent_channels, [('e', [])])
        self.assertEqual(declvisitor.broadcast_channels, [('f', [])])
        self.assertEqual(declvisitor.urgent_broadcast_channels, [('g', [])])

    def test_parse_declarations2(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_simple_declarations2.txt'), "r")

        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        res = pars.AST.children

        declvisitor = parser.DeclVisitor(pars)
        declvisitor.visit(pars.AST)

        self.assertEqual(len(declvisitor.variables), 10)
        self.assertTrue(('L', 'TypeInt', [], None) in map(tuple, declvisitor.variables))
        self.assertTrue(('time', 'TypeClock', [], None) in map(tuple, declvisitor.variables))
        self.assertTrue(('y1', 'TypeClock', [], None) in map(tuple, declvisitor.variables))
        self.assertTrue(('y2', 'TypeClock', [], None) in map(tuple, declvisitor.variables))
        self.assertTrue(('y3', 'TypeClock', [], None) in map(tuple, declvisitor.variables))
        self.assertTrue(('y4', 'TypeClock', [], None) in map(tuple, declvisitor.variables))
        #TODO test complex vaiables as well
        #    ('lalala', 'TypeInt', [], node.Node('Expression', [node.Node('Number', [], 3)], [])) ])
        #    ('msg', 'TypeBool', node.Node('IndexList', 
        #       [node.Node('Index', [], node.Node('Expression', [node.Node('Identifier', ['N'], None)], [])), 
        #          node.Node('Index', [], node.Node('Expression', [node.Node('Identifier', ['N'], None)], []))], None), None), 
        # ('lock', 'TypeBool', [], node.Node('Expression', [node.Node('False', [], [])], [])), 
        #('lock2', 'TypeBool', [], node.Node('Expression', [node.Node('True', [], [])], []))] )

        self.assertEqual(declvisitor.clocks, [('time', 10), ('y1', 10), ('y2', 10), ('y3', 10), ('y4', 10)])
        self.assertEqual(declvisitor.channels, [('take', []), ('release', [])])

        inorder = ["fastest", "fast", "slow", "slowest", "N"]
        self.assertEqual(declvisitor.constants.keys(), inorder)


    def test_parse_empty_query(self):
        lex = lexer.lexer
        pars = parser.Parser("", lex)

        self.assertEqual(len(pars.AST.children), 0)

    def test_parse_array(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_array.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        self.assertEqual(len(pars.AST.children), 7) #TODO add more asserts
        res = pars.AST.children

        self.assertEqual(res[0].children[0].children[0].leaf.type, "IndexList") 
        self.assertEqual(res[1].children[0].children[0].leaf.type, "IndexList") 
        self.assertEqual(res[2].children[0].children[0].leaf.type, "IndexList") 
        self.assertEqual(res[3].children[0].children[0].leaf.type, "IndexList") 
        self.assertEqual(res[4].children[0].children[0].leaf.type, "IndexList") 
        self.assertEqual(res[6].children[0].children[0].leaf.type, "IndexList") 
        indexlist = res[6].children[0].children[0].leaf
        self.assertEqual(len(indexlist.children), 2)
        indexlist.visit()
        self.assertEqual(indexlist.children[0].type, "Index")
        self.assertEqual(indexlist.children[1].type, "Index")

    def test_struct(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_struct.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        self.assertEqual(len(pars.AST.children), 1) #TODO add more asserts
        
    def test_struct_initializer(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_struct_initializer.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        pars.AST.visit()
        self.assertEqual(len(pars.AST.children), 4)
        
        vardecl = pars.AST.children[3]
        self.assertEqual(vardecl.type, "VarDeclList")
        initializer = vardecl.children[0].leaf
        self.assertEqual(initializer.type, "Initializer")
        self.assertEqual(len(initializer.children), 3)

        init1 = initializer.children[0]
        self.assertEqual(init1.type, "Initializer")
        self.assertEqual(len(init1.children), 3)
        self.assertEqual(init1.children[0].type, "Number")
        self.assertEqual(init1.children[0].leaf, 0)
        self.assertEqual(init1.children[1].type, "Identifier")
        self.assertEqual(init1.children[1].children[0], "DORMANT")
        self.assertEqual(init1.children[2].type, "Number")
        self.assertEqual(init1.children[2].leaf, 0)

    def test_parse_typedef_simple(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_typedef_simple.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        pars.AST.visit()


        self.assertEqual(len(pars.AST.children), 4)
        self.assertEqual(pars.AST.type, "RootNode")
        self.assertEqual(pars.AST.children[0].type, "NodeTypedef") 
        self.assertEqual(pars.AST.children[0].leaf, "id_t") 
        self.assertEqual(pars.AST.children[0].children[0].type, "TypeInt")
        self.assertEqual(pars.AST.children[1].type, "NodeTypedef") 
        self.assertEqual(pars.AST.children[1].leaf, "id_t") 
        self.assertEqual(pars.AST.children[1].children[0].type, "TypeInt")
        self.assertEqual(pars.AST.children[1].children[0].children[0].type, "Expression")
        self.assertEqual(pars.AST.children[1].children[0].children[0].children[0].leaf, 0)
        self.assertEqual(pars.AST.children[1].children[0].children[1].type, "Expression")
        self.assertEqual(pars.AST.children[1].children[0].children[1].children[0].leaf, 4)
        self.assertEqual(pars.AST.children[2].type, "NodeTypedef") 
        self.assertEqual(pars.AST.children[2].leaf, "id_t") 
        self.assertEqual(pars.AST.children[2].children[0].type, "TypeInt")
        self.assertEqual(pars.AST.children[2].children[0].children[0].type, "Expression")
        self.assertEqual(pars.AST.children[2].children[0].children[1].type, "Expression")
        self.assertEqual(pars.AST.children[2].children[0].children[1].children[0].leaf, 4)
        self.assertEqual(pars.AST.children[2].type, "NodeTypedef") 
        self.assertEqual(pars.AST.children[2].leaf, "id_t") 
        self.assertEqual(pars.AST.children[2].children[0].type, "TypeInt")
        self.assertEqual(pars.AST.children[2].children[0].children[0].type, "Expression")
        self.assertEqual(pars.AST.children[2].children[0].children[1].type, "Expression")
        self.assertEqual(pars.AST.children[2].children[0].children[1].children[0].leaf, 4)

        self.assertEqual(len(pars.typedefDict), 1)
        self.assertTrue('id_t' in pars.typedefDict)


    def test_parse_typedef(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_typedef.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        #pars.AST.visit()
        #self.assertEqual(len(pars.AST.children), 8)

        self.assertEqual(len(pars.typedefDict), 4)
        self.assertTrue('myStructType' in pars.typedefDict)
        self.assertTrue('adr' in pars.typedefDict)
        self.assertTrue('DBMClock' in pars.typedefDict)
        self.assertTrue('clock' in pars.typedefDict)

        ctype = pars.typedefDict['clock']
        self.assertEqual(ctype.type, 'NodeTypedef')
        self.assertEqual(ctype.leaf, 'DBMClock')
        self.assertEqual(len(ctype.children), 1)
        self.assertEqual(ctype.children[0], pars.typedefDict['DBMClock'])

        declvisitor = parser.DeclVisitor(pars)
        declvisitor.visit(pars.AST)
        #XXX parses to deeply into structs!
        self.assertEqual(len(declvisitor.variables), 4)
        
        #pars.AST.visit()
        print "variables", map(tuple, declvisitor.variables)
        varnames = [x for (x, _, _, _) in declvisitor.variables]
        self.assertTrue('m' in varnames)
        
        self.assertTrue(('m', 'myStructType', [], None) in map(tuple, declvisitor.variables))
        self.assertTrue('n' in varnames)
        self.assertTrue(('n', 'adr', [], None) in map(tuple, declvisitor.variables))
        self.assertTrue('n2' in varnames)
        
        #check ranges inherited from typedef
        print "type", declvisitor.get_vardecl('n').vartype
        self.assertEqual(declvisitor.get_vardecl('n').basic_type, "TypeInt")
        self.assertEqual(declvisitor.get_vardecl('n').range_min.type, "Number")
        self.assertEqual(declvisitor.get_vardecl('n').range_min.leaf, 1)
        self.assertEqual(declvisitor.get_vardecl('n').range_max.type, "Number")
        self.assertEqual(declvisitor.get_vardecl('n').range_max.leaf, 3)

        for (x, _, _, initval) in declvisitor.variables:
            if x == "n2":
                self.assertEqual(initval.type, "Expression")
                self.assertEqual(initval.children[0].type, "Number")
                self.assertEqual(initval.children[0].leaf, 3)

        self.assertTrue('c' in varnames)
        self.assertTrue(('c', 'DBMClock', [], None) in map(tuple, declvisitor.variables))
        #XXX parses to deeply into structs!
        #self.assertFalse('a' in varnames)

    def test_parse_typedef_clock(self):
        lex = lexer.lexer
        declaration = 'typedef clock rtclock;'
        
        with self.assertRaises(Exception) as context:
            parser.Parser(declaration, lex)
        
        self.assertEqual(context.exception.message, 'Currently, we do not allow adding new clock types, e.g., typedef clock rtclock')

    def test_parse_brackets(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_brackets.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)

    def test_comments(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_comments.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        self.assertEqual(pars.AST.type, "RootNode")
        self.assertEqual(pars.AST.children[0].type, "VarDeclList") 
        self.assertEqual(pars.AST.children[1].type, "Function")
        self.assertEqual(pars.AST.children[1].children[0].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[0].children[0].type, "Expression")
        self.assertEqual(pars.AST.children[1].children[0].children[0].children[0].type, "Divide")
        self.assertEqual(len(pars.AST.children), 2) 

    def test_operators(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_operators.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        self.assertEqual(pars.AST.type, "RootNode")
        self.assertEqual(pars.AST.children[0].type, "VarDeclList") 
        self.assertEqual(pars.AST.children[1].type, "Function")
        self.assertEqual(pars.AST.children[1].children[0].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[0].children[0].type, "Expression")
        self.assertEqual(pars.AST.children[1].children[0].children[0].children[0].type, "Plus")
        self.assertEqual(pars.AST.children[1].children[1].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[1].children[0].type, "Expression")
        self.assertEqual(pars.AST.children[1].children[1].children[0].children[0].type, "Minus")
        self.assertEqual(pars.AST.children[1].children[2].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[2].children[0].children[0].type, "Times")
        self.assertEqual(pars.AST.children[1].children[3].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[3].children[0].children[0].type, "Divide")
        self.assertEqual(pars.AST.children[1].children[4].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[4].children[0].children[0].type, "UnaryMinus")
        self.assertEqual(pars.AST.children[1].children[5].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[5].children[0].children[0].type, "Minus")
        self.assertEqual(pars.AST.children[1].children[5].children[0].children[0].children[0].type, "UnaryMinus")
        self.assertEqual(pars.AST.children[1].children[6].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[6].children[0].children[0].type, "Minus")
        self.assertEqual(pars.AST.children[1].children[6].children[0].children[0].children[0].type, "PlusPlusPost")
        self.assertEqual(pars.AST.children[1].children[7].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[7].children[0].children[0].type, "Plus")
        self.assertEqual(pars.AST.children[1].children[7].children[0].children[0].children[0].type, "PlusPlusPost")
        self.assertEqual(pars.AST.children[1].children[8].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[8].children[0].children[0].type, "Plus")
        self.assertEqual(pars.AST.children[1].children[8].children[0].children[0].children[0].type, "PlusPlusPre")
        self.assertEqual(pars.AST.children[1].children[9].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[9].children[0].children[0].type, "Plus")
        self.assertEqual(pars.AST.children[1].children[9].children[0].children[0].children[0].type, "PlusPlusPre")
        self.assertEqual(pars.AST.children[1].children[9].children[0].children[0].children[1].type, "PlusPlusPost")
        self.assertEqual(pars.AST.children[1].children[10].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[10].children[0].children[0].type, "Plus")
        self.assertEqual(pars.AST.children[1].children[10].children[0].children[0].children[0].type, "PlusPlusPost")
        self.assertEqual(pars.AST.children[1].children[10].children[0].children[0].children[1].type, "PlusPlusPre")
        self.assertEqual(pars.AST.children[1].children[11].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[11].children[0].children[0].type, "Minus")
        self.assertEqual(pars.AST.children[1].children[11].children[0].children[0].children[0].type, "MinusMinusPost")
        self.assertEqual(pars.AST.children[1].children[12].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[12].children[0].children[0].type, "Minus")
        self.assertEqual(pars.AST.children[1].children[12].children[0].children[0].children[0].type, "MinusMinusPost")
        self.assertEqual(pars.AST.children[1].children[12].children[0].children[0].children[1].type, "MinusMinusPre")
        self.assertEqual(pars.AST.children[1].children[13].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[13].children[0].children[0].type, "Plus")
        self.assertEqual(pars.AST.children[1].children[13].children[0].children[0].children[0].type, "MinusMinusPost")
        self.assertEqual(pars.AST.children[1].children[14].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[14].children[0].children[0].type, "Plus")
        self.assertEqual(pars.AST.children[1].children[14].children[0].children[0].children[0].type, "MinusMinusPre")
        self.assertEqual(pars.AST.children[1].children[15].type, "Assignment")
        self.assertEqual(pars.AST.children[1].children[15].children[0].children[0].type, "Modulo")
        self.assertEqual(pars.AST.children[1].children[15].children[0].children[0].children[0].type, "Identifier")
        self.assertEqual(pars.AST.children[1].children[15].children[0].children[0].children[0].children[0], "a")
        self.assertEqual(pars.AST.children[1].children[15].children[0].children[0].children[1].type, "Identifier")
        self.assertEqual(pars.AST.children[1].children[15].children[0].children[0].children[1].children[0], "a")

        #TODO add more operators pars.AST.visit() 
        self.assertEqual(len(pars.AST.children), 2)   

    def test_parse_assignments(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_assignments.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        self.assertEqual(pars.AST.type, "RootNode")
        self.assertEqual(pars.AST.children[0].type, "VarDeclList") 
        self.assertEqual(pars.AST.children[1].type, "VarDeclList") 
        self.assertEqual(pars.AST.children[2].type, "Function")
        self.assertEqual(pars.AST.children[2].children[0].type, "Assignment")
        self.assertEqual(pars.AST.children[2].children[0].children[0].type, "Expression")
        self.assertEqual(pars.AST.children[2].children[0].children[0].children[0].type, "PlusPlusPost")
        self.assertEqual(pars.AST.children[2].children[1].type, "Assignment")
        self.assertEqual(pars.AST.children[2].children[1].children[0].type, "Expression")
        self.assertEqual(pars.AST.children[2].children[1].children[0].children[0].type, "PlusPlusPre")
        self.assertEqual(pars.AST.children[2].children[2].type, "Assignment")
        self.assertEqual(pars.AST.children[2].children[2].children[0].type, "Expression")
        self.assertEqual(pars.AST.children[2].children[2].children[0].children[0].type, "MinusMinusPre")
        self.assertEqual(pars.AST.children[2].children[3].type, "Assignment")
        self.assertEqual(pars.AST.children[2].children[3].children[0].children[0].type, "Times")
        self.assertEqual(pars.AST.children[2].children[3].children[0].children[0].children[0].type, "PlusPlusPre")
        self.assertEqual(pars.AST.children[2].children[3].children[0].children[0].children[1].type, "PlusPlusPost")
        self.assertEqual(pars.AST.children[2].children[4].type, "Assignment")
        self.assertEqual(pars.AST.children[2].children[4].children[0].children[0].type, "Times")
        self.assertEqual(pars.AST.children[2].children[4].children[0].children[0].children[0].type, "Times")
        self.assertEqual(pars.AST.children[2].children[4].children[0]. \
                        children[0].children[0].children[0].type, "PlusPlusPre")
        self.assertEqual(pars.AST.children[2].children[4].children[0]. \
                        children[0].children[0].children[1].type, "PlusPlusPost")
        self.assertEqual(pars.AST.children[2].children[4].children[0]. \
                        children[0].children[0].children[1].type, "PlusPlusPost")
        self.assertEqual(len(pars.AST.children), 3) 

    def test_parse_for_loop(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_for_loop.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        self.assertEqual(len(pars.AST.children), 1) #TODO add more asserts

    def test_parse_while_loop(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_while_loop.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        self.assertEqual(len(pars.AST.children), 1) #TODO add more asserts

    def test_parse_while_loop_nobraces(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_while_loop_nobraces.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        self.assertEqual(len(pars.AST.children), 1) #TODO add more asserts

    def test_parse_do_while_loop(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_do_while_loop.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        self.assertEqual(len(pars.AST.children), 1) #TODO add more asserts

    def test_parse_simple_function(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_simple_function.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        self.assertEqual(len(pars.AST.children), 4) #TODO add more asserts

    def test_parse_function_ref_arg(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_function_ref_arg.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        self.assertEqual(len(pars.AST.children), 1) #TODO add more asserts

    def test_parse_expression(self):
        parser = expressionParser

        res = parser.parse_expression("")
        #should not fail
        self.assertFalse(res)

        res = parser.parse_expression(" ")
        #should not fail
        self.assertFalse(res)

        res = parser.parse_expression("5")
        self.assertEqual(res.type, "Number")
        self.assertEqual(res.leaf, 5)
  
        res = parser.parse_expression("5 > 5")
        self.assertEqual(res.type, "Greater") 
        self.assertEqual(res.children[0].type, "Number")
        self.assertEqual(res.children[0].leaf, 5)
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 5)

        res = parser.parse_expression("5 != 5")
        #res.visit()
        self.assertEqual(res.type, "NotEqual") 
        self.assertEqual(res.children[0].type, "Number")
        self.assertEqual(res.children[0].leaf, 5)
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 5)

        res = parser.parse_expression("!True")
        self.assertEqual(res.type, "UnaryNot")
        self.assertEqual(res.children[0].type, 'True')
  
        res = parser.parse_expression("5 && 4")
        self.assertEqual(res.type, "And")
        self.assertEqual(res.children[0].type, "Number")
        self.assertEqual(res.children[0].leaf, 5)
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 4)

        res = parser.parse_expression("5 and 4")
        res.visit()
        self.assertEqual(res.type, "And")
        self.assertEqual(res.children[0].type, "Number")
        self.assertEqual(res.children[0].leaf, 5)
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 4)

        res = parser.parse_expression("!(5 && 4)")
        self.assertEqual(res.type, "UnaryNot")
        self.assertEqual(res.children[0].type, "And")
        self.assertEqual(res.children[0].children[0].type, "Number")
        self.assertEqual(res.children[0].children[0].leaf, 5)
        self.assertEqual(res.children[0].children[1].type, "Number")
        self.assertEqual(res.children[0].children[1].leaf, 4)

        res = parser.parse_expression("not (5 && 4)")
        self.assertEqual(res.type, "UnaryNot")
        self.assertEqual(res.children[0].type, "And")
        self.assertEqual(res.children[0].children[0].type, "Number")
        self.assertEqual(res.children[0].children[0].leaf, 5)
        self.assertEqual(res.children[0].children[1].type, "Number")
        self.assertEqual(res.children[0].children[1].leaf, 4)

        res = parser.parse_expression("5 || 4")
        self.assertEqual(res.type, "Or")
        self.assertEqual(res.children[0].type, "Number")
        self.assertEqual(res.children[0].leaf, 5)
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 4)

        res = parser.parse_expression("5 or 4")
        self.assertEqual(res.type, "Or")
        self.assertEqual(res.children[0].type, "Number")
        self.assertEqual(res.children[0].leaf, 5)
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 4)
  
        res = parser.parse_expression("5 < 5 and 4 > 3")
        self.assertEqual(res.type, "And")
        self.assertEqual(res.children[0].type, "Less")
        self.assertEqual(res.children[0].children[0].type, "Number")
        self.assertEqual(res.children[0].children[0].leaf, 5)
        self.assertEqual(res.children[0].children[1].type, "Number")
        self.assertEqual(res.children[0].children[1].leaf, 5)
  
        res = parser.parse_expression("3 * 2 + 4")
        self.assertEqual(res.type, "Plus")
        self.assertEqual(res.children[0].type, "Times")
        self.assertEqual(res.children[0].children[0].type, "Number")
        self.assertEqual(res.children[0].children[0].leaf, 3)
        self.assertEqual(res.children[0].children[1].type, "Number")
        self.assertEqual(res.children[0].children[1].leaf, 2)
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 4)

        res = parser.parse_expression("Viking1.safe and Viking2.safe") #TODO add struct support
        self.assertEqual(res.type, "And")
        self.assertEqual(res.children[0].type, "Identifier")
        print res.children[0]
        self.assertEqual(res.children[0].children[0], "Viking1")
        self.assertEqual(res.children[0].children[1].type, "Identifier")
        self.assertEqual(res.children[0].children[1].children[0], "safe")
        self.assertEqual(res.children[1].type, "Identifier")
        self.assertEqual(res.children[1].children[0], "Viking2")
        self.assertEqual(res.children[1].children[1].type, "Identifier")
        self.assertEqual(res.children[1].children[1].children[0], "safe")

        res = parser.parse_expression(
            "Viking1.safe and Viking2.safe and Viking3.safe and Viking4.safe")
        self.assertEqual(res.type, "And")
        self.assertEqual(res.children[0].type, "And")
        self.assertEqual(res.children[1].type, "Identifier")
        self.assertEqual(res.children[1].children[0], "Viking4")
        self.assertEqual(res.children[1].children[1].type, "Identifier")
        self.assertEqual(res.children[1].children[1].children[0], "safe")

        self.assertEqual(res.children[0].children[0].type, "And")
        self.assertEqual(res.children[0].children[1].type, "Identifier")
        self.assertEqual(res.children[0].children[1].children[0], "Viking3")
        self.assertEqual(res.children[0].children[1].children[1].type, "Identifier")
        self.assertEqual(res.children[0].children[1].children[1].children[0], "safe")

        self.assertEqual(res.children[0].children[0].children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0].children[0].children[0], "Viking1")
        self.assertEqual(res.children[0].children[0].children[0].children[1].type, "Identifier")
        self.assertEqual(res.children[0].children[0].children[0].children[1].children[0], "safe")
        self.assertEqual(res.children[0].children[0].children[1].type, "Identifier")
        self.assertEqual(res.children[0].children[0].children[1].children[0], "Viking2")
        self.assertEqual(res.children[0].children[0].children[1].children[1].type, "Identifier")
        self.assertEqual(res.children[0].children[0].children[1].children[1].children[0], "safe")

        res = parser.parse_expression("N - 1")
        self.assertEqual(res.type, "Minus") 
        self.assertEqual(res.children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0], 'N')
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 1)

        res = parser.parse_expression("f() == 2")
        self.assertEqual(res.type, "Equal") 
        self.assertEqual(res.children[0].type, "FunctionCall")
        self.assertEqual(res.children[0].children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0].children[0], "f")
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 2)

        res = parser.parse_expression("dbm.isEmpty()")
        self.assertEqual(res.type, "FunctionCall") 
        self.assertEqual(res.children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0], "dbm")
        self.assertEqual(res.children[0].children[1].type, "Identifier")
        self.assertEqual(res.children[0].children[1].children[0], "isEmpty")

        res = parser.parse_expression("a[42]")
        res.visit()
        self.assertEqual(res.type, "Identifier")
        self.assertEqual(res.strname, "a")
        indexList = res.indexList
        self.assertEqual(indexList.type, "IndexList")
        self.assertEqual(len(indexList.children), 1)
        self.assertEqual(indexList.children[0].type, "Index")
        self.assertEqual(indexList.children[0].leaf.type, "Number")
        self.assertEqual(indexList.children[0].leaf.leaf, 42)
        self.assertEqual(res.dotchild, None)
        

    def test_parse_expression2(self):
        parser = expressionParser

        res = parser.parse_expression("(N - 0 - 1)")
        self.assertEqual(res.type, "Minus")
        self.assertEqual(res.children[0].type, "Minus")
        self.assertEqual(res.children[0].children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0].children[0], 'N')
        self.assertEqual(res.children[0].children[1].type, "Number")
        self.assertEqual(res.children[0].children[1].leaf, 0)
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 1)

        res = parser.parse_expression("-42")
        self.assertEqual(res.type, "UnaryMinus")
        self.assertEqual(res.children[0].type, "Number")
        self.assertEqual(res.children[0].leaf, 42)

        res = parser.parse_expression("-(42+1)")
        self.assertEqual(res.type, "UnaryMinus")
        self.assertEqual(res.children[0].type, "Plus")
        self.assertEqual(res.children[0].children[0].type, "Number")
        self.assertEqual(res.children[0].children[0].leaf, 42)
        self.assertEqual(res.children[0].children[1].type, "Number")
        self.assertEqual(res.children[0].children[1].leaf, 1)

        res = parser.parse_expression("N- 0- 1")
        self.assertEqual(res.type, "Minus")
        self.assertEqual(res.children[0].type, "Minus")
        self.assertEqual(res.children[0].children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0].children[0], 'N')
        self.assertEqual(res.children[0].children[1].type, "Number")
        self.assertEqual(res.children[0].children[1].leaf, 0)
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 1)


        res = parser.parse_expression("N-0-1")
        self.assertEqual(res.type, "Minus")
        self.assertEqual(res.children[0].type, "Minus")
        self.assertEqual(res.children[0].children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0].children[0], 'N')
        self.assertEqual(res.children[0].children[1].type, "Number")
        self.assertEqual(res.children[0].children[1].leaf, 0)
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 1)

        res = parser.parse_expression("(x == 5 && y == 4)")
        self.assertEqual(res.type, "And")
        self.assertEqual(res.children[0].type, "Equal")
        self.assertEqual(res.children[0].children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0].children[0], 'x')
        self.assertEqual(res.children[0].children[1].type, "Number")
        self.assertEqual(res.children[0].children[1].leaf, 5)
        self.assertEqual(res.children[1].children[0].type, "Identifier")
        self.assertEqual(res.children[1].children[0].children[0], 'y')
        self.assertEqual(res.children[1].children[1].type, "Number")
        self.assertEqual(res.children[1].children[1].leaf, 4)

        res = parser.parse_expression("True")
        self.assertEqual(res.type, "True")

        res = parser.parse_expression("true")
        res.visit()
        self.assertEqual(res.type, "True")

        res = parser.parse_expression("x[0][1] == True")
        self.assertEqual(res.type, "Equal")
        self.assertEqual(res.children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0], 'x')
        self.assertEqual(res.children[0].leaf.type, "IndexList")
        self.assertEqual(res.children[0].leaf.children[0].type, "Index")
        self.assertEqual(res.children[0].leaf.children[0].leaf.type, 'Number')
        self.assertEqual(res.children[0].leaf.children[0].leaf.leaf, 0)
        self.assertEqual(res.children[0].leaf.children[1].type, "Index")
        self.assertEqual(res.children[0].leaf.children[1].leaf.type, 'Number')
        self.assertEqual(res.children[0].leaf.children[1].leaf.leaf, 1)
        self.assertEqual(res.children[1].type, "True")

        res = parser.parse_expression("msg[ 0 ][ N - 0 - 1 ] == True")
        self.assertEqual(res.type, "Equal")
        self.assertEqual(res.children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0], 'msg')
        self.assertEqual(res.children[0].leaf.type, "IndexList")
        self.assertEqual(res.children[0].leaf.children[0].type, "Index")
        self.assertEqual(res.children[0].leaf.children[0].leaf.type, 'Number')
        self.assertEqual(res.children[0].leaf.children[0].leaf.leaf, 0)
        self.assertEqual(res.children[0].leaf.children[1].type, "Index")
        index2 = res.children[0].leaf.children[1].leaf
        self.assertEqual(index2.type, 'Minus')
        self.assertEqual(index2.children[0].type, 'Minus')
        self.assertEqual(index2.children[0].children[0].type, 'Identifier')
        self.assertEqual(index2.children[0].children[0].children[0], 'N')
        self.assertEqual(index2.children[0].children[1].type, 'Number')
        self.assertEqual(index2.children[0].children[1].leaf, 0)
        self.assertEqual(res.children[1].type, "True")


    def test_parse_expression3(self):
        parser = expressionParser

        res = parser.parse_expression("(x == true) && (0 > N-0-1)")
        self.assertEqual(res.type, 'And')
        self.assertEqual(len(res.children), 2)
        self.assertEqual(res.children[0].type, 'Equal')
        self.assertEqual(res.children[0].children[0].type, 'Identifier')
        self.assertEqual(res.children[0].children[0].children[0], 'x')
        self.assertEqual(res.children[0].children[1].type, 'True')
        self.assertEqual(res.children[1].type, 'Greater')
        self.assertEqual(res.children[1].children[0].type, 'Number')
        self.assertEqual(res.children[1].children[0].leaf, 0)
        self.assertEqual(res.children[1].children[1].type, 'Minus')
        self.assertEqual(res.children[1].children[1].children[0].type, 'Minus')
        self.assertEqual(res.children[1].children[1].children[0].children[0].type, 'Identifier')
        self.assertEqual(res.children[1].children[1].children[0].children[0].children[0], 'N')
        self.assertEqual(res.children[1].children[1].children[0].children[1].type, 'Number')
        self.assertEqual(res.children[1].children[1].children[0].children[1].leaf, 0)
        self.assertEqual(res.children[1].children[1].children[1].type, 'Number')
        self.assertEqual(res.children[1].children[1].children[1].leaf, 1)

        res = parser.parse_expression("x == true && (0 > N-0-1)")
        self.assertEqual(res.type, 'And')
        self.assertEqual(len(res.children), 2)
        self.assertEqual(res.children[0].type, 'Equal')
        self.assertEqual(res.children[0].children[0].type, 'Identifier')
        self.assertEqual(res.children[0].children[0].children[0], 'x')
        self.assertEqual(res.children[0].children[1].type, 'True')
        self.assertEqual(res.children[1].type, 'Greater')
        self.assertEqual(res.children[1].children[0].type, 'Number')
        self.assertEqual(res.children[1].children[0].leaf, 0)
        self.assertEqual(res.children[1].children[1].type, 'Minus')
        self.assertEqual(res.children[1].children[1].children[0].type, 'Minus')
        self.assertEqual(res.children[1].children[1].children[0].children[0].type, 'Identifier')
        self.assertEqual(res.children[1].children[1].children[0].children[0].children[0], 'N')
        self.assertEqual(res.children[1].children[1].children[0].children[1].type, 'Number')
        self.assertEqual(res.children[1].children[1].children[0].children[1].leaf, 0)
        self.assertEqual(res.children[1].children[1].children[1].type, 'Number')
        self.assertEqual(res.children[1].children[1].children[1].leaf, 1)

    def test_parse_expression4(self):
        parser = expressionParser

        res = parser.parse_expression("x' == 0")
        res.visit()
        self.assertEqual(res.type, 'Equal')
        self.assertEqual(res.children[0].type, 'ClockRate')
        self.assertEqual(res.children[0].leaf, 'x')
        self.assertEqual(res.children[1].type, 'Number')
        self.assertEqual(res.children[1].leaf, 0)

        res = parser.parse_expression("y >= 5 && x' == 0")
        res.visit()
        self.assertEqual(res.type, 'And')
        self.assertEqual(len(res.children), 2)
        self.assertEqual(res.children[0].type, 'GreaterEqual')
        self.assertEqual(res.children[0].children[0].type, 'Identifier')
        self.assertEqual(res.children[0].children[0].children[0], 'y')
        self.assertEqual(res.children[0].children[1].type, 'Number')
        self.assertEqual(res.children[0].children[1].leaf, 5)

        self.assertEqual(res.children[1].type, 'Equal')
        self.assertEqual(res.children[1].children[0].type, 'ClockRate')
        self.assertEqual(res.children[1].children[0].leaf, 'x')
        self.assertEqual(res.children[1].children[1].type, 'Number')
        self.assertEqual(res.children[1].children[1].leaf, 0)

    def test_parse_expression_conditional_operator(self):
        parser = expressionParser

        res = parser.parse_expression("1 ? 42 : 0")
        self.assertEqual(res.type, "Conditional") 
        self.assertEqual(res.children[0].type, "Number")
        self.assertEqual(res.children[0].leaf, 1)
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 42)
        self.assertEqual(res.children[2].type, "Number")
        self.assertEqual(res.children[2].leaf, 0)


        res = parser.parse_expression("1 ? (42+3) : (0*3)")
        self.assertEqual(res.type, "Conditional") 
        self.assertEqual(res.children[0].type, "Number") 
        self.assertEqual(res.children[0].leaf, 1)
        self.assertEqual(res.children[1].type, "Plus")
        self.assertEqual(res.children[2].type, "Times")

        res = parser.parse_expression("(1 == 1 ? 3 :6) ")
        self.assertEqual(res.children[0].type, "Equal") 
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[2].type, "Number")

    
    def test_parse_expression_nested_conditional_operator(self):
        parser = expressionParser
        res = parser.parse_expression("1 ? (0 ? 0 : 42) : (0*3)")

        self.assertEqual(res.type, "Conditional") 
        self.assertEqual(res.children[0].type, "Number")
        self.assertEqual(res.children[1].type, "Conditional") 
        self.assertEqual(res.children[1].children[0].type, "Number")
        self.assertEqual(res.children[1].children[1].type, "Number")
        self.assertEqual(res.children[1].children[2].type, "Number")
        self.assertEqual(res.children[2].type, "Times")

    def test_parse_func_with_params(self):
        parser = expressionParser

        res = parser.parse_expression("ishit(4)")
        self.assertEqual(res.type, "FunctionCall")
        self.assertEqual(res.children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0], "ishit")
        #parameters
        self.assertEqual(len(res.leaf), 1)
        self.assertEqual(res.leaf[0].type, "Number")
        self.assertEqual(res.leaf[0].leaf, 4)

        res = parser.parse_expression("cache.ishit(4)")
        self.assertEqual(res.type, "FunctionCall")
        self.assertEqual(res.children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0], "cache")
        self.assertEqual(res.children[0].children[1].type, "Identifier")
        self.assertEqual(res.children[0].children[1].children[0], "ishit")
        #parameters
        self.assertEqual(len(res.leaf), 1)
        self.assertEqual(res.leaf[0].type, "Number")
        self.assertEqual(res.leaf[0].leaf, 4)


        res = parser.parse_expression("cache.ishit(acc)")
        self.assertEqual(res.type, "FunctionCall")
        self.assertEqual(res.children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0], "cache")
        self.assertEqual(res.children[0].children[1].type, "Identifier")
        self.assertEqual(res.children[0].children[1].children[0], "ishit")
        #parameters
        self.assertEqual(len(res.leaf), 1)
        self.assertEqual(res.leaf[0].type, "Identifier")
        self.assertEqual(res.leaf[0].children[0], "acc")

        res = parser.parse_expression("ishit(4, 5, x, True, a.b.c)")
        res.visit()
        self.assertEqual(res.type, "FunctionCall")
        self.assertEqual(res.children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0], "ishit")
        #parameters
        self.assertEqual(len(res.leaf), 5)
        self.assertEqual(res.leaf[0].type, "Number")
        self.assertEqual(res.leaf[0].leaf, 4)
        self.assertEqual(res.leaf[1].type, "Number")
        self.assertEqual(res.leaf[1].leaf, 5)
        self.assertEqual(res.leaf[2].type, "Identifier")
        self.assertEqual(res.leaf[2].children[0], "x")
        self.assertEqual(res.leaf[3].type, "True")
        self.assertEqual(res.leaf[4].type, "Identifier")
        self.assertEqual(res.leaf[4].children[0], "a")
        self.assertEqual(res.leaf[4].children[1].type, "Identifier")
        self.assertEqual(res.leaf[4].children[1].children[0], "b")
        self.assertEqual(res.leaf[4].children[1].children[1].type, "Identifier")
        self.assertEqual(res.leaf[4].children[1].children[1].children[0], "c")

    def test_parse_array_index_expression(self):
        parser = expressionParser

        res = parser.parse_expression("a[1] == 2")
        self.assertEqual(res.type, "Equal") 
        self.assertEqual(res.children[0].type, "Identifier")
        self.assertEqual(res.children[0].leaf.type, "IndexList")
        self.assertEqual(res.children[0].leaf.children[0].type, "Index")
        self.assertEqual(res.children[0].leaf.children[0].leaf.type, "Number")
        self.assertEqual(res.children[0].leaf.children[0].leaf.leaf, 1)
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 2)

        res = parser.parse_expression("N-1")
        self.assertEqual(res.type, "Minus") 
        self.assertEqual(res.children[0].type, "Identifier")
        self.assertEqual(res.children[0].children[0], 'N')
        self.assertEqual(res.children[1].type, "Number")
        self.assertEqual(res.children[1].leaf, 1)

    def test_parse_array_index_mixed_expression(self):
        parser = expressionParser

        res = parser.parse_expression("a[1].foo")
        res.visit()
        self.assertEqual(res.type, "Identifier")
        ident = res

        self.assertEqual(len(ident.children), 2)
        self.assertEqual(ident.children[0], "a")
        self.assertEqual(ident.leaf.type, "IndexList")
        indexlist = ident.leaf

        self.assertEqual(len(indexlist.children), 1)
        self.assertEqual(indexlist.children[0].type, "Index")
        self.assertEqual(indexlist.children[0].leaf.type, "Number")
        self.assertEqual(indexlist.children[0].leaf.leaf, 1)
        
        self.assertEqual(ident.children[1].type, "Identifier")
        self.assertEqual(ident.children[1].children[0], "foo")


        res = parser.parse_expression("a.foo.bar.baz")
        res.visit()
        self.assertEqual(res.type, "Identifier")
        ident = res

        self.assertEqual(len(ident.children), 2)
        self.assertEqual(ident.children[0], "a")

        dot = ident.children[1]
        self.assertEqual(len(dot.children), 2)
        self.assertEqual(dot.type, "Identifier")
        self.assertEqual(dot.children[0], "foo")

        dot = dot.children[1]
        self.assertEqual(len(dot.children), 2)
        self.assertEqual(dot.type, "Identifier")
        self.assertEqual(dot.children[0], "bar")

        dot = dot.children[1]
        self.assertEqual(len(dot.children), 1)
        self.assertEqual(dot.type, "Identifier")
        self.assertEqual(dot.children[0], "baz")


        res = parser.parse_expression("a.foo[2].bar[i].baz")
        res.visit()
        self.assertEqual(res.type, "Identifier")
        ident = res

        self.assertEqual(len(ident.children), 2)
        self.assertEqual(ident.children[0], "a")

        dot = ident.children[1]
        self.assertEqual(len(dot.children), 2)
        self.assertEqual(dot.type, "Identifier")
        self.assertEqual(dot.children[0], "foo")
        indexlist = dot.leaf
        self.assertEqual(indexlist.type, "IndexList")
        self.assertEqual(len(indexlist.children), 1)
        index = indexlist.children[0]
        self.assertEqual(index.type, "Index")
        self.assertEqual(index.leaf.type, "Number")
        self.assertEqual(index.leaf.leaf, 2)

        dot = dot.children[1]
        self.assertEqual(len(dot.children), 2)
        self.assertEqual(dot.type, "Identifier")
        self.assertEqual(dot.children[0], "bar")
        indexlist = dot.leaf
        self.assertEqual(indexlist.type, "IndexList")
        self.assertEqual(len(indexlist.children), 1)
        index = indexlist.children[0]
        self.assertEqual(index.type, "Index")
        self.assertEqual(index.leaf.type, "Identifier")
        self.assertEqual(index.leaf.children[0], "i")

        dot = dot.children[1]
        self.assertEqual(len(dot.children), 1)
        self.assertEqual(dot.type, "Identifier")
        self.assertEqual(dot.children[0], "baz")


        res = parser.parse_expression("a[1][2][3].foo")
        res.visit()
        self.assertEqual(res.type, "Identifier")
        ident = res

        self.assertEqual(len(ident.children), 2)
        self.assertEqual(ident.children[0], "a")
        self.assertEqual(ident.leaf.type, "IndexList")
        indexlist = ident.leaf

        self.assertEqual(len(indexlist.children), 3)
        self.assertEqual(indexlist.children[0].type, "Index")
        self.assertEqual(indexlist.children[0].leaf.type, "Number")
        self.assertEqual(indexlist.children[0].leaf.leaf, 1)
        self.assertEqual(indexlist.children[1].type, "Index")
        self.assertEqual(indexlist.children[1].leaf.type, "Number")
        self.assertEqual(indexlist.children[1].leaf.leaf, 2)
        self.assertEqual(indexlist.children[2].type, "Index")
        self.assertEqual(indexlist.children[2].leaf.type, "Number")
        self.assertEqual(indexlist.children[2].leaf.leaf, 3)
        
        self.assertEqual(ident.children[1].type, "Identifier")
        self.assertEqual(ident.children[1].children[0], "foo")

    def test_parse_extern(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_extern.txt'), "r")

        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        res = pars.AST.children

        #pars.AST.visit()

        declvisitor = parser.DeclVisitor(pars)
        declvisitor.visit(pars.AST)

    def test_parse_extern2(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_extern2.txt'), "r")

        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        res = pars.AST.children

        pars.AST.visit()

        declvisitor = parser.DeclVisitor(pars)
        declvisitor.visit(pars.AST)

        self.assertTrue('TestExternalLattice' in pars.externList)

        self.assertEqual(declvisitor.get_type('mylat'), 'TestExternalLattice')

    def test_parse_extern3(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_extern3.txt'), "r")

        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        res = pars.AST.children

        pars.AST.visit()

        declvisitor = parser.DeclVisitor(pars)
        declvisitor.visit(pars.AST)

        self.assertTrue('WideningIntRange' in pars.externList)

        self.assertEqual(declvisitor.get_type('x'), 'WideningIntRange')

        wideningIntRangeTypeNode = pars.typedefDict['WideningIntRange']

        print "typedefdict:"
        wideningIntRangeTypeNode.visit()

        self.assertEqual(wideningIntRangeTypeNode.leaf.type, "Identifier")
        self.assertEqual(wideningIntRangeTypeNode.leaf.children[0], "WideningIntRange")
        
        self.assertEqual(len(wideningIntRangeTypeNode.children), 1)
        self.assertEqual(wideningIntRangeTypeNode.children[0].type, 'FunctionCall')
        parameters = wideningIntRangeTypeNode.children[0].leaf
        self.assertEqual(len(parameters), 4)
        self.assertEqual(parameters[0].leaf, 1)
        self.assertEqual(parameters[1].leaf, 2)
        self.assertEqual(parameters[2].leaf, 3)
        self.assertEqual(parameters[3].leaf, 9)



    def test_parse_extern_dbm(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_extern_dbm.txt'), "r")

        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        res = pars.AST.children

        declvisitor = parser.DeclVisitor(pars)
        declvisitor.visit(pars.AST)

        self.assertEqual(len(declvisitor.variables), 5)

        self.assertEqual(tuple(declvisitor.variables[0]), ('dbm', 'DBMFederation', [], None))
        self.assertEqual(tuple(declvisitor.variables[1]), ('dbm.x', 'DBMClock', [], None))
        self.assertEqual(tuple(declvisitor.variables[2]), ('dbm.c', 'DBMClock', [], None))
        self.assertEqual(declvisitor.variables[3].identifier, 'dbm.y') #('dbm.y', 'DBMClock', [10])
        self.assertEqual(declvisitor.variables[3].vartype, 'DBMClock')
        self.assertEqual(declvisitor.variables[3].array_dimensions[0].children[0].leaf, 10)
        self.assertEqual(declvisitor.variables[4].identifier, 'dbm.z') #('dbm.z', 'DBMClock', [10, 20])
        self.assertEqual(declvisitor.variables[4].vartype, 'DBMClock')
        self.assertEqual(declvisitor.variables[4].array_dimensions[0].children[0].leaf, 10)
        self.assertEqual(declvisitor.variables[4].array_dimensions[1].children[0].leaf, 20)

    def test_parse_extern_octagon(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_extern_octagon.txt'), "r")

        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        res = pars.AST.children
        pars.AST.visit()


        declvisitor = parser.DeclVisitor(pars)
        declvisitor.visit(pars.AST)

        self.assertTrue('ApronOctagon' in pars.externList)

        self.assertEqual(declvisitor.get_type('oct'), 'ApronOctagon')

        octTypeNode = pars.typedefDict['ApronOctagon']

        self.assertEqual(octTypeNode.leaf.type, "Identifier")
        self.assertEqual(octTypeNode.leaf.children[0], "ApronOctagon")
        
        self.assertEqual(declvisitor.get_vardecl('i').basic_type, 'TypeExternChild')
        self.assertEqual(declvisitor.get_type('i'), ['oct', 'intvar'])
        self.assertEqual(declvisitor.get_vardecl('f').basic_type, 'TypeExternChild')
        self.assertEqual(declvisitor.get_type('f'), ['oct', 'floatvar'])

    def test_parse_constants(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_parse_constants.txt'), "r")

        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        res = pars.AST.children

        #pars.AST.visit()

        declvisitor = parser.DeclVisitor(pars)
        declvisitor.visit(pars.AST)


        inorder = ["a", "b", "c", "d", "N"]
        #should return the constants in file order
        self.assertEqual(declvisitor.constants.keys(), inorder)

    def test_parse_declare_intrange(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_declare_intrange.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        pars.AST.visit()

        self.assertEqual(pars.AST.children[0].type, "VarDeclList") 
        self.assertEqual(pars.AST.children[0].leaf.type, 'TypeInt')

        vdecl = pars.AST.children[0].children[0]
        self.assertEqual(vdecl.type, "VarDecl")
        self.assertEqual(vdecl.children[0].children[0], "i")

        self.assertEqual(vdecl.range_min.type, "Number")
        self.assertEqual(vdecl.range_min.leaf, 0)
        self.assertEqual(vdecl.range_max.type, "Number")
        self.assertEqual(vdecl.range_max.leaf, 4)
        
        self.assertEqual(pars.AST.children[0].leaf.children[0].type, "Expression")
        self.assertEqual(pars.AST.children[0].leaf.children[0].children[0].leaf, 0)
        self.assertEqual(pars.AST.children[0].leaf.children[1].type, "Expression")
        self.assertEqual(pars.AST.children[0].leaf.children[1].children[0].leaf, 4)

        declvisitor = parser.DeclVisitor(pars)
        declvisitor.visit(pars.AST)
        vardecl_i = declvisitor.get_vardecl("i")
        self.assertEqual(vardecl_i.range_min.type, "Number")
        self.assertEqual(vardecl_i.range_min.leaf, 0)
        self.assertEqual(vardecl_i.range_max.type, "Number")
        self.assertEqual(vardecl_i.range_max.leaf, 4)
        
        vardecl_i = declvisitor.get_vardecl("j")
        #self.assertEqual(vardecl_j.range, (-32767, 32767))
        self.assertEqual(vardecl_i.range_min.type, "Number")
        self.assertEqual(vardecl_i.range_min.leaf, -32767)
        self.assertEqual(vardecl_i.range_max.type, "Number")
        self.assertEqual(vardecl_i.range_max.leaf, 32767)

    def test_parse_if_elseif(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_if_elseif.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        pars.AST.visit()

        ifnode = pars.AST.children[0].children[0]

        ifbodynode = ifnode.children[0]
        elseifbodynode = ifnode.children[1]
        elsebodynode = ifnode.children[2]

        self.assertEqual(ifnode.leaf, [])

        self.assertEqual(ifbodynode.leaf[0].children[0].type, "Number")
        self.assertEqual(ifbodynode.leaf[0].children[0].leaf, 4)

        self.assertEqual(elseifbodynode.leaf[0].children[0].type, "Number")
        self.assertEqual(elseifbodynode.leaf[0].children[0].leaf, 3)

    def test_parse_function_typedef_return(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_function_typedef_return.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        declvisitor = parser.DeclVisitor(pars)
        declvisitor.visit(pars.AST)

        self.assertEqual(len(declvisitor.functions), 2)
        foo = declvisitor.functions[0]
        self.assertEqual(foo.leaf[1].children[0], "foo")
        self.assertEqual(foo.basic_type, "TypeInt")

        bar = declvisitor.functions[1]
        self.assertEqual(bar.leaf[1].children[0], "bar")
        self.assertEqual(bar.basic_type, "TypeVoid")

    def test_parse_array_types(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_array_types.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        res = pars.AST.children
        pars.AST.visit()

        self.assertEqual(res[1].type, "VarDeclList")
        self.assertEqual(res[1].children[0].type, "VarDecl")
        self.assertEqual(res[1].children[0].children[0].type, "Identifier")
        self.assertEqual(res[1].children[0].children[0].leaf.type, "IndexList")
        self.assertEqual(res[1].children[0].children[0].leaf.children[0].type, "Index")
        self.assertEqual(res[1].children[0].children[0].leaf.children[0].leaf.type, "NodeTypedef")

        self.assertEqual(res[2].type, "VarDeclList")
        self.assertEqual(res[2].children[0].type, "VarDecl")
        self.assertEqual(res[2].children[0].children[0].type, "Identifier")
        self.assertEqual(res[2].children[0].children[0].leaf.type, "IndexList")
        self.assertEqual(res[2].children[0].children[0].leaf.children[0].type, "Index")
        self.assertEqual(res[2].children[0].children[0].leaf.children[0].leaf.type, "TypeInt")
        self.assertEqual(len(res[2].children[0].children[0].leaf.children[0].leaf.children), 2)
        self.assertEqual(res[2].children[0].children[0].leaf.children[0].leaf.children[0].children[0].type, "Number")
        self.assertEqual(res[2].children[0].children[0].leaf.children[0].leaf.children[0].children[0].leaf, 2)
        self.assertEqual(res[2].children[0].children[0].leaf.children[0].leaf.children[1].children[0].type, "Number")
        self.assertEqual(res[2].children[0].children[0].leaf.children[0].leaf.children[1].children[0].leaf, 4)

        self.assertEqual(res[3].type, "VarDeclList")
        self.assertEqual(res[3].children[0].type, "VarDecl")
        self.assertEqual(res[3].children[0].children[0].type, "Identifier")
        self.assertEqual(res[3].children[0].children[0].leaf.type, "IndexList")
        self.assertEqual(res[3].children[0].children[0].leaf.children[0].type, "Index")
        self.assertEqual(res[3].children[0].children[0].leaf.children[0].leaf.type, "TypeInt")
        self.assertEqual(len(res[3].children[0].children[0].leaf.children[0].leaf.children), 2)
        self.assertEqual(res[3].children[0].children[0].leaf.children[0].leaf.children[0].children[0].type, "Number")
        self.assertEqual(res[3].children[0].children[0].leaf.children[0].leaf.children[0].children[0].leaf, 3)
        self.assertEqual(res[3].children[0].children[0].leaf.children[0].leaf.children[1].children[0].type, "Number")
        self.assertEqual(res[3].children[0].children[0].leaf.children[0].leaf.children[1].children[0].leaf, 4)

    def test_conditional_operator(self):
        test_file = open(os.path.join(os.path.dirname(__file__), 'test_conditional_operator.txt'), "r")
        lex = lexer.lexer
        pars = parser.Parser(test_file.read(), lex)
        res = pars.AST.children
        pars.AST.visit()



if '__name__'  == '__main__':
    unittest.main()
