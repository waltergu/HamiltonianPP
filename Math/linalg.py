'''
Linear algebra, including
1) constants: TOL
2) functions: eigsh,block_diag,csrkron,csckron,kron,kronsum,parity,dagger,truncated_svd
3) classes: Lanczos
'''

__all__=['TOL','eigsh','block_diag','csrkron','csckron','kron','kronsum','parity','dagger','truncated_svd','Lanczos']

import numpy as np
import numpy.linalg as nl
import scipy.sparse as sp
import scipy.linalg as sl
from linalg_Fortran import *
from copy import copy

TOL=5*10**-12

def eigsh(A,max_try=6,**karg):
    '''
    Find the eigenvalues and eigenvectors of the real symmetric square matrix or complex hermitian matrix A.
    This is a wrapper for scipy.sparse.linalg.eigsh to handle the exceptions it raises.
    Parameters:
        A: An NxN matrix, array, sparse matrix, or LinearOperator
            The matrix whose eigenvalues and eigenvectors is to be computed.
        max_try: integer, optional
            The maximum number of tries to do the computation when the computed eigenvalues/eigenvectors do not converge.
        karg: dict
            Please refer to https://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.sparse.linalg.eigsh.html for details.
    '''
    if A.shape==(1,1):
        assert 'M' not in karg
        assert 'sigma' not in karg
        es=np.array([A.todense()[0,0]])
        vs=np.ones((1,1),dtype=A.dtype)
    else:
        num=1
        while True:
            try:
                es,vs=sp.linalg.eigsh(A,**karg)
                break
            except sp.linalg.ArpackNoConvergence as err:
                if num<max_try:
                    num+=1
                else:
                    raise err
    return es,vs

def block_diag(*ms):
    '''
    Create a block diagonal matrix from provided ones.
    Parameters:
        ms: list of 2d ndarray
            The input matrices.
    Returns: 2d ndarray
        The constructed block diagonal matrix.
    '''
    if len(ms)==0: ms=[np.zeros((0,0))]
    shapes=np.array([a.shape for a in ms])
    dtype=np.find_common_type([m.dtype for m in ms],[])
    result=np.zeros(np.sum(shapes,axis=0),dtype=dtype)
    r,c=0,0
    for i,(cr,cc) in enumerate(shapes):
        result[r:r+cr,c:c+cc]=ms[i]
        r+=cr
        c+=cc
    return result

def csrkron(m1,m2,rows):
    '''
    Kronecker product of two compressed sparse row matrices.
    Parameters:
        m1,m2: csr_matrix
            The matrices.
        rows: list of sorted integer, optional
            The wanted rows of the result.
    Returns: csr_matrix
        The result.
    '''
    assert m1.dtype==m2.dtype
    rs1=np.divide(rows,m2.shape[0])
    rs2=np.mod(rows,m2.shape[0])
    nnz=(m1.indptr[rs1+1]-m1.indptr[rs1]).dot(m2.indptr[rs2+1]-m2.indptr[rs2])
    if nnz>0:
        if m1.dtype==np.float32:
            data,indices,indptr,shape=fkron_csr_r4(m1.data,m1.indices,m1.indptr,m1.shape,rs1,m2.data,m2.indices,m2.indptr,m2.shape,rs2,nnz)
        elif m1.dtype==np.float64:
            data,indices,indptr,shape=fkron_csr_r8(m1.data,m1.indices,m1.indptr,m1.shape,rs1,m2.data,m2.indices,m2.indptr,m2.shape,rs2,nnz)
        elif m1.dtype==np.complex64:
            data,indices,indptr,shape=fkron_csr_c4(m1.data,m1.indices,m1.indptr,m1.shape,rs1,m2.data,m2.indices,m2.indptr,m2.shape,rs2,nnz)
        elif m1.dtype==np.complex128:
            data,indices,indptr,shape=fkron_csr_c8(m1.data,m1.indices,m1.indptr,m1.shape,rs1,m2.data,m2.indices,m2.indptr,m2.shape,rs2,nnz)
        else:
            raise ValueError("csrkron error: only matrices with dtype being float32, float64, complex64 or complex128 are supported.")
        result=sp.csr_matrix((data,indices,indptr),shape=shape)
    else:
        result=sp.csr_matrix((len(rows),m1.shape[1]*m2.shape[1]),dtype=m1.dtype)
    return result

