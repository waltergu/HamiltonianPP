'''
KSpacePack test.
'''

__all__=['test_database_kspace']

from numpy import *
from HamiltonianPy.Basics.DataBase.KSpacePack import *

def test_database_kspace():
    print 'test_database_kspace'
    c=square_bz(reciprocals=[array([1.0,1.0]),array([1.0,-1.0])],nk=100)
    print 'volume: %s'%c.volume('k')
    c.plot(name='diamond')

    d=rectangle_bz(nk=100)
    print 'volume: %s'%(d.volume('k')/(2*pi)**2)
    d.plot(name='rectangle')

    e=hexagon_bz(nk=100,vh='v')
    print 'volume: %s'%(e.volume('k')/(2*pi)**2)
    e.plot(name='hexagon_v')

    f=hexagon_bz(nk=100,vh='h')    
    print 'volume: %s'%(f.volume('k')/(2*pi)**2)
    f.plot(name='hexagon_h')

    hexagon_gkm(nk=100).plot(name='hexagon_gkm')
    square_gxm(nk=100).plot(name='square_gxm')

    print