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

from collections import OrderedDict
import copy

from lexer import *
import expressionParser
from node import *
from util import *


class UnexpectedTokenException(Exception):
    pass
    
class Parser(object):

    currentToken = None
    lexer = None
    expressionParser = None
    
    def __init__(self, data, lexer, typedefDict=None):
        self.lexer = lexer
        self.lexer.input(data+'\n')
        self.currentToken = self.lexer.token()

        self.typedefDict = typedefDict or {}
        self.externList = []
        self.identifierTypeDict = {}
        self.inFunction = False
        self.globalIdentifierTypeDict = {}

        children = []        
        if self.currentToken != None:
            children = self.parseStatements()
        self.AST = Node('RootNode', children)
  
    def parseStatements(self):
        statements = []

        try:
            while self.currentToken:
                statements.append(self.parseCurrentStatement())
            return statements
        except UnexpectedTokenException, e:
            self.error('at token "%s" on line %d: Did not expect any token, but found token of type %s' % (self.currentToken.value, self.currentToken.lineno, self.currentToken.type))

    def parseCurrentStatement(self):
        if self.currentToken:
            if self.currentToken.type in ('VOID'): #Function
                type = self.parseFuncType()
                identifier = self.parseIdentifier()
                return self.parseFunction(type, identifier)
            elif self.currentToken.type in ('CLOCK', 'CHANNEL', 'URGENT', 'BROADCAST'): #Declaration
                type = self.parseDeclType()
                identifier = self.parseIdentifierComplex()
                return self.parseDeclaration(type, identifier, isglobal=True)
            elif self.currentToken.type in ('CONST', 'INT', 'BOOL', 'IDENTIFIER'): #Function or declaration           
                isConst = False
                if self.currentToken.type == 'CONST':
                    self.accept('CONST')
                    isConst = True
                type = self.parseStdType(isConst)
                identifier = self.parseIdentifierComplex()
                
                if self.currentToken.type == 'LPAREN':  #TODO check that it is not a complex identifier
                    return self.parseFunction(type, identifier)
                else:
                    return self.parseDeclaration(type, identifier)
            elif self.currentToken.type == 'STRUCT':
                structDecl = self.parseStruct()
                structIden = self.parseIdentifier()
                self.accept('SEMI')
                return Node('Struct', structDecl, structIden)
            elif self.currentToken.type == 'TYPEDEF':
                return self.parseTypedef()
            elif self.currentToken.type == 'EXTERN': #EXTENSION of UPPAAL C language
                return self.parseExtern()
            else:
                raise UnexpectedTokenException()
        else:
            return None


    def parseStruct(self):
        structDecl = []
        self.accept('STRUCT')
        self.accept('LCURLYPAREN')
        while self.currentToken.type in ('INT', 'BOOL', 'IDENTIFIER'): 
            type = self.parseDeclType()
            identifier = self.parseIdentifierComplex()
            structDecl.append(self.parseDeclaration(type, identifier))

        self.accept('RCURLYPAREN')
        return structDecl

    '''
    if called with type is some form of interger/struct variable:
       it should accept:
        int iden0, iden1 = expression; or
        bool iden0[1], iden1[2][3] = {{...},{..},}, iden2[2][3] = {{...},{..}};
       and return a VarDeclList->[Children=list of VarDecl->[Children=[initval, index],Leaf=identifier],Leaf=type]
    if called with type is clock:
       it should accept:
        clock iden0, iden1[2][2];
       and return a ClockList
    if called with type is chan:
       it should accepts:
        chan iden0, iden1[2][2];
        urgent chan iden0, broadcast chan iden1;
       and return a ChannelList
    '''
    #TODO scalars

    def parseDeclaration(self, type, identifier, isglobal=False):
        declList = []
        allowInitVal = True
        nodeType = 'VarDecl'
        defaultValue = None
        
        if type.type in ['TypeClock', 'TypeChannel', 'TypeUrgentChannel', 'TypeBroadcastChannel', 'TypeUrgentBroadcastChannel']:
            allowInitVal = False
            defaultValue = None

            if type.type == 'TypeClock':
                nodeType = 'ClockDecl'
                if 'clock' in self.typedefDict:
                    type = self.typedefDict['clock']
            else:
                nodeType = 'ChannelDecl'

        while True:
            
            if allowInitVal == True and self.currentToken.type in ('EQUALS', 'ASSIGN'):
                self.accept(self.currentToken.type)

                if self.currentToken.type == 'LCURLYPAREN':
                    initVal = self.parseInitializer()
                else:
                    initVal = self.parseExpression()

                if nodeType == 'VarDecl':
                    declList.append(VarDecl(identifier, type, initval=initVal))
                else:
                    declList.append(Node(nodeType, [identifier], initVal,
                        identifier=identifier, initval=initVal))
            else:
                if nodeType == 'VarDecl':
                    declList.append(VarDecl(identifier, type, initval=defaultValue))
                else:
                    declList.append(Node(nodeType, [identifier], defaultValue,
                        identifier=identifier, initval=defaultValue))

            if self.currentToken.type == 'COMMA':
                self.accept('COMMA')
                identifier = self.parseIdentifierComplex()
            else:
                break

        if self.currentToken.type == 'SEMI':           
            self.accept('SEMI')

        for decl in declList:
            if self.inFunction:
                self.identifierTypeDict[get_full_name_from_complex_identifier(decl.identifier)] = type
            else:
                self.globalIdentifierTypeDict[get_full_name_from_complex_identifier(decl.identifier)] = type

        return Node(nodeType+'List', declList, type, 
                vartype=type)

    def parseTypedef(self):
        self.accept('TYPEDEF')
        clockHack = False

        if self.currentToken.type == 'STRUCT':
            structDecl = self.parseStruct()
            if self.currentToken.type == 'IDENTIFIER':
                typeName = self.currentToken.value
                self.accept('IDENTIFIER')
            else:
                typeName = 'ErrorName'
                self.error('Expected identifier')
            n = Node('NodeTypedef', structDecl, typeName)
            self.typedefDict[typeName] = n
            self.accept('SEMI')
            return n
        else:
            if self.currentToken.type == 'CLOCK':
                raise Exception("Currently, we do not allow adding new clock types, e.g., typedef clock rtclock")

            type = self.parseStdType(False)

            if self.currentToken.type == 'IDENTIFIER':
                typeName = self.currentToken.value
                self.accept('IDENTIFIER')
            elif self.currentToken.type == 'CLOCK':
                #allow overriding the clock type, e.g., typedef int clock
                typeName = 'clock'
                clockHack = True
                self.accept('CLOCK')
            else:
                typeName = 'ErrorName'
                self.error('Expected identifier')
           
            if clockHack:
                n = Node('NodeTypedef', [type], type.leaf.children[0])
            else:
                n = Node('NodeTypedef', [type], typeName)

            self.typedefDict[typeName] = n

            self.accept('SEMI')
            return n

    def parseExtern(self):
        self.accept('EXTERN')
        #has the form "extern somelib.somelib.ClassName"
        identnode = self.parseIdentifierComplex()
        n = Node('NodeExtern', [], identnode)
        
        ident = get_last_name_from_complex_identifier(identnode)

        #do we have constructor parameters?
        if self.currentToken.type == 'EQUALS':
            self.accept('EQUALS')
            constructor_call_expr = self.parseExpression()
            assert len(constructor_call_expr.children) == 1
            assert constructor_call_expr.children[0].type == 'FunctionCall'
            constructor_call = constructor_call_expr.children[0]
            n.children = [constructor_call]
        
        self.typedefDict[ident] = n
        self.externList += [ident]

        self.accept('SEMI')
        return n


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
        #can be Type
        elif self.currentToken.type in ('INT', 'BOOL', 'CONST'):
            isConst = False
            if self.currentToken.type == 'CONST':
                self.accept('CONST')
                isConst = True
            e = self.parseStdType(isConst) 
        #can be typedef'ed type
        elif self.currentToken.type in ('IDENTIFIER',) and \
                self.isType(self.currentToken.value):
            e = self.parseTypedefType(self.currentToken.value)
        #or expression
        else:
            e = self.parseExpression()
        self.accept('RBRACKET')
        return Node('Index', [], e, 
                expr=e)

    def parseFunction(self, type, identifier):
        self.inFunction = True #used to determine if variables are global or not
        tmpIdentifierTypeDict = self.identifierTypeDict
        self.identifierTypeDict = {}

        children = []
        self.accept('LPAREN')
        parameters = self.parseParameters()
        self.accept('RPAREN')
        self.accept('LCURLYPAREN')
        children.extend(self.parseBodyStatements())
        self.accept('RCURLYPAREN')

        self.inFunction = False

        funcIdentifierTypeDict = self.identifierTypeDict
        self.identifierTypeDict = tmpIdentifierTypeDict 

        n = Node('Function', children, (type, identifier, parameters, funcIdentifierTypeDict),
                returntype=type, identifier=identifier, parameters=parameters, identifierTypeDict=funcIdentifierTypeDict)
        #typedef'ed return value?
        if type.type == "NodeTypedef":
            n.basic_type = type.children[0].type
        else:
            n.basic_type = type.type
        return n
    
    def parseParameters(self):
        parameters = []
        while self.currentToken.type in ('INT', 'BOOL', 'CONST', 'IDENTIFIER'):
            isConst = False
            if self.currentToken.type == 'CONST':
                self.accept('CONST')
                isConst = True
            type = self.parseStdType(isConst) 
            identifier = self.parseIdentifierComplex()
            self.identifierTypeDict[get_full_name_from_complex_identifier(identifier)] = type
            parameters.append( Node('Parameter', [], (type, identifier)) )
            if self.currentToken.type == 'COMMA':
                self.accept('COMMA')

        return parameters
   
    def parseBodyStatements(self, single = False):
        statements = []
        while self.currentToken.type not in ('RCURLYPAREN', 'ELSE'):
            identifier = None

            if self.currentToken.type in ('INT', 'BOOL', 'CONST'):
                if self.currentToken.type == 'CONST':
                    type = self.parseStdType(True)
                else:
                    type = self.parseStdType(False)
                identifier = self.parseIdentifierComplex()
                statements.append(self.parseDeclaration(type, identifier))
            elif self.currentToken.type == 'FOR':
                statements.append(self.parseForLoop())
            elif self.currentToken.type == 'WHILE':
                statements.append(self.parseWhileLoop())
            elif self.currentToken.type == 'DO':
                statements.append(self.parseDoWhileLoop())
            elif self.currentToken.type in ('IDENTIFIER', 'PLUSPLUS', 'MINUSMINUS'):
                if self.isType(self.currentToken.value):
                    utype = self.parseTypedefType(self.currentToken.value)
                    identifier = self.parseIdentifierComplex()
                    statements.append(self.parseDeclaration(utype, identifier))
                else:
                    if self.currentToken.type == 'IDENTIFIER':
                        identifier = self.parseIdentifierComplex()

                    if self.currentToken.type == 'LPAREN':
                        statements.append(self.parseFunctionCall(identifier))
                    else:
                        statements.append(self.parseAssignment(identifier))
                    self.accept('SEMI')
            elif self.currentToken.type == 'IF':
                statements.append(self.parseIf())
            elif self.currentToken.type == 'RETURN':
                self.accept('RETURN')
                if self.currentToken.type != 'SEMI':
                    expression = self.parseExpression()
                else:
                    expression = Node('Expression', children=[Node('Number', [], '0')])
                n = Node('Return', [], expression)
                statements.append(n)
                self.accept('SEMI')
            else:
                self.error('parseBodyStatement unknown token: %s' % self.currentToken.type)
                break

            if single:
                break

        return statements 

    def parseVariableList(self):
        children = []
        while self.currentToken.type == 'COMMA':
            self.accept('COMMA')
            children.append(self.parseIdentifier())
         
        return children

    def parseExpression(self):
        exprParser = expressionParser.ExpressionParser(self.lexer, self)
        return Node('Expression', children=[exprParser.parse()])
       
    def parseNumber(self):
        if self.currentToken.type == 'MINUS':
            self.accept('MINUS')
            n = Node('Number', [], -self.currentToken.value)
        else:
            n = Node('Number', [], self.currentToken.value)
        self.accept('NUMBER')
        return n

    def parseInitializer(self):
        self.accept(self.currentToken.type)
        childList = []

        while True:
            if self.currentToken.type == 'LCURLYPAREN':
                childList.append(self.parseInitializer())
            elif self.currentToken.type == 'RCURLYPAREN':
                self.accept(self.currentToken.type)
                if self.currentToken.type == 'COMMA':
                    self.accept('COMMA')
                break
            elif self.currentToken.type in ('NUMBER', 'MINUS', ):
                childList.append(self.parseNumber())
                if self.currentToken.type == 'COMMA':
                    self.accept('COMMA')
            elif self.currentToken.type in ('TRUE', 'FALSE', ):
                childList.append(Node(self.currentToken.type == 'TRUE' and 'True' or 'False'))
                self.accept(self.currentToken.type)
                if self.currentToken.type == 'COMMA':
                    self.accept('COMMA')
            elif self.currentToken.type in ('IDENTIFIER',):
                childList.append(self.parseIdentifier())
                if self.currentToken.type == 'COMMA':
                    self.accept('COMMA')
            else:
                self.error('parseInitializer: parse error, unexpected token type: %s' % self.currentToken.type)
           
        return Node('Initializer', children=childList)

    #This method should not be used for initialization assignments (handled by parseDeclaration)
    def parseAssignment(self, identifier, shorthand = True):
        if self.currentToken.type in ['EQUALS', 'ASSIGN']:
            self.accept(self.currentToken.type)

            #TODO refactor
            n = self.parseExpression()
            return Node('Assignment', [n], identifier,
                    identifier=identifier)
        elif self.currentToken.type in ['ANDEQUAL', 'TIMESEQUAL', 'DIVEQUAL', \
                        'MODEQUAL', 'PLUSEQUAL', 'MINUSEQUAL', 'LSHIFTEQUAL', \
                        'RSHIFTEQUAL', 'ANDEQUAL', 'OREQUAL', 'XOREQUAL']:
            return self.transformXEqual(identifier)

        elif shorthand:  
            if self.currentToken.type == 'PLUSPLUS':
                self.accept('PLUSPLUS')
                if identifier == None:
                    identifier = self.parseIdentifierComplex()
                    ppnode = Node('PlusPlusPre', [identifier])
                else:
                    ppnode = Node('PlusPlusPost', [identifier])         
                return Node('Assignment', children=[Node('Expression', children=[ppnode])],
                        identifier=identifier)
            elif self.currentToken.type == 'MINUSMINUS':
                self.accept('MINUSMINUS')
                if identifier == None:
                    identifier = self.parseIdentifierComplex()
                    mmnode = Node('MinusMinusPre', [identifier])
                else:
                    mmnode = Node('MinusMinusPost', [identifier])
                return Node('Assignment', children=[Node('Expression', children=[mmnode])],
                        identifier=identifier)
        self.error('at assignment parsing, at token "%s" on line %d: Did not expect token type: "%s"' % (self.currentToken.value, self.currentToken.lineno, self.currentToken.type))

    def parseBooleanExpression(self):
        exprParser = expressionParser.ExpressionParser(self.lexer, self)
        return Node('BooleanExpression', children=[exprParser.parse()])

    def parseForLoop(self):
        leaf = []
        self.accept('FOR')
        self.accept('LPAREN')
        leaf.append(self.parseAssignment(self.parseIdentifierComplex()))
        self.accept('SEMI')
        leaf.append(self.parseBooleanExpression())
        self.accept('SEMI')
        leaf.append(self.parseAssignment(self.parseIdentifierComplex()))
        self.accept('RPAREN')
        self.accept('LCURLYPAREN')
        children = self.parseBodyStatements()
        self.accept('RCURLYPAREN')

        return Node('ForLoop', children, leaf)
           
    def parseWhileLoop(self):
        leaf = []
        self.accept('WHILE')
        self.accept('LPAREN')
        leaf.append(self.parseBooleanExpression())
        self.accept('RPAREN')

        if self.currentToken.type == 'LCURLYPAREN':
            self.accept('LCURLYPAREN')
            children = self.parseBodyStatements()
            self.accept('RCURLYPAREN')
        else:
            children = self.parseBodyStatements(single=True)

        return Node('WhileLoop', children, leaf)

    def parseDoWhileLoop(self):
        leaf = []
        self.accept('DO')
        self.accept('LCURLYPAREN')
        children = self.parseBodyStatements()
        self.accept('RCURLYPAREN')
        self.accept('WHILE')
        self.accept('LPAREN')
        leaf.append(self.parseBooleanExpression())
        self.accept('RPAREN')
        self.accept('SEMI')

        return Node('DoWhileLoop', children, leaf)

    def parseIf(self):
        leaf = []
        children = []
        self.accept('IF')
        self.accept('LPAREN')
        leaf.append(self.parseBooleanExpression())
        self.accept('RPAREN')
        if self.currentToken.type == 'LCURLYPAREN':
            self.accept('LCURLYPAREN')
            children.append(Node('IfBodyStatements', self.parseBodyStatements(), leaf))
            self.accept('RCURLYPAREN')
        else:
            children.append(Node('IfBodyStatements', self.parseBodyStatements(single=True), leaf))

        elseCase = False
        while self.currentToken.type == 'ELSE' and elseCase == False:
            self.accept('ELSE')
            if self.currentToken.type == 'IF':
                self.accept('IF')
                leaf = []
                self.accept('LPAREN')
                leaf.append(self.parseBooleanExpression())
                self.accept('RPAREN')

                if self.currentToken.type == 'LCURLYPAREN':
                    self.accept('LCURLYPAREN')
                    children.append(Node('ElseIfBodyStatements', self.parseBodyStatements(), leaf))
                    self.accept('RCURLYPAREN')
                else:
                    children.append(Node('ElseIfBodyStatements', self.parseBodyStatements(single=True), leaf))                
            else:
                elseCase = True
                if self.currentToken.type == 'LCURLYPAREN':
                    self.accept('LCURLYPAREN')
                    children.append(Node('ElseBodyStatements', self.parseBodyStatements(), None))
                    self.accept('RCURLYPAREN')
                else:
                    children.append(Node('ElseBodyStatements', self.parseBodyStatements(single=True), None))

        return Node('If', children)

    def parseIdentifier(self):
        n = Identifier(self.currentToken.value)
        self.accept('IDENTIFIER')
        return n

    """ Should accept something like
        d[34].sdf.df[3][2].df[2] =
        d.sdf.df[3][2].df =
    """
    def parseIdentifierComplex(self):
        strname = self.currentToken.value
        self.accept('IDENTIFIER')

        indexList = self.parseIndexList()

        dotchild = None
        if self.currentToken.type == 'DOT':
            self.accept('DOT')
            dotchild = self.parseIdentifierComplex()
        return Identifier(strname, indexList, dotchild)
   
    ### 
    ### FIXME: Notice similar functionalty exist in expressionParser, 
    ### however not posible to reuse as identifier must be parsed first
    ### should probably be refactored.
    ###
    def parseFunctionCall(self, identifier): 
        self.accept('LPAREN')
        parameters = []
        
        while self.currentToken.type != 'RPAREN':
            expr = self.parseExpression()
            if self.currentToken.type == 'COMMA':
                self.accept('COMMA')
            parameters += [expr]
            
        self.accept('RPAREN')
        return Node('FunctionCall', [identifier], parameters)
    
    def transformXEqual(self, identifier):

        if self.currentToken.type == 'ANDEQUAL':
            self.accept(self.currentToken.type)
            n = self.parseExpression()
            expr = [Node('Expression', [Node('Equal', [identifier, n.children[0]], [])], [])]
            return Node('Assignment', expr, identifier,
                    identifier=identifier)
        elif self.currentToken.type == 'PLUSEQUAL':
            self.accept(self.currentToken.type)
            n = self.parseExpression()
            expr = [Node('Expression', [Node('Plus', [identifier, n.children[0]], [])], [])]
            return Node('Assignment', expr, identifier,
                    identifier=identifier) 
        elif self.currentToken.type == 'MINUSEQUAL':
            self.accept(self.currentToken.type)
            n = self.parseExpression()
            expr = [Node('Expression', [Node('Minus', [identifier, n.children[0]], [])], [])]
            return Node('Assignment', expr, identifier,
                    identifier=identifier)
        #elif self.currentToken.type == 'TIMESEQUAL':
        #elif self.currentToken.type == 'DIVEQUAL':
        #elif self.currentToken.type == 'MODEQUAL':
        #elif self.currentToken.type == 'LSHIFTEQUAL':
        #elif self.currentToken.type == 'RSHIFTEQUAL':
        #elif self.currentToken.type == 'ANDEQUAL':
        #elif self.currentToken.type == 'OREQUAL':
        #elif self.currentToken.type == 'XOREQUAL':

        return None


    def parseDeclType(self):
        if self.currentToken.type == 'URGENT':
            self.accept('URGENT')
            if self.currentToken.type == 'CHANNEL':
                self.accept('CHANNEL')
                return Node('TypeUrgentChannel')
            else:
                self.accept('BROADCAST')
                self.accept('CHANNEL')
                return Node('TypeUrgentBroadcastChannel')
        elif self.currentToken.type == 'CHANNEL':
            self.accept('CHANNEL')
            return Node('TypeChannel')
        elif self.currentToken.type == 'BROADCAST':
            self.accept('BROADCAST')
            self.accept('CHANNEL')
            return Node('TypeBroadcastChannel')
        elif self.currentToken.type == 'CLOCK':
            self.accept('CLOCK')
            return Node('TypeClock')
        else: 
            return self.parseStdType(False)
    
    def parseFuncType(self):
        if self.currentToken.type == 'VOID':
            self.accept('VOID')
            return Node('TypeVoid')

    def parseStdType(self, isConst):
        if self.currentToken.type == 'INT':
            self.accept('INT')
            if self.currentToken.type == 'BITAND' and not isConst:
                self.accept('BITAND')
                return Node('TypeIntReference')
            elif self.currentToken.type == 'LBRACKET':
                self.accept('LBRACKET')
                #range-constrained int
                lower = self.parseExpression()
                self.accept('COMMA')
                upper = self.parseExpression()
                self.accept('RBRACKET')
                return Node('TypeInt', [lower, upper])
            elif isConst:
                return Node('TypeConstInt')
            else:
                return Node('TypeInt')
        elif self.currentToken.type == 'BOOL':
            self.accept('BOOL')
            if self.currentToken.type == 'BITAND' and not isConst:
                self.accept('BITAND')
                return Node('TypeBoolReference')
            elif isConst:
                return Node('TypeConstBool')
            else:
                return Node('TypeBool')
        elif self.currentToken.type == 'IDENTIFIER':
            identn = self.parseIdentifierComplex()

            # typedef vardecl, e.g. myint i;
            if len(identn.children) == 1 and self.isType(identn.children[0]):
                typedefedtype = self.getType(identn.children[0])
                if isConst:
                    typedefedtype = copy.copy(typedefedtype)
                    typedefedtype.type = "TypeConstTypedef"
                return typedefedtype
            # extern vardecl child, e.g. oct.intvar x
            elif self.globalIdentifierTypeDict[identn.children[0]].type == "NodeExtern":
                n = Node('TypeExternChild', [identn])
                return n
        self.error('Not a type')

    def parseTypedefType(self, str):
        if self.isType(str):
            self.accept('IDENTIFIER')
            return self.getType(str)
        else:
            self.error('Not a typedef type:'+self.currentToken.value)


    def isType(self, str):
        if str in self.typedefDict:
            return True
        else:
            return False

    def getType(self, str):
        return self.typedefDict[str]

    def accept(self, expectedTokenType):
        if self.currentToken.type == expectedTokenType:
            try:
                self.currentToken = self.lexer.token()
                return
            except:
                self.error('Lexer error at token %s on line %d' % (self.currentToken.value, self.currentToken.lineno, ))
        else:
            self.error('at token %s on line %d: Expected %s but was %s' % (self.currentToken.value, self.currentToken.lineno, expectedTokenType, self.currentToken.type))

    def error(self, msg):
        token = self.currentToken

        if token.lexpos - 100 < 0:
            startIndex = 0
        else:
            startIndex = token.lexpos - 100

        if self.lexer.lexlen < token.lexpos + 100:
            endIndex = self.lexer.lexlen
        else:
            endIndex = token.lexpos + 100

        print "\n\nError parsing:\n", self.lexer.lexdata[startIndex:endIndex], "\n\n\n"
        raise Exception('Error: Parser error '+ msg)





