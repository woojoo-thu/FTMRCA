import numpy as np 
from collections import defaultdict
from itertools import combinations

class CUSC:
    def __init__(self, df, min_sup=6000):
        self.min_sup = min_sup
        self.attrs = ['i', 'e', 'c', 'p', 'l']
        data = df[self.attrs].to_numpy()
        self.value = np.array(df['real'])
        self.pred  = np.array(df['predict'])
        self.support = defaultdict(list)
        self.hash_store = {}
        self.mask = {}
        self.compute_L1(data)

    def compute_L1(self, data):
        K = 1
        for i in range(len(self.attrs)):
            attr = self.attrs[i]
            attr_cnt = defaultdict(int)
            pred_cnt = defaultdict(int)
            tids = data[:, i]
            self.hash_store[tuple([i])] = tids
            for tid, key in enumerate(tids):
                if tid < 0: continue
                attr_cnt[key] += self.value[tid]
                pred_cnt[key] += self.pred[tid]
            for k, v in attr_cnt.items():
                if v < self.min_sup:
                    continue 
                self.support[K].append((f'{attr}{k}', v, pred_cnt[k]))
    
    def get_attrs(self, attrs, num):
        mod = 1 << 7
        attr_str = []
        for attr_idx in attrs[::-1]:
            attr_str.append(f'{self.attrs[attr_idx]}{num % mod}')
            num //= mod
        return ','.join(sorted(attr_str))
    
    def get_fim(self, attrs, tids, K):
        attr_cnt = defaultdict(int)
        pred_cnt = defaultdict(int)
        for tid in range(len(tids)):
            if tid < 0: continue
            attr_cnt[tids[tid]] += self.value[tid]
            pred_cnt[tids[tid]] += self.pred[tid]
        res = []
        for k, v in attr_cnt.items():
            if v < self.min_sup:
                continue
            res.append((self.get_attrs(attrs, k), v, pred_cnt[k]))
        self.support[K].extend(res)
    
    def compute_LK(self, K):
        for attrs in combinations([i for i in range(len(self.attrs))], K):
            hash_tids = (self.hash_store[attrs[:-1]] << 7) + self.hash_store[attrs[-1:]]
            self.hash_store[attrs] = hash_tids
            self.get_fim(attrs, hash_tids, K)
        if K > 2:
            for attrs in combinations([i for i in range(len(self.attrs))], K - 1):
                del self.hash_store[attrs]
 
def get_fim(df, minsup):
    cusc = CUSC(df, min_sup=minsup)
    for level in range(2, 5 + 1):
        cusc.compute_LK(level)
    res = []
    for _, v in cusc.support.items():
        res.extend(v)
    return res
