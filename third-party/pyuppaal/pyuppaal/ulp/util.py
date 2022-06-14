""" 
    Copyright (C) 2009,2014
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

def get_index_of_last_ident(node):
    last_index = node.leaf

    #parse out entire name (follow dots)
    curnode = node
    while len(curnode.children) == 2 and curnode.children[1].type == 'Identifier':
        curnode = curnode.children[1]        
        last_index = curnode.leaf

    if last_index == None:
        return []
    else:
        return last_index.children

def get_last_name_from_complex_identifier(n):
    """Follow the children of a complex identifier node, i.e.
    "a.b.c.d" to just return "d"
    """
    full_str = get_full_name_from_complex_identifier(n)
    if '.' in full_str:
        return full_str.rsplit('.',1)[1] #FIXME this could be done without constructing the full string first
    else:
        return full_str

""" Takes an identifier and return the full name:
    e.g., myidentifier.someotheridentifier.nestedidentifier.
    """
def get_full_name_from_complex_identifier(identifierNode):
    id_str = identifierNode.children[0]

    #parse out entire name (follow dots)
    curnode = identifierNode
    while len(curnode.children) == 2 and curnode.children[1].type == 'Identifier':
        curnode = curnode.children[1]
        id_str += '.' + curnode.children[0]

    return id_str

""" Takes an identifier and return the list of names:
    e.g., ['myidentifier', 'someotheridentifier', 'nestedidentifier']
    """
def get_name_list_from_complex_identifier(identifierNode):
    n = identifierNode
    names = [n.children[0]]
    cur = n
    while len(cur.children) == 2 and \
        cur.children[1].type == 'Identifier':
        cur = cur.children[1]
        names.append(cur.children[0])
    return names
