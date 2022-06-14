""" 
    Copyright (C) 2009 
    Andreas Engelbredt Dalsgaard <andreas.dalsgaard@gmail.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>. 

    This program is based on the public domain example programs from the blog post:
    <http://eli.thegreenplace.net/2009/03/20/a-recursive-descent-parser-with-an-infix-expression-evaluator/>
    made by: Eli Bendersky (eliben@gmail.com)
"""

from lexer import *
from node import *
import operator
import logging
logger = logging.getLogger('expressionParser')
#no debug output by default
logger.setLevel(logging.INFO)

def ternary(condition, if_true, if_false):
    if eval(condition):
        return if_true
    else:
        return if_false

class IllegalExpressionException(Exception):
    pass

def parse_expression(data):
    """Helper function. Parses the string "data" and returns an AST of the
    expression."""
    class myToken:
        type = None
        def __init__(self, type):
            self.type = type

    class DummyHelperParser:
        def __init__(self, lexer):
            self.lex = lexer

        def parse(self, str):
            self.lex.input(str)
            self.currentToken = self.lex.token()
            exParser = ExpressionParser(self.lex, self)
            return exParser.parse()

        def parseNumber(self):
            n = Node('Number', [], self.currentToken.value)
            self.accept('NUMBER')
            return n
       
        def parseExpression(self):
            exParser = ExpressionParser(self.lex, self)
            return exParser.parse()
       
        def parseIndexList(self):
            indexList = []
            
            while self.currentToken.type == 'LBRACKET':
                index = self.parseIndex()
                indexList += [index]
        
            if len(indexList) > 0:
                return Node('IndexList', indexList, None)
            else:
                return None

        def parseIndex(self):
            self.accept('LBRACKET')
            if self.currentToken.type == 'RBRACKET':
                self.error('invalid expression')
                e = None
            else:
                e = self.parseExpression()
            self.accept('RBRACKET')
            return Node('Index', [], e)
  
        def parseIdentifier(self):
            n = Identifier(self.currentToken.value)
            self.accept('IDENTIFIER')
            return n

        def parseIdentifierComplex(self):
            strname = self.currentToken.value
            self.accept('IDENTIFIER')

            indexList = self.parseIndexList()

            dotchild = None
            if self.currentToken.type == 'DOT':
                self.accept('DOT')
                dotchild = self.parseIdentifierComplex()
            return Identifier(strname, indexList, dotchild)

        def accept(self, expectedTokenType):
            if self.currentToken.type == expectedTokenType:
                self.currentToken = self.lex.token()
                if self.currentToken == None:
                    t = myToken('UNKNOWN')
                    self.currentToken = t
            else:
                self.error('at token %s on line %d: Expected %s but was %s' % (self.currentToken.value, self.currentToken.lineno, expectedTokenType, self.currentToken.type))

        def error(self, msg):
            raise IllegalExpressionException('Illegal expression: ' + msg)

    helperParser = DummyHelperParser(lexer)
    return helperParser.parse(data)

class ExpressionParser:

    def __init__(self, lexer, parser):
        self.lexer = lexer
        self.parser = parser

    def parse(self):
        if not self.parser.currentToken: #eof?
            return None
        o = self._infix_eval()
        return o
    ##
    ## The infix expression evaluator. 
    ## Returns the value of the evaluated expression.
    ##
    ## Infix expressions are numbers and identifiers separated by
    ## binary (and unary) operators, possibly with parts delimited
    ## by parentheses. The operators supported by this evaluator
    ## and their precedences are controlled through the _ops 
    ## table.
    ##
    ## Internally, uses two stacks. One for keeping the operations
    ## that still await results, and another for keeping the 
    ## results.
    ##
    ##

    def _infix_eval(self):
        """ Run the infix evaluator and return the result.
        """
        self.op_stack = []
        self.res_stack = []
        
        self.op_stack.append(self._sentinel)
        self._infix_eval_expr()
        try:
            return self.res_stack[-1]
        except:
            self.parser.error("ExpressionParser parsing error")
    
    class Op(object):
        """ Represents an operator recognized by the infix 
            evaluator. Each operator has a numeric precedence, 
            and flags specifying whether it's unary/binary and 
            right/left associative.
        """
        def __init__(   self, name, op, prec, 
                        arguments=2, right_assoc=False):
            self.name = name
            self.op = op
            self.prec = prec

            self.unary = False
            self.binary = False
            self.ternary = False

            if arguments == 2:
                self.binary = True
            elif arguments == 1:
                self.unary = True
            else:
                self.ternary = ternary

            self.right_assoc = right_assoc
            self.left_assoc = not self.right_assoc
            
        def apply(self, *args):
            return Node(self.name, args)

        def precedes(self, other):
            """ The '>' operator from the Shunting Yard algorithm.
                I don't call it '>' on purpose, as its semantics 
                are unusual (i.e. this is not the familiar 
                algebraic '>')
            """
            return self.prec >= other.prec
