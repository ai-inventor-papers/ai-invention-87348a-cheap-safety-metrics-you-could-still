import time, numpy as np, os
os.environ.setdefault("OMP_NUM_THREADS","2")
rs=np.random.default_rng(0)
out={}
for (d,din) in [(1024,3072),(1536,4608),(2048,6144)]:
    W32=rs.standard_normal((d,din)).astype(np.float32)
    t=time.time(); G32=(W32@W32.T); t_g32=time.time()-t
    t=time.time(); G64=W32.astype(np.float64)@W32.astype(np.float64).T; t_g64=time.time()-t
    t=time.time(); np.linalg.eigh(G32.astype(np.float64)); t_e=time.time()-t
    out[d]=dict(gram_f32=round(t_g32,2),gram_f64=round(t_g64,2),eigh=round(t_e,2),
                total_f32=round(t_g32+t_e,2))
    print(d,out[d],flush=True)
