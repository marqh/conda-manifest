import unittest

from conda_manifest.build_recipes import resolve_index
from conda_manifest.tests import DummyPackage, DummyIndex


class Test_resolve_index(unittest.TestCase):
    def setUp(self):
        self.pkgs = {'a': DummyPackage('a', [], ['b']),
                     'b': DummyPackage('b', ['c']),
                     'c': DummyPackage('c'),
                     'b_alt': DummyPackage('b', ['c', 'd']),
                     'd': DummyPackage('d')}

    def pkg_index(self, packages, version='0.1', source=None, index=None):
        if index is None:
            index = DummyIndex()
        for pkg in packages:
            if source is not None:
                kwargs = {'source': source}
            else:
                kwargs = {}
            index.add_pkg(pkg.name(), version, depends=pkg.run_deps, **kwargs)
        return index

    def test_combining_of_source_different_level(self):
        # a should be removed from the cd source, as they live at
        # a different sources level.
        a, b, c, d = [self.pkgs[name] for name in 'abcd']
        src_indices = {'ab': self.pkg_index([a, b]),
                       'cd': self.pkg_index([a, c, d])}

        result = resolve_index(src_indices, env_sources=[['ab'], ['cd']])

        ab_index = self.pkg_index([a, b], source='ab')
        cd_index = self.pkg_index([c, d], source='cd')
        expected_index = cd_index
        expected_index.update(ab_index)

        self.assertEqual(result, expected_index)

    def test_combining_of_source_same_level_identical_packages(self):
        # a is in both ab and cd, and they produce the same level.
        a, b, c, d = [self.pkgs[name] for name in 'abcd']
        src_indices = {'ab': self.pkg_index([a, b], source='ab'),
                       'cd': self.pkg_index([a, c, d], source='cd')}

        with self.assertRaises(ValueError):
            resolve_index(src_indices, env_sources=[['ab', 'cd']])

    def test_combining_of_source_same_level(self):
        # a should be in both ab and cd source, as they live at
        # the same sources level.
        a, b, c, d = [self.pkgs[name] for name in 'abcd']
        src_indices = {'ab': self.pkg_index([a, b], source='ab'),
                       'cd': self.pkg_index([c, d], source='cd')}
        self.pkg_index([a], version='0.2', index=src_indices['cd'])

        result = resolve_index(src_indices, env_sources=[['ab', 'cd']])

        ab_index = self.pkg_index([a, b], source='ab')
        cd_index = self.pkg_index([c, d], source='cd')
        expected_index = cd_index
        expected_index.update(ab_index)
        self.pkg_index([a], version='0.2', source='cd', index=expected_index)

        self.assertEqual(result.keys(), expected_index.keys())
        self.assertEqual(result, expected_index)


if __name__ == '__main__':
    unittest.main()
