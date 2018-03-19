'''
=======================
Miscellaneous functions
=======================

Miscellaneous functions (mainly for tensor decomposition), including:
    * functions: random, directsum, eigh, partitioned_svd, svd, expanded_svd, deparallelization
'''

__all__=['random','directsum','eigh','partitioned_svd','svd','expanded_svd','deparallelization']

import numpy as np
import itertools as it
import scipy.linalg as sl
import HamiltonianPy.Misc as hm
from TensorBase import Label
from Tensor import DTensor,STensor
from HamiltonianPy import QuantumNumbers

def random(labels,mode='D',dtype=np.float64):
    '''
    Construct a random block-structured tensor.

    Parameters
    ----------
    labels : list of Label
        The labels of the random tensor.
    mode : 'D'/'S', optional
        'D' for dense and 'S' for sparse.
    dtype : np.float64, np.complex128, optional
        The data type of the random tensor.

    Returns
    -------
    DTensor/STensor
        A random block-structured tensor.
    '''
    assert  mode in 'DS' and dtype in (np.float32,np.float64,np.complex64,np.complex128)
    np.random.seed()
    if next(iter(labels)).qnon:
        paxes,plbls,maxes,mlbls=[],[],[],[]
        for axis,label in enumerate(labels):
            (paxes if label.flow==1 else maxes).append(axis)
            (plbls if label.flow==1 else mlbls).append(label)
        traxes=np.argsort(list(it.chain(paxes,maxes)))
        if mode=='D':
            plabel,ppermutation=Label.union(plbls,'__TENSOR_RANDOM_D_+__',+1,mode=1)
            mlabel,mpermutation=Label.union(mlbls,'__TENSOR_RANDOM_D_-__',-1,mode=1)
            data=np.zeros((plabel.dim,mlabel.dim),dtype=dtype)
            pod,mod=plabel.qns.to_ordereddict(),mlabel.qns.to_ordereddict()
            for qn in it.ifilter(pod.has_key,mod):
                bshape=(pod[qn].stop-pod[qn].start,mod[qn].stop-mod[qn].start)
                data[pod[qn],mod[qn]]=np.random.random(bshape)
                if dtype in (np.complex64,np.complex128):
                    data[pod[qn],mod[qn]]+=1j*np.random.random(bshape)
            for axis,permutation in [(0,np.argsort(ppermutation)),(1,np.argsort(mpermutation))]:
                data=hm.reorder(data,axes=[axis],permutation=permutation)
            data=data.reshape(tuple(label.dim for label in it.chain(plbls,mlbls))).transpose(*traxes)
            result=DTensor(data,labels=labels)
        else:
            plabel,precord=Label.union(plbls,'__TENSOR_RANDOM_S_+__',+1,mode=2)
            mlabel,mrecord=Label.union(mlbls,'__TENSOR_RANDOM_S_-__',-1,mode=2)
            data={}
            ods=[label.qns.to_ordereddict(protocol=QuantumNumbers.COUNTS) for label in labels]
            pod,mod=plabel.qns.to_ordereddict(),mlabel.qns.to_ordereddict()
            for qn in it.ifilter(pod.has_key,mod):
                for pqns,mqns in it.product(precord[qn],mrecord[qn]):
                    qns=tuple(it.chain(pqns,mqns))
                    qns=tuple(qns[axis] for axis in traxes)
                    data[qns]=np.zeros(tuple(od[qn] for od,qn in zip(ods,qns)),dtype=dtype)
                    data[qns][...]=np.random.random(data[qns].shape)
                    if dtype in (np.complex64,np.complex128):
                        data[qns][...]+=1j*np.random.random(data[qns].shape)
            result=STensor(data,labels=labels)
    else:
        assert mode=='D'
        data=np.zeros(tuple(label.dim for label in labels),dtype=dtype)
        data[...]=np.random.random(data.shape)
        if dtype in (np.complex64,np.complex128):
            data[...]+=1j*np.random.random(data.shape)
        result=DTensor(data,labels=labels)
    return result

