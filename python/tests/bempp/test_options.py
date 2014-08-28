""" Test general BEM++ option class

    For simplicity, only test a subset of options one per type more or less.
"""
from bempp.options import Options
from py.test import mark, fixture


@fixture
def from_kwargs():
    return Options(
        eps=1e-8, maximum_block_size=100, recompress=False,
        aca_assembly_mode="local", max_threads=5, assembly_mode="aca",
        sparse_storage_of_local_operators=False
    )


@fixture
def from_set():
    options = Options()

    options.eps = 1e-8
    options.maximum_block_size = 100
    options.recompress = False,
    options.aca_assembly_mode = "local"
    options.max_threads = 5
    options.sparse_storage_of_local_operators = False
    options.assembly_mode = "aca"

    return options


@mark.parametrize("instantiater", [from_kwargs, from_set])
def test_options(instantiater):
    options = instantiater()

    assert abs(options.eta - 1e-4) < 1e-8
    assert abs(options.eps - 1e-8) < 1e-8
    assert options.maximum_block_size == 100
    assert options.minimum_block_size == 16
    assert options.maximum_rank in [2**32-2, 2**64-2]
    assert options.reaction_to_unsupported_mode == "warning"
    assert options.aca_assembly_mode == "local"
    assert options.max_threads == 5
    assert options.assembly_mode == "aca"
    assert not options.sparse_storage_of_local_operators


def test_max_thread_auto():
    options = Options()
    for value in ['auto', -1, -5, None]:
        options.max_threads = 5
        assert options.max_threads == 5

        options.max_threads = value
        assert options.max_threads == 'auto'


def test_unknown_init_arg_throws():
    from py.test import raises
    with raises(TypeError):
        Options(nothing=0)


def test_incorrect_enum_value_raises():
    from py.test import raises
    options = Options()
    with raises(ValueError):
        options.aca_assembly_mode = "dummy"
