#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
import os
from thegram import reference_files

print(dir(reference_files))


class ReferenceFiles(unittest.TestCase):

    def test_reference_file(self):
        for filename in os.listdir(reference_files.folder):
            if not filename[-4:-1] == '.rf':
                continue
            path = os.path.join(reference_files.folder, filename)
            out = reference_files.reference_file(path)

    def list_reference_files(self):
        r = reference_files.list_reference_files()
        self.assertIn('copper_diffusivity.rf3', r)
        self.assertIn('copper_density.rf2', r)
        self.assertIn('copper_specificheat.rf1', r)
        for g in range(5):
            r = reference_files.list_reference_files(g)
            self.assertEqual(set([e[-4:] for e in r]).pop(), '.rf' + str(g))

    def test_class_ReferenceFile(self):
        r = reference_files.ReferenceFile('copper_specificheat.rf1')
        self.assertEqual(r.name, 'copper_specificheat.rf1')
        self.assertEqual(r.title, 'Copper Specific Heat')
        self.assertEqual(r.Tmax, 800)
        self.assertEqual(r(400), 423)
        self.assertEqual(r(425), 425)

    def test_poly(self):
        r = reference_files.ReferenceFile('copper_density.rf2')
        d = r(400)
        self.assertLess(d, 8968.782227)
        self.assertEqual(d, 8777.8558606)

        # 0th
        self.assertEqual(r._poly(1, 400), 8968.782227)
        self.assertEqual(r._poly(1, 500), 8968.782227)
        # 1th
        self.assertEqual(r._poly(2, 0), 8968.782227)
        self.assertAlmostEqual(r._poly(2, 100), 8968.782227-44.4428)
        # 2th
        self.assertEqual(r._poly(3, 0), 8968.782227)
        self.assertAlmostEqual(r._poly(3, 100), 8968.782227-44.4428-0.8221979)       


if __name__ == "__main__":
    unittest.main(verbosity=2)