def directsum(tensors,labels,axes=()):
    '''
    The directsum of a couple of tensors.

    Parameters
    ----------
    tensors : list of DTensor/STensor
        The tensors to be directsummed.
    labels : list of Label
        The labels of the directsum.
    axes : list of int, optional
            The axes along which the directsum is block diagonal.

    Returns
    -------
    DTensor/STensor
        The directsum of the tensors.
    '''
    TENSOR=next(iter(tensors))
    assert TENSOR.ndim>len(axes)
    assert len({tensor.ndim for tensor in tensors})==1
    assert len({tuple(tensor.shape[axis] for axis in axes) for tensor in tensors})==1
    assert len({tuple(label.flow for label in tensor.labels) for tensor in tensors})==1
    alters=set(xrange(TENSOR.ndim))-set(axes)
    if isinstance(TENSOR,DTensor):
        assert len({tensor.qnon for tensor in tensors})==1
        shape,dtypes=[0 if axis in alters else TENSOR.shape[axis] for axis in xrange(TENSOR.ndim)],[]
        for tensor in tensors:
            for alter in alters: shape[alter]+=tensor.shape[alter]
            dtypes.append(tensor.dtype)
        data=np.zeros(tuple(shape),dtype=np.find_common_type([],dtypes))
        slices=[slice(0,0,0) if axis in alters else slice(None,None,None) for axis in xrange(TENSOR.ndim)]
        for tensor in tensors:
            for alter in alters: slices[alter]=slice(slices[alter].stop,slices[alter].stop+tensor.shape[alter])
            data[tuple(slices)]=tensor.data
        for alter in alters: labels[alter].qns=(QuantumNumbers.union if TENSOR.qnon else np.sum)([tensor.labels[alter].qns for tensor in tensors])
    else:
        content={}
        for qns,block in it.chain(*tuple(tensor.iteritems() for tensor in tensors)):
            if qns not in content: content[qns]=([0 if axis in alters else block.shape[axis] for axis in xrange(block.ndim)],[],[])
            for alter in alters: content[qns][0]+=block.shape[alter]
            content[qns][1].append(block.dtype)
            content[qns][2].append(block)
        data={}
        for qns,(shape,dtypes,blocks) in content.iteritems():
            data[qns]=np.zeros(tuple(shape),dtype=np.find_common_type([],dtypes))
            slices=[slice(0,0,0) if axis in alters else slice(None,None,None) for axis in xrange(TENSOR.ndim)]
            for block in blocks:
                for alter in alters: slices[alter]=slice(slices[alter].stop,slices[alter].stop+block.shape[alter])
                data[tupe(slices)]=block
        for alter in alters: labels[alter].qns=QuantumNumbers.union([tensor.labels[alter].qns for tensor in tensors]).sorted(history=False)
    for axis in xrange(TENSOR.ndim): labels[axis].flow=TENSOR.labels[axis].flow
    for axis in axes: labels[axis].qns=tensor.labels[axis].qns
    return type(TENSOR)(data,labels=labels)

