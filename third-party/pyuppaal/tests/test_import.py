#!/usr/bin/python
import sys
import os.path
projdir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path = [projdir] + sys.path
import pyuppaal
import unittest
import os

class TestMinimalImport(unittest.TestCase):
    def test_import_minimal(self):
        file = open(os.path.join(os.path.dirname(__file__), 'minimal.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(len(nta.templates), 1)
        self.assertEqual(len(nta.templates[0].locations), 1)
        self.assertEqual(len(nta.templates[0].transitions), 0)
        self.assertEqual(nta.templates[0].locations[0].xpos, 16)
        self.assertEqual(nta.templates[0].locations[0].ypos, -40)
        self.assertTrue(nta.templates[0].locations[0] == nta.templates[0].initlocation)
        self.assertEqual(nta.declaration, '// Place global declarations here.\n')
        self.assertEqual(nta.system, """// Place template instantiations here.
Process = Template();

// List one or more processes to be composed into a system.
system Process;""")

    def test_import_small(self):
        file = open(os.path.join(os.path.dirname(__file__), 'small.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(len(nta.templates), 1)
        self.assertEqual(len(nta.templates[0].locations), 2)
        self.assertEqual(len(nta.templates[0].transitions), 1)
        self.assertEqual(nta.templates[0].locations[1].committed, True)

    def test_import_petur_boegholm(self):
        file = open(os.path.join(os.path.dirname(__file__), 'petur_boegholm_testcase.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(len(nta.templates), 20)
        schedulerTemplate = nta.templates[0]
        self.assertEqual(schedulerTemplate.name, 'Scheduler')
        self.assertEqual(len(schedulerTemplate.locations), 4)
        self.assertEqual(len(schedulerTemplate.transitions), 6)
        for template in nta.templates:
            #print "Layouting ", template.name
            template.layout()

    def test_import_petur_boegholm_minimal(self):
        file = open(os.path.join(os.path.dirname(__file__), 'petur_boegholm_testcase_minimal.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(len(nta.templates), 1)
        schedulerTemplate = nta.templates[0]
        self.assertEqual(schedulerTemplate.name, 'Scheduler')
        self.assertEqual(len(schedulerTemplate.locations), 4)
        self.assertEqual(len(schedulerTemplate.transitions), 6)
        schedulerTemplate.layout(auto_nails=True)

    def test_import_template_parameter_minimal(self):
        file = open(os.path.join(os.path.dirname(__file__), 'parameter_minimal.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(len(nta.templates), 1)
        self.assertEqual(nta.templates[0].parameter, 'int id')

    def test_import_minimal_noinitlocation(self):
        file = open(os.path.join(os.path.dirname(__file__), 'noinit_minimal.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(nta.templates[0].initlocation, None)

    def test_import_minimal_name(self):
        file = open(os.path.join(os.path.dirname(__file__), 'minimal_name.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(nta.templates[0].initlocation.name.value, "abemad")

    def test_import_strangeguard(self):
        file = open(os.path.join(os.path.dirname(__file__), 'strangeguard.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(nta.templates[0].transitions[0].guard.get_value(), "")
        self.assertEqual(nta.templates[0].transitions[0].guard.xpos, -44)
        self.assertEqual(nta.templates[0].transitions[0].guard.ypos, -10)

    def test_import_noxypos(self):
        file = open(os.path.join(os.path.dirname(__file__), 'location_no_xypos.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(nta.templates[0].locations[0].xpos, 0)
        self.assertEqual(nta.templates[0].locations[0].ypos, 0)

    def test_import_urgent(self):
        file = open(os.path.join(os.path.dirname(__file__), 'urgent.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(nta.templates[0].locations[0].urgent, True)

    def test_import_nocoords(self):
        file = open(os.path.join(os.path.dirname(__file__), 'small_nocoords.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        for l in nta.templates[0].locations:
            self.assertEqual(l.invariant.xpos, None)
            self.assertEqual(l.invariant.ypos, None)
            self.assertEqual(l.name.xpos, None)
            self.assertEqual(l.name.ypos, None)
        t = nta.templates[0].transitions[0]
        for a in [t.select, t.guard, t.synchronisation, t.assignment]:
            self.assertEqual(a.xpos, None)
            self.assertEqual(a.ypos, None)

    def test_import_all_labels(self):
        file = open(os.path.join(os.path.dirname(__file__), 'small_all_labels.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        temp = nta.templates[0]
        l1 = temp.locations[1]
        l2 = temp.locations[0]
        t1 = temp.transitions[0]

        self.assertEqual(l1.name.get_value(), "name1")
        self.assertEqual(l1.invariant.get_value(), "invariant1")
        self.assertEqual(l2.name.get_value(), "name2")
        self.assertEqual(l2.invariant.get_value(), "invariant2")

        self.assertEqual(t1.select.get_value(), "select")
        self.assertEqual(t1.guard.get_value(), "guard")
        self.assertEqual(t1.synchronisation.get_value(), "sync")
        self.assertEqual(t1.assignment.get_value(), "update")

    def test_import_minimal_0coord(self):
        file = open(os.path.join(os.path.dirname(__file__), 'minimal_0coord.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(len(nta.templates), 1)
        self.assertEqual(nta.templates[0].locations[0].xpos, 0)
        self.assertEqual(nta.templates[0].locations[0].ypos, 0)
        self.assertTrue(nta.templates[0].locations[0].xpos != None)
        self.assertTrue(nta.templates[0].locations[0].ypos != None)

        #the name label
        self.assertEqual(nta.templates[0].locations[0].name.xpos, 0)
        self.assertEqual(nta.templates[0].locations[0].name.ypos, 0)
        self.assertTrue(nta.templates[0].locations[0].name.xpos != None)
        self.assertTrue(nta.templates[0].locations[0].name.ypos != None)

    def test_export_queryfile(self):
        qf = pyuppaal.QueryFile()
        qf.addQuery('')

        (fh, path) = qf.getTempFile()

        lines = fh.read().split('\n')
        self.assertEqual(lines[-1], '//NO_QUERY')

    def test_tga(self):
        file = open(os.path.join(os.path.dirname(__file__), 'tga.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(len(nta.templates), 1)
        self.assertEqual(len(nta.templates[0].transitions), 2)
        controllable = []
        uncontrollable = []
        for transition in nta.templates[0].transitions:
            self.assertEqual(type(transition.controllable), bool)
            if transition.controllable:
                controllable.append(transition)
            else:
                uncontrollable.append(transition)
        self.assertEqual(len(controllable), 1)
        self.assertEqual(len(uncontrollable),  1)
        self.assertEqual(str(controllable[0].target.name), 'to_controllable')
        self.assertEqual(str(uncontrollable[0].target.name), 'to_uncontrollable')
        # now test that XML created in non-TIGA version of UPPAAL contains only controllable transitions
        file = open(os.path.join(os.path.dirname(__file__), 'small.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(len(nta.templates), 1)
        self.assertEqual(len(nta.templates[0].transitions), 1)
        self.assertTrue(nta.templates[0].transitions[0].controllable)

    def test_import_tapall_simple(self):
        file = open(os.path.join(os.path.dirname(__file__), 'tapaal-simple.xml'))
        nta = pyuppaal.NTA.from_xml(file)
        self.assertEqual(len(nta.templates), 1)
        lock = nta.templates[0]

        self.assertEqual(len(lock.locations), 1)
        loc = lock.locations[0]
        self.assertEqual(len(lock.transitions), 1)
        trans = lock.transitions[0]

        self.assertEqual(trans.assignment.value, None)
        self.assertEqual(trans.assignment.get_value(), "")


if __name__ == '__main__':
    unittest.main()
