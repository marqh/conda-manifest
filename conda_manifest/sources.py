import conda
import yaml
import os
import subprocess

import shutil

import conda.plan
import conda_build.config

import conda


def load_sources(sources_yaml):
    with open(sources_yaml, 'r') as fh:
        return yaml.safe_load(fh)


def fetch_sources(sources, sources_root):
    """
    Fetch the given sources to the given location.

    """
    for source_name, source in sources.items():
        target = os.path.join(sources_root, source_name)
        if os.path.exists(target):
            shutil.rmtree(target)
        if source.get('git_url') is not None:
            fname = git_source(source['git_url'],
                               conda_manifest.config.GIT_CACHE,
                               target,
                               git_rev=source.get('git_rev', None))
        else:
            fname = os.path.expanduser(source['fn'])
            if not os.path.exists(fname):
                raise IOError('Source does not exist {}'.format(source))
            shutil.copytree(fname, target)


from conda_build.external import find_executable


def git_source(git_url, cache_dir, target_directory, git_rev=None):
    """
    Clone the given git resource into the target directory.
    Caching the git repository in the cache directory.

    This is an adaptation of conda_build.source.git_source.

    """
    git = find_executable('git')
    git_dn = git_url
    if git_rev:
        git_dn += '_{}'.format(git_rev)
    git_dn = git_dn.split(':')[-1].replace('/', '_')
    cache_repo = os.path.join(cache_dir, git_dn)
    if not os.path.exists(os.path.dirname(cache_repo)):
        os.makedirs(os.path.dirname(cache_repo))
    if os.path.isdir(cache_repo):
        subprocess.check_call([git, 'fetch'], cwd=cache_repo)
    else:
        subprocess.check_call([git, 'clone', '--mirror', git_url, cache_repo])

    if os.path.exists(target_directory):
        raise IOError('{} already exists. Remove first.'.format(target_directory))

    subprocess.check_call([git, 'clone', '--recursive', cache_repo, target_directory])
    if git_rev:
        subprocess.check_call([git, 'checkout', git_rev], cwd=target_directory)
    return target_directory


if __name__ == '__main__':
    import conda_manifest.config
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default='sources.yaml',
                        help="Location of sources.yaml")
    if 1 or conda_manifest.config.DEBUG:
        args = parser.parse_args(['--sources', '../sources.yaml'])
    else:
        args = parser.parse_args()

    sources = load_sources(args.sources)

    with conda_manifest.config.managed_stdout():
        fetch_sources(sources, conda_manifest.config.build_root)