def eigh(tensor,row,new,col,return_dagger=False):
    '''
    Eigenvalue decomposition of a tensor.

    Parameters
    ----------
    tensor : DTensor/STensor
        The tensor to be eigenvalue-decomposed.
    row,col : list of Label or int
        The axes or labels to be merged as the row/column during the eigenvalue decomposition.
    new : Label
        The label for the eigenvalues.
    return_dagger : logical, optional
        True for returning the Hermitian conjugate of the eigenvalue matrix and False for not.

    Returns
    -------
    E,U : DTensor/STensor
        The eigenvalue decomposition of the tensor, such that ``tensor==U*E*U.dagger``.
    UD : DTensor/STensor, optional
        The Hermitian conjugate of the tensor `U`, with the column split in accordance with `tensor`.

    Notes
    -----
    The tensor to be decomposed must be Hermitian after the merge of its dimensions.
    '''
    assert len(row)+len(col)==tensor.ndim
    row=[r if isinstance(r,Label) else tensor.label(r) for r in row]
    col=[c if isinstance(c,Label) else tensor.label(c) for c in col]
    if isinstance(tensor,STensor):
        row_label,row_record=Label.union(row,'__TENSOR_EIGH_ROW__',+1,mode=2)
        col_label,col_record=Label.union(col,'__TENSOR_EIGH_COL__',-1,mode=2)
        assert len(row_label.qns)==len(col_label.qns)
        m=tensor.merge((row,row_label,row_record),(col,col_label,col_record)).data
        Es,Us=[],{}
        for qns,block in m.iteritems():
            assert qns[0]==qns[1] and block.shape[0]==block.shape[1]
            e,u=sl.eigh(block,check_finite=False)
            Es.append(e)
            Us[qns]=u
        new=new.replace(qns=row_label.qns,flow=None)
        E=DTensor(np.concatenate(Es),labels=[new])
        U=DTensor(Us,labels=[row_label,new.replace(flow=-1)]).split((row_label,row,row_record))
    elif tensor.qnon:
        row_label,row_permutation=Label.union(row,'__TENSOR_EIGH_ROW__',+1,mode=1)
        col_label,col_permutation=Label.union(col,'__TENSOR_EIGH_COL__',-1,mode=1)
        assert len(row_label.qns)==len(col_label.qns)
        m=tensor.merge((row,row_label,row_permutation),(col,col_label,col_permutation)).data
        row_od,col_od=row_label.qns.to_ordereddict(),col_label.qns.to_ordereddict()
        E=np.zeros(len(row_label.qns),dtype=np.float64)
        U=np.zeros((len(row_label.qns),len(row_label.qns)),dtype=tensor.dtype)
        for qn in row_od:
            assert row_od[qn]==col_od[qn]
            e,u=sl.eigh(m[row_od[qn],row_od[qn]],check_finite=False)
            E[row_od[qn]]=e
            U[row_od[qn],row_od[qn]]=u
        new=new.replace(qns=row_label.qns,flow=None)
        E=DTensor(E,labels=[new])
        U=DTensor(U,labels=[row_label,new.replace(flow=-1)]).split((row_label,row,np.argsort(row_permutation)))
    else:
        row_label=Label('__TENSOR_EIGH_ROW__',qns=np.product([label.dim for label in row]))
        col_label=Label('__TENSOR_EIGH_COL__',qns=np.product([label.dim for label in col]))
        assert row_label.qns==col_label.qns
        e,u=sl.eigh(tensor.merge((row,row_label),(col,col_label)).data,check_finite=False)
        new=new.replace(qns=len(row_label),flow=None)
        E=DTensor(e,labels=[new])
        U=DTensor(u,labels=[row_label,new.replace(flow=0)]).split((row_label,row))
    return (E,U,U.dagger) if return_dagger else (E,U)

