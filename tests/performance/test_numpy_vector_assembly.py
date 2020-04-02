# Copyright (C) 2015-2020 by the RBniCS authors
#
# This file is part of RBniCS.
#
# SPDX-License-Identifier: LGPL-3.0-or-later

import pytest
from numpy import isclose
from numpy.linalg import norm
from rbnics.backends import product as factory_product, sum as factory_sum
from rbnics.backends.online import OnlineAffineExpansionStorage, online_product, online_sum
from rbnics.backends.online.numpy import product as numpy_product, sum as numpy_sum
from test_utils import RandomNumpyVector, RandomTuple

product = None
sum = None
all_product = {"numpy": numpy_product, "online": online_product, "factory": factory_product}
all_sum = {"numpy": numpy_sum, "online": online_sum, "factory": factory_sum}

class Data(object):
    def __init__(self, N, Q):
        self.N = N
        self.Q = Q

    def generate_random(self):
        F = OnlineAffineExpansionStorage(self.Q)
        for i in range(self.Q):
            # Generate random vector
            F[i] = RandomNumpyVector(self.N)
        # Genereate random theta
        theta = RandomTuple(self.Q)
        # Return
        return (theta, F)

    def evaluate_builtin(self, theta, F):
        result_builtin = theta[0] * F[0]
        for i in range(1, self.Q):
            result_builtin += theta[i] * F[i]
        return result_builtin

    def evaluate_backend(self, theta, F):
        return sum(product(theta, F))

    def assert_backend(self, theta, F, result_backend):
        result_builtin = self.evaluate_builtin(theta, F)
        relative_error = norm(result_builtin - result_backend) / norm(result_builtin)
        assert isclose(relative_error, 0., atol=1e-12)

@pytest.mark.parametrize("N", [2**i for i in range(1, 9)])
@pytest.mark.parametrize("Q", [10 + 4 * j for j in range(1, 4)])
@pytest.mark.parametrize("test_type", ["builtin"] + list(all_product.keys()))
def test_numpy_vector_assembly(N, Q, test_type, benchmark):
    data = Data(N, Q)
    print("N = " + str(N) + ", Q = " + str(Q))
    if test_type == "builtin":
        print("Testing", test_type)
        benchmark(data.evaluate_builtin, setup=data.generate_random)
    else:
        print("Testing", test_type, "backend")
        global product, sum
        product, sum = all_product[test_type], all_sum[test_type]
        benchmark(data.evaluate_backend, setup=data.generate_random, teardown=data.assert_backend)
