# -*- coding: utf-8 -*-
"""
Domain adaptation with optimal transport
"""

# Author: Remi Flamary <remi.flamary@unice.fr>
#         Nicolas Courty <ncourty@irisa.fr>
#         Michael Perrot <michael.perrot@univ-st-etienne.fr>
#
# License: MIT License

import numpy as np
from .bregman import sinkhorn
from .lp import emd
from .utils import unif, dist, kernel
from .optim import cg
from .optim import gcg
import warnings


def sinkhorn_lpl1_mm(a, labels_a, b, M, reg, eta=0.1, numItermax=10,
                     numInnerItermax=200, stopInnerThr=1e-9, verbose=False,
                     log=False):
    """
    Solve the entropic regularization optimal transport problem with nonconvex
    group lasso regularization

    The function solves the following optimization problem:

    .. math::
        \gamma = arg\min_\gamma <\gamma,M>_F + reg\cdot\Omega_e(\gamma)
        + \eta \Omega_g(\gamma)

        s.t. \gamma 1 = a

             \gamma^T 1= b

             \gamma\geq 0
    where :

    - M is the (ns,nt) metric cost matrix
    - :math:`\Omega_e` is the entropic regularization term
        :math:`\Omega_e(\gamma)=\sum_{i,j} \gamma_{i,j}\log(\gamma_{i,j})`
    - :math:`\Omega_g` is the group lasso  regulaization term
      :math:`\Omega_g(\gamma)=\sum_{i,c} \|\gamma_{i,\mathcal{I}_c}\|^{1/2}_1`
      where  :math:`\mathcal{I}_c` are the index of samples from class c
      in the source domain.
    - a and b are source and target weights (sum to 1)

    The algorithm used for solving the problem is the generalised conditional
    gradient as proposed in  [5]_ [7]_


    Parameters
    ----------
    a : np.ndarray (ns,)
        samples weights in the source domain
    labels_a : np.ndarray (ns,)
        labels of samples in the source domain
    b : np.ndarray (nt,)
        samples weights in the target domain
    M : np.ndarray (ns,nt)
        loss matrix
    reg : float
        Regularization term for entropic regularization >0
    eta : float, optional
        Regularization term  for group lasso regularization >0
    numItermax : int, optional
        Max number of iterations
    numInnerItermax : int, optional
        Max number of iterations (inner sinkhorn solver)
    stopInnerThr : float, optional
        Stop threshold on error (inner sinkhorn solver) (>0)
    verbose : bool, optional
        Print information along iterations
    log : bool, optional
        record log if True


    Returns
    -------
    gamma : (ns x nt) ndarray
        Optimal transportation matrix for the given parameters
    log : dict
        log dictionary return only if log==True in parameters


    References
    ----------

    .. [5] N. Courty; R. Flamary; D. Tuia; A. Rakotomamonjy,
       "Optimal Transport for Domain Adaptation," in IEEE
       Transactions on Pattern Analysis and Machine Intelligence ,
       vol.PP, no.99, pp.1-1
    .. [7] Rakotomamonjy, A., Flamary, R., & Courty, N. (2015).
       Generalized conditional gradient: analysis of convergence
       and applications. arXiv preprint arXiv:1510.06567.

    See Also
    --------
    ot.lp.emd : Unregularized OT
    ot.bregman.sinkhorn : Entropic regularized OT
    ot.optim.cg : General regularized OT

    """
    p = 0.5
    epsilon = 1e-3

    indices_labels = []
    classes = np.unique(labels_a)
    for c in classes:
        idxc, = np.where(labels_a == c)
        indices_labels.append(idxc)

    W = np.zeros(M.shape)

    for cpt in range(numItermax):
        Mreg = M + eta * W
        transp = sinkhorn(a, b, Mreg, reg, numItermax=numInnerItermax,
                          stopThr=stopInnerThr)
        # the transport has been computed. Check if classes are really
        # separated
        W = np.ones(M.shape)
        for (i, c) in enumerate(classes):
            majs = np.sum(transp[indices_labels[i]], axis=0)
            majs = p * ((majs + epsilon)**(p - 1))
            W[indices_labels[i]] = majs

    return transp


def sinkhorn_l1l2_gl(a, labels_a, b, M, reg, eta=0.1, numItermax=10,
                     numInnerItermax=200, stopInnerThr=1e-9, verbose=False,
                     log=False):
    """
    Solve the entropic regularization optimal transport problem with group
    lasso regularization

    The function solves the following optimization problem:

    .. math::
        \gamma = arg\min_\gamma <\gamma,M>_F + reg\cdot\Omega_e(\gamma)+
        \eta \Omega_g(\gamma)

        s.t. \gamma 1 = a

             \gamma^T 1= b

             \gamma\geq 0
    where :

    - M is the (ns,nt) metric cost matrix
    - :math:`\Omega_e` is the entropic regularization term
      :math:`\Omega_e(\gamma)=\sum_{i,j} \gamma_{i,j}\log(\gamma_{i,j})`
    - :math:`\Omega_g` is the group lasso regulaization term
      :math:`\Omega_g(\gamma)=\sum_{i,c} \|\gamma_{i,\mathcal{I}_c}\|^2`
      where  :math:`\mathcal{I}_c` are the index of samples from class
      c in the source domain.
    - a and b are source and target weights (sum to 1)

    The algorithm used for solving the problem is the generalised conditional
    gradient as proposed in  [5]_ [7]_


    Parameters
    ----------
    a : np.ndarray (ns,)
        samples weights in the source domain
    labels_a : np.ndarray (ns,)
        labels of samples in the source domain
    b : np.ndarray (nt,)
        samples in the target domain
    M : np.ndarray (ns,nt)
        loss matrix
    reg : float
        Regularization term for entropic regularization >0
    eta : float, optional
        Regularization term  for group lasso regularization >0
    numItermax : int, optional
        Max number of iterations
    numInnerItermax : int, optional
        Max number of iterations (inner sinkhorn solver)
    stopInnerThr : float, optional
        Stop threshold on error (inner sinkhorn solver) (>0)
    verbose : bool, optional
        Print information along iterations
    log : bool, optional
        record log if True


    Returns
    -------
    gamma : (ns x nt) ndarray
        Optimal transportation matrix for the given parameters
    log : dict
        log dictionary return only if log==True in parameters


    References
    ----------

    .. [5] N. Courty; R. Flamary; D. Tuia; A. Rakotomamonjy,
       "Optimal Transport for Domain Adaptation," in IEEE Transactions
       on Pattern Analysis and Machine Intelligence , vol.PP, no.99, pp.1-1
    .. [7] Rakotomamonjy, A., Flamary, R., & Courty, N. (2015).
       Generalized conditional gradient: analysis of convergence and
       applications. arXiv preprint arXiv:1510.06567.

    See Also
    --------
    ot.optim.gcg : Generalized conditional gradient for OT problems

    """
    lstlab = np.unique(labels_a)

    def f(G):
        res = 0
        for i in range(G.shape[1]):
            for lab in lstlab:
                temp = G[labels_a == lab, i]
                res += np.linalg.norm(temp)
        return res

    def df(G):
        W = np.zeros(G.shape)
        for i in range(G.shape[1]):
            for lab in lstlab:
                temp = G[labels_a == lab, i]
                n = np.linalg.norm(temp)
                if n:
                    W[labels_a == lab, i] = temp / n
        return W

    return gcg(a, b, M, reg, eta, f, df, G0=None, numItermax=numItermax,
               numInnerItermax=numInnerItermax, stopThr=stopInnerThr,
               verbose=verbose, log=log)


