<%
from bempp_operators import bops, dtypes, compatible_dtypes
ifloop = lambda x: "if" if getattr(x, 'index', x) == 0 else "elif"
module_name  = lambda x, y: '.'.join([x] + [u for u in y if len(u) > 0]) 
%>
<%def name="create_module(name, desc)"%>
%   for submod in sorted(set([u['location'] for u in bops.itervalues])):
        ${module_name(name, submod)} = ModuleType("${submod[-1]}",
                "${bops[submod]}"
        )
%   endfor
%   for key, desc in bops.iteritems():
        ${'.'.join([name][key])} = self.${value['py_creator']}
%   endfor
</%def>

<%def name="create_operator(py_creator, c_creator, doc, **kwargs)">
    def ${py_creator}(self, ${'\\'}
        Space domain, Space range, Space dual_to_range, ${'\\'}
        str label="", int symmetry=0):
        """ ${doc}

            Parameters
            ----------
            domain: Space
                Function space to be taken as the domain of the operator.
            range: Space
                Function space to be taken as the range of the operator.
            dualToRange: Space
                Function space to be taken as the dual to the range of the
                operator.
            label: string
                Textual label of the operator. If not given (default), a unique
                label will be generated automatically.
            symmetry: int
                Defaults to zero.
        """

        # Check space types match this context
        if self.basis_type != range.dtype \
            or self.basis_type != dual_to_range.dtype \
            or self.basis_type != domain.dtype:
                raise TypeError("Incompatible spaces")

        # Creates C accuracy option
        cdef c_AccuracyOptions acc_ops
        self._accuracy.to_cpp(acc_ops)

        result = BoundaryOperator(basis_type=self.basis_type,
                result_type=self.result_type)

        # Loop over possible basis and result type combinations,
        # And call templated function to create the operator
% for i, (pybasis, cybasis) in enumerate(dtypes.iteritems()):
%    for j, (pyresult, cyresult) in enumerate(dtypes.iteritems()):
%       if pyresult in compatible_dtypes[pybasis]:
        ${ifloop(i + j)} self.basis_type == '${pybasis}' ${'\\'}
            and self.result_type == '${pyresult}':
                ${c_creator}[${cybasis}, ${cyresult}](
                    deref(
                        <c_BoundaryOperator[${cybasis}, ${cyresult}]*>
                        result.memory
                    ),
                    acc_ops, self.assembly,
                    domain.impl_${pybasis},
                    range.impl_${pybasis},
                    dual_to_range.impl_${pybasis},
                    label, symmetry
                )
%       endif
%    endfor
% endfor
        else:
            msg = "Unknown or incompatible basis and result types"
            raise RuntimeError(msg)

        return result
</%def>

from libcpp.string cimport string
from cython.operator cimport dereference as deref
from bempp.fiber.accuracy_options cimport c_AccuracyOptions
from bempp.assembly.boundary_operator cimport c_BoundaryOperator
from bempp.assembly.boundary_operator cimport BoundaryOperator
from bempp.options cimport AssemblyOptions, Options
from bempp.space.space cimport Space, c_Space
from bempp.utils cimport shared_ptr

# Declares complex type explicitly.
# Cython 0.20 will fail if templates are nested more than three-deep,
# as in shared_ptr[ c_Space[ complex[float] ] ]
cdef extern from "bempp/space/types.h":
% for ctype in dtypes.itervalues():
%     if 'complex'  in ctype:
    ctypedef struct ${ctype}
%     endif
% endfor

cdef extern from "bempp/assembly/python.hpp":
% for opname, description in bops.iteritems():
%     if description['implementation'] == 'standard':
    c_BoundaryOperator[BASIS, RESULT] \
        ${description['c_creator']}[BASIS, RESULT](
            c_BoundaryOperator[BASIS, RESULT]& _output,
            const c_AccuracyOptions& accuracyOptions,
            const AssemblyOptions& assemblyOptions,
            const shared_ptr[c_Space[BASIS]]& domain,
            const shared_ptr[c_Space[BASIS]]& range,
            const shared_ptr[c_Space[BASIS]]& dualToRange,
            const string& label,
            int symmetry
        )
%     endif
% endfor


cdef class Context(Options):
    cdef:
        ## simplified access to operators
        readonly object operators

    def __init__(self, **kwargs):
        super(Context, self).__init__(**kwargs)

        from types import ModuleType

<%
    allmodules = set([
        u['location'][:i] for u in bops.itervalues() for i in range(1, len(u))
    ])
%>
% for submod in sorted(set([u[:-1] for u in allmodules if len(u) > 1])):
        self.${'.'.join(submod)} = ModuleType("${submod[-1]}",
                "Operator module")
% endfor
% for desc in bops.itervalues():
        self.${'.'.join(desc['location'])} = self.${desc['py_creator']}
% endfor

    def scalar_space(self, grid, *args, **kwargs):
        """ Creates a scalar space

            This is a convenience function for creating scalar spaces. It
            merely avoids refering to the `basis_type`. The input is the same
            as :py:func:`bempp.space.scalar_spaces`, but *without* the `dtypes`
            argument.
        """
        from .. import scalar_space
        return scalar_space(grid, self.basis_type, *args, **kwargs)


% for description in bops.itervalues():
    %     if description['implementation'] == 'standard':
    ${create_operator(**description)}
%     endif
% endfor