#            if self.ternary and other.ternary:
#                if self.prec > other.prec:
#                    return True
#                elif self.left_assoc and (self.prec == other.prec):
#                    return True
#            elif self.binary and other.binary:
#                if self.prec > other.prec:
#                    return True
#                elif self.left_assoc and (self.prec == other.prec):
#                    return True
#            elif self.unary and other.binary:
#                return self.prec >= other.prec
            
            return False

        def __repr__(self):
            return '<%s(%s)>' % (self.name, self.prec)
    
    # The operators recognized by the evaluator.
    #
    _ops = {
        'uMINUS':    Op('UnaryMinus', operator.neg, 90, arguments=1),
        'uLNOT':     Op('UnaryNot', operator.not_, 90, arguments=1),
        'uNOT':      Op('UnaryNot', operator.not_, 90, arguments=1),
        'TIMES':     Op('Times', operator.mul, 50),
        'DIVIDE':    Op('Divide', operator.div, 50),
        'MODULO':    Op('Modulo', operator.mod, 50),
        'PLUS':      Op('Plus', operator.add, 40),
        'MINUS':     Op('Minus', operator.sub, 40),
        'LSHIFT':    Op('LeftShift', operator.lshift, 35),
        'RSHIFT':    Op('RightShift', operator.rshift, 35),
        'BITAND':    Op('BitAnd', operator.and_, 30),
        'XOR':       Op('Xor', operator.xor, 29),
        'BITOR':     Op('BitOr', operator.or_, 28),

        'GREATER':   Op('Greater', operator.gt, 20),
        'GREATEREQ': Op('GreaterEqual', operator.ge, 20),
        'LESS':      Op('Less', operator.lt, 20),
        'LESSEQ':    Op('LessEqual', operator.le, 20),
        
        'EQUAL':     Op('Equal', operator.eq, 15),
        'NOTEQUAL':  Op('NotEqual', operator.ne, 15),

        'BITAND':    Op('BitAnd', operator.and_, 14),
        'XOR':       Op('Xor', operator.xor, 13),
        'BITOR':     Op('BitOr', operator.or_, 12),
        'LAND':      Op('And', operator.and_, 11), # && notice the operator is incorrect
        'AND':      Op('And', operator.and_, 11), # && notice the operator is incorrect
        'OR':      Op('Or', operator.or_, 11), # && notice the operator is incorrect
        'LOR':       Op('Or', operator.or_, 11),   # || notice the operator is incorrect 
        'CONDITIONAL':   Op('Conditional', ternary, 10, arguments=3,right_assoc=True),

        #'AND':       Op('And', operator.and_, 10), # and
        #'OR':        Op('Or', operator.or_, 10),   # or
        #XXX, we treat the logical ops the same as their names, e.g.
        # "&&" ~ "and", "!" ~ "not", this is not the same as the uppaal
        #documentation prescribes.
    }          
    
    # A set of operators that can be unary. If such an operator
    # is found, 'u' is prepended to its symbol for finding it in
    # the _ops table
    #
    _unaries = set(['MINUS', 'LNOT', 'NOT'])
    
    # Dummy operator with the lowest possible precedence (the 
    # Sentinel value in the Shunting Yard algorithm)
    #
    _sentinel = Op(None, None, 0)

    def _infix_eval_expr(self):
        """ Evaluates an 'expression' - atoms separated by binary or ternary
            operators.
        """
        self._infix_eval_atom()
        ternary = False

        while ( self.parser.currentToken and
                self.parser.currentToken.type in self._ops and 
                (self._ops[self.parser.currentToken.type].binary or self._ops[self.parser.currentToken.type].ternary)):
            if self._ops[self.parser.currentToken.type].ternary:
                ternary = True
            logger.debug("%s, %s" % (str(self.res_stack), str(self.op_stack)))
            self._push_op(self._ops[self.parser.currentToken.type])
            self._get_next_token()
            self._infix_eval_atom()

            if ternary:
                self._get_next_token()
                self._infix_eval_atom()
                ternary = False
        
        while self.op_stack[-1] != self._sentinel:
            self._pop_op()
        
    def _infix_eval_atom(self):
        """ Evaluates an 'atom' - either an identifier/number, or
            an atom prefixed by a unary operation, or a full
            expression inside parentheses.
        """
        if self.parser.currentToken.type == 'TRUE':
            self.res_stack.append(Node('True'))
            self.parser.accept('TRUE')
        elif self.parser.currentToken.type == 'FALSE':
            self.res_stack.append(Node('False'))
            self.parser.accept('FALSE')
        elif self.parser.currentToken.type in ['IDENTIFIER', 'NUMBER']:
            if self.parser.currentToken.type == 'IDENTIFIER':
                ident = self.parser.parseIdentifierComplex()
                self.res_stack.append(ident)
                if self.parser.currentToken.type == 'PLUSPLUS': #x++
                    identifier = self.res_stack.pop()
                    self.res_stack.append(Node('PlusPlusPost',[identifier]))
                    self.parser.accept('PLUSPLUS')
                elif self.parser.currentToken.type == 'MINUSMINUS': #x--
                    identifier = self.res_stack.pop()
                    self.res_stack.append(Node('MinusMinusPost', [identifier]))
                    self.parser.accept('MINUSMINUS')
                elif self.parser.currentToken.type == 'LPAREN':  #function call, f(..)
                    self.parser.accept('LPAREN')
                    #assert self.parser.currentToken.type == 'RPAREN'
                    parameters = []
                    while self.parser.currentToken.type != 'RPAREN':
                        self.op_stack.append(self._sentinel)
                        self._infix_eval_expr()
                        if self.parser.currentToken.type == 'COMMA':
                            self.parser.accept('COMMA')
                        self.op_stack.pop()
                        expr = self.res_stack.pop()
                        parameters += [expr]
                    self.parser.accept('RPAREN')
                    
                    identifier = self.res_stack.pop()
                    self.res_stack.append(Node('FunctionCall', [identifier], parameters))
                elif self.parser.currentToken.type == 'APOSTROPHE': #x' (used for clock rate "assignment")
                    identifier = self.res_stack.pop()
                    self.res_stack.append(Node('ClockRate', [], identifier.children[0]))
                    self.parser.accept('APOSTROPHE')
           # elif self.parser.currentToken.type == 'CONDITIONAL':
           #     print "con", self.res_stack
            else:
                self.res_stack.append(self.parser.parseNumber())
        elif self.parser.currentToken.type == 'LPAREN':
            self._get_next_token()
            self.op_stack.append(self._sentinel)
            self._infix_eval_expr()
            self.parser.accept('RPAREN')
            self.op_stack.pop()
        elif self.parser.currentToken.type in self._unaries:
            self._push_op(self._ops['u' + self.parser.currentToken.type])
            self._get_next_token()
            self._infix_eval_atom()
        elif self.parser.currentToken.type == 'PLUSPLUS':
            self.parser.accept('PLUSPLUS')
            self.res_stack.append(Node('PlusPlusPre', [self.parser.parseIdentifierComplex()]))
        elif self.parser.currentToken.type == 'MINUSMINUS':
            self.parser.accept('MINUSMINUS')
            self.res_stack.append(Node('MinusMinusPre', [self.parser.parseIdentifierComplex()]))
    
    def _push_op(self, op):
        """ Pushes an operation onto the op stack. 
            But first computes and removes all higher-precedence 
            operators from it.
        """
        logger.debug('push_op: op_stack = %s + %s' , str(self.op_stack), str(op))
        while self.op_stack[-1].precedes(op):
            self._pop_op()
        self.op_stack.append(op)
        logger.debug('     ... op_stack = %s', str(self.op_stack))
    
    def _pop_op(self):
        """ Pops an operation from the op stack, computing its
            result and storing it on the result stack.
        """
        logger.debug('pop_op: op_stack = %s', str(self.op_stack))
        logger.debug('    ... res_stack = %s', str(self.res_stack))
        top_op = self.op_stack.pop()
        
        if top_op.unary:
            self.res_stack.append(top_op.apply(self.res_stack.pop()))
        elif top_op.ternary:
            t2 = self.res_stack.pop()
            t1 = self.res_stack.pop()
            t0 = self.res_stack.pop()
            self.res_stack.append(top_op.apply(t0, t1, t2))
        else:
            if len(self.res_stack) < 2:
                self.parser.error('Not enough arguments for operator %s' % top_op.name)
                
            t1 = self.res_stack.pop()
            t0 = self.res_stack.pop()
            self.res_stack.append(top_op.apply(t0, t1))
        logger.debug('    ... res_stack = %s', str(self.res_stack))

    def _get_next_token(self):
        self.parser.currentToken = self.lexer.token()