def joint_OT_mapping_linear(xs, xt, mu=1, eta=0.001, bias=False, verbose=False,
                            verbose2=False, numItermax=100, numInnerItermax=10,
                            stopInnerThr=1e-6, stopThr=1e-5, log=False,
                            **kwargs):
    """Joint OT and linear mapping estimation as proposed in [8]

    The function solves the following optimization problem:

    .. math::
        \min_{\gamma,L}\quad \|L(X_s) -n_s\gamma X_t\|^2_F +
          \mu<\gamma,M>_F + \eta  \|L -I\|^2_F

        s.t. \gamma 1 = a

             \gamma^T 1= b

             \gamma\geq 0
    where :

    - M is the (ns,nt) squared euclidean cost matrix between samples in
       Xs and Xt (scaled by ns)
    - :math:`L` is a dxd linear operator that approximates the barycentric
      mapping
    - :math:`I` is the identity matrix (neutral linear mapping)
    - a and b are uniform source and target weights

    The problem consist in solving jointly an optimal transport matrix
    :math:`\gamma` and a linear mapping that fits the barycentric mapping
    :math:`n_s\gamma X_t`.

    One can also estimate a mapping with constant bias (see supplementary
    material of [8]) using the bias optional argument.

    The algorithm used for solving the problem is the block coordinate
    descent that alternates between updates of G (using conditionnal gradient)
    and the update of L using a classical least square solver.


    Parameters
    ----------
    xs : np.ndarray (ns,d)
        samples in the source domain
    xt : np.ndarray (nt,d)
        samples in the target domain
    mu : float,optional
        Weight for the linear OT loss (>0)
    eta : float, optional
        Regularization term  for the linear mapping L (>0)
    bias : bool,optional
        Estimate linear mapping with constant bias
    numItermax : int, optional
        Max number of BCD iterations
    stopThr : float, optional
        Stop threshold on relative loss decrease (>0)
    numInnerItermax : int, optional
        Max number of iterations (inner CG solver)
    stopInnerThr : float, optional
        Stop threshold on error (inner CG solver) (>0)
    verbose : bool, optional
        Print information along iterations
    log : bool, optional
        record log if True


    Returns
    -------
    gamma : (ns x nt) ndarray
        Optimal transportation matrix for the given parameters
    L : (d x d) ndarray
        Linear mapping matrix (d+1 x d if bias)
    log : dict
        log dictionary return only if log==True in parameters


    References
    ----------

    .. [8] M. Perrot, N. Courty, R. Flamary, A. Habrard,
        "Mapping estimation for discrete optimal transport",
        Neural Information Processing Systems (NIPS), 2016.

    See Also
    --------
    ot.lp.emd : Unregularized OT
    ot.optim.cg : General regularized OT

    """

    ns, nt, d = xs.shape[0], xt.shape[0], xt.shape[1]

    if bias:
        xs1 = np.hstack((xs, np.ones((ns, 1))))
        xstxs = xs1.T.dot(xs1)
        I = np.eye(d + 1)
        I[-1] = 0
        I0 = I[:, :-1]

        def sel(x):
            return x[:-1, :]
    else:
        xs1 = xs
        xstxs = xs1.T.dot(xs1)
        I = np.eye(d)
        I0 = I

        def sel(x):
            return x

    if log:
        log = {'err': []}

    a, b = unif(ns), unif(nt)
    M = dist(xs, xt) * ns
    G = emd(a, b, M)

    vloss = []

    def loss(L, G):
        """Compute full loss"""
        return np.sum((xs1.dot(L) - ns * G.dot(xt))**2) + mu * np.sum(G * M) + eta * np.sum(sel(L - I0)**2)

    def solve_L(G):
        """ solve L problem with fixed G (least square)"""
        xst = ns * G.dot(xt)
        return np.linalg.solve(xstxs + eta * I, xs1.T.dot(xst) + eta * I0)

    def solve_G(L, G0):
        """Update G with CG algorithm"""
        xsi = xs1.dot(L)

        def f(G):
            return np.sum((xsi - ns * G.dot(xt))**2)

        def df(G):
            return -2 * ns * (xsi - ns * G.dot(xt)).dot(xt.T)
        G = cg(a, b, M, 1.0 / mu, f, df, G0=G0,
               numItermax=numInnerItermax, stopThr=stopInnerThr)
        return G

    L = solve_L(G)

    vloss.append(loss(L, G))

    if verbose:
        print('{:5s}|{:12s}|{:8s}'.format(
            'It.', 'Loss', 'Delta loss') + '\n' + '-' * 32)
        print('{:5d}|{:8e}|{:8e}'.format(0, vloss[-1], 0))

    # init loop
    if numItermax > 0:
        loop = 1
    else:
        loop = 0
    it = 0

    while loop:

        it += 1

        # update G
        G = solve_G(L, G)

        # update L
        L = solve_L(G)

        vloss.append(loss(L, G))

        if it >= numItermax:
            loop = 0

        if abs(vloss[-1] - vloss[-2]) / abs(vloss[-2]) < stopThr:
            loop = 0

        if verbose:
            if it % 20 == 0:
                print('{:5s}|{:12s}|{:8s}'.format(
                    'It.', 'Loss', 'Delta loss') + '\n' + '-' * 32)
            print('{:5d}|{:8e}|{:8e}'.format(
                it, vloss[-1], (vloss[-1] - vloss[-2]) / abs(vloss[-2])))
    if log:
        log['loss'] = vloss
        return G, L, log
    else:
        return G, L


