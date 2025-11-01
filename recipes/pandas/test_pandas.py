def test_basic():
    from pandas import DataFrame

    df = DataFrame(
        [("alpha", 1), ("bravo", 2), ("charlie", 3)],
        columns=["Letter", "Number"],
    )
    assert df.to_csv() == (",Letter,Number\n0,alpha,1\n1,bravo,2\n2,charlie,3\n")
