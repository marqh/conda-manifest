import conda.resolve
from conda.resolve import MatchSpec
import conda_build.config
import conda_manifest.config


def conda_special_versions(meta, index, version_matrix=None):
    """
    Returns a generator which configures conda build's PY and NPY versions
    according to the given version matrix. If no version matrix is given, it
    will be computed by :func:`special_case_version_matrix`.

    """
    if version_matrix is None:
        version_matrix = special_case_version_matrix(meta, index)

    for case in version_matrix:
        for pkg, version in case:
            version = int(version.replace('.', ''))
            if pkg == 'python':
                conda_build.config.config.CONDA_PY = version
            elif pkg == 'numpy':
                conda_build.config.config.CONDA_NPY = version
            else:
                raise NotImplementedError('Package {} not yet implemented.'
                                          ''.format(pkg))
        yield case


def special_case_version_matrix(meta, index):
    """
    Return the non-orthogonal version matrix for special software within conda
    (numpy, python).

    For example, supposing there was a numpy 1.8 & 1.9 for python 2.7,
    but only a numpy 1.9 for python 3.5, the matrix should be:

        ([('python', '2.7.0'), ('numpy', '1.8.0')],
         [('python', '2.7.0'), ('numpy', '1.9.0')],
         [('python', '3.5.0'), ('numpy', '1.9.0')])

    Packages which don't depend on any of the special cases will return an
    iterable with an empty list, so that code such as:

    for case in special_case_version_matrix(...):
        ... setup the case ...
        ... build ...

    can be written provided that the process which handles the cases can handle
    an empty list.

    .. note::

        This algorithm does not deal with PERL and R versions at this time.

    """
    r = conda.resolve.Resolve(index)
    requirements = meta.get_value('requirements/build', [])
    requirement_specs = {MatchSpec(spec).name: MatchSpec(spec)
                         for spec in requirements}

    def minor_vn(version_str):
        """
        Take an string of the form 1.8.2, into integer form 1.8
        """
        return '.'.join(version_str.split('.')[:2])

    cases = []
    if 'numpy' in requirement_specs:
        np_spec = requirement_specs.pop('numpy')
        for numpy_pkg in r.get_pkgs(np_spec):
            np_vn = minor_vn(index[numpy_pkg.fn]['version'])
            numpy_deps = index[numpy_pkg.fn]['depends']
            numpy_deps = {MatchSpec(spec).name: MatchSpec(spec)
                          for spec in numpy_deps}
            for python_pkg in r.get_pkgs(numpy_deps['python']):
                # XXX Get the python spec here too...?
                py_vn = minor_vn(index[python_pkg.fn]['version'])
                cases.append((('python', py_vn),
                              ('numpy', np_vn),
                              ))
    elif 'python' in requirement_specs:
        py_spec = requirement_specs.pop('python')
        for python_pkg in r.get_pkgs(py_spec):
            py_vn = minor_vn(index[python_pkg.fn]['version'])
            cases.append((('python', py_vn),
                          ))

    if 'perl' in requirement_specs:
        raise NotImplementedError('PERL version matrix not yet implemented.')
    if 'r' in requirement_specs:
        raise NotImplementedError('R version matrix not yet implemented.')

    cases = list(filter_cases(cases, index, requirement_specs.keys()))

    # Put an empty case in to allow simple iteration of the results.
    if not cases:
        cases.append(())
    return set(cases)


def filter_cases(cases, index, extra_specs=None):
    r = conda.resolve.Resolve(index)
    for case in cases:
        specs = ['{} {}.*'.format(pkg, version) for pkg, version in case]
        try:
            specs = extra_specs + ['{} {}.*'.format(pkg, version)
                                   for pkg, version in case]
            print specs, index.keys()
            r.solve(specs)
            yield case
        except SystemExit as err:
            # Output the useful message along the lines of "the following
            # packages conflict with each other".
            conda_manifest.config.stdout.debug(str(err) + '\n')