def joint_OT_mapping_kernel(xs, xt, mu=1, eta=0.001, kerneltype='gaussian',
                            sigma=1, bias=False, verbose=False, verbose2=False,
                            numItermax=100, numInnerItermax=10,
                            stopInnerThr=1e-6, stopThr=1e-5, log=False,
                            **kwargs):
    """Joint OT and nonlinear mapping estimation with kernels as proposed in [8]

    The function solves the following optimization problem:

    .. math::
        \min_{\gamma,L\in\mathcal{H}}\quad \|L(X_s) -
        n_s\gamma X_t\|^2_F + \mu<\gamma,M>_F + \eta  \|L\|^2_\mathcal{H}

        s.t. \gamma 1 = a

             \gamma^T 1= b

             \gamma\geq 0
    where :

    - M is the (ns,nt) squared euclidean cost matrix between samples in
      Xs and Xt (scaled by ns)
    - :math:`L` is a ns x d linear operator on a kernel matrix that
      approximates the barycentric mapping
    - a and b are uniform source and target weights

    The problem consist in solving jointly an optimal transport matrix
    :math:`\gamma` and the nonlinear mapping that fits the barycentric mapping
    :math:`n_s\gamma X_t`.

    One can also estimate a mapping with constant bias (see supplementary
    material of [8]) using the bias optional argument.

    The algorithm used for solving the problem is the block coordinate
    descent that alternates between updates of G (using conditionnal gradient)
    and the update of L using a classical kernel least square solver.


    Parameters
    ----------
    xs : np.ndarray (ns,d)
        samples in the source domain
    xt : np.ndarray (nt,d)
        samples in the target domain
    mu : float,optional
        Weight for the linear OT loss (>0)
    eta : float, optional
        Regularization term  for the linear mapping L (>0)
    bias : bool,optional
        Estimate linear mapping with constant bias
    kerneltype : str,optional
        kernel used by calling function ot.utils.kernel (gaussian by default)
    sigma : float, optional
        Gaussian kernel bandwidth.
    numItermax : int, optional
        Max number of BCD iterations
    stopThr : float, optional
        Stop threshold on relative loss decrease (>0)
    numInnerItermax : int, optional
        Max number of iterations (inner CG solver)
    stopInnerThr : float, optional
        Stop threshold on error (inner CG solver) (>0)
    verbose : bool, optional
        Print information along iterations
    log : bool, optional
        record log if True


    Returns
    -------
    gamma : (ns x nt) ndarray
        Optimal transportation matrix for the given parameters
    L : (ns x d) ndarray
        Nonlinear mapping matrix (ns+1 x d if bias)
    log : dict
        log dictionary return only if log==True in parameters


    References
    ----------

    .. [8] M. Perrot, N. Courty, R. Flamary, A. Habrard,
       "Mapping estimation for discrete optimal transport",
       Neural Information Processing Systems (NIPS), 2016.

    See Also
    --------
    ot.lp.emd : Unregularized OT
    ot.optim.cg : General regularized OT

    """

    ns, nt = xs.shape[0], xt.shape[0]

    K = kernel(xs, xs, method=kerneltype, sigma=sigma)
    if bias:
        K1 = np.hstack((K, np.ones((ns, 1))))
        I = np.eye(ns + 1)
        I[-1] = 0
        Kp = np.eye(ns + 1)
        Kp[:ns, :ns] = K

        # ls regu
        # K0 = K1.T.dot(K1)+eta*I
        # Kreg=I

        # RKHS regul
        K0 = K1.T.dot(K1) + eta * Kp
        Kreg = Kp

    else:
        K1 = K
        I = np.eye(ns)

        # ls regul
        # K0 = K1.T.dot(K1)+eta*I
        # Kreg=I

        # proper kernel ridge
        K0 = K + eta * I
        Kreg = K

    if log:
        log = {'err': []}

    a, b = unif(ns), unif(nt)
    M = dist(xs, xt) * ns
    G = emd(a, b, M)

    vloss = []

    def loss(L, G):
        """Compute full loss"""
        return np.sum((K1.dot(L) - ns * G.dot(xt))**2) + mu * np.sum(G * M) + eta * np.trace(L.T.dot(Kreg).dot(L))

    def solve_L_nobias(G):
        """ solve L problem with fixed G (least square)"""
        xst = ns * G.dot(xt)
        return np.linalg.solve(K0, xst)

    def solve_L_bias(G):
        """ solve L problem with fixed G (least square)"""
        xst = ns * G.dot(xt)
        return np.linalg.solve(K0, K1.T.dot(xst))

    def solve_G(L, G0):
        """Update G with CG algorithm"""
        xsi = K1.dot(L)

        def f(G):
            return np.sum((xsi - ns * G.dot(xt))**2)

        def df(G):
            return -2 * ns * (xsi - ns * G.dot(xt)).dot(xt.T)
        G = cg(a, b, M, 1.0 / mu, f, df, G0=G0,
               numItermax=numInnerItermax, stopThr=stopInnerThr)
        return G

    if bias:
        solve_L = solve_L_bias
    else:
        solve_L = solve_L_nobias

    L = solve_L(G)

    vloss.append(loss(L, G))

    if verbose:
        print('{:5s}|{:12s}|{:8s}'.format(
            'It.', 'Loss', 'Delta loss') + '\n' + '-' * 32)
        print('{:5d}|{:8e}|{:8e}'.format(0, vloss[-1], 0))

    # init loop
    if numItermax > 0:
        loop = 1
    else:
        loop = 0
    it = 0

    while loop:

        it += 1

        # update G
        G = solve_G(L, G)

        # update L
        L = solve_L(G)

        vloss.append(loss(L, G))

        if it >= numItermax:
            loop = 0

        if abs(vloss[-1] - vloss[-2]) / abs(vloss[-2]) < stopThr:
            loop = 0

        if verbose:
            if it % 20 == 0:
                print('{:5s}|{:12s}|{:8s}'.format(
                    'It.', 'Loss', 'Delta loss') + '\n' + '-' * 32)
            print('{:5d}|{:8e}|{:8e}'.format(
                it, vloss[-1], (vloss[-1] - vloss[-2]) / abs(vloss[-2])))
    if log:
        log['loss'] = vloss
        return G, L, log
    else:
        return G, L


