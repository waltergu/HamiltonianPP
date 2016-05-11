'''
Matrix product state, including:
1) constants: LLINK, SITE, RLINK
2) classes: MPS, GMPS, VMPS, MMPS
'''

__all__=['LLINK','SITE','RLINK','MPS','GMPS','VMPS','MMPS']

from numpy import *
from TensorPy import *
from copy import deepcopy

LLINK,SITE,RLINK=0,1,2

class MPS(object):
    '''
    The base class for matrix product states.
    Attributes:
        order: list of int
            The order of the three axis of each matrix.
    '''
    order=[LLINK,SITE,RLINK]
    
    @property
    def state(self):
        '''
        Convert to the normal representation.
        '''
        raise NotImplementedError()

    @property
    def L(self):
        '''
        The axes of LLINK.
        '''
        return self.order.index(LLINK)

    @property
    def S(self):
        '''
        The axes of SITE.
        '''
        return self.order.index(SITE)

    @property
    def R(self):
        '''
        The axes of RLINK.
        '''
        return self.order.index(RLINK)

class GMPS(MPS):
    '''
    The general matrix product state.
    Attributes:
        ms: list of Tensor
            The matrices.
    '''

    def __init__(self,ms,labels):
        '''
        Constructor.
        Parameters:
            ms: list of 3d ndarray
                The matrices.
            labels: list of 3 tuples
                The labels of the axis of the matrices.
                Its length should be equal to that of ms.
                For each label in labels, 
                    label[0]: any hashable object
                        The left link label of the matrix.
                    label[1]: any hashable object
                        The site label of the matrix.
                    label[2]: any hashable object
                        The right link label of the matrix.
        '''
        if len(ms)!=len(labels):
            raise ValueError('GMPS construction error: the number of matrices(%s) is not equal to that of the labels(%s).'%(len(ms),len(labels)))
        self.ms=[]
        temp=[None]*3
        for i,(m,label) in enumerate(zip(ms,labels)):
            if m.ndim!=3:
                raise ValueError('GMPS construction error: all input matrices should be 3 dimensional.')
            L,S,R=label
            temp[self.L]=L
            temp[self.S]=S
            temp[self.R]=R
            self.ms.append(Tensor(m,labels=deepcopy(temp)))

    def __str__(self):
        '''
        Convert an instance to string.
        '''
        return '\n'.join(['%s'%m for m in self.ms])

    @property
    def state(self):
        '''
        Convert to the normal representation.
        '''
        result=None
        for m in self.ms:
            if result is None:
                result=m
            else:
                result=contract(result,m)
        return asarray(result).ravel()

    @property
    def norm(self):
        '''
        The norm of the matrix product state.
        '''
        for i,M in enumerate(self.ms):
            L,S,R=M.labels[self.L],M.labels[self.S],M.labels[self.R]
            if i==0:
                temp=M
            else:
                temp=contract(v*asarray(s)[:,newaxis],M)
                temp.relabel(news=[L],olds=['_'+L])
            u,s,v=temp.svd([L,S],'_'+str(R),[R])
        return (asarray(v)*asarray(s)[:,newaxis])[0,0]

    def to_vmps(self):
        '''
        Convert to the VMPS representation.
        '''
        Gammas,Lambdas,labels=[],[],[]
        for i,M in enumerate(self.ms):
            L,S,R=M.labels[self.L],M.labels[self.S],M.labels[self.R]
            if i==0:
                temp=M
            else:
                temp=contract(v*asarray(old)[:,newaxis],M)
                temp.relabel(news=[L],olds=['_'+L])
            u,new,v=temp.svd([L,S],'_'+str(R),[R])
            labels.append((L,S,R))
            if i==0:
                Gammas.append(asarray(u))
            else:
                Gammas.append(asarray(u)/asarray(old)[:,newaxis])
            old=new
            if i<len(self.ms)-1:
                Lambdas.append(asarray(new))
        return VMPS(Gammas,Lambdas,labels)

    def to_mmps(self,cut):
        '''
        Convert to the MMPS representation.
        '''
        As,Lambda,Bs,labels=[],None,[],[]
        for i,M in enumerate(self.ms):
            L,S,R=M.labels[self.L],M.labels[self.S],M.labels[self.R]
            if i==0:
                temp=M
            else:
                temp=contract(v*asarray(s)[:,newaxis],M)
                temp.relabel(news=[L],olds=['_'+L])
            labels.append((L,S,R))
            if i<cut:
                u,s,v=temp.svd([L,S],'_'+str(R),[R])
                As.append(asarray(u))
            else:
                print temp.labels
                u,s,v=temp.svd([L],'_'+str(R),[S,R])
                if i==cut:Lambda=s
                Bs.append(asarray(v))
        return MMPS(As,Lambda,Bs,labels)

