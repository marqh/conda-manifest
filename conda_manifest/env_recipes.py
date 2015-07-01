import yaml
import os
import glob

import shutil
import json

from conda.resolve import Resolve, MatchSpec
from copy import deepcopy

from conda_build_missing import find_all_recipes

from conda_manifest.sources import load_sources


def load_env(env_yaml):
    with open(env_yaml, 'r') as fh:
        return yaml.safe_load(fh)


def load_envs(environment_globs):
    envs = []
    for pattern in environment_globs:
        for fname in glob.glob(pattern):
            envs.append(load_env(fname))
    if not envs:
        raise IOError('No environment specs found.')
    return envs


def filter_packages(env_sources, env_specs, source_metas):
    """
    Figure out which packages are needed, given the env specs, and
    critically, which source each package comes from.

    Parameters
    ----------
    env_sources - list of lists of sources
        The names of the sources. The nested list structure allows a
        heirachy of precedence. For instance, supposing both a and b
        provided a recipe for 'foobar', if env_sources were
        ``[['a', 'b']]`` both recipes would be returned, essentially
        allowing conda to resolve the presenence. If env_sources were
        ``[['a'], ['b']]`` then only foobar from 'a' would be allowed.
    env_specs - list of specifications
        The specification for the environment. These will be cast to
        MatchSpecs, as per usual conda specifications.
    source_metas - dict mapping source name to list of conda metas
        The metas (recipes) that each source provides.

    Returns
    -------
    which_packages_to_use - dict
        A dictionary mapping package name, to a list of
        (src_name, meta) pairs. All dependencies of env_specs are
        traversed, and every dependency which is resolvable will have
        been resolved. If a dependency is listed for which there is no source,
        the algorithm will continue without the missing dependency.

    """
    source_meta_names = {src: [meta.name() for meta in metas]
                         for src, metas in source_metas.items()}
    where_from = {}
    specs = deepcopy(env_specs)
    while specs:
        package = specs.pop()
        name = MatchSpec(package).name
        for sources in env_sources:
            if name in where_from:
                break
            for source in sources:
                # n.b. all sources here should have an equal standing on
                # whether a package is included, so no breaks within this loop.

                if name in source_meta_names[source]:
                    metas = [meta for meta in source_metas[source]
                             if meta.name() == name]
                    for meta in metas:
                        all_deps = (tuple(meta.get_value('requirements/run', ())) +
                                    tuple(meta.get_value('requirements/build', ())))
                        # Put any missing deps in as specs.
                        for dep in all_deps:
                            dep_name = MatchSpec(dep).name
                            if dep_name not in where_from:
                                specs.append(dep)
                        where_from.setdefault(name, []).append((source, meta))
    return where_from


def create_env_recipes(pkgs, location):
    """
    Create a clean directory of all the recipes in the source metas.

    Parameters
    ----------
    pkgs - dict
        The metas, such as those from :func:`which_metas`.
        pkgs is a dictionary mapping package name to an iterable of
        (src_name, meta) pairs.
    target_location - str
        Where the clean directory of recipes should be placed. If the
        directory already exists, it will be emptied before proceeding.

    """
    if os.path.exists(location):
        shutil.rmtree(location)
    os.mkdir(location)

    # Turn this information into a single place for all of the recipes.
    for pkg_name, sources in pkgs.items():
        for src_name, meta in sources:
            link_locn = os.path.join(location, '{}_{}'.format(src_name,
                                                              meta.dist()))
            if os.path.exists(link_locn):
                raise ValueError('{} has multiple recipes for {}'
                                 ''.format(src_name, meta.dist()))
            os.symlink(meta.path, link_locn)
            with open(os.path.join(link_locn, 'source.json'), 'w') as fh:
                # TODO: Make this repeatable information (full URL, tag etc.)
                json.dump({'name': src_name}, fh)


def source_metas(sources):
    """
    Given the sources, return a dictionary of all conda recipes
    keyed by source name.

    """
    # Map source name to location of source.
    source_dict = {source_name: os.path.join(conda_manifest.config.build_root,
                                             source_name)
                   for source_name, source in sources.items()}
    # Map source name to all metas within the source.
    source_metas = {src: list(find_all_recipes([source_dict[src]]))
                    for src in sources}
    return source_metas


if __name__ == '__main__':
    import conda_manifest.config
    import glob
    import argparse

    parser = argparse.ArgumentParser("Pull together the environment recipes "
                                     "directory.")
    parser.add_argument("--sources", default='sources.yaml',
                        help="Location of sources.yaml")
    parser.add_argument("--envs", nargs='+', default=['env.specs/*.yaml'],
                        help="Glob pattern of environment yamls.")
    if 1 or conda_manifest.config.DEBUG:
        args = parser.parse_args(['--envs', '../env.specs/*.yaml',
                                  '--sources', '../sources.yaml'])
    else:
        args = parser.parse_args()

    
    sources = load_sources(args.sources)

    envs = load_envs(args.envs)

    with conda_manifest.config.managed_stdout():
        for env in envs:
            env_recipe_dir = conda_manifest.config.env_recipes_dir(env=env)
            print("Creating {}'s environment recipes in {}"
                  "".format(env['name'], env_recipe_dir))
            pkgs = filter_packages(env['sources'], env['packages'],
                                   source_metas(sources))
            create_env_recipes(pkgs, env_recipe_dir)