class OTDA(object):

    """Class for domain adaptation with optimal transport as proposed in [5]


    References
    ----------

    .. [5] N. Courty; R. Flamary; D. Tuia; A. Rakotomamonjy,
       "Optimal Transport for Domain Adaptation," in IEEE Transactions on
       Pattern Analysis and Machine Intelligence , vol.PP, no.99, pp.1-1

    """

    def __init__(self, metric='sqeuclidean'):
        """ Class initialization"""
        self.xs = 0
        self.xt = 0
        self.G = 0
        self.metric = metric
        self.computed = False

    def fit(self, xs, xt, ws=None, wt=None, norm=None):
        """Fit domain adaptation between samples is xs and xt
        (with optional weights)"""
        self.xs = xs
        self.xt = xt

        if wt is None:
            wt = unif(xt.shape[0])
        if ws is None:
            ws = unif(xs.shape[0])

        self.ws = ws
        self.wt = wt

        self.M = dist(xs, xt, metric=self.metric)
        self.normalizeM(norm)
        self.G = emd(ws, wt, self.M)
        self.computed = True

    def interp(self, direction=1):
        """Barycentric interpolation for the source (1) or target (-1) samples

        This Barycentric interpolation solves for each source (resp target)
        sample xs (resp xt) the following optimization problem:

        .. math::
            arg\min_x \sum_i \gamma_{k,i} c(x,x_i^t)

        where k is the index of the sample in xs

        For the moment only squared euclidean distance is provided but more
        metric  could be used in the future.

        """
        if direction > 0:  # >0 then source to target
            G = self.G
            w = self.ws.reshape((self.xs.shape[0], 1))
            x = self.xt
        else:
            G = self.G.T
            w = self.wt.reshape((self.xt.shape[0], 1))
            x = self.xs

        if self.computed:
            if self.metric == 'sqeuclidean':
                return np.dot(G / w, x)  # weighted mean
            else:
                print(
                    "Warning, metric not handled yet, using weighted average")
                return np.dot(G / w, x)  # weighted mean
                return None
        else:
            print("Warning, model not fitted yet, returning None")
            return None

    def predict(self, x, direction=1):
        """ Out of sample mapping using the formulation from [6]

        For each sample x to map, it finds the nearest source sample xs and
        map the samle x to the position xst+(x-xs) wher xst is the barycentric
        interpolation of source sample xs.

        References
        ----------

        .. [6] Ferradans, S., Papadakis, N., Peyré, G., & Aujol, J. F. (2014).
          Regularized discrete optimal transport. SIAM Journal on Imaging
          Sciences, 7(3), 1853-1882.

        """
        if direction > 0:  # >0 then source to target
            xf = self.xt
            x0 = self.xs
        else:
            xf = self.xs
            x0 = self.xt

        D0 = dist(x, x0)  # dist netween new samples an source
        idx = np.argmin(D0, 1)  # closest one
        xf = self.interp(direction)  # interp the source samples
        # aply the delta to the interpolation
        return xf[idx, :] + x - x0[idx, :]

    def normalizeM(self, norm):
        """ Apply normalization to the loss matrix


        Parameters
        ----------
        norm : str
            type of normalization from 'median','max','log','loglog'

        """

        if norm == "median":
            self.M /= float(np.median(self.M))
        elif norm == "max":
            self.M /= float(np.max(self.M))
        elif norm == "log":
            self.M = np.log(1 + self.M)
        elif norm == "loglog":
            self.M = np.log(1 + np.log(1 + self.M))


class OTDA_sinkhorn(OTDA):

    """Class for domain adaptation with optimal transport with entropic
    regularization"""

    def fit(self, xs, xt, reg=1, ws=None, wt=None, norm=None, **kwargs):
        """Fit regularized domain adaptation between samples is xs and xt
        (with optional weights)"""
        self.xs = xs
        self.xt = xt

        if wt is None:
            wt = unif(xt.shape[0])
        if ws is None:
            ws = unif(xs.shape[0])

        self.ws = ws
        self.wt = wt

        self.M = dist(xs, xt, metric=self.metric)
        self.normalizeM(norm)
        self.G = sinkhorn(ws, wt, self.M, reg, **kwargs)
        self.computed = True


class OTDA_lpl1(OTDA):

    """Class for domain adaptation with optimal transport with entropic and
    group regularization"""

    def fit(self, xs, ys, xt, reg=1, eta=1, ws=None, wt=None, norm=None,
            **kwargs):
        """Fit regularized domain adaptation between samples is xs and xt
        (with optional weights),  See ot.da.sinkhorn_lpl1_mm for fit
        parameters"""
        self.xs = xs
        self.xt = xt

        if wt is None:
            wt = unif(xt.shape[0])
        if ws is None:
            ws = unif(xs.shape[0])

        self.ws = ws
        self.wt = wt

        self.M = dist(xs, xt, metric=self.metric)
        self.normalizeM(norm)
        self.G = sinkhorn_lpl1_mm(ws, ys, wt, self.M, reg, eta, **kwargs)
        self.computed = True


class OTDA_l1l2(OTDA):

    """Class for domain adaptation with optimal transport with entropic
    and group lasso regularization"""

    def fit(self, xs, ys, xt, reg=1, eta=1, ws=None, wt=None, norm=None,
            **kwargs):
        """Fit regularized domain adaptation between samples is xs and xt
           (with optional weights),  See ot.da.sinkhorn_lpl1_gl for fit
           parameters"""
        self.xs = xs
        self.xt = xt

        if wt is None:
            wt = unif(xt.shape[0])
        if ws is None:
            ws = unif(xs.shape[0])

        self.ws = ws
        self.wt = wt

        self.M = dist(xs, xt, metric=self.metric)
        self.normalizeM(norm)
        self.G = sinkhorn_l1l2_gl(ws, ys, wt, self.M, reg, eta, **kwargs)
        self.computed = True