def csckron(m1,m2,cols):
    '''
    Kronecker product of two compressed sparse column matrices.
    Parameters:
        m1,m2: csc_matrix
            The matrices.
        cols: list of sorted integer
            The wanted columns of the result.
    Returns: csc_matrix
        The result.
    '''
    assert m1.dtype==m2.dtype
    cs1=np.divide(cols,m2.shape[1])
    cs2=np.mod(cols,m2.shape[1])
    nnz=(m1.indptr[cs1+1]-m1.indptr[cs1]).dot(m2.indptr[cs2+1]-m2.indptr[cs2])
    if nnz>0:
        if m1.dtype==np.float32:
            data,indices,indptr,shape=fkron_csc_r4(m1.data,m1.indices,m1.indptr,m1.shape,cs1,m2.data,m2.indices,m2.indptr,m2.shape,cs2,nnz)
        elif m1.dtype==np.float64:
            data,indices,indptr,shape=fkron_csc_r8(m1.data,m1.indices,m1.indptr,m1.shape,cs1,m2.data,m2.indices,m2.indptr,m2.shape,cs2,nnz)
        elif m1.dtype==np.complex64:
            data,indices,indptr,shape=fkron_csc_c4(m1.data,m1.indices,m1.indptr,m1.shape,cs1,m2.data,m2.indices,m2.indptr,m2.shape,cs2,nnz)
        elif m1.dtype==np.complex128:
            data,indices,indptr,shape=fkron_csc_c8(m1.data,m1.indices,m1.indptr,m1.shape,cs1,m2.data,m2.indices,m2.indptr,m2.shape,cs2,nnz)
        else:
            raise ValueError("csckron error: only matrices with dtype being float32, float64, complex64 or complex128 are supported.")
        result=sp.csc_matrix((data,indices,indptr),shape=shape)
    else:
        result=sp.csc_matrix((m1.shape[0]*m2.shape[0],len(cols)),dtype=m1.dtype)
    return result

def kron(m1,m2,rows=None,cols=None,format='csr'):
    '''
    Kronecker product of two matrices.
    Parameters:
        m1,m2: 2d ndarray
            The matrices.
        rows,cols: list of sorted integer, optional
            The wanted rows and cols.
        format: string, optional
            The format of the product.
    Returns: sparse matrix whose format is specified by the parameter format
        The product.
    '''
    if rows is not None and cols is not None:
        if len(rows)>=len(cols):
            result=csckron(sp.csc_matrix(m1),sp.csc_matrix(m2),cols)[rows,:].asformat(format)
        else:
            result=csrkron(sp.csr_matrix(m1),sp.csr_matrix(m2),rows)[:,cols].asformat(format)
    elif rows is not None:
        result=csrkron(sp.csr_matrix(m1),sp.csr_matrix(m2),rows).asformat(format)
    elif cols is not None:
        result=csckron(sp.csc_matrix(m1),sp.csc_matrix(m2),cols).asformat(format)
    else:
        result=sp.kron(m1,m2,format=format)
    return result

def kronsum(m1,m2,rows=None,cols=None,format='csr'):
    '''
    Kronecker sum of two matrices.
    Parameters:
        m1,m2: 2d ndarray
            The matrices.
        rows,cols: list of sorted integer, optional
            The wanted rows and cols.
        format: string, optional
            The format of the product.
    Returns: sparse matrix whose format is specified by the parameter format
        The Kronecker sum.
    '''
    return kron(m2,sp.identity(m1.shape[0],dtype=m1.dtype),rows,cols,format)+kron(sp.identity(m2.shape[0],dtype=m2.dtype),m1,rows,cols,format)

def parity(permutation):
    '''
    Determine the parity of a permutation.
    Parameters:
        permutation: list of integer
            A permutation of integers from 0 to N-1.
    Returns: -1 or +1
        -1 for odd permutation, and
        +1 for even permutation.
    '''
    result=1
    for i in xrange(len(permutation)-1):
        if permutation[i]!=i:
            result*=-1
            pos=min(xrange(i,len(permutation)),key=permutation.__getitem__)
            permutation[i],permutation[pos]=permutation[pos],permutation[i]
    return result

def dagger(m):
    '''
    The Hermitian conjugate of a matrix.
    '''
    assert m.ndim==2
    if m.dtype in (np.int,np.int8,np.int16,np.int32,np.int64,np.float,np.float16,np.float32,np.float64,np.float128):
        return m.T
    else:
        return m.T.conjugate()

def truncated_svd(m,nmax=None,tol=None,return_truncation_err=False,**karg):
    '''
    Perform the truncated svd.
    Parameters:
        m: 2d ndarray
            The matrix to be truncated_svded.
        nmax: integer, optional
            The maximum number of singular values to be kept. 
            If it is None, it takes no effect.
        tol: float64, optional
            The truncation tolerance.
            If it is None, it takes no effect.
        return_truncation_err: logical, optional
            If it is True, the truncation err will be returned.
        For other parameters, please see http://docs.scipy.org/doc/numpy/reference/generated/numpy.linalg.svd.html for details.
    Returns:
        u,s,v: ndarray
            The truncated result.
        err: float64, optional
            The truncation error.
    '''
    u,s,v=sl.svd(m,**karg)
    nmax=len(s) if nmax is None else min(nmax,len(s))
    tol=s[nmax-1] if tol is None else max(s[nmax-1],tol)
    indices=(s>=tol)
    if return_truncation_err:
        u,s,v,err=u[:,indices],s[indices],v[indices,:],(s[~indices]**2).sum()
        return u,s,v,err
    else:
        u,s,v=u[:,indices],s[indices],v[indices,:]
        return u,s,v

