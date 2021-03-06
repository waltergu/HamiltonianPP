'''
FOperator test (4 tests in total).
'''

__all__=['fockoperator']

from HamiltonianPy.Basics.Geometry import *
from HamiltonianPy.Basics.DegreeOfFreedom import *
from HamiltonianPy.Basics.Operator import *
from HamiltonianPy.Basics.FockPackage import *
from unittest import TestCase,TestLoader,TestSuite

class TestOperator(TestCase):
    def setUp(self):
        self.operator=FQuadratic(
                            value=      1.0j,
                            indices=    [   Index(PID(site=1),FID(orbital=0,spin=0,nambu=CREATION)),
                                            Index(PID(site=1),FID(orbital=0,spin=0,nambu=ANNIHILATION))
                                        ],
                            seqs=       [1,1],
                            rcoord=     [0.0,0.0],
                            icoord=     [0.0,0.0]
                            )

    def test_dagger(self):
        result=FQuadratic(
                    value=      -1.0j,
                    indices=    [   Index(PID(site=1),FID(orbital=0,spin=0,nambu=CREATION)),
                                    Index(PID(site=1),FID(orbital=0,spin=0,nambu=ANNIHILATION))
                                ],
                    seqs=       [1,1],
                    rcoord=     [0.0,0.0],
                    icoord=     [0.0,0.0]
                    )
        self.assertEqual(self.operator.dagger,result)

    def test_isHermitian(self):
        self.assertFalse(self.operator.isHermitian())
        self.assertTrue((self.operator*1.0j).isHermitian())

    def test_isnormalordered(self):
        self.assertTrue(self.operator.isnormalordered())

class TestOperators(TestCase):
    def setUp(self):
        self.a=FQuadratic(
                    value=      1.0j,
                    indices=    [   Index(PID(site=1),FID(orbital=0,spin=0,nambu=CREATION)),
                                    Index(PID(site=1),FID(orbital=0,spin=0,nambu=ANNIHILATION))
                                ],
                    seqs=       [1,1],
                    rcoord=     [0.0,0.0],
                    icoord=     [0.0,0.0]
                    )
        self.b=FQuadratic(
                    value=      2.0,
                    indices=    [   Index(PID(site=0),FID(orbital=0,spin=0,nambu=ANNIHILATION)),
                                    Index(PID(site=0),FID(orbital=0,spin=0,nambu=ANNIHILATION))
                                ],
                    seqs=       [0,1],
                    rcoord=     [1.0,0.0],
                    icoord=     [0.0,0.0]
                    )

    def test_algebra(self):
        result=Operators()
        result+=self.a
        result+=self.b
        result+=result.dagger
        result*=2
        self.assertEqual(len(result),2)
        self.assertEqual(result[self.b.id],self.b*2)

fockoperator=TestSuite([
                    TestLoader().loadTestsFromTestCase(TestOperator),
                    TestLoader().loadTestsFromTestCase(TestOperators),
                    ])