class OTDA_mapping_linear(OTDA):

    """Class for optimal transport with joint linear mapping estimation as in
    [8]
    """

    def __init__(self):
        """ Class initialization"""

        self.xs = 0
        self.xt = 0
        self.G = 0
        self.L = 0
        self.bias = False
        self.computed = False
        self.metric = 'sqeuclidean'

    def fit(self, xs, xt, mu=1, eta=1, bias=False, **kwargs):
        """ Fit domain adaptation between samples is xs and xt (with optional
            weights)"""
        self.xs = xs
        self.xt = xt
        self.bias = bias

        self.ws = unif(xs.shape[0])
        self.wt = unif(xt.shape[0])

        self.G, self.L = joint_OT_mapping_linear(
            xs, xt, mu=mu, eta=eta, bias=bias, **kwargs)
        self.computed = True

    def mapping(self):
        return lambda x: self.predict(x)

    def predict(self, x):
        """ Out of sample mapping estimated during the call to fit"""
        if self.computed:
            if self.bias:
                x = np.hstack((x, np.ones((x.shape[0], 1))))
            return x.dot(self.L)  # aply the delta to the interpolation
        else:
            print("Warning, model not fitted yet, returning None")
            return None


class OTDA_mapping_kernel(OTDA_mapping_linear):

    """Class for optimal transport with joint nonlinear mapping
    estimation as in [8]"""

    def fit(self, xs, xt, mu=1, eta=1, bias=False, kerneltype='gaussian',
            sigma=1, **kwargs):
        """ Fit domain adaptation between samples is xs and xt """
        self.xs = xs
        self.xt = xt
        self.bias = bias

        self.ws = unif(xs.shape[0])
        self.wt = unif(xt.shape[0])
        self.kernel = kerneltype
        self.sigma = sigma
        self.kwargs = kwargs

        self.G, self.L = joint_OT_mapping_kernel(
            xs, xt, mu=mu, eta=eta, bias=bias, **kwargs)
        self.computed = True

    def predict(self, x):
        """ Out of sample mapping estimated during the call to fit"""

        if self.computed:
            K = kernel(
                x, self.xs, method=self.kernel, sigma=self.sigma,
                **self.kwargs)
            if self.bias:
                K = np.hstack((K, np.ones((x.shape[0], 1))))
            return K.dot(self.L)
        else:
            print("Warning, model not fitted yet, returning None")
            return None

##############################################################################
# proposal
##############################################################################


# adapted from sklearn

class BaseEstimator(object):
    """Base class for all estimators in scikit-learn
    Notes
    -----
    All estimators should specify all the parameters that can be set
    at the class level in their ``__init__`` as explicit keyword
    arguments (no ``*args`` or ``**kwargs``).
    """

    @classmethod
    def _get_param_names(cls):
        """Get parameter names for the estimator"""
        try:
            from inspect import signature
        except ImportError:
            from .externals.funcsigs import signature
        # fetch the constructor or the original constructor before
        # deprecation wrapping if any
        init = getattr(cls.__init__, 'deprecated_original', cls.__init__)
        if init is object.__init__:
            # No explicit constructor to introspect
            return []

        # introspect the constructor arguments to find the model parameters
        # to represent
        init_signature = signature(init)
        # Consider the constructor parameters excluding 'self'
        parameters = [p for p in init_signature.parameters.values()
                      if p.name != 'self' and p.kind != p.VAR_KEYWORD]
        for p in parameters:
            if p.kind == p.VAR_POSITIONAL:
                raise RuntimeError("scikit-learn estimators should always "
                                   "specify their parameters in the signature"
                                   " of their __init__ (no varargs)."
                                   " %s with constructor %s doesn't "
                                   " follow this convention."
                                   % (cls, init_signature))
        # Extract and sort argument names excluding 'self'
        return sorted([p.name for p in parameters])

    def get_params(self, deep=True):
        """Get parameters for this estimator.
        Parameters
        ----------
        deep : boolean, optional
            If True, will return the parameters for this estimator and
            contained subobjects that are estimators.
        Returns
        -------
        params : mapping of string to any
            Parameter names mapped to their values.
        """
        out = dict()
        for key in self._get_param_names():
            # We need deprecation warnings to always be on in order to
            # catch deprecated param values.
            # This is set in utils/__init__.py but it gets overwritten
            # when running under python3 somehow.
            warnings.simplefilter("always", DeprecationWarning)
            try:
                with warnings.catch_warnings(record=True) as w:
                    value = getattr(self, key, None)
                if len(w) and w[0].category == DeprecationWarning:
                    # if the parameter is deprecated, don't show it
                    continue
            finally:
                warnings.filters.pop(0)

            # XXX: should we rather test if instance of estimator?
            if deep and hasattr(value, 'get_params'):
                deep_items = value.get_params().items()
                out.update((key + '__' + k, val) for k, val in deep_items)
            out[key] = value
        return out

    def set_params(self, **params):
        """Set the parameters of this estimator.
        The method works on simple estimators as well as on nested objects
        (such as pipelines). The latter have parameters of the form
        ``<component>__<parameter>`` so that it's possible to update each
        component of a nested object.
        Returns
        -------
        self
        """
        if not params:
            # Simple optimisation to gain speed (inspect is slow)
            return self
        valid_params = self.get_params(deep=True)
        # for key, value in iteritems(params):
        for key, value in params.items():
            split = key.split('__', 1)
            if len(split) > 1:
                # nested objects case
                name, sub_name = split
                if name not in valid_params:
                    raise ValueError('Invalid parameter %s for estimator %s. '
                                     'Check the list of available parameters '
                                     'with `estimator.get_params().keys()`.' %
                                     (name, self))
                sub_object = valid_params[name]
                sub_object.set_params(**{sub_name: value})
            else:
                # simple objects case
                if key not in valid_params:
                    raise ValueError('Invalid parameter %s for estimator %s. '
                                     'Check the list of available parameters '
                                     'with `estimator.get_params().keys()`.' %
                                     (key, self.__class__.__name__))
                setattr(self, key, value)
        return self

    def __repr__(self):
        from sklearn.base import _pprint
        class_name = self.__class__.__name__
        return '%s(%s)' % (class_name, _pprint(self.get_params(deep=False),
                                               offset=len(class_name),),)

    # __getstate__ and __setstate__ are omitted because they only contain
    # conditionals that are not satisfied by our objects (e.g.,
    # ``if type(self).__module__.startswith('sklearn.')``.


