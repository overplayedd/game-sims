"""Independent re-implementation (absolute board squares, different structure) to cross-check ludo.c."""
import random, sys, json
from multiprocessing import Pool
SAFE={0,8,13,21,26,34,39,47}
def play(args):
    hero_bot, n, seed = args
    rng=random.Random(seed); wins=0; rounds=0
    for g in range(n):
        hero=g%4
        steps=[[None]*4 for _ in range(4)]   # None=base, int steps travelled, 56=home
        def sq(pl,s): return (13*pl+s)%52
        turn=0; t=0; winner=None
        while winner is None:
            pl=turn%4; t+=1; sixes=0
            while True:
                r=rng.randint(1,6)
                if r==6:
                    sixes+=1
                    if sixes==3: break
                opts=[]; seen=set()
                for i,s in enumerate(steps[pl]):
                    if s==56 or s in seen: continue
                    if s is None:
                        if r!=6: continue
                        ns=0
                    else:
                        ns=s+r
                        if ns>56: continue
                    seen.add(s); opts.append((i,ns))
                if opts:
                    bot = hero_bot if pl==hero else 'random'
                    def victims(ns):
                        if ns>50 or sq(pl,ns) in SAFE: return []
                        return [(o,j) for o in range(4) if o!=pl for j,s in enumerate(steps[o]) if s is not None and s<=50 and sq(o,s)==sq(pl,ns)]
                    if bot=='random': ch=rng.choice(opts)
                    elif bot=='capturer':
                        c=[o for o in opts if victims(o[1])]
                        if c:
                            best=max(sum(steps[a][b] for a,b in victims(o[1])) for o in c)
                            c=[o for o in c if sum(steps[a][b] for a,b in victims(o[1]))==best]
                        ch=rng.choice(c or opts)
                    elif bot=='rusher':
                        key=lambda o:-1 if steps[pl][o[0]] is None else steps[pl][o[0]]
                        m=max(map(key,opts)); ch=rng.choice([o for o in opts if key(o)==m])
                    elif bot=='spreader':
                        ex=[o for o in opts if steps[pl][o[0]] is None]
                        if ex: ch=ex[0]
                        else:
                            m=min(steps[pl][o[0]] for o in opts); ch=rng.choice([o for o in opts if steps[pl][o[0]]==m])
                    elif bot=='out_random':
                        ex=[o for o in opts if steps[pl][o[0]] is None]
                        ch=ex[0] if ex else rng.choice(opts)
                    elif bot=='out_lead':
                        ex=[o for o in opts if steps[pl][o[0]] is None]
                        if ex: ch=ex[0]
                        else:
                            m=max(steps[pl][o[0]] for o in opts); ch=rng.choice([o for o in opts if steps[pl][o[0]]==m])
                    i,ns=ch
                    for o,j in victims(ns): steps[o][j]=None
                    steps[pl][i]=ns
                    if all(s==56 for s in steps[pl]): winner=pl; break
                if r!=6: break
            turn+=1
        wins+= winner==hero; rounds+=(t+3)//4
    return wins,rounds
if __name__=='__main__':
    N=15000
    with Pool(2) as p:
        for bot in ['random','capturer','rusher','spreader','out_random','out_lead']:
            res=p.map(play,[(bot,N,1),(bot,N,2)])
            w=sum(r[0] for r in res); rd=sum(r[1] for r in res)
            print(bot, round(100*w/(2*N),2), 'avg rounds',round(rd/(2*N),1), flush=True)
