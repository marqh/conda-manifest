import conda
import yaml
import os
from subprocess import check_call

import shutil

with open('sources.yaml', 'r') as fh:
    sources = yaml.safe_load(fh)


with open('env.specs/lts.yaml', 'r') as fh:
    env_lts = yaml.safe_load(fh)


print sources
print env_lts


import conda.plan
import conda_build.config

import conda


from conda.api import get_index
from conda.fetch import fetch_repodata

url = 'file:///data/local/itpe/miniconda/conda-builds-scientific_software_stack_since_05_15/linux-64/'
repo = fetch_repodata(url)

from conda.resolve import Resolve, MatchSpec

print repo

r = Resolve(repo['packages'])
r.solve(env_lts['packages'], features=set())

r.solve2(env_lts['packages'], features=set())

# conda.api.fetch_repodata is the underlying index loader.



#index = get_index(channel_urls=channel_urls,
#                              prepend=not args.override_channels,
#                              use_cache=args.use_index_cache,
#                              unknown=args.unknown,
#                              json=args.json,
#                              offline=args.offline)


from conda.resolve import MatchSpec

fn = 'numpy-1.8.3-py27_0.tar.bz2'

ms = MatchSpec('numpy >=1.7,<1.9')

print ms.match(fn)

#for name in orig_packages:
#    pkgs = sorted(r.get_pkgs(MatchSpec(name)))