class VMPS(MPS):
    '''
    The Vidal canonical matrix product state.
    Attributes:
        Gammas: list of Tensor
            The Gamma matrices on the site.
        Lambdas: list of Tensor
            The Lambda matrices (singular values) on the link.
    '''

    def __init__(self,Gammas,Lambdas,labels):
        '''
        Constructor.
        Parameters:
            Gammas: list of 3d ndarray
                The Gamma matrices on the site.
            Lamdas: list of 1d ndarray
                The Lambda matrices (singular values) on the link.
            labels: list of 3 tuples
                The labels of the axis of the Gamma matrices.
                Its length should be equal to that of Gammas.
                For each label in labels, 
                    label[0]: any hashable object
                        The left link label of the matrix.
                    label[1]: any hashable object
                        The site label of the matrix.
                    label[2]: any hashable object
                        The right link label of the matrix.
        '''
        if len(Gammas)!=len(Lambdas)+1:
            raise ValueError('VMPS construction error: there should be one more Gamma matrices(%s) than the Lambda matrices(%s).'%(len(Gammas),len(Lambdas)))
        if len(Gammas)!=len(labels):
            raise ValueError('VMPS construction error: the number of Gamma matrices(%s) is not equal to that of the labels(%s).'%(len(Gammas),len(labels)))
        self.Gammas=[]
        self.Lambdas=[]
        temp,buff=[None]*3,[]
        for i,(Gamma,label) in enumerate(zip(Gammas,labels)):
            if Gamma.ndim!=3:
                raise ValueError('VMPS construction error: all Gamma matrices should be 3 dimensional.')
            L,S,R=label
            if i<len(Gammas)-1:
                buff.append(R)
            temp[self.L]=L
            temp[self.S]=S
            temp[self.R]=R
            self.Gammas.append(Tensor(Gamma,labels=deepcopy(temp)))
        for Lambda,label in zip(Lambdas,buff):
            if Lambda.ndim!=1:
                raise ValueError("VMPS construction error: all Lambda matrices should be 1 dimensional.")
            self.Lambdas.append(Tensor(Lambda,labels=[label]))

    def __str__(self):
        '''
        Convert an instance to string.
        '''
        result=[]
        for i,Gamma in enumerate(self.Gammas):
            result.append(str(Gamma))
            if i<len(self.Gammas)-1:
                result.append(str(self.Lambdas[i]))
        return '\n'.join(result)

    @property
    def state(self):
        '''
        Convert to the normal representation.
        '''
        result=None
        for i,Gamma in enumerate(self.Gammas):
            if result is None:
                result=Gamma
            else:
                result=contract(result,self.Lambdas[i-1],Gamma)
        return asarray(result).ravel()

    def to_mmps(self,cut):
        '''
        Convert to the MMPS representation.
        '''
        As,Lambda,Bs,labels=[],None,[],[]
        shape=[1]*3
        for i,Gamma in enumerate(self.Gammas):
            L,S,R=Gamma.labels[self.L],Gamma.labels[self.S],Gamma.labels[self.R]
            labels.append((L,S,R))
            if i<cut:
                if i==0:
                    As.append(Gamma)
                else:
                    shape[self.S]=len(self.Lambdas[i-1])
                    As.append(asarray(Gamma)*asarray(self.Lambdas[i-1]).reshape(shape))
            else:
                if i==cut:
                    Lambda=asarray(self.Lambdas[i-1])
                if i<len(self.Lambdas):
                    shape[self.S]=len(self.Lambdas[i])
                    Bs.append(asarray(Gamma)*asarray(self.Lambdas[i]).reshape(shape))
                else:
                    Bs.append(asarray(Gamma))
        return MMPS(As,Lambda,Bs,labels)

class MMPS(MPS):
    '''
    The mixed canonical matrix product state.
    Attributes:
        As,Bs: list of Tensor
            The A/B matrices.
        Lambda: Tensor
            The Lambda matrix (singular values) on the connecting link.
    Note the left-canonical MPS and right-canonical MPS are considered as special cases of this form.
    '''

    def __init__(self,As,Lambda,Bs,labels):
        '''
        Constructor.
        Parameters:
            As,Bs: list of 3d ndarray
                The A matrices and B matrices.
            Lambda: 1d ndarray
                The Lambda matrix on the connecting link.
            labels: list of 3 tuples
                The labels of the axis of the A/B matrices.
                Its length should be equal to the sum of that of As and Bs.
                For each label in labels, 
                    label[0]: any hashable object
                        The left link label of the matrix.
                    label[1]: any hashable object
                        The site label of the matrix.
                    label[2]: any hashable object
                        The right link label of the matrix.
        '''
        if len(As)+len(Bs)!=len(labels):
            raise ValueError('MMPS construction error: the total number of A/B matrices(%s) is not equal to that of the labels(%s).'%(len(As)+len(Bs),len(labels)))
        buff,temp=[],[None]*3
        for i,(M,label) in enumerate(zip(As+Bs,labels)):
            if M.ndim!=3:
                raise ValueError('MMPS construction error: all A/B matrices should be 3 dimensional.')
            L,S,R=label
            temp[self.L]=L
            temp[self.S]=S
            temp[self.R]=R
            buff.append(Tensor(M,labels=deepcopy(temp)))
        self.As=buff[:len(As)]
        self.Bs=buff[len(As):]
        print labels[len(As)][0]
        self.Lambda=None if Lambda is None else Tensor(Lambda,labels=[deepcopy(labels[len(As)][0])])

    def __str__(self):
        '''
        Convert an instance to string.
        '''
        result=[]
        for A in self.As:
            result.append(str(A))
        result.append(str(self.Lambda))
        for B in self.Bs:
            result.append(str(B))
        return '\n'.join(result)

    @property
    def state(self):
        '''
        Convert to the normal representation.
        '''
        result=None
        for A in self.As:
            if result is None:
                result=A
            else:
                result=contract(result,A)
        for i,B in enumerate(self.Bs):
            if result is None:
                result=B
            elif i==0:
                result=contract(result,self.Lambda,B)
            else:
                result=contract(result,B)
        return asarray(result).ravel()

    def to_vmps(self):
        '''
        Convert to the VMPS representation.
        '''
        pass

    def from_state(self,state):
        '''
        Convert a normal representation to the MMPS representation.
        '''
        pass
