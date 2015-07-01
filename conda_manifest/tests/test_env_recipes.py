import unittest

from conda_manifest.filter_recipes import filter_packages
from conda_manifest.tests import DummyPackage


class Test_resolve_recipes(unittest.TestCase):
    def setUp(self):
        self.pkgs = {'a': DummyPackage('a', [], ['b']),
                     'b': DummyPackage('b', ['c']),
                     'c': DummyPackage('c'),
                     'b_alt': DummyPackage('b', ['c', 'd']),
                     'd': DummyPackage('d')}

    def test_linear_src(self):
        # ac takes precedence over cd, so any recipes found in the former
        # would be picked over those of the former.
        a, b, c, d = [self.pkgs[name] for name in 'abcd']
        src_metas = {'ab': [a, b], 'cd': [a, c, d]}

        r = filter_packages(env_sources=[['ab'], ['cd']],
                            env_specs=['a'],
                            source_metas=src_metas)
        self.assertEqual(r, {'a': [('ab', a)],
                             'b': [('ab', b)],
                             'c': [('cd', c)]})

    def test_paired_src(self):
        # ab and cd have equal importance, and so a should be being built from
        # both ac and cd.
        a, b, c, d = [self.pkgs[name] for name in 'abcd']
        src_metas = {'ab': [a, b], 'cd': [a, c, d]}

        r = filter_packages(env_sources=[['ab', 'cd']],
                            env_specs=['a'],
                            source_metas=src_metas)
        self.assertEqual(r, {'a': [('ab', a), ('cd', a)],
                             'b': [('ab', b)],
                             'c': [('cd', c)]})

    def test_paired_src_alternative(self):
        a, b, c, d = [self.pkgs[name] for name in 'abcd']
        b_alt = self.pkgs['b_alt']
        src_metas = {'ab': [a, b], 'b_alt_d': [b_alt, c, d]}

        r = filter_packages(env_sources=[['ab', 'b_alt_d']],
                            env_specs=['a'],
                            source_metas=src_metas)
        self.assertEqual(r, {'a': [('ab', a)],
                             'b': [('ab', b),
                                   ('b_alt_d', b_alt)],
                             'c': [('b_alt_d', c)],
                             'd': [('b_alt_d', d)]})

    def test_unresolvable(self):
        a = self.pkgs['a']
        src_metas = {'ab': [a]}

        r = filter_packages(env_sources=[['ab']],
                            env_specs=['a'],
                            source_metas=src_metas)
        self.assertEqual(r, {'a': [('ab', a)]})


if __name__ == '__main__':
    unittest.main()
