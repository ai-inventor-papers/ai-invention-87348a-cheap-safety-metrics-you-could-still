import time, numpy as np, scipy.linalg as sla
rs=np.random.default_rng(0)
for d,din in [(1024,3072),(2048,6144)]:
    W=rs.standard_normal((d,din)).astype(np.float32)
    G32=(W@W.T); G32=0.5*(G32+G32.T); G64=G32.astype(np.float64)
    r={}
    t=time.time(); sla.eigvalsh(G32, driver='ev'); r['eigvalsh_f32']=round(time.time()-t,2)
    t=time.time(); sla.eigh(G32, subset_by_index=[0,47], driver='evr'); r['subset_bot48_f32']=round(time.time()-t,2)
    t=time.time(); sla.eigh(G32, subset_by_index=[d-4,d-1], driver='evr'); r['subset_top4_f32']=round(time.time()-t,2)
    t=time.time(); sla.eigh(G64, subset_by_index=[0,47], driver='evr'); r['subset_bot48_f64']=round(time.time()-t,2)
    print(d, r, flush=True)
