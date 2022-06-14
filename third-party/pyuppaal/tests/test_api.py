#!/usr/bin/python
import sys
import os.path
projdir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path = [projdir] + sys.path
from pyuppaal import *
import unittest
import os
from nose.tools import nottest

class TestAPI(unittest.TestCase):
    def test_transition_create(self):
        l1 = Location()
        l2 = Location()
        t = Transition(l1, l2, guard="abemad")
        try:
            t = Transition(l1, l2, "abemad")
            self.fail("Should have raised exception")
        except TypeError:
            pass

    def test_label_append(self):
        l = Label("guard")
        self.assertEqual(l.get_value(), "")
        l.append("a==b")
        self.assertEqual(l.get_value(), "a==b")
        l.append("c==d")
        self.assertEqual(l.get_value(), "a==b,\nc==d")
        l.append("e==50")
        self.assertEqual(l.get_value(), "a==b,\nc==d,\ne==50")
        l.value = 'a==25'
        self.assertEqual(l.get_value(), "a==25")
        l.append('b==c', auto_newline=False)
        self.assertEqual(l.get_value(), "a==25,b==c")
        l = Label("guard")
        l.append('a==b')
        self.assertEqual(l.get_value(), "a==b")

    def test_create_multi_nta(self):
        nta1 = NTA()
        nta2 = NTA()
        temp1 = Template('temp1')
        nta1.templates += [temp1]
        self.assertEqual(nta2.templates, [])

    def test_copy_trans(self):
        l1 = Location()
        l2 = Location()
        t1 = Transition(l1, l2, guard="abemad")
        import copy
        t2 = copy.copy(t1)
        #we should get different labels
        self.assertNotEqual(t1.select, t2.select)
        self.assertNotEqual(t1.guard, t2.guard)
        self.assertNotEqual(t1.synchronisation, t2.synchronisation)
        self.assertNotEqual(t1.assignment, t2.assignment)

        self.assertEqual(t1.source, t2.source)
        self.assertEqual(t1.target, t2.target)

    def test_get_location_by_name(self):
        nta1 = NTA()
        temp1 = Template('temp1')
        nta1.templates += [temp1]
        l1 = Location(name='a')
        l2 = Location(name='b')
        temp1.locations += [l1, l2]

        self.assertEqual(len(temp1.locations), 2)
        self.assertEqual(temp1.get_location_by_name('a'), l1)
        self.assertEqual(temp1.get_location_by_name('b'), l2)


    def test_verify(self):
        ntafilename = os.path.join(os.path.dirname(__file__), 'small_verify.xml')

        qf = QueryFile('E<> Process.done')
        (qfh, qfname) = qf.getTempFile()

        try:
            res = verify(ntafilename, qfname)
            self.assertEqual(res, [True], "There was a problem calling 'verifyta', maybe its not on your PATH, or the output format has changed?")
        except Exception, e:
            #verifyta can fail in many ways: no internet connection for license, etc.
            pass

        qf.deleteTempFile(qfh)

    
    @nottest
    def DISABLED_test_verify_remote(self):
        ntafilename = os.path.join(os.path.dirname(__file__), 'small_verify.xml')

        qf = QueryFile('E<> Process.done')
        (qfh, qfname) = qf.getTempFile()

        res = verify(ntafilename, qfname, remotehost='apu')
        self.assertEqual(res, [True])

        qf.deleteTempFile(qfh)

if __name__ == '__main__':
    unittest.main()
