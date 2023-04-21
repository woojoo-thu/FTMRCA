# FTMRCA
Implementation of paper 《FTM-RCA: A Fast Two-Stage Multi-dimensional Root-Cause Analysis of Network Anomalies》

## Pre-requisites

### compile and install boost 
install dependency

```
>>> sudo apt-get install mpi-default-dev
>>> sudo apt-get install libicu-dev 
>>> sudo apt-get install python-dev
>>> sudo apt-get install libbz2-dev
```

download boost source code from https://www.boost.org/users/history/

```
>>> ./bootstrap.sh
>>> sudo ./b2
>>> sudo ./b2 install
```

Ensure the version result of the code are the same

1. `>>> cat /usr/include/boost/version.hpp | grep BOOST_LIB_VERSION`

2. run the following code
    ```
    #include <boost/version.hpp>
    #include <iostream>

    int main() {
        std::cout << "Boost version: " << BOOST_LIB_VERSION << std::endl;
        return 0;
    }
    ```


### compile and install NumCpp

Download NumCpp source code (the compatible version with boost) from https://github.com/dpilger26/NumCpp/releases 

Then compile and install NumCpp

```
>>> cd NumCpp
>>> mkdir build
>>> cd build
>>> cmake ..
>>> cmake --build . --target install
```

### compile and install discreture
```
>>> sudo apt-get install libboost-all-dev git build-essential >>> cmake
>>> git clone --recursive https://github.com/mraggi/discreture
>>> cd discreture
>>> mkdir build
>>> cd build
>>> cmake ..
>>> make
>>> sudo make install
```

## Run CUSC Algorithm
```
>>> g++ cusc.cpp -std=c++17 -o cuse
// The first parameter is filepath, and the second is the minimum support
>>> ./cusc ./data/cpp_sample_data.csv 100
```


## Run FTM-RCA Sample
```
>>> python3 root_cause_analysis.py
```
