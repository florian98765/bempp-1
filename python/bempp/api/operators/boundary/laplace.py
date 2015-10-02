# pylint: disable-msg=too-many-arguments

"""Definition of the Laplace boundary operators."""


def single_layer(domain, range_, dual_to_range,
                 label="SLP", symmetry='no_symmetry',
                 parameters=None):
    """Return the single-layer boundary operator."""

    import bempp
    from bempp.core.operators.boundary.laplace import single_layer_ext
    from bempp.api.assembly import ElementaryBoundaryOperator

    if parameters is None:
        parameters = bempp.api.global_parameters

    return ElementaryBoundaryOperator( \
        single_layer_ext(parameters, domain, range_,
                         dual_to_range, "", symmetry),
        parameters=parameters, label=label)


def double_layer(domain, range_, dual_to_range,
                 label="DLP", symmetry='no_symmetry',
                 parameters=None):
    """Return the double-layer boundary operator."""

    import bempp
    from bempp.core.operators.boundary.laplace import double_layer_ext
    from bempp.api.assembly import ElementaryBoundaryOperator


    if parameters is None:
        parameters = bempp.api.global_parameters

    return ElementaryBoundaryOperator( \
        double_layer_ext(parameters, domain, range_,
                         dual_to_range, "", symmetry),
        parameters=parameters, label=label)


def adjoint_double_layer(domain, range_, dual_to_range,
                         label="ADJ_DLP", symmetry='no_symmetry',
                         parameters=None):
    """Return the adjoint double-layer boundary operator."""

    import bempp
    from bempp.core.operators.boundary.laplace import adjoint_double_layer_ext
    from bempp.api.assembly import ElementaryBoundaryOperator


    if parameters is None:
        parameters = bempp.api.global_parameters

    return ElementaryBoundaryOperator( \
        adjoint_double_layer_ext(parameters, domain, range_,
                                 dual_to_range, "", symmetry),
        parameters=parameters, label=label)


def hypersingular(domain, range_, dual_to_range,
                  label="HYP", symmetry='no_symmetry',
                  parameters=None, use_slp=False):
    """Return the hypersingular boundary operator."""

    import bempp
    from bempp.core.operators.boundary.laplace import hypersingular_ext
    from bempp.api.assembly.boundary_operator import BoundaryOperator
    from bempp.api.assembly import ElementaryBoundaryOperator
    from bempp.api.assembly import LocalBoundaryOperator

    if parameters is None:
        parameters = bempp.api.global_parameters

    if domain != dual_to_range and use_slp:
        print("Compound assembly based on slp operator requires 'domain' and 'dual_to_range' space to be identical." +
              " Switching to standard assembly.")
        use_slp = False

    if not use_slp:
        return ElementaryBoundaryOperator( \
            hypersingular_ext(parameters, domain, range_,
                              dual_to_range, label, symmetry),
            parameters=parameters, label=label)
    else:
        if not isinstance(use_slp, BoundaryOperator):
            new_domain = domain.discontinuous_space
            new_dual_to_range = dual_to_range.discontinuous_space
            slp = single_layer(new_domain, range_, new_dual_to_range, parameters=parameters)
        else:
            slp = use_slp

        # Test that the spaces are correct.
        if slp.domain != slp.dual_to_range:
            raise ValueError("'domain' and 'dual_to_range' spaces must be identical for the slp operator.")

        # Now generate the compound operator

        test_local_ops = []
        trial_local_ops = []

        from bempp.api.assembly.boundary_operator import CompoundBoundaryOperator
        from bempp.core.operators.boundary.sparse import curl_value_ext

        for index in range(3):
            # Definition of range_ does not matter in next operator
            test_local_op = LocalBoundaryOperator(curl_value_ext(slp.dual_to_range, range_, dual_to_range, index),
                label='CURL')
            test_local_ops.append(test_local_op)
            trial_local_ops.append(test_local_op.transpose(range_)) # Range parameter arbitrary

        return CompoundBoundaryOperator(test_local_ops, slp, trial_local_ops, label=label)


def interior_calderon_projector(grid, parameters=None):

    import bempp.api
    from bempp.api.assembly import BlockedOperator
    from bempp.api.space import project_operator

    if parameters is None:
        parameters = bempp.api.global_parameters

    blocked_operator = BlockedOperator(2, 2)

    const_space = bempp.api.function_space(grid, "DUAL", 0)
    lin_space = bempp.api.function_space(grid, "P", 1)
    lin_space_bary = bempp.api.function_space(grid, "B-P", 1)
    lin_space_disc_bary = bempp.api.function_space(grid, "B-DP", 1)
    lin_space_disc = bempp.api.function_space(grid.barycentric_grid(), "P", 1)


    slp = bempp.api.operators.boundary.laplace.single_layer(lin_space_disc, lin_space_bary, lin_space_disc,
                                                            parameters=parameters)
    ident1 = bempp.api.operators.boundary.sparse.identity(lin_space_bary, lin_space_bary, const_space)
    ident2 = bempp.api.operators.boundary.sparse.identity(const_space, const_space, lin_space_bary)

    dlp = bempp.api.operators.boundary.laplace.double_layer(lin_space_bary, lin_space_bary, const_space,
                                                            parameters=parameters)

    blocked_operator[0,1] = project_operator(slp, domain=const_space, range_=lin_space_bary,
                                             dual_to_range=const_space)

    blocked_operator[1,0] = (bempp.api.operators.boundary.laplace.hypersingular(\
                             lin_space_bary, const_space, lin_space_bary,
                             use_slp=project_operator(slp, domain=lin_space_disc_bary,
                                                      dual_to_range=lin_space_disc_bary),
                             parameters=parameters))
    blocked_operator[0, 0] = .5 * ident1 - dlp
    blocked_operator[1, 1] = .5 * ident2 + dlp.transpose(const_space)

    return blocked_operator