def partitioned_svd(tensor,L,new,R,mode='D',nmax=None,tol=None,return_truncation_err=False):
    '''
    Partition a 1d-tensor according to L and R and then perform the Schmitt decomposition.

    Parameters
    ----------
    tensor : DTensor
        The tensor to be partitioned_svded.
    L,R : Label
        The left/right part of the partition.
    new : Label
        The label for the singular values.
    mode : 'D'/'S', optional
        'D' for dense and 'S' for sparse.
    nmax,tol,return_truncation_err :
        Please refer to HamiltonianPy.Misc.Linalg.truncated_svd for details.

    Returns
    -------
    U,S,V : DTensor/STensor
        The Schmitt decomposition of the 1d tensor.
    err : np.float64, optional
        The truncation error.
    '''
    assert tensor.ndim==1 and mode in 'DS'
    if tensor.qnon:
        data,qns=tensor.data,tensor.labels[0].qns
        assert qns.num==1 and sl.norm(qns.contents)<10**-6
        lod,rod=L.qns.to_ordereddict(),R.qns.to_ordereddict()
        us,ss,vs,qns,count=[],[],[],[],0
        for qn in it.ifilter(lod.has_key,rod):
            s1,s2=lod[qn],rod[qn]
            n1,n2=s1.stop-s1.start,s2.stop-s2.start
            u,s,v=sl.svd(data[count:count+n1*n2].reshape((n1,n2)),full_matrices=False,lapack_driver='gesvd')[0:3]
            us.append(u)
            ss.append(s)
            vs.append(v)
            qns.append(qn)
            count+=n1*n2
        temp=np.sort(np.concatenate([-s for s in ss]))
        nmax=len(temp) if nmax is None else min(nmax,len(temp))
        tol=temp[nmax-1] if tol is None else min(-tol,temp[nmax-1])
        if mode=='D':
            Us,Ss,Vs,contents=[],[],[],([],[])
            for u,s,v,qn in zip(us,ss,vs,qns):
                cut=np.searchsorted(-s,tol,side='right')
                if cut>0:
                    Us.append(u[:,0:cut])
                    Ss.append(s[0:cut])
                    Vs.append(v[0:cut,:])
                    contents[0].append(qn)
                    contents[1].append(cut)
            new=new.replace(qns=QuantumNumbers('U',contents,QuantumNumbers.COUNTS),flow=None)
            nod=new.qns.to_ordereddict()
            U=np.zeros((L.dim,new.dim),dtype=tensor.dtype)
            S=np.concatenate(Ss)
            V=np.zeros((new.dim,R.dim),dtype=tensor.dtype)
            for u,v,qn in zip(Us,Vs,nod):
                U[lod[qn],nod[qn]]=u
                V[nod[qn],rod[qn]]=v
            U=DTensor(U,labels=[L,new.replace(flow=-1)])
            S=DTensor(S,labels=[new])
            V=DTensor(V,labels=[new.replace(flow=+1),R])
        else:
            Us,Ss,Vs,contents={},[],{},([],[])
            for u,s,v,qn in zip(us,ss,vs,qns):
                cut=np.searchsorted(-s,tol,side='right')
                if cut>0:
                    Us[(qn,qn)]=u[:,0:cut]
                    Ss.append(s[0:cut])
                    Vs[(qn,qn)]=v[0:cut,:]
                    contents[0].append(qn)
                    contents[1].append(cut)
            new=new.replace(qns=QuantumNumbers('U',contents,QuantumNumbers.COUNTS),flow=None)
            U=STensor(Us,labels=[L,new.replace(flow=-1)])
            S=DTensor(np.concatenate(Ss),labels=[new])
            V=STensor(Vs,labels=[new.replace(flow=+1),R])
        if return_truncation_err: err=(temp[nmax:]**2).sum()
    else:
        m=tensor.data.reshape((L.dim,R.dim))
        data=hm.truncated_svd(m,full_matrices=False,nmax=nmax,tol=tol,return_truncation_err=return_truncation_err)
        new=new.replace(qns=len(data[1]),flow=None)
        U=DTensor(data[0],labels=[L,new.replace(flow=0)])
        S=DTensor(data[1],labels=[new])
        V=DTensor(data[2],labels=[new.replace(flow=0),R])
        if return_truncation_err: err=data[3]
    return (U,S,V,err) if return_truncation_err else (U,S,V)

