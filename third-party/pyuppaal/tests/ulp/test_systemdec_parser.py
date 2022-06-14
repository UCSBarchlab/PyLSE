#!/usr/bin/python
import sys
import os
import unittest
from pyuppaal.ulp import lexer
from pyuppaal.ulp.systemdec_parser import SystemDeclarationParser


class TestBasicParsing(unittest.TestCase):

    def test_parse_very_simple_systemdec(self):
        sysdec = """system Process;"""

        #lex = lexer.lexer
        pars = SystemDeclarationParser(sysdec)
        res = pars.AST
        res.visit()

        self.assertEqual(res.type, 'SystemDec')
        self.assertEqual(len(res.children), 1)
        self.assertEqual(res.children[0].type, 'System')
        systemnode = res.children[0]
        self.assertEqual(len(systemnode.children), 1)
        self.assertEqual(systemnode.children[0].type, 'TemplateInstantiation')
        inst = systemnode.children[0]
        self.assertEqual(systemnode.children[0].ident.type, 'Identifier')
        self.assertEqual(len(systemnode.children[0].ident.children), 1)
        self.assertEqual(systemnode.children[0].ident.children[0], 'Process')

    def test_parse_simple_systemdec(self):
        sysdec = """// Place template instantiations here.
Process = Template();

// List one or more processes to be composed into a system.
system Process;"""

        pars = SystemDeclarationParser(sysdec)
        res = pars.AST
        res.visit()

        self.assertEqual(res.type, 'SystemDec')
        self.assertEqual(len(res.children), 2)
        self.assertEqual(res.children[0].type, 'ProcessAssignment')
        assign = res.children[0]
        self.assertEqual(assign.ident.type, 'Identifier')
        self.assertEqual(assign.ident.children[0], 'Process')

        #self.assertEqual(len(assign.children), 1)
        self.assertEqual(assign.instantiation.type, 'TemplateInstantiation')
        inst = assign.instantiation
        self.assertEqual(inst.ident.type, 'Identifier')
        self.assertEqual(inst.ident.children[0], 'Template')
        self.assertEqual(len(inst.children), 0)
        self.assertEqual(len(inst.parameters), 0)

        self.assertEqual(res.children[1].type, 'System')
        systemnode = res.children[1]
        self.assertEqual(len(systemnode.children), 1)
        self.assertEqual(systemnode.children[0].type, 'TemplateInstantiation')
        inst = systemnode.children[0]
        self.assertEqual(inst.ident.type, 'Identifier')
        self.assertEqual(inst.ident.children[0], 'Process')

    def test_parse_parameter_binding(self):
        sysdec = """//Insert process assignments.

N0 := Node(0,1);
N1 := Node(1,0);
N2 := Node(2,5);
N3 := Node(3,4);
N4 := Node(4,2);
N5 := Node(5,3);
N6 := Node(5,3,42, 47);


//Edit system definition.
system N0, N1, N2, N3, N4, N5;"""

        #lex = lexer.lexer
        pars = SystemDeclarationParser(sysdec)
        res = pars.AST
        res.visit()

        self.assertEqual(res.type, 'SystemDec')
        self.assertEqual(len(res.children), 8)
        for i in range(0, 6):
            self.assertEqual(res.children[i].type, 'ProcessAssignment')
            assign = res.children[i]
            self.assertEqual(assign.leaf.type, 'Identifier')
            self.assertEqual(assign.leaf.children[0], 'N' + str(i))

            inst = assign.instantiation
            self.assertEqual(inst.type, "TemplateInstantiation")
            self.assertEqual(len(inst.parameters), 2)
            parameters = inst.parameters
            self.assertEqual(parameters[0].type, 'Expression')
            self.assertEqual(parameters[0].children[0].type, 'Number')
            self.assertEqual(parameters[1].type, 'Expression')
            self.assertEqual(parameters[1].children[0].type, 'Number')

        self.assertEqual(res.children[6].type, 'ProcessAssignment')
        assign = res.children[6]
        self.assertEqual(assign.leaf.type, 'Identifier')
        self.assertEqual(assign.leaf.children[0], 'N6')
        self.assertEqual(assign.children[0].type, 'TemplateInstantiation')
        inst = assign.children[0]
        self.assertEqual(len(inst.parameters), 4)
        self.assertEqual(inst.parameters[0].children[0].leaf, 5)
        self.assertEqual(inst.parameters[1].children[0].leaf, 3)
        self.assertEqual(inst.parameters[2].children[0].leaf, 42)
        self.assertEqual(inst.parameters[3].children[0].leaf, 47)

        self.assertEqual(res.children[7].type, 'System')
        systemnode = res.children[7]
        self.assertEqual(len(systemnode.children), 6)
        for i in range(0, 6):
            self.assertEqual(systemnode.children[i].type, 'TemplateInstantiation')
            self.assertEqual(systemnode.children[i].leaf.type, 'Identifier')
            self.assertEqual(systemnode.children[i].leaf.children[0], 'N' + str(i))

    def test_parse_priorities1(self):
        sysdec = """system B < A;"""

        #lex = lexer.lexer
        pars = SystemDeclarationParser(sysdec)
        res = pars.AST
        res.visit()

        self.assertEqual(res.type, 'SystemDec')
        self.assertEqual(len(res.children), 1)
        self.assertEqual(res.children[0].type, 'System')
        systemnode = res.children[0]
        self.assertEqual(len(systemnode.children), 2)
        self.assertEqual(systemnode.children[0].type, 'TemplateInstantiation')
        inst = systemnode.children[0]
        self.assertEqual(inst.leaf.type, 'Identifier')
        self.assertEqual(inst.leaf.children[0], 'B')
        self.assertEqual(inst.priority, 0)
        self.assertEqual(systemnode.children[1].type, 'TemplateInstantiation')
        inst = systemnode.children[1]
        self.assertEqual(inst.leaf.type, 'Identifier')
        self.assertEqual(inst.leaf.children[0], 'A')
        self.assertEqual(inst.priority, 1)

    def test_parse_priorities2(self):
        sysdec = """system C < B < A;"""

        #lex = lexer.lexer
        pars = SystemDeclarationParser(sysdec)
        res = pars.AST
        res.visit()

        self.assertEqual(res.type, 'SystemDec')
        self.assertEqual(len(res.children), 1)
        self.assertEqual(res.children[0].type, 'System')
        systemnode = res.children[0]
        self.assertEqual(len(systemnode.children), 3)
        self.assertEqual(systemnode.children[0].type, 'TemplateInstantiation')
        inst = systemnode.children[0]
        self.assertEqual(inst.leaf.type, 'Identifier')
        self.assertEqual(inst.leaf.children[0], 'C')
        self.assertEqual(inst.priority, 0)
        self.assertEqual(systemnode.children[1].type, 'TemplateInstantiation')
        inst = systemnode.children[1]
        self.assertEqual(inst.leaf.type, 'Identifier')
        self.assertEqual(inst.leaf.children[0], 'B')
        self.assertEqual(inst.priority, 1)
        self.assertEqual(systemnode.children[2].type, 'TemplateInstantiation')
        inst = systemnode.children[2]
        self.assertEqual(inst.leaf.type, 'Identifier')
        self.assertEqual(inst.leaf.children[0], 'A')
        self.assertEqual(inst.priority, 2)

    def test_parse_advanced1(self):
        sysdec = """
Supplier1   = SupplierAsync(1); 
CPU1        = Resource(1, true, EDF);
Task1       = Task(1);
Task2       = Task(2);
//Mon1         = Monitor(1);
system 
        Supplier1, 
        CPU1, 
        Task1, Task2, 
        chop, 
//        Mon1,
        Sched_EDF; 
        """
        pars = SystemDeclarationParser(sysdec)
        res = pars.AST
        res.visit()

        Supplier1 = res.children[0]
        self.assertEqual(Supplier1.type, "ProcessAssignment")
        self.assertEqual(Supplier1.leaf.type, "Identifier")
        self.assertEqual(Supplier1.leaf.children[0], "Supplier1")

        SupplierAsync1Inst = Supplier1.children[0]
        self.assertEqual(SupplierAsync1Inst.type, "TemplateInstantiation")
        self.assertEqual(SupplierAsync1Inst.leaf.type, "Identifier")
        self.assertEqual(SupplierAsync1Inst.leaf.children[0], "SupplierAsync")
        self.assertEqual(len(SupplierAsync1Inst.parameters), 1)
        self.assertEqual(SupplierAsync1Inst.parameters[0].type, "Expression")
        self.assertEqual(SupplierAsync1Inst.parameters[0].children[0].type, "Number")
        self.assertEqual(SupplierAsync1Inst.parameters[0].children[0].leaf, 1)

        CPU1 = res.children[1]
        self.assertEqual(CPU1.type, "ProcessAssignment")
        self.assertEqual(CPU1.leaf.type, "Identifier")
        self.assertEqual(CPU1.leaf.children[0], "CPU1")

        Resource1Inst = CPU1.children[0]
        self.assertEqual(Resource1Inst.type, "TemplateInstantiation")
        self.assertEqual(Resource1Inst.leaf.type, "Identifier")
        self.assertEqual(Resource1Inst.leaf.children[0], "Resource")
        self.assertEqual(len(Resource1Inst.parameters), 3)
        self.assertEqual(Resource1Inst.parameters[0].type, "Expression")
        self.assertEqual(Resource1Inst.parameters[0].children[0].type, "Number")
        self.assertEqual(Resource1Inst.parameters[0].children[0].leaf, 1)
        self.assertEqual(Resource1Inst.parameters[1].type, "Expression")
        self.assertEqual(Resource1Inst.parameters[1].children[0].type, "True")
        self.assertEqual(Resource1Inst.parameters[2].type, "Expression")
        self.assertEqual(Resource1Inst.parameters[2].children[0].type, "Identifier")
        self.assertEqual(Resource1Inst.parameters[2].children[0].children[0], "EDF")

        systemnode = res.children[4]
        self.assertEqual(systemnode.type, "System")
        self.assertEqual(len(systemnode.children), 6)

    def test_parse_advanced2(self):
        sysdec = """
system 
        SupplierAsync(1), 
        Resource(1, true, EDF), 
        Task(1), Task(2); 
        """
        
        pars = SystemDeclarationParser(sysdec)
        res = pars.AST
        res.visit()

        systemnode = res.children[0]
        self.assertEqual(systemnode.type, "System")
        self.assertEqual(len(systemnode.children), 4)

        SupplierAsync1Inst = systemnode.children[0]
        self.assertEqual(SupplierAsync1Inst.type, "TemplateInstantiation")
        self.assertEqual(SupplierAsync1Inst.leaf.type, "Identifier")
        self.assertEqual(SupplierAsync1Inst.leaf.children[0], "SupplierAsync")
        self.assertEqual(len(SupplierAsync1Inst.parameters), 1)
        self.assertEqual(SupplierAsync1Inst.parameters[0].type, "Expression")
        self.assertEqual(SupplierAsync1Inst.parameters[0].children[0].type, "Number")
        self.assertEqual(SupplierAsync1Inst.parameters[0].children[0].leaf, 1)

        Resource1Inst = systemnode.children[1]
        self.assertEqual(Resource1Inst.type, "TemplateInstantiation")
        self.assertEqual(Resource1Inst.leaf.type, "Identifier")
        self.assertEqual(Resource1Inst.leaf.children[0], "Resource")
        self.assertEqual(len(Resource1Inst.parameters), 3)
        self.assertEqual(Resource1Inst.parameters[0].type, "Expression")
        self.assertEqual(Resource1Inst.parameters[0].children[0].type, "Number")
        self.assertEqual(Resource1Inst.parameters[0].children[0].leaf, 1)
        self.assertEqual(Resource1Inst.parameters[1].type, "Expression")
        self.assertEqual(Resource1Inst.parameters[1].children[0].type, "True")
        self.assertEqual(Resource1Inst.parameters[2].type, "Expression")
        self.assertEqual(Resource1Inst.parameters[2].children[0].type, "Identifier")
        self.assertEqual(Resource1Inst.parameters[2].children[0].children[0], "EDF")

if __name__ == '__main__':
    unittest.main()
