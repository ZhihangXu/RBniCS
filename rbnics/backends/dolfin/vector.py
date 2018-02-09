# Copyright (C) 2015-2018 by the RBniCS authors
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

from ufl import Form
from dolfin import assemble, has_pybind11
if has_pybind11():
    from dolfin.cpp.la import GenericVector
else:
    from dolfin import GenericVector

def Vector():
    raise NotImplementedError("This is dummy function (not required by the interface) just store the Type")
    
# Attach a Type() function
def Type():
    return GenericVector
Vector.Type = Type

# pybind11 wrappers do not implement __neg__ unary operator
if has_pybind11():
    def custom__neg__(self):
        return -1.*self
    setattr(GenericVector, "__neg__", custom__neg__)

# Preserve generator attribute in algebraic operators, as required by DEIM
def preserve_generator_attribute(operator):
    original_operator = getattr(GenericVector, operator)
    def custom_operator(self, other):
        if hasattr(self, "generator"):
            output = original_operator(self, other)
            output.generator = self.generator
            return output
        else:
            return original_operator(self, other)
    setattr(GenericVector, operator, custom_operator)
    
for operator in ("__add__", "__radd__", "__iadd__", "__sub__", "__rsub__", "__isub__", "__mul__", "__rmul__", "__imul__", "__truediv__", "__itruediv__"):
    preserve_generator_attribute(operator)

# Allow sum and sub between vector and form by assemblying the form. This is required because
# affine expansion storage is not assembled if it is parametrized, and it may happen that
# some terms are parametrized (and thus not assembled) while others are not parametrized
# (and thus assembled).
def arithmetic_with_form(operator):
    original_operator = getattr(GenericVector, operator)
    def custom_operator(self, other):
        from rbnics.backends.dolfin.parametrized_tensor_factory import ParametrizedTensorFactory # cannot import at global scope due to cyclic dependence
        if isinstance(other, Form):
            assert len(other.arguments()) is 1
            other = assemble(other)
        elif isinstance(other, ParametrizedTensorFactory):
            from rbnics.backends.dolfin.evaluate import evaluate # cannot import at global scope due to cyclic dependence
            assert len(other._form.arguments()) is 1
            other = evaluate(other)
        return original_operator(self, other)
    setattr(GenericVector, operator, custom_operator)

for operator in ("__add__", "__radd__", "__sub__", "__rsub__"):
    arithmetic_with_form(operator)
