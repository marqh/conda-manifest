import argparse
import conda_manifest.config
import yaml
import os
from conda_manifest.env_recipes import load_envs
from conda_manifest.sources import load_sources

import conda.resolve


from conda_manifest.build_recipes import compute_source_indices, fixed_get_index, resolve_index


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Deploy the given manifest.")
    parser.add_argument("--sources", default='sources.yaml',
                        help="Location of sources.yaml")
    parser.add_argument("manifest", help="The manifest to deploy.")
    parser.add_argument("prefix", help="Where to deploy the manifest.")
    if 1 or conda_manifest.config.DEBUG:
        args = parser.parse_args(['env_lts.manifest', '/downloads/foobar',
                                  '--sources', '../sources.yaml'])
    else:
        args = parser.parse_args()

    sources = load_sources(args.sources)

    manifest = args.manifest
    prefix = args.prefix

    # Map source to a list of canonical package name.
    packages_by_source = {}
    with open(args.manifest, 'r') as fh:
        for line in fh:
            name, version, build_str, source = line.split()
            packages_by_source.setdefault(source, []).append('{}-{}-{}'.format(name, version, build_str))
    print packages_by_source

    import conda.install as ci
    linked = ci.linked(prefix)
    # TODO: Find out what the source of the linked package is!
    print linked

    import conda_manifest.config
    import conda.install as cinstall

    pkgs_dir = '/downloads/manager/pkgs'
    root_env_dir = '/downloads/manager/envs'
    prefix = os.path.join(root_env_dir, 'lts')
    if not os.path.exists(pkgs_dir):
        os.makedirs(pkgs_dir)

    for_installation = [pkg
                        for packages in packages_by_source.values()
                        for pkg in packages]

    # Extract the pkgs if they haven't already been extracted.
    for source_name, packages in packages_by_source.items():
        src_distro_dir = conda_manifest.config.src_distributions_dir(source_name)
        for dist in packages:
            dist_tar = os.path.join(src_distro_dir,
                                    conda.config.subdir,
                                    dist) + '.tar.bz2'
            if not os.path.exists(dist_tar):
                raise IOError('Could not find {} at ({})\n'
                              'It may be that the content is out of synch. '
                              'Have you run a build of this environment?\n'
                              "One of the designs of the conda-manager is "
                              'that a MANIFEST does not guarantee that all '
                              'of the distributions \nhave come from the existing '
                              "recipes (particularly if a recipe's version has "
                              "been decreased).".format(dist, dist_tar))
            src_pkgs = os.path.join(pkgs_dir, source_name)
            if not os.path.exists(src_pkgs):
                os.makedirs(src_pkgs)
            if not cinstall.is_extracted(src_pkgs, dist):
                placed_dist_file = os.path.join(src_pkgs, dist + '.tar.bz2')
                if not os.path.exists(placed_dist_file):
                    import shutil
                    shutil.copy(dist_tar, placed_dist_file)
                cinstall.extract(src_pkgs, dist)
                # Tidy up immediately by removing the distribution.
                os.remove(placed_dist_file)

    # Remove any packages which are no longer needed.
    for dist in ci.linked(prefix):
        if dist not in for_installation:
            cinstall.unlink(prefix, dist)

    # Install the packages.
    for source_name, packages in packages_by_source.items():
        src_distro_dir = conda_manifest.config.src_distributions_dir(source)
        for dist in packages:
            src_pkgs = os.path.join(pkgs_dir, source_name)
            cinstall.link(src_pkgs, prefix, dist)
