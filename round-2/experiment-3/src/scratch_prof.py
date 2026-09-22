import time, numpy as np
from scipy.linalg import cho_factor, cho_solve
rs=np.random.default_rng(0)
for d in (1024,2048):
    W=rs.standard_normal((d,3*d)).astype(np.float32)
    t=time.time(); Wd=W.astype(np.float64); G=Wd@Wd.T; G=0.5*(G+G.T); t_g=time.time()-t
    t=time.time(); cf=cho_factor(G+1e-8*np.trace(G)/d*np.eye(d),lower=True,check_finite=False); t_c=time.time()-t
    Q,_=np.linalg.qr(rs.standard_normal((d,32)))
    t=time.time()
    for _ in range(8):
        X=cho_solve(cf,Q,check_finite=False); Q,_=np.linalg.qr(X)
    t_i=time.time()-t
    t=time.time(); B=Q.T@(G@Q); np.linalg.eigh(0.5*(B+B.T)); t_r=time.time()-t
    t=time.time(); np.linalg.eigh(G); t_e=time.time()-t
    print(f"d={d} gram={t_g:.2f} chol={t_c:.2f} iter8x32={t_i:.2f} ritz={t_r:.2f} | FULL_EIGH={t_e:.2f}",flush=True)
