#include <iostream>
#include <vector>
#include <fstream>
#include <sstream>
#include <map>
#include <bitset>
#include <iostream>
#include <discreture.hpp>
#include <typeinfo>
#include <ctime>
#include <unistd.h>
#include <sys/resource.h>
#include <filesystem>
#include <malloc.h>
#include "NumCpp.hpp"
#include "boost/filesystem.hpp"

using namespace discreture;
using discreture::operator<<;
using namespace std;
using std::filesystem::directory_iterator;

string int2string(int k) {
    stringstream ss;
    ss << k;
    return ss.str();
}

string get_str_from_comb(const vector<int>& combination) {
    string name = "";
    int idx = 0;
    for(auto item : combination) {
        string s = int2string(item);
        name = idx > 0 ? name + "," + s : name + s;
        idx++;
    }
    return name;
}

class CUSC {
private:
    vector<string> attrs {"i", "e", "c", "p", "l"};
    float minsup;
    map<int, vector<int> > support;
    string filepath;
    map<string, nc::NdArray<bool> > mask;
    map<string, nc::NdArray<int> > hash_store;
    nc::NdArray<float> values;
    int FIM_cnt = 0;
    set<string> pre_keys;
public:
    CUSC(float minsup, string filepath): minsup(minsup), filepath(filepath) {
        ifstream fp(filepath);
        string line;
        vector<vector<int> > transactions;
        vector<float> val_vec;
        string attr;
        string val;
        getline(fp, line);  // skip the head line
        while(getline(fp, line)) {
            vector<int> attrs;
            istringstream readstr(line); 
            for(int j = 0; j < this->attrs.size(); j++) {
                getline(readstr, attr, ',');
                attrs.push_back(atoi(attr.c_str()));
            }
            transactions.push_back(attrs);
            getline(readstr, val, ',');
            val_vec.push_back(atof(val.c_str()));
        }

        fp.close();
        this->values = nc::NdArray<float>(val_vec);
        nc::NdArray<int>transactions_arr = nc::NdArray<int>(transactions);

        vector<vector<int> >().swap(transactions);
        malloc_trim(0);
        compute_L1(transactions_arr);
    }

    void compute_L1(nc::NdArray<int>& transactions) {
        int K = 1;
        for (int i = 0; i < get_attr_lens(); i++) {
            string attr = this->attrs[i];
            map<int, float> attr_cnt;
            auto tids = transactions(transactions.rSlice(), i);
            string key = int2string(i);
            pre_keys.insert(key);
            this->hash_store[key] = tids;
            nc::NdArray<bool> mask (tids.size(), 1);
            mask = true;
            this->mask[key] = mask;
            for(int i = 0; i < tids.shape().rows; i++) {
                attr_cnt[tids(i, 0)] += this->values(0, i);
            }
            for(auto it = attr_cnt.begin(); it != attr_cnt.end(); it++) {
                int k = it->first;
                if (it->second >= this->minsup) {
                    this->support[K].push_back(k);
                } else {
                    this->mask[key] &= ((this->hash_store[key] ^ k) != 0);
                }
            }
        }
        this->FIM_cnt += (this->support[K].size());
    }

    void get_fim(string& attrs, nc::NdArray<int>& tids, int K) {
        map<int, float> attr_cnt;
        auto rowsCols = nc::nonzero(this->mask[attrs]);
        if (rowsCols.first.isempty()) return;
        map<int, vector<int> > idx_vec;
        for(auto it = rowsCols.first.begin(); it != rowsCols.first.end(); it++) {
            attr_cnt[tids[*it]] += this->values(0, *it);
            idx_vec[tids[*it]].push_back(*it);
        }
        
        int idx = 0;
        for(auto it = attr_cnt.begin(); it != attr_cnt.end(); it++) {
            int k = it->first;
            if (it->second >= this->minsup) {
                this->support[K].push_back(k);
            } else {
                for (int j : idx_vec[k]) {
                    this->mask[attrs][j] = 0;
                }
                idx += 1;
            }
        }
    }

    string get_pre_combination(const vector<int>& combination) {
        vector<int> n_combination;
        n_combination.assign(combination.begin(), combination.begin() + combination.size() - 1);  
        string pre_key = get_str_from_comb(n_combination);
        return pre_key;
    }

    string get_aft_combination(const vector<int>& combination) {
        vector<int> n_combination;
        n_combination.assign(combination.begin() + 1, combination.end());  
        string pre_key = get_str_from_comb(n_combination);
        return pre_key;
    }

    void compute_LK(int K) {
        set<string> prekey_sets = pre_keys;
        pre_keys.clear();
        for (auto&& combination : discreture::combinations(5, K)) {
            string pre_key = get_pre_combination(combination);
            string aft_key = get_aft_combination(combination);
            string key = get_str_from_comb(combination);
            pre_keys.insert(key);
            nc::NdArray<int> hash_tids = (this->hash_store[pre_key] << 8) + this->hash_store[aft_key];
            this->mask[key] = (this->mask[pre_key]) & (this->mask[aft_key]);
            this->hash_store[key] = hash_tids;
            get_fim(key, hash_tids, K);
        }
        this->FIM_cnt += (this->support[K].size());
        for(string prekey : prekey_sets) {
            this->hash_store.erase(prekey);
            this->mask.erase(prekey);
        } 
    }

    int get_attr_lens() {
        return this->attrs.size();
    }

    int get_FIM_cnt() {
        return this->FIM_cnt;
    }
};

void Run_CUSC(float minsup, string filepath) {
    CUSC cusc(minsup, filepath);
    malloc_trim(0);
    for(int i = 2; i <= cusc.get_attr_lens(); i++) {
        cusc.compute_LK(i);
    }
    cout << cusc.get_FIM_cnt() << endl;
}

int main(int argc, char* argv[]) {
    string filepath = argv[1]; // "./data/cpp_sample_data.csv";
    int minimum_support = stoi(argv[2]);
    Run_CUSC(minimum_support, filepath);
    return 0;
}