def svd(tensor,row,new,col,nmax=None,tol=None,return_truncation_err=False,**karg):
    '''
    Perform the svd.

    Parameters
    ----------
    tensor : DTensor/STensor
        The tensor to be svded.
    row,col : list of Label or int
        The labels or axes to be merged as the row/column during the svd.
    new : Label
        The label for the singular values.
    nmax,tol,return_truncation_err :
        Please refer to HamiltonianPy.Misc.Linalg.truncated_svd for details.

    Returns
    -------
    U,S,V : DTensor/STensor
        The result tensor.
    err : np.float64, optional
        The truncation error.
    '''
    assert len(row)+len(col)==tensor.ndim
    row=[r if isinstance(r,Label) else tensor.label(r) for r in row]
    col=[c if isinstance(c,Label) else tensor.label(c) for c in col]
    if isinstance(tensor,STensor):
        row_label,row_record=Label.union(row,'__TENSOR_SVD_ROW__',+1,mode=2)
        col_label,col_record=Label.union(col,'__TENSOR_SVD_COL__',-1,mode=2)
        m=tensor.merge((row,row_label,row_record),(col,col_label,col_record)).data
        us,ss,vs,qns=[],[],[],[]
        for (rowqn,colqn),block in m.iteritems():
            assert rowqn==colqn
            u,s,v=sl.svd(block,full_matrices=False,lapack_driver='gesvd')[0:3]
            us.append(u)
            ss.append(s)
            vs.append(v)
            qns.append(rowqn)
        temp=np.sort(np.concatenate([-s for s in ss]))
        nmax=len(temp) if nmax is None else min(nmax,len(temp))
        tol=temp[nmax-1] if tol is None else min(-tol,temp[nmax-1])
        Us,Ss,Vs,contents={},[],{},([],[])
        for u,s,v,qn in zip(us,ss,vs,qns):
            cut=np.searchsorted(-s,tol,side='right')
            if cut>0:
                Us[(qn,qn)]=u[:,0:cut]
                Ss.append(s[0:cut])
                Vs[(qn,qn)]=v[0:cut,:]
                contents[0].append(qn)
                contents[1].append(cut)
        new=new.replace(qns=QuantumNumbers('U',contents,protocol=QuantumNumbers.COUNTS),flow=None)
        U=STensor(Us,labels=[row_label,new.replace(flow=-1)]).split((row_label,row,row_record))
        S=DTensor(np.concatenate(Ss),labels=[new])
        V=STensor(Vs,labels=[new.replace(flow=+1),col_label]).split((col_label,col,col_record))
        if return_truncation_err: err=(temp[nmax:]**2).sum()
    elif tensor.qnon:
        row_label,row_permutation=Label.union(row,'__TENSOR_SVD_ROW__',+1,mode=1)
        col_label,col_permutation=Label.union(col,'__TENSOR_SVD_COL__',-1,mode=1)
        m=tensor.merge((row,row_label,row_permutation),(col,col_label,col_permutation)).data
        row_od,col_od=row_label.qns.to_ordereddict(),col_label.qns.to_ordereddict()
        us,ss,vs,qns=[],[],[],[]
        for qn in it.ifilter(row_od.has_key,col_od):
            u,s,v=sl.svd(m[row_od[qn],col_od[qn]],full_matrices=False,lapack_driver='gesvd')[0:3]
            us.append(u)
            ss.append(s)
            vs.append(v)
            qns.append(qn)
        temp=np.sort(np.concatenate([-s for s in ss]))
        nmax=len(temp) if nmax is None else min(nmax,len(temp))
        tol=temp[nmax-1] if tol is None else min(-tol,temp[nmax-1])
        Us,Ss,Vs,contents=[],[],[],([],[])
        for u,s,v,qn in zip(us,ss,vs,qns):
            cut=np.searchsorted(-s,tol,side='right')
            if cut>0:
                Us.append(u[:,0:cut])
                Ss.append(s[0:cut])
                Vs.append(v[0:cut,:])
                contents[0].append(qn)
                contents[1].append(cut)
        S=np.concatenate(Ss)
        new=new.replace(qns=QuantumNumbers('U',contents,protocol=QuantumNumbers.COUNTS),flow=None)
        od=new.qns.to_ordereddict()
        U=np.zeros((row_label.dim,new.dim),dtype=tensor.dtype)
        V=np.zeros((new.dim,col_label.dim),dtype=tensor.dtype)
        for u,v,qn in zip(Us,Vs,od):
            U[row_od[qn],od[qn]]=u
            V[od[qn],col_od[qn]]=v
        U=DTensor(U,labels=[row_label,new.replace(flow=-1)]).split((row_label,row,np.argsort(row_permutation)))
        S=DTensor(S,labels=[new])
        V=DTensor(V,labels=[new.replace(flow=+1),col_label]).split((col_label,col,np.argsort(col_permutation)))
        if return_truncation_err: err=(temp[nmax:]**2).sum()
    else:
        row_label=Label('__TENSOR_SVD_ROW__',qns=np.product([label.dim for label in row]))
        col_label=Label('__TENSOR_SVD_COL__',qns=np.product([label.dim for label in col]))
        m=tensor.merge((row,row_label),(col,col_label)).data
        temp=hm.truncated_svd(m,full_matrices=False,nmax=nmax,tol=tol,return_truncation_err=return_truncation_err,**karg)
        u,s,v=temp[0],temp[1],temp[2]
        new=new.replace(qns=len(s),flow=None)
        U=DTensor(u,labels=[row_label,new.replace(flow=0)]).split((row_label,row))
        S=DTensor(s,labels=[new])
        V=DTensor(v,labels=[new.replace(flow=0),col_label]).split((col_label,col))
        if return_truncation_err: err=temp[3]
    return (U,S,V,err) if return_truncation_err else (U,S,V)

