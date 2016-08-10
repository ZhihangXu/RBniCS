# Copyright (C) 2015-2016 by the RBniCS authors
#
# This file is part of RBniCS.
#
# RBniCS is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RBniCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with RBniCS. If not, see <http://www.gnu.org/licenses/>.
#
## @file product.py
#  @brief product function to assemble truth/reduced affine expansions.
#
#  @author Francesco Ballarin <francesco.ballarin@sissa.it>
#  @author Gianluigi Rozza    <gianluigi.rozza@sissa.it>
#  @author Alberto   Sartori  <alberto.sartori@sissa.it>

from RBniCS.backend.numpy.affine_expansion_storage import AffineExpansionStorage
from RBniCS.backend.numpy.matrix import Matrix_Type
from RBniCS.backend.numpy.vector import Vector_Type
from RBniCS.backend.numpy.function import Function_Type
from RBniCS.utils.decorators import any, backend_for

# product function to assemble truth/reduced affine expansions. To be used in combination with sum,
# even though this one actually carries out both the sum and the product!
@backend_for("NumPy", inputs=(tuple, AffineExpansionStorage, any(tuple, None)))
def product(thetas, operators, thetas2=None):
    assert len(thetas) == len(operators)
    order = operators.order()
    assert order == 1 or order == 2
    if order == 1: # vector storage of affine expansion online data structures (e.g. reduced matrix/vector expansions)
        assert isinstance(operators[0], (Matrix_Type, Vector_Type, Function_Type))
        assert thetas2 is None
        # Single for loop version:
        output = 0
        for (theta, operator) in zip(thetas, operators):
            output += theta*operator
        return ProductOutput(output)
        '''
        # Vectorized version:
        # Profiling has reveleaded that the following vectorized (over q) version
        # introduces an overhead of 10%~20%
        from numpy import asmatrix
        output = asmatrix(thetas)*operators.as_matrix().transpose()
        output = output.item(0, 0)
        return ProductOutput(output)
        '''
    elif order == 2: # matrix storage of affine expansion online data structures (e.g. error estimation ff/af/aa products)
        assert isinstance(operators[0, 0], (OnlineMatrix_Type, OnlineVector_Type, float))
        assert thetas2 is not None
        # no checks here on the first dimension of operators should be equal to len(thetas), and
        # similarly that the second dimension should be equal to len(thetas2), because the
        # current operator interface does not provide a 2D len method
        '''
        # Double for loop version:
        # Profiling has revelead a sensible speedup for large values of N and Q 
        # when compared to the double/triple/quadruple for loop in the legacy version.
        # Vectorized version (below) provides an additional 25%~50% speedup when dealing with
        # the (A, A) Riesz representor products (case of quadruple loop),
        # while this version introduces overhead when for (F, F) Riesz 
        # representor products (case of double loop).
        output = 0.
        for i in range(len(thetas)):
            for j in range(len(thetas2)):
                output += thetas[i]*operators[i, j]*thetas2[j]
        # Thus we selected the following:
        '''
        # Vectorized version:
        from numpy import asmatrix
        thetas_vector = asmatrix(thetas)
        thetas2_vector = asmatrix(thetas2).transpose()
        output = thetas_vector*operators.as_matrix()*thetas2_vector
        return ProductOutput(output.item(0, 0))
    else:
        raise AssertionError("product(): invalid operands.")
    
        
# Auxiliary class to signal to the sum() function that it is dealing with an output of the product() method
class ProductOutput(object):
    def __init__(self, sum_product_return_value):
        self.sum_product_return_value = sum_product_return_value
    
