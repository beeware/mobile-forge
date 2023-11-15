# Based on https://kiwisolver.readthedocs.io/en/latest/basis/basic_systems.html
def test_basic():
    from kiwisolver import Solver, Variable

    x1 = Variable("x1")
    x2 = Variable("x2")
    xm = Variable("xm")

    constraints = [x1 >= 0, x2 <= 100, x2 >= x1 + 10, xm == (x1 + x2) / 2]
    solver = Solver()
    for cn in constraints:
        solver.addConstraint(cn)

    solver.addConstraint((x1 == 40) | "weak")
    solver.addEditVariable(xm, "strong")
    solver.suggestValue(xm, 60)
    solver.updateVariables()

    assert xm.value() == 60
    assert x1.value() == 40
    assert x2.value() == 80