def expanded_svd(tensor,L,S,R,E,I,cut=0,nmax=None,tol=None):
    '''
    Expand a label of a tensor and perform a sequential svd.

    Parameters
    ----------
    tensor : DTensor/STensor
        The tensor to be expanded_svded.
    L,R : list of Label/int
        The labels or axes to be merged as the left/right dimension during the expanded svd.
    S : Label/int
        The label/axis to be expanded.
    E : list of Label
        The expansion of the merge of S labels.
    I : list of Label
        The labels of the newly generated internal legs during the expanded svd.
    cut : int, optional
        The labels in E whose sequences are less than cut will be tied with the u matrices of the svds from the left;
        The labels in E whose sequences are equal to or greater than cut will be tied with the v matrices of the svds from the right.
    nmax : int, optional
        The maximum number of singular values to be kept.
    tol : np.float64, optional
        The tolerance of the singular values.

    Returns
    -------
    list of DTensor/STensor
        The results of the expanded svd.
    '''
    assert len(L)+len(R)==tensor.ndim-1 and 0<=cut<=len(E)
    L=[l if isinstance(l,Label) else tensor.label(l) for l in L]
    S=S if isinstance(S,Label) else tensor.label(S)
    R=[r if isinstance(r,Label) else tensor.label(r) for r in R]
    llabel=Label.union(L,'__TENSOR_EXPANDED_SVD_L__',+1,mode=0)
    rlabel=Label.union(R,'__TENSOR_EXPANDED_SVD_R__',-1,mode=0)
    data=tensor.merge((L,llabel),(R,rlabel)).split((S,E))
    ms,u,s,v=[],None,None,None
    if cut==len(E):
        assert len(E)==len(I)
        for i in xrange(cut):
            if i>0: data=s*v
            u,s,v=svd(data,row=data.labels[:2],new=I[i],col=data.labels[2:],nmax=nmax,tol=tol)
            ms.append(u)
        ms[+0]=ms[+0].split((llabel,L))
        v=v.split((rlabel,R))
        return ms,s,v
    elif cut==0:
        assert len(E)==len(I)
        for i in xrange(len(E)-1,-1,-1):
            if i<len(E)-1: data=u*s
            u,s,v=svd(data,row=data.labels[:-2],new=I[i],col=data.labels[-2:],nmax=nmax,tol=tol)
            ms.insert(0,v)
        u=u.split((llabel,L))
        ms[-1]=ms[-1].split((rlabel,R))
        return u,s,ms
    else:
        assert len(E)==len(I)+1
        for i in xrange(cut):
            if i>0: data=s*v
            new=I[i] if i<cut-1 else Label('__TENSOR_EXPANDED_SVD_LINNER__',None)
            u,s,v=svd(data,row=data.labels[:2],new=new,col=data.labels[2:],nmax=nmax,tol=tol)
            ms.append(u)
        ls,data=s,v
        for i in xrange(len(E)-1,cut-1,-1):
            if i<len(E)-1: data=u*s
            new=I[i-1] if i>cut else Label('__TENSOR_EXPANDED_SVD_RINNER__',None)
            u,s,v=svd(data,row=data.labels[:-2],new=new,col=data.labels[-2:],nmax=nmax,tol=tol)
            ms.insert(cut,v)
        data,rs=u,s
        u,s,v=svd(ls*data*rs,row=[0],new=I[cut-1],col=[1])
        ms[cut-1]=ms[cut-1]*u
        ms[cut]=v*ms[cut]
        Lambda=s
        ms[+0]=ms[+0].split((llabel,L))
        ms[-1]=ms[-1].split((rlabel,R))
        return ms,Lambda

