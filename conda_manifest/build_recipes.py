import json
import yaml
from conda_build_missing import build, find_all_recipes, sort_dependency_order
import os

from conda_build.config import config as conda_bld_config
import conda_build
import conda.api

from conda.utils import url_path

from contextlib import contextmanager

import logging

import conda_manifest.core_vn_matrix as vn_matrix


import conda_manifest.config
import argparse

import conda_manifest.config
import conda.config
from conda.api import get_index

from conda_manifest.env_recipes import load_envs
from conda_manifest.sources import load_sources


stdoutlog = logging.getLogger('conda-manager.stdoutlog')



def build_null(meta):
    meta.meta.setdefault('build', {})['script'] = 'echo "Hello!"'
    build(meta, test=False)


def resolve_index(src_indices, env_sources):
    """
    Given the indices for all sources, produce an index with
    filtered packages based on the sources specification.

    """
    pkg_names_handled = []
    index = {}
    for sources in env_sources:
        pkgs_handled_at_this_level = []
        for source in sources:
            for tar_name, pkg_info in src_indices[source].items():
                name = pkg_info['name']
                if name in pkg_names_handled:
                    continue
                pkgs_handled_at_this_level.append(name)
                if tar_name in index:
                    raise ValueError('Conflicting package information for {} '
                                     'from {} and {}.'
                                     ''.format(tar_name,
                                               index[tar_name]['channel'],
                                               pkg_info['channel']))
                index[tar_name] = pkg_info.copy()
                # Put the source into the pkg_info.
                index[tar_name]['source'] = source

        pkg_names_handled.extend(pkgs_handled_at_this_level)
    return index


@contextmanager
def fixed_get_index(desired_index):
    """
    No matter what, get_index should return the desired_index, and nothing else.

    """
    orig_get_index = conda.api.get_index

    def new_get_index(*args, **kwargs):
        return desired_index
    conda.api.get_index = conda_build.build.get_index = new_get_index
    yield
    conda.api.get_index = conda_build.build.get_index = orig_get_index


@contextmanager
def conda_build_croot_for_source(source_name):
    """
    Change the conda build build_root/croot for the lifetime of the context
    manager.

    """
    orig_build_root = conda_bld_config.croot
    conda_bld_config.croot = conda_manifest.config.src_distributions_dir(source_name)
    conda_bld_config.bldpkgs_dir = os.path.join(conda_bld_config.croot,
                                                conda.config.subdir)
    yield
    conda_bld_config.croot = orig_build_root
    conda_bld_config.bldpkgs_dir = os.path.join(conda_bld_config.croot,
                                                conda.config.subdir)


def compute_source_indices(env_sources):
    """Generate a dictionary mapping source name to source index."""
    src_index = {}
    for sources in env_sources:
        for source_name in sources:
            with conda_build_croot_for_source(source_name):
                if os.path.exists(conda_bld_config.bldpkgs_dir):
                    # Get hold of just the built packages.
                    src_urls = [url_path(conda_bld_config.croot)]
                    index = conda.api.get_index(src_urls, prepend=False)
                    src_index[source_name] = index
                else:
                    src_index[source_name] = {}
    return src_index


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Pull together the environment recipes "
                                     "directory.")
    parser.add_argument("--sources", default='sources.yaml',
                        help="Location of sources.yaml")
    parser.add_argument("--envs", nargs='+', default=['env.specs/*.yaml'],
                        help="Glob pattern of environment yamls.")
    if 1 or conda_manifest.config.DEBUG:
        args = parser.parse_args(['--envs', '../env.specs/lts.yaml',
                                  '--sources', '../sources.yaml'])
    else:
        args = parser.parse_args()

    sources = load_sources(args.sources)
    envs = load_envs(args.envs)

    for env in envs:
        env_sources = env['sources']

        orig_build_root = conda_bld_config.croot
        channels = []
        for sources in env_sources:
            for source_name in sources:
                source_build_directory = conda_manifest.config.src_distributions_dir(source_name)
                s = os.path.join(source_build_directory, conda.config.subdir)
                if not os.path.exists(s):
                    os.makedirs(s)
                    import conda_build.index
                    conda_build.index.update_index(s)
                channels.append(url_path(source_build_directory))

        conda.config.rc['channels'] = channels
        print 'Channels:', channels

        env_recipe_dir = conda_manifest.config.env_recipes_dir(env=env)

        metas = list(find_all_recipes([env_recipe_dir]))
        stdoutlog.debug('Found the following recipes:\n{}\n-------------------'
                        ''.format('\n'.join(meta.name() for meta in metas)))

        metas = sort_dependency_order(metas)
        stdoutlog.debug('Metas sorted into the following order:\n{}\n---------'
                        ''.format('\n'.join(meta.name() for meta in metas)))

        src_index = {}

        src_index = compute_source_indices(env_sources)
        index = resolve_index(src_index, env_sources)
        r = conda.resolve.Resolve(index)

        for meta in metas:
            stdoutlog.debug('Starting to look at: ', meta.name())
            with open(os.path.join(meta.path, 'source.json'), 'r') as fh:
                source = json.load(fh)
            source_name = source['name']
            version_matrix = vn_matrix.special_case_version_matrix(meta, index)
#            version_matrix = vn_matrix.filter_cases(version_matrix, index, env['packages'])
            for case in vn_matrix.conda_special_versions(meta, index, version_matrix):
                if meta.dist() + '.tar.bz2' not in src_index[source_name]:
                    stdoutlog.info('Building {} from {}.\n'
                                   ''.format(meta.name(), source_name))
                    with conda_build_croot_for_source(source_name):
                        print conda_bld_config.croot
                        print conda.config.rc['channels']
                        print 'BUILDING IN:', conda_bld_config.croot
                        with conda_manifest.config.pipe_check_call(os.path.join(meta.path,
                                                                               'build.{}.log'.format(conda.config.subdir))):
#                            with fixed_get_index(index):
                            build(meta, channels, test=True)
#                            src_index = compute_source_indices(env_sources)
#                            index = resolve_index(src_index, env_sources)
#                            with fixed_get_index(index):
#                                build(meta, channels, test=True)
                        
                else:
                    stdoutlog.info('Not building {} from {}, as it has already been '
                                   'built.\n'.format(meta.name(), source_name))