class Lanczos(object):
    '''
    The Lanczos algorithm to deal with csr-formed sparse Hermitian matrices.
    Attributes:
        matrix: csr_matrix
            The csr-formed sparse Hermitian matrix.
        zero: float
            The precision used to cut off the Lanczos iterations.
        new,old: 1D ndarray
            The new and old vectors updated in the Lanczos iterations.
        a,b: 1D list of floats
            The coefficients calculated in the Lanczos iterations.
        cut: logical
            A flag to tag whether the iteration has been cut off.
    '''
    def __init__(self,matrix,v0=None,check_normalization=True,vtype='rd',zero=10**-10,dtype=np.complex128):
        '''
        Constructor.
        Parameters:
            matrix: csr_matrix
                The csr-formed sparse Hermitian matrix.
            v0: 1D ndarray,optional
                The initial vector to begin with the Lanczos iterations. 
                It must be normalized already.
            check_nomalization: logical, optional
                When it is True, the input v0 will be check to see whether it is normalized.
            vtype: string,optional
                A flag to tell what type of initial vectors to use when the parameter vector is None.
                'rd' means a random vector while 'sy' means a symmetric vector.
            zero: float,optional
                The precision used to cut off the Lanczos iterations.
            dtype: dtype,optional
                The data type of the iterated vectors.
        '''
        self.matrix=matrix
        self.zero=zero
        if v0 is None:
            if vtype.lower()=='rd':
                self.new=np.zeros(matrix.shape[0],dtype=dtype)
                self.new[:]=np.random.rand(matrix.shape[0])
            else:
                self.new=np.ones(matrix.shape[0],dtype=dtype)
            self.new[:]=self.new[:]/nl.norm(self.new)
        else:
            if check_normalization:
                temp=nl.norm(v0)
                if abs(temp-v0)>zero:
                    raise ValueError('Lanczos constructor error: v0(norm=%s) is not normalized.'%temp)
            self.new=v0
        self.old=copy(self.new)
        self.cut=False
        self.a=[]
        self.b=[]

    def iter(self):
        '''
        The Lanczos iteration.
        '''
        count=len(self.a)
        buff=self.matrix.dot(self.new)
        self.a.append(np.vdot(self.new,buff))
        if count>0:
            buff[:]=buff[:]-self.a[count]*self.new-self.b[count-1]*self.old
        else:
            buff[:]=buff[:]-self.a[count]*self.new
        nbuff=nl.norm(buff)
        if nbuff>self.zero:
            self.b.append(nbuff)
            self.old[:]=self.new[:]
            self.new[:]=buff[:]/nbuff
        else:
            self.cut=True
            self.b.append(0.0)
            self.old[:]=self.new[:]
            self.new[:]=0.0

    def tridiagnoal(self):
        '''
        This method returns the tridiagnoal matrix representation of the original sparse Hermitian matrix.
        Returns:
            result: 2D ndarray
                The tridiagnoal matrix representation of the original sparse Hermitian matrix.
        '''
        nmatrix=len(self.a)
        result=np.zeros((nmatrix,nmatrix))
        for i,(a,b) in enumerate(zip(self.a,self.b)):
            result[i,i]=a.real
            if i<nmatrix-1: 
                result[i+1,i]=b
                result[i,i+1]=b
        return result

    def eig(self,job='n',precision=10**-10):
        '''
        This method returns the ground state energy and optionally the ground state of the original sparse Hermitian matrix.
        Parameters:
            job: string
                A flag to tag what jobs the method does.
                'n' means ground state energy only and 'v' means ground state energy and ground state both.
            precision: float
                The precision of the calculated ground state energy which is used to terminate the Lanczos iteration.
        Returns:
            gse: float
                the ground state energy.
            gs: 1D ndarray,optional
                The ground state. Present when the parameter job is set to be 'V' or 'v'.
        '''
        if job in ('V','v'):gs=copy(self.new)
        delta=1.0;buff=np.inf
        while not self.cut and delta>precision:
            self.iter()
            if job in ('V','v'):
                w,vs=sl.eigh(self.tridiagnoal())
                gse=w[0];v=vs[:,0]
            else:
                gse=sl.eigh(self.tridiagnoal(),eigvals_only=True)[0]
            delta=abs(gse-buff)
            buff=gse
        if job in ('V','v'):
            self.a=[];self.b=[]
            for i in xrange(len(v)):
                if i==0:
                    self.new[:]=gs[:]
                    gs[:]=0.0
                gs[:]+=self.new*v[i]
                self.iter()
            return gse,gs
        else:
            return gse