def distribution_estimation_uniform(X):
    """estimates a uniform distribution from an array of samples X

    Parameters
    ----------
    X : array-like of shape = [n_samples, n_features]
        The array of samples
    Returns
    -------
    mu : array-like, shape = [n_samples,]
        The uniform distribution estimated from X
    """

    return unif(X.shape[0])


class BaseTransport(BaseEstimator):

    def fit(self, Xs=None, ys=None, Xt=None, yt=None):
        """Build a coupling matrix from source and target sets of samples
        (Xs, ys) and (Xt, yt)
        Parameters
        ----------
        Xs : array-like of shape = [n_source_samples, n_features]
            The training input samples.
        ys : array-like, shape = [n_source_samples]
            The class labels
        Xt : array-like of shape = [n_target_samples, n_features]
            The training input samples.
        yt : array-like, shape = [n_labeled_target_samples]
            The class labels
        Returns
        -------
        self : object
            Returns self.
        """

        # pairwise distance
        self.Cost = dist(Xs, Xt, metric=self.metric)

        if (ys is not None) and (yt is not None):

            if self.limit_max != np.infty:
                self.limit_max = self.limit_max * np.max(self.Cost)

            # assumes labeled source samples occupy the first rows
            # and labeled target samples occupy the first columns
            classes = np.unique(ys)
            for c in classes:
                idx_s = np.where((ys != c) & (ys != -1))
                idx_t = np.where(yt == c)

                # all the coefficients corresponding to a source sample
                # and a target sample :
                # with different labels get a infinite
                for j in idx_t[0]:
                    self.Cost[idx_s[0], j] = self.limit_max

        # distribution estimation
        self.mu_s = self.distribution_estimation(Xs)
        self.mu_t = self.distribution_estimation(Xt)

        # store arrays of samples
        self.Xs = Xs
        self.Xt = Xt

        return self

    def fit_transform(self, Xs=None, ys=None, Xt=None, yt=None):
        """Build a coupling matrix from source and target sets of samples
        (Xs, ys) and (Xt, yt) and transports source samples Xs onto target
        ones Xt
        Parameters
        ----------
        Xs : array-like of shape = [n_source_samples, n_features]
            The training input samples.
        ys : array-like, shape = [n_source_samples]
            The class labels
        Xt : array-like of shape = [n_target_samples, n_features]
            The training input samples.
        yt : array-like, shape = [n_labeled_target_samples]
            The class labels
        Returns
        -------
        transp_Xs : array-like of shape = [n_source_samples, n_features]
            The source samples samples.
        """

        return self.fit(Xs, ys, Xt, yt).transform(Xs, ys, Xt, yt)

    def transform(self, Xs=None, ys=None, Xt=None, yt=None):
        """Transports source samples Xs onto target ones Xt
        Parameters
        ----------
        Xs : array-like of shape = [n_source_samples, n_features]
            The training input samples.
        ys : array-like, shape = [n_source_samples]
            The class labels
        Xt : array-like of shape = [n_target_samples, n_features]
            The training input samples.
        yt : array-like, shape = [n_labeled_target_samples]
            The class labels
        Returns
        -------
        transp_Xs : array-like of shape = [n_source_samples, n_features]
            The transport source samples.
        """

        if np.array_equal(self.Xs, Xs):
            # perform standard barycentric mapping
            transp = self.Coupling_ / np.sum(self.Coupling_, 1)[:, None]

            # set nans to 0
            transp[~ np.isfinite(transp)] = 0

            # compute transported samples
            transp_Xs = np.dot(transp, self.Xt)
        else:
            # perform out of sample mapping
            print("Warning: out of sample mapping not yet implemented")
            print("input data will be returned")
            transp_Xs = Xs

        return transp_Xs

    def inverse_transform(self, Xs=None, ys=None, Xt=None, yt=None):
        """Transports target samples Xt onto target samples Xs
        Parameters
        ----------
        Xs : array-like of shape = [n_source_samples, n_features]
            The training input samples.
        ys : array-like, shape = [n_source_samples]
            The class labels
        Xt : array-like of shape = [n_target_samples, n_features]
            The training input samples.
        yt : array-like, shape = [n_labeled_target_samples]
            The class labels
        Returns
        -------
        transp_Xt : array-like of shape = [n_source_samples, n_features]
            The transported target samples.
        """

        if np.array_equal(self.Xt, Xt):
            # perform standard barycentric mapping
            transp_ = self.Coupling_.T / np.sum(self.Coupling_, 0)[:, None]

            # set nans to 0
            transp_[~ np.isfinite(transp_)] = 0

            # compute transported samples
            transp_Xt = np.dot(transp_, self.Xs)
        else:
            # perform out of sample mapping
            print("Warning: out of sample mapping not yet implemented")
            print("input data will be returned")
            transp_Xt = Xt

        return transp_Xt


