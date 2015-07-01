import logging
import os
import sys

from conda_build.config import config as conda_bld_config


DEBUG = True
VERBOSE = False

manager_root = os.path.join(conda_bld_config.croot, 'conda-manager')
build_root = os.path.join(manager_root, 'recipe_sources')
#build_root = '/net/home/h02/itpe/dev/stash/scientificsoftwarestack/conda-manager/buildroot'


def env_recipes_dir(env):
    return os.path.join(build_root, 'env_{env[name]}_recipes').format(env=env)


def src_distributions_dir(source_name):
    """The build root for a given source."""
    return os.path.join(os.path.dirname(conda_bld_config.croot),
                        'conda-manager', source_name)


GIT_CACHE = os.path.join(manager_root, 'cache', 'git_cache')

# Override the conda logging handlers.
import conda.fetch
import conda.resolve
from conda.console import SysStdoutWriteHandler


if not os.path.exists(manager_root):
    os.makedirs(manager_root)

if not DEBUG:
    hdlr = logging.FileHandler(os.path.join(manager_root,
                                            'manager.{}.log'
                                            ''.format(os.getpid())))
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)

    loggers = ['progress', 'progress.start', 'progress.update',
               'progress.stop', 'stdoutlog', 'stderrlog',
               'conda.resolve', 'dotupdate']

    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARN)
        logger.handlers = [hdlr]


stdout = logging.getLogger('conda-manager.stdoutlog')
stdout.addHandler(SysStdoutWriteHandler())
if DEBUG:
    stdout.setLevel(logging.DEBUG)
elif VERBOSE:
    stdout.setLevel(logging.INFO)
else:
    stdout.setLevel(logging.WARN)


from contextlib import contextmanager
import subprocess


@contextmanager
def pipe_check_call(fname):
    with open(fname, 'w') as fh:
        orig = subprocess.check_call
        notified = [False]
        def new_check_call(*args, **kwargs):
            if not notified[0]:
                print('Piping output to {}'.format(fname))
                notified[0] = True
            kwargs.setdefault('stdout', fh)
            kwargs.setdefault('stderr', fh)
            return orig(*args, **kwargs)
        subprocess.check_call = new_check_call
        yield
    subprocess.check_call = orig


@contextmanager
def managed_stdout():
    if DEBUG:
        yield
    else:
        with pipe_check_call(os.path.join(manager_root, 'run.log')):
            yield
