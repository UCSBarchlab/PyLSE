from io import StringIO
from pylse.io import export_to_blif
import unittest

from pylse import working_circuit, m, c, c_inv, split, inp, Wire

blif_example_1 = '''\
# Generated automatically via PyLSE

.model top

.inputs i j
.gate C_INV a=i3 b=c_o1 q=w1
.gate C a=i2 b=w1 q=c_o1
.gate C a=i5 b=m_o1 q=c_o2
.gate M a=c_o2 b=j q=m_o2
.gate M a=i4 b=i1 q=m_o1
.gate S a=_0 l=i1 r=i2
.gate S a=_1 l=i3 r=_2
.gate S a=_2 l=i4 r=i5
.gate S a=i l=_0 r=_1

.end
'''


class TestIO(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_export_blif(self):
        i, j = inp(name='i'), inp(name='j')
        i1, i2, i3, i4, i5 = split(i, 5, names='i1 i2 i3 i4 i5')
        w1 = Wire()
        m_o1 = m(i4, i1, name='m_o1')
        c_o1 = c(i2, w1, name='c_o1')
        w1 <<= c_inv(i3, c_o1, name='w1')
        c_o2 = c(i5, m_o1, name='c_o2')
        m_o2 = m(c_o2, j, name='m_o2')

        buffer = StringIO()
        with buffer as f:
            export_to_blif(f)
            self.assertEqual(
                buffer.getvalue(),
                blif_example_1
            )


if __name__ == "__main__":
    unittest.main()
