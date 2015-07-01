import argparse
import conda_manifest.config
import yaml
import os
from conda_manifest.env_recipes import load_envs
from conda_manifest.sources import load_sources

import conda.resolve


from conda_manifest.build_recipes import compute_source_indices, fixed_get_index, resolve_index


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Create the environment manifest.")
    parser.add_argument("--sources", default='sources.yaml',
                        help="Location of sources.yaml")
    parser.add_argument("--envs", nargs='+', default=['env.specs/*.yaml'],
                        help="Glob pattern of environment yamls.")
    parser.add_argument("--outfile", default='env_{env[name]}.manifest',
                        help=("The output file for the environment manifest. "
                              "Uses python string formatting, with env being "
                              "passed as a named argument."))
    if 1 or conda_manifest.config.DEBUG:
        args = parser.parse_args(['--envs', '../env.specs/lts.yaml',
                                  '--sources', '../sources.yaml'])
    else:
        args = parser.parse_args()

    sources = load_sources(args.sources)
    envs = load_envs(args.envs)

    for env in envs:
        src_index = compute_source_indices(env['sources'])
        index = resolve_index(src_index, env['sources'])

        r = conda.resolve.Resolve(index)
        full_list_of_packages = sorted(r.solve(env['packages']))
        lines = []
        for pkg_name in full_list_of_packages:
            pkg = index[pkg_name]
            lines.append(('{pkg[name]: <20} {pkg[version]: <12} '
                          '{pkg[build]: <12} {pkg[source]}'.format(pkg=pkg)))

        with open(args.outfile.format(env=env), 'w') as fh:
            fh.write('\n'.join(lines))

        repodata_dir = 'indices/index_for_{env[name]}/{plat}'.format(env=env,
                                                                     plat=conda.config.subdir)

        if not os.path.exists(repodata_dir):
            os.makedirs(repodata_dir)
        from conda_build.index import write_repodata
        index = {'info': {}, 'packages': index}
        write_repodata(index, repodata_dir)

