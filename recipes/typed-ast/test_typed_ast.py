# Test parsing something which is valid in Python 2 but not in Python 3.
def test_ast27():
    from typed_ast import ast27

    mod_node = ast27.parse("print 'Hello world'")
    assert isinstance(mod_node, ast27.Module)

    print_node = mod_node.body[0]
    assert isinstance(print_node, ast27.Print)

    str_node = print_node.values[0]
    assert isinstance(str_node, ast27.Str)
    assert str_node.s == b"Hello world"
