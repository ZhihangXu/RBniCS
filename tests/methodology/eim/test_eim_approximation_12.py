# Copyright (C) 2015-2022 by the RBniCS authors
#
# This file is part of RBniCS.
#
# SPDX-License-Identifier: LGPL-3.0-or-later

import os
import pytest
from dolfin import (assemble, cos, dx, exp, Function, FunctionSpace, IntervalMesh, pi, project, SpatialCoordinate,
                    TestFunction, TrialFunction)
from rbnics import EquispacedDistribution
from rbnics.backends import ParametrizedExpressionFactory, ParametrizedTensorFactory, SymbolicParameters
from rbnics.eim.problems.eim_approximation import EIMApproximation
from rbnics.eim.reduction_methods.eim_approximation_reduction_method import EIMApproximationReductionMethod
from rbnics.problems.base import ParametrizedProblem
from rbnics.reduction_methods.base import ReductionMethod
from rbnics.utils.decorators import (StoreMapFromProblemNameToProblem, StoreMapFromProblemToReductionMethod,
                                     StoreMapFromProblemToTrainingStatus, StoreMapFromSolutionToProblem)


@pytest.mark.parametrize("expression_type", ["Function", "Vector", "Matrix"])
@pytest.mark.parametrize("basis_generation", ["Greedy", "POD"])
def test_eim_approximation_12(expression_type, basis_generation):
    """
    The aim of this script is to test EIM/DEIM for nonlinear problems, extending test 11.
    The difference with respect to test 11 is that a parametrized problem is defined but it is not
    reduced any further.
    Thus, the high fidelity solution will be used inside the parametrized expression/tensor, while
    in test 11 the reduced order solution was being used.
    * EIM: the expression to be interpolated is the solution of the nonlinear high fidelity problem.
    * DEIM: the form to be interpolated contains the solution of the nonlinear high fidelity problem.
    """

    @StoreMapFromProblemNameToProblem
    @StoreMapFromProblemToTrainingStatus
    @StoreMapFromSolutionToProblem
    class MockProblem(ParametrizedProblem):
        def __init__(self, V, **kwargs):
            # Call parent
            ParametrizedProblem.__init__(self, os.path.join(
                "test_eim_approximation_12_tempdir", expression_type, basis_generation, "mock_problem"))
            # Minimal subset of a ParametrizedDifferentialProblem
            self.V = V
            self._solution = Function(V)
            self.components = ["u"]
            # Parametrized function to be interpolated
            x = SpatialCoordinate(V.mesh())
            mu = SymbolicParameters(self, V, (1., ))
            self.f = (1 - x[0]) * cos(3 * pi * mu[0] * (1 + x[0])) * exp(- mu[0] * (1 + x[0]))
            # Inner product
            f = TrialFunction(self.V)
            g = TestFunction(self.V)
            self.inner_product = assemble(f * g * dx)

        def name(self):
            return "MockProblem_12_" + expression_type + "_" + basis_generation

        def init(self):
            pass

        def solve(self):
            print("solving mock problem at mu =", self.mu)
            assert not hasattr(self, "_is_solving")
            self._is_solving = True
            project(self.f, self.V, function=self._solution)
            delattr(self, "_is_solving")
            return self._solution

    @StoreMapFromProblemToReductionMethod
    class MockReductionMethod(ReductionMethod):
        def __init__(self, truth_problem, **kwargs):
            # Call parent
            ReductionMethod.__init__(self, os.path.join(
                "test_eim_approximation_12_tempdir", expression_type, basis_generation, "mock_problem"))
            # Minimal subset of a DifferentialProblemReductionMethod
            self.truth_problem = truth_problem
            self.reduced_problem = None

        def initialize_training_set(self, ntrain, enable_import=True, sampling=None, **kwargs):
            return ReductionMethod.initialize_training_set(
                self, self.truth_problem.mu_range, ntrain, enable_import, sampling, **kwargs)

        def initialize_testing_set(self, ntest, enable_import=False, sampling=None, **kwargs):
            return ReductionMethod.initialize_testing_set(
                self, self.truth_problem.mu_range, ntest, enable_import, sampling, **kwargs)

        def offline(self):
            pass

        def update_basis_matrix(self, snapshot):
            pass

        def error_analysis(self, N=None, **kwargs):
            pass

        def speedup_analysis(self, N=None, **kwargs):
            pass

    class ParametrizedFunctionApproximation(EIMApproximation):
        def __init__(self, truth_problem, expression_type, basis_generation, function):
            self.V = truth_problem.V
            #
            folder_prefix = os.path.join("test_eim_approximation_12_tempdir", expression_type, basis_generation)
            assert expression_type in ("Function", "Vector", "Matrix")
            if expression_type == "Function":
                # Call Parent constructor
                EIMApproximation.__init__(
                    self, truth_problem, ParametrizedExpressionFactory(truth_problem._solution), folder_prefix,
                    basis_generation)
            elif expression_type == "Vector":
                v = TestFunction(self.V)
                form = truth_problem._solution * v * dx
                # Call Parent constructor
                EIMApproximation.__init__(
                    self, truth_problem, ParametrizedTensorFactory(form), folder_prefix, basis_generation)
            elif expression_type == "Matrix":
                u = TrialFunction(self.V)
                v = TestFunction(self.V)
                form = truth_problem._solution * u * v * dx
                # Call Parent constructor
                EIMApproximation.__init__(
                    self, truth_problem, ParametrizedTensorFactory(form), folder_prefix, basis_generation)
            else:  # impossible to arrive here anyway thanks to the assert
                raise AssertionError("Invalid expression_type")

    # 1. Create the mesh for this test
    mesh = IntervalMesh(100, -1., 1.)

    # 2. Create Finite Element space (Lagrange P1)
    V = FunctionSpace(mesh, "Lagrange", 1)

    # 3. Create a parametrized problem
    problem = MockProblem(V)
    mu_range = [(1., pi), ]
    problem.set_mu_range(mu_range)

    # 4. Create a reduction method, but postpone generation of the reduced problem
    MockReductionMethod(problem)

    # 5. Allocate an object of the ParametrizedFunctionApproximation class
    parametrized_function_approximation = ParametrizedFunctionApproximation(
        problem, expression_type, basis_generation, lambda u: exp(u))
    parametrized_function_approximation.set_mu_range(mu_range)

    # 6. Prepare reduction with EIM
    parametrized_function_reduction_method = EIMApproximationReductionMethod(parametrized_function_approximation)
    parametrized_function_reduction_method.set_Nmax(12)
    parametrized_function_reduction_method.set_tolerance(0.)

    # 7. Perform EIM offline phase
    parametrized_function_reduction_method.initialize_training_set(51, sampling=EquispacedDistribution())
    reduced_parametrized_function_approximation = parametrized_function_reduction_method.offline()

    # 8. Perform EIM online solve
    online_mu = (1., )
    reduced_parametrized_function_approximation.set_mu(online_mu)
    reduced_parametrized_function_approximation.solve()

    # 9. Perform EIM error analysis
    parametrized_function_reduction_method.initialize_testing_set(100)
    parametrized_function_reduction_method.error_analysis()