class SinkhornTransport(BaseTransport):
    """Domain Adapatation OT method based on Sinkhorn Algorithm

    Parameters
    ----------
    reg_e : float, optional (default=1)
        Entropic regularization parameter
    mode : string, optional (default="unsupervised")
        The DA mode. If "unsupervised" no target labels are taken into account
        to modify the cost matrix. If "semisupervised" the target labels
        are taken into account to set coefficients of the pairwise distance
        matrix to 0 for row and columns indices that correspond to source and
        target samples which share the same labels.
    max_iter : int, float, optional (default=1000)
        The minimum number of iteration before stopping the optimization
        algorithm if no it has not converged
    tol : float, optional (default=10e-9)
        The precision required to stop the optimization algorithm.
    mapping : string, optional (default="barycentric")
        The kind of mapping to apply to transport samples from a domain into
        another one.
        if "barycentric" only the samples used to estimate the coupling can
        be transported from a domain to another one.
    metric : string, optional (default="sqeuclidean")
        The ground metric for the Wasserstein problem
    distribution : string, optional (default="uniform")
        The kind of distribution estimation to employ
    verbose : int, optional (default=0)
        Controls the verbosity of the optimization algorithm
    log : int, optional (default=0)
        Controls the logs of the optimization algorithm
    limit_max: float, optional (defaul=np.infty)
        Controls the semi supervised mode. Transport between labeled source
        and target samples of different classes will exhibit an infinite cost
    Attributes
    ----------
    Coupling_ : the optimal coupling

    References
    ----------
    .. [1] N. Courty; R. Flamary; D. Tuia; A. Rakotomamonjy,
           "Optimal Transport for Domain Adaptation," in IEEE Transactions
           on Pattern Analysis and Machine Intelligence , vol.PP, no.99, pp.1-1
    .. [2] M. Cuturi, Sinkhorn Distances : Lightspeed Computation of Optimal
           Transport, Advances in Neural Information Processing Systems (NIPS)
           26, 2013
    """

    def __init__(self, reg_e=1., max_iter=1000,
                 tol=10e-9, verbose=False, log=False,
                 metric="sqeuclidean",
                 distribution_estimation=distribution_estimation_uniform,
                 out_of_sample_map='ferradans', limit_max=np.infty):

        self.reg_e = reg_e
        self.max_iter = max_iter
        self.tol = tol
        self.verbose = verbose
        self.log = log
        self.metric = metric
        self.limit_max = limit_max
        self.distribution_estimation = distribution_estimation
        self.out_of_sample_map = out_of_sample_map

    def fit(self, Xs=None, ys=None, Xt=None, yt=None):
        """Build a coupling matrix from source and target sets of samples
        (Xs, ys) and (Xt, yt)
        Parameters
        ----------
        Xs : array-like of shape = [n_source_samples, n_features]
            The training input samples.
        ys : array-like, shape = [n_source_samples]
            The class labels
        Xt : array-like of shape = [n_target_samples, n_features]
            The training input samples.
        yt : array-like, shape = [n_labeled_target_samples]
            The class labels
        Returns
        -------
        self : object
            Returns self.
        """

        super(SinkhornTransport, self).fit(Xs, ys, Xt, yt)

        # coupling estimation
        self.Coupling_ = sinkhorn(
            a=self.mu_s, b=self.mu_t, M=self.Cost, reg=self.reg_e,
            numItermax=self.max_iter, stopThr=self.tol,
            verbose=self.verbose, log=self.log)

        return self


class EMDTransport(BaseTransport):
    """Domain Adapatation OT method based on Earth Mover's Distance
    Parameters
    ----------
    mode : string, optional (default="unsupervised")
        The DA mode. If "unsupervised" no target labels are taken into account
        to modify the cost matrix. If "semisupervised" the target labels
        are taken into account to set coefficients of the pairwise distance
        matrix to 0 for row and columns indices that correspond to source and
        target samples which share the same labels.
    mapping : string, optional (default="barycentric")
        The kind of mapping to apply to transport samples from a domain into
        another one.
        if "barycentric" only the samples used to estimate the coupling can
        be transported from a domain to another one.
    metric : string, optional (default="sqeuclidean")
        The ground metric for the Wasserstein problem
    distribution : string, optional (default="uniform")
        The kind of distribution estimation to employ
    verbose : int, optional (default=0)
        Controls the verbosity of the optimization algorithm
    log : int, optional (default=0)
        Controls the logs of the optimization algorithm
    limit_max: float, optional (default=10)
        Controls the semi supervised mode. Transport between labeled source
        and target samples of different classes will exhibit an infinite cost
        (10 times the maximum value of the cost matrix)
    Attributes
    ----------
    Coupling_ : the optimal coupling

    References
    ----------
    .. [1] N. Courty; R. Flamary; D. Tuia; A. Rakotomamonjy,
           "Optimal Transport for Domain Adaptation," in IEEE Transactions
           on Pattern Analysis and Machine Intelligence , vol.PP, no.99, pp.1-1
    """

    def __init__(self, verbose=False,
                 log=False, metric="sqeuclidean",
                 distribution_estimation=distribution_estimation_uniform,
                 out_of_sample_map='ferradans', limit_max=10):

        self.verbose = verbose
        self.log = log
        self.metric = metric
        self.limit_max = limit_max
        self.distribution_estimation = distribution_estimation
        self.out_of_sample_map = out_of_sample_map

    def fit(self, Xs, ys=None, Xt=None, yt=None):
        """Build a coupling matrix from source and target sets of samples
        (Xs, ys) and (Xt, yt)
        Parameters
        ----------
        Xs : array-like of shape = [n_source_samples, n_features]
            The training input samples.
        ys : array-like, shape = [n_source_samples]
            The class labels
        Xt : array-like of shape = [n_target_samples, n_features]
            The training input samples.
        yt : array-like, shape = [n_labeled_target_samples]
            The class labels
        Returns
        -------
        self : object
            Returns self.
        """

        super(EMDTransport, self).fit(Xs, ys, Xt, yt)

        # coupling estimation
        self.Coupling_ = emd(
            a=self.mu_s, b=self.mu_t, M=self.Cost,
            # verbose=self.verbose,
            # log=self.log
        )

        return self


