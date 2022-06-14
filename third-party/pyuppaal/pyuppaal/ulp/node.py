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

from util import *

#AST
class Node(object):
    def __init__(self, type, children=[], leaf=[], **kwargs):
        """
        Old style:
        Node("TemplateInstantiation", parameters, templateident)
                                      ^children[] ^leaf
        New style:
        Node("TemplateInstantiation", parameters, templateident, ident=templateident, parameters=parameters)
                                      ^children[] ^leaf          ^shortcuts...
        """
        super(Node, self).__init__()
        if type == "VarDecl":
            assert isinstance(self, VarDecl), "Use subclass VarDecl"
        elif type == "Identifier":
            assert isinstance(self, Identifier), "Use subclass Identifier"
        self.type = type
        self.children = children
        self.leaf = leaf

        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def print_node(self):
        print "visit", "  "*self.level, self.type, 
        if self.leaf != []:
            print self.leaf
            if self.leaf.__class__.__name__ == 'Node':
                print "visit-node", "  "*(self.level+1), self.leaf.type
        else:
            print 
        return True

    def __repr__(self):
        return "Node(%s, %s, %s)" % (self.type, self.children, self.leaf)

    def visit(self, visitor=None, level=0):
        """Visit this node and subnodes.
        visitor should be a function taking a node as parameter, and returning
        True if children should be visited."""
        self.level = level
        if not visitor:
            visitor = Node.print_node
        if visitor(self):
            for v in self.children:
                try:
                    v.visit(visitor, self.level+1);
                except:
                    if visitor == Node.print_node:
                        print "visit", "  "*(self.level+1), v
                    pass 

class Identifier(Node):
    """
    An Identifier node.

    @strname is the name of the identifier (as string)
    @indexList is an array access
    @dotchild is an dot access of a child element (struct)

    e.g. "a[5].b" =>
    Identifier("a", indexList=[5], dotchild=Identifier("b"))
    """
    def __init__(self, strname, indexList=None, dotchild=None):
        children = [strname]
        if dotchild:
            children.append(dotchild)
        super(Identifier, self).__init__("Identifier", children=children, leaf=indexList)
        self.strname = strname
        self.indexList = indexList
        self.dotchild = dotchild

class VarDecl(Node):
    """
    A VarDecl node.

    @identifier is name of var (as string)
    @vartype is type used at declaration, e.g. "addr" if a typedef'ed var
    @basic_type is the underlying type, e.g. "TypeInt"
    @typenode is a reference to the AST node representing the type
    """

    def __init__(self, identifier, typeNode, array_dimensions=None, initval=None):
        super(VarDecl, self).__init__("VarDecl", children=[identifier], leaf=initval)
        self.identifier = identifier
        isTypedefStruct = False
        
        if typeNode.type == 'NodeTypedef': #TODO recursively find type
            if typeNode.children[0].type == 'VarDeclList': #Means that this is a Struct
                self.vartype = typeNode.leaf
                self.basic_type = self.vartype
            else: 
                self.vartype = typeNode.leaf
                typeNode = typeNode.children[0]
                self.basic_type = typeNode.type
        elif typeNode.type == 'Identifier':
            self.vartype = typeNode.children[0]
            self.basic_type = self.vartype
        elif typeNode.type == "TypeExternChild":
            self.basic_type = "TypeExternChild"
            typeNode.children[0].visit()
            self.vartype = get_name_list_from_complex_identifier(typeNode.children[0])
        else: #basic type
            self.vartype = typeNode.type
            self.basic_type = self.vartype
        
        self.array_dimensions = array_dimensions or []
        self.initval = initval
        #Default ranges
        if typeNode.type in ['TypeInt', 'TypeConstInt'] or (typeNode.type == 'NodeTypedef' and typeNode.children[0].type != 'VarDeclList'): #alias typedef
            if len(typeNode.children) == 2:
                self.range_min = typeNode.children[0].children[0]
                self.range_max = typeNode.children[1].children[0]
            else:
                self.range_min = Node('Number', [], -32767)
                self.range_max = Node('Number', [], 32767)
        elif typeNode.type in ['TypeBool', 'TypeConstBool']:
            self.range_min = Node('Number', [], 0)
            self.range_max = Node('Number', [], 1)
        else:
            self.range_min = None
            self.range_max = None

    def __iter__(self):
        "For backwards compatibility."
        for x in (self.identifier, self.vartype, self.array_dimensions, self.initval):
            yield x