def deparallelization(tensor,row,new,col,mode='R',zero=10**-8,tol=10**-6):
    '''
    Deparallelize a tensor.

    Parameters
    ----------
    tensor : DTensor
        The tensor to be deparalleled.
    row,col : list of Label or int
        The labels or axes to be merged as the row/column during the deparallelization.
    new : Label
        The label for the new axis after the deparallelization.
    mode : 'R', 'C', optional
        'R' for the deparallelization of the row dimension;
        'C' for the deparallelization of the col dimension.
    zero : np.float64, optional
        The absolute value to identity zero vectors.
    tol : np.float64, optional
        The relative tolerance for rows or columns that can be considered as paralleled.

    Returns
    -------
    M : DTensor
        The deparallelized tensor.
    T : DTensor
        The coefficient matrix that satisfies T*M==m('R') or M*T==m('C').
    '''
    assert len(row)+len(col)==tensor.ndim
    row=[r if isinstance(r,Label) else tensor.label(r) for r in row]
    col=[c if isinstance(c,Label) else tensor.label(c) for c in col]
    rlabel=Label.union(row,'__TENSOR_DEPARALLELIZATION_ROW__',+1 if tensor.qnon else 0,mode=0)
    clabel=Label.union(col,'__TENSOR_DEPARALLELIZATION_COL__',-1 if tensor.qnon else 0,mode=0)
    data=tensor.merge((row,rlabel),(col,clabel)).data
    m1,m2,indices=hm.deparallelization(data,mode=mode,zero=zero,tol=tol,return_indices=True)
    if mode=='R':
        new=new.replace(qns=rlabel.qns.reorder(permutation=indices,protocol='EXPANSION') if tensor.qnon else len(indices))
        T=DTensor(m1,labels=[rlabel,new.replace(flow=-1 if tensor.qnon else 0)]).split((rlabel,row))
        M=DTensor(m2,labels=[new.replace(flow=+1 if tensor.qnon else 0),clabel]).split((clabel,col))
        return T,M
    else:
        new=new.replace(qns=clabel.qns.reorder(permutation=indices,protocol='EXPANSION') if tensor.qnon else len(indices))
        M=DTensor(m1,labels=[rlabel,new.replace(flow=-1 if tensor.qnon else 0)]).split((rlabel,row))
        T=DTensor(m2,labels=[new.replace(flow=+1 if tensor.qnon else 0),clabel]).split((clabel,col))
        return M,T