class DeclVisitor(object):
    def __init__(self, parser):
        """Extract variables, constants, clocks, channels and functions from an AST (given a parser as it contains a type dictionary)
        """
        #assert isinstance(parser, Parser)
        self.parser = parser

        #calculate variables, clocks and channels
        self.constants = OrderedDict()  #Mappeing from iden->expression
        #variables: list of VarDecl objects
        self.variables = [] #List of VarDecl objects
        self.clocks = []
        #The 4 channel lists contain tuples where the first element is an identifer and the second is the dimensions 
        self.channels = []  
        self.urgent_channels = []
        self.broadcast_channels = []
        self.urgent_broadcast_channels = []
        self.functions = [] #List of AST-nodes where type is set to 'Function'

    def visit(self, node):
        if node.type == 'RootNode':
            for c in node.children:
                self.visit(c)
        elif node.type == 'Parameter':
            self.visit_Parameter(node)
        elif node.type == 'VarDeclList':
            self.visit_VarDeclList(node)
        elif node.type == 'ClockDeclList':
            self.visit_ClockDeclList(node)
        elif node.type == 'ChannelDeclList':
            self.visit_ChannelDeclList(node)
        elif node.type == 'Function':
            self.functions.append(node)
        elif node.type in ['NodeTypedef', 'NodeExtern', 'Assignment', 'WhileLoop', 'If', 'Return', 'ForLoop', 'DoWhileLoop', 'FunctionCall']:
            pass
        else:
            raise Exception("not impl node type: "+ node.type)


    def visit_Identifier(self, node):
        ident_str = get_full_name_from_complex_identifier(node)
        index_list = get_index_of_last_ident(node)
        
        if len(index_list) == 0:
            return (ident_str, index_list)
        else:
            exprList = []
            for index in index_list:
                exprList += [index.leaf]

            return (ident_str, exprList)

    def visit_Parameter(self, node):
        (ptype, iden) = node.leaf
        self.add_variable(ptype, iden.children[0], None, [])

    def visit_VarDeclList(self, node):
        list_type = node.leaf

        for c in node.children:
            (iden, initval, array_dimen) = self.visit_VarDecl(c)
            self.add_variable(list_type, iden, initval, array_dimen)

    def visit_VarDecl(self, node):
        (iden, dimen) = self.visit_Identifier(node.children[0])
        return (iden, node.leaf, dimen)

    def visit_ClockDeclList(self, node):
        list_type = node.leaf

        for c in node.children:
            (ident, array_dimen) = self.visit_Clock(c)
            self.variables += [VarDecl(ident, list_type, array_dimen, None)]
            self.clocks += [(ident, 10)] #XXX why 10???

    def visit_Clock(self, node):
        return self.visit_Identifier(node.children[0])

    def visit_ChannelDeclList(self, node):
        list_type = node.leaf

        for c in node.children:
            (channel_ident, _, dimen) = self.visit_VarDecl(c)
            channel = (channel_ident, dimen)
            if list_type.type == 'TypeChannel':
                self.channels += [channel]
            elif list_type.type == 'TypeUrgentChannel':
                self.urgent_channels += [channel]
            elif list_type.type == 'TypeBroadcastChannel':
                self.broadcast_channels += [channel]
            elif list_type.type == 'TypeUrgentBroadcastChannel':
                self.urgent_broadcast_channels += [channel]
    
    def add_variable(self, list_type, iden, initval, array_dimen):
        if list_type.type in ['TypeConstInt', 'TypeConstBool'] or (list_type.type == 'TypeConstTypedef' and list_type.children[0].type != 'VarDeclList'): #alias const typedef
            self.constants[iden] = initval
        else:
            if list_type.type == 'TypeBool' and initval == 0:
                initval = False
            elif list_type.type == 'NodeExtern': 
                last_type = get_last_name_from_complex_identifier(list_type.leaf)
                varType = Identifier(last_type)
            elif list_type.type == 'NodeTypedef':
                if iden in self.parser.identifierTypeDict:
                    varType = self.parser.identifierTypeDict[iden]
                else: 
                    varType = self.parser.globalIdentifierTypeDict[iden]
            else:
                varType = list_type
       
            vdecl = VarDecl(iden, varType, array_dimen, initval)
            self.variables += [vdecl]
   
    #Is suppose to be called after parsing is done
    #The preprocessed typedef dict still need to have min/max ranges evaluated
    def preprocess_typedefs(self):
        pTypedefDict = {}
        tmp_var = self.variables
        self.variables = []

        for (typename, typedef) in self.parser.typedefDict.items():
            if typedef.type != 'NodeExtern' and typedef.children[0].type == 'VarDeclList':
                n = Node('RootNode', typedef.children)
                self.visit(n)
                pTypedefDict[typename] = self.variables
                self.variables = []

        self.variables = tmp_var
        return pTypedefDict

    def get_vardecl(self, ident):
        """Return the VarDecl object for ident, assumes the type of ident is a
           variable type."""
        return [x for x in self.variables if x.identifier == ident][0]

    def get_type(self, ident):
        """Return the type of ident"""
        if ident in [n for (n, _, _, _) in self.variables]:
            (n, t, k, l) = [(n, t, k, l) for (n, t, k, l) in self.variables if n == ident][0]
            if t == 'TypeInt':
                return "TypeInt"
            elif t == 'TypeBool':
                return "TypeBool"
            elif isinstance(t, str):
                #some extern type
                return t
            elif isinstance(t, list):
                #some extern child type
                return t
            else:
                assert False
        elif ident in [c for (c, _) in self.clocks]:
            return "TypeClock"
        elif ident in self.constants.keys():
            return "TypeConstInt"
        elif ident in [n for (n, _) in self.channels]:
            return "TypeChannel"
        elif ident in [n for (n, _) in self.urgent_channels]:
            return "TypeUrgenChannel"
        elif ident in [n for (n, _) in self.broadcast_channels]:
            return "TypeBroadcastChannel"
        elif ident in [n for (n, _) in self.urgent_broadcast_channels]:
            return "TypeUrgentBroadcastChannel"
        return None

    def is_alias_type(self, node): #TODO use this method in parser code
        if (node.type == 'TypeConstTypedef' or node.type == 'NodeTypedef') and node.children[0].type != 'VarDeclList':
            return True
        else:
            return False

    def is_reference(self, node):
        if node.type == 'Reference':
            return True

        for c in node.children:
            if c.type == 'Reference':
                return True

        return False

# vim:ts=4:sw=4:expandtab
