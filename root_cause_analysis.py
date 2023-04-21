import argparse
import numpy as np
import pandas as pd
from queue import Queue
from collections import defaultdict
from cusc_fim import get_fim
from kneed import KneeLocator

def get_entropy(a):
    p = a / sum(a)
    entropy = sum([-x * np.log(x) for x in p])
    return entropy    

class Node:
    def __init__(self, k, v={}, des='', anomaly_value=0):
        self.k = k  
        self.v = v 
        self.son = defaultdict(list)
        self.des = des
        self.parent = []
        self.anomaly_value = anomaly_value  # total traffic in abnormal period

class ItemTree:
    def __init__(self, root_real, root_pred, transaction, total_anomaly, alpha=0.9, beta=0.1, entropy_thres=1, flag=1):
        self.alpha, self.beta = alpha, beta

        self.transaction, self.total_anomaly = transaction, total_anomaly
    
        self.anomaly_value_dic = {}
        self.entropy_thres = entropy_thres
        
        self.root = Node(k=set(), v=[root_real, root_pred, total_anomaly], des='', anomaly_value=self.total_anomaly)
        self.flag=flag

        for k, v in sorted(self.transaction.items(), key=lambda x: len(x[0].split(','))):
            k_set = set(k.split(','))
            anomaly_value = self.flag * (v[1] - v[0])
            self.add_node(k_set, k, v, anomaly_value)

    def add(self, root, new_node, item_set, k, v):
        """
            add nodes to the tree
        """
        if len(root.k) == len(item_set) - 1:
            try:
                add_attr = list(item_set.difference(root.k))[0]
                attr_type = add_attr[:1]
                if new_node not in root.son[attr_type]:
                    root.son[attr_type].append(new_node)
                    new_node.parent.append(root)
            except:
                pass
            return 
        for _, nodes in root.son.items():
            for node in nodes:
                if node.k.issubset(item_set):
                    self.add(node, new_node, item_set, k, v)

    def add_node(self, item_set, k, v, anomaly_value):
        """
            first create a node which key=item_set, then add to the tree
        """
        new_node = Node(item_set, v, des=k, anomaly_value=anomaly_value)
        self.add(self.root, new_node, item_set, k, v)
        return new_node

    def select_son(self, node, sons):
        sorted_son = sorted(sons, key=lambda x: x.v[2] / (x.v[1] + 1e-4), reverse=True if self.root.anomaly_value > 0 else False)
        sumed_anomaly_value = 0
        selected_node = []
        pert = []
        for son in sorted_son:
            selected_node.append(son)
            pert.append(son.anomaly_value / (son.v[1] + 1e-4))
            sumed_anomaly_value += son.anomaly_value
            
            if sumed_anomaly_value > self.alpha * min(self.root.anomaly_value, node.anomaly_value) and son.anomaly_value > self.beta * self.root.anomaly_value:
                pert = np.array(pert)
                pert = pert / np.sum(pert)
                entropy = get_entropy(np.array(pert))
                if entropy > self.entropy_thres:
                    return False, selected_node
                return True, selected_node
            if son.anomaly_value < self.beta * node.anomaly_value:
                return False, selected_node
        return False, selected_node

    def up_to_down(self):
        """
            Traverse the whole ItemTree, and maintaine the queue of extensible nodes
            Finally obtaine the abnormal traffic child node set that meets the most conditions
        """
        self.visited_dic = {self.root: True} # 可扩展节点
        self.choosed_extend_node = {self.root: self.root.anomaly_value}
        self.end_node_dic = {}
        q = Queue()
        q.put(self.root)
        self.unchoosed_nodes = {}
        while q.qsize() > 0:
            size = q.qsize()
            for _ in range(size):
                cur_node = q.get()
                for _, sons in cur_node.son.items():
                    is_extend, selected_son = self.select_son(cur_node, sons)
                    if not is_extend:
                        for node in selected_son:
                            self.unchoosed_nodes[node.des] = (node.anomaly_value, node.v)
                        continue
                    
                    tot_anomaly = 0
                    anomaly_sons = {}
                    for son in selected_son: 
                        tot_anomaly += son.anomaly_value
                        if son not in self.visited_dic.keys():
                            anomaly_sons[son.des] = son.anomaly_value 
                            self.visited_dic[son] = True
                            son.label = 1
                            cur_node.label = 1
                            q.put(son)
                        
                            del_node = []
                            for end_node in self.end_node_dic.keys():
                                if end_node.k.issubset(son.k):
                                    del_node.append(end_node)
                            for each in del_node:
                                del self.end_node_dic[each]
                            self.end_node_dic[son] = True
                            self.choosed_extend_node[son] = son.anomaly_value
        res = []
        for node in self.end_node_dic.keys():
            res.append(node.des)
        return res
    
def run(args):
    df = pd.read_csv(args.filepath)
    root_real = sum(df['real'])
    root_pred = sum(df['predict'])
    flag = 1 if root_pred > root_real else -1
    
    anomaly_list = np.log(1 + np.array(df['real']))
    hists, bins = np.histogram(anomaly_list,80)
    cdf = np.cumsum(hists)
    x = bins[1: ]
    kneedle = KneeLocator(x,cdf,S=1.0,curve='concave',direction='increasing',online=True)
    knee = kneedle.knee
    knee = np.exp(knee) - 1
    
    result = defaultdict(int)
    res_predict = defaultdict(int)
    res_real = defaultdict(int)
    _result = defaultdict(list)
    for itemset, tot_real, tot_predict in get_fim(df, knee):
        attr = itemset
        res_predict[attr] += tot_predict
        res_real[attr] += tot_real
        result[attr] += flag * (res_predict[attr] - res_real[attr])
        _result[attr] = [tot_real, tot_predict, result[attr]]
    result = sorted(result.items(), key=lambda x: x[1])
    res_dic = {}
    for k, v in result:
        res_dic[k] = [res_real[k], res_predict[k], v]
        
    root_real = sum(df['real'])
    root_pred = sum(df['predict'])
    total_anomaly = flag * (root_pred - root_real)
    tree = ItemTree(root_real, root_pred, res_dic, total_anomaly, alpha=args.alpha, beta=args.beta, entropy_thres=args.entropy, flag=flag)
    tree.up_to_down()
    des_res = []
    for node in tree.end_node_dic.keys():
        des_res.append(node.des)
    print("root cause:", des_res)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--filepath', type=str,   default='./data/sample_data.csv')
    parser.add_argument('--alpha'  , type=float, default=0.8)
    parser.add_argument('--beta'   , type=float, default=0.10)
    parser.add_argument('--entropy', type=float, default=0.85)
    args = parser.parse_args()
    
    run(args)
    