class SinkhornLpl1Transport(BaseTransport):
    """Domain Adapatation OT method based on sinkhorn algorithm +
    LpL1 class regularization.

    Parameters
    ----------
    reg_e : float, optional (default=1)
        Entropic regularization parameter
    reg_cl : float, optional (default=0.1)
        Class regularization parameter
    mode : string, optional (default="unsupervised")
        The DA mode. If "unsupervised" no target labels are taken into account
        to modify the cost matrix. If "semisupervised" the target labels
        are taken into account to set coefficients of the pairwise distance
        matrix to 0 for row and columns indices that correspond to source and
        target samples which share the same labels.
    mapping : string, optional (default="barycentric")
        The kind of mapping to apply to transport samples from a domain into
        another one.
        if "barycentric" only the samples used to estimate the coupling can
        be transported from a domain to another one.
    metric : string, optional (default="sqeuclidean")
        The ground metric for the Wasserstein problem
    distribution : string, optional (default="uniform")
        The kind of distribution estimation to employ
    max_iter : int, float, optional (default=10)
        The minimum number of iteration before stopping the optimization
        algorithm if no it has not converged
    max_inner_iter : int, float, optional (default=200)
        The number of iteration in the inner loop
    verbose : int, optional (default=0)
        Controls the verbosity of the optimization algorithm
    log : int, optional (default=0)
        Controls the logs of the optimization algorithm
    limit_max: float, optional (defaul=np.infty)
        Controls the semi supervised mode. Transport between labeled source
        and target samples of different classes will exhibit an infinite cost

    Attributes
    ----------
    Coupling_ : the optimal coupling

    References
    ----------

    .. [1] N. Courty; R. Flamary; D. Tuia; A. Rakotomamonjy,
       "Optimal Transport for Domain Adaptation," in IEEE
       Transactions on Pattern Analysis and Machine Intelligence ,
       vol.PP, no.99, pp.1-1
    .. [2] Rakotomamonjy, A., Flamary, R., & Courty, N. (2015).
       Generalized conditional gradient: analysis of convergence
       and applications. arXiv preprint arXiv:1510.06567.

    """

    def __init__(self, reg_e=1., reg_cl=0.1,
                 max_iter=10, max_inner_iter=200,
                 tol=10e-9, verbose=False, log=False,
                 metric="sqeuclidean",
                 distribution_estimation=distribution_estimation_uniform,
                 out_of_sample_map='ferradans', limit_max=np.infty):

        self.reg_e = reg_e
        self.reg_cl = reg_cl
        self.max_iter = max_iter
        self.max_inner_iter = max_inner_iter
        self.tol = tol
        self.verbose = verbose
        self.log = log
        self.metric = metric
        self.distribution_estimation = distribution_estimation
        self.out_of_sample_map = out_of_sample_map
        self.limit_max = limit_max

    def fit(self, Xs, ys=None, Xt=None, yt=None):
        """Build a coupling matrix from source and target sets of samples
        (Xs, ys) and (Xt, yt)
        Parameters
        ----------
        Xs : array-like of shape = [n_source_samples, n_features]
            The training input samples.
        ys : array-like, shape = [n_source_samples]
            The class labels
        Xt : array-like of shape = [n_target_samples, n_features]
            The training input samples.
        yt : array-like, shape = [n_labeled_target_samples]
            The class labels
        Returns
        -------
        self : object
            Returns self.
        """

        super(SinkhornLpl1Transport, self).fit(Xs, ys, Xt, yt)

        self.Coupling_ = sinkhorn_lpl1_mm(
            a=self.mu_s, labels_a=ys, b=self.mu_t, M=self.Cost,
            reg=self.reg_e, eta=self.reg_cl, numItermax=self.max_iter,
            numInnerItermax=self.max_inner_iter, stopInnerThr=self.tol,
            verbose=self.verbose, log=self.log)

        return self


class SinkhornL1l2Transport(BaseTransport):
    """Domain Adapatation OT method based on sinkhorn algorithm +
    l1l2 class regularization.

    Parameters
    ----------
    reg_e : float, optional (default=1)
        Entropic regularization parameter
    reg_cl : float, optional (default=0.1)
        Class regularization parameter
    mode : string, optional (default="unsupervised")
        The DA mode. If "unsupervised" no target labels are taken into account
        to modify the cost matrix. If "semisupervised" the target labels
        are taken into account to set coefficients of the pairwise distance
        matrix to 0 for row and columns indices that correspond to source and
        target samples which share the same labels.
    mapping : string, optional (default="barycentric")
        The kind of mapping to apply to transport samples from a domain into
        another one.
        if "barycentric" only the samples used to estimate the coupling can
        be transported from a domain to another one.
    metric : string, optional (default="sqeuclidean")
        The ground metric for the Wasserstein problem
    distribution : string, optional (default="uniform")
        The kind of distribution estimation to employ
    max_iter : int, float, optional (default=10)
        The minimum number of iteration before stopping the optimization
        algorithm if no it has not converged
    max_inner_iter : int, float, optional (default=200)
        The number of iteration in the inner loop
    verbose : int, optional (default=0)
        Controls the verbosity of the optimization algorithm
    log : int, optional (default=0)
        Controls the logs of the optimization algorithm
    limit_max: float, optional (default=10)
        Controls the semi supervised mode. Transport between labeled source
        and target samples of different classes will exhibit an infinite cost
        (10 times the maximum value of the cost matrix)

    Attributes
    ----------
    Coupling_ : the optimal coupling

    References
    ----------

    .. [1] N. Courty; R. Flamary; D. Tuia; A. Rakotomamonjy,
       "Optimal Transport for Domain Adaptation," in IEEE
       Transactions on Pattern Analysis and Machine Intelligence ,
       vol.PP, no.99, pp.1-1
    .. [2] Rakotomamonjy, A., Flamary, R., & Courty, N. (2015).
       Generalized conditional gradient: analysis of convergence
       and applications. arXiv preprint arXiv:1510.06567.

    """

    def __init__(self, reg_e=1., reg_cl=0.1,
                 max_iter=10, max_inner_iter=200,
                 tol=10e-9, verbose=False, log=False,
                 metric="sqeuclidean",
                 distribution_estimation=distribution_estimation_uniform,
                 out_of_sample_map='ferradans', limit_max=10):

        self.reg_e = reg_e
        self.reg_cl = reg_cl
        self.max_iter = max_iter
        self.max_inner_iter = max_inner_iter
        self.tol = tol
        self.verbose = verbose
        self.log = log
        self.metric = metric
        self.distribution_estimation = distribution_estimation
        self.out_of_sample_map = out_of_sample_map
        self.limit_max = limit_max

    def fit(self, Xs, ys=None, Xt=None, yt=None):
        """Build a coupling matrix from source and target sets of samples
        (Xs, ys) and (Xt, yt)
        Parameters
        ----------
        Xs : array-like of shape = [n_source_samples, n_features]
            The training input samples.
        ys : array-like, shape = [n_source_samples]
            The class labels
        Xt : array-like of shape = [n_target_samples, n_features]
            The training input samples.
        yt : array-like, shape = [n_labeled_target_samples]
            The class labels
        Returns
        -------
        self : object
            Returns self.
        """

        super(SinkhornL1l2Transport, self).fit(Xs, ys, Xt, yt)

        self.Coupling_ = sinkhorn_l1l2_gl(
            a=self.mu_s, labels_a=ys, b=self.mu_t, M=self.Cost,
            reg=self.reg_e, eta=self.reg_cl, numItermax=self.max_iter,
            numInnerItermax=self.max_inner_iter, stopInnerThr=self.tol,
            verbose=self.verbose, log=self.log)

        return self
