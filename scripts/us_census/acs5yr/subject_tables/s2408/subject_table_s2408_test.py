# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test for S2408 of the subject table."""

import os
import tempfile
import unittest
from .process import set_column_map, process_subject_tables


def _get_paths(table_dir):
    """Gets paths to the spec, CSV, StatVar MCF, Column Map and test zip file.
    Args:
        table_dir: Path to the subject table directory.
          Expected directory structure is (<code> refers to subject table code)
          table_dir
            - <code>_spec.json
            - testdata
                - <code>_output.mcf
                - <code>_cleaned.csv
                - column_map.json
                - test zip file

    Returns:
        A tuple of the paths to the spec, CSV, Stat Var MCF, column map and test
        zip file.
    """
    paths = {}

    # Find spec, Expects spec to be in table_dir
    for filename in os.listdir(table_dir):
        if 'spec.json' in filename:
            paths['spec'] = os.path.join(table_dir, filename)

    # Expects StatVar MCF, Column Map, CSV and test zip to be in testdata folder
    testdata_path = os.path.join(table_dir, 'testdata')
    for filename in os.listdir(testdata_path):
        if 'cleaned.csv' in filename:
            paths['csv'] = os.path.join(testdata_path, filename)
        elif 'output.mcf' in filename:
            paths['mcf'] = os.path.join(testdata_path, filename)
        elif 'column_map.json' in filename:
            paths['cmap'] = os.path.join(testdata_path, filename)
        elif filename.endswith('.zip'):
            paths['zip'] = os.path.join(testdata_path, filename)

    return paths


def _read_files(test_path, expected_path):
    with open(test_path, 'r') as test_f:
        test_result = test_f.read()
    with open(expected_path, 'r') as expected_f:
        expected_result = expected_f.read()
    return test_result, expected_result


class TestSubjectTableS2408(unittest.TestCase):

    def test_csv_mcf_column_map(self):

        script_path = os.path.dirname(os.path.abspath(__file__))
        table_dir_path = os.path.join(script_path, '.')
        paths = _get_paths(table_dir_path)

        # Check if all required files exist
        expected_keys = ['spec', 'csv', 'mcf', 'cmap', 'zip']
        for file_key in expected_keys:
            with self.subTest(table=table_dir_path, file_key=file_key):
                self.assertTrue(file_key in paths)

        with tempfile.TemporaryDirectory() as tmp_dir:
            # generate CSV, MCF and Column Map
            set_column_map(paths['zip'], paths['spec'], tmp_dir)
            process_subject_tables(table_prefix='test',
                                   input_path=paths['zip'],
                                   output_dir=tmp_dir,
                                   column_map_path=os.path.join(
                                       tmp_dir, 'column_map.json'),
                                   spec_path=paths['spec'],
                                   debug=False,
                                   delimiter='!!',
                                   has_percent=True)

            test_mcf_path = os.path.join(tmp_dir, 'test_output.mcf')
            test_cmap_path = os.path.join(tmp_dir, 'column_map.json')
            test_csv_path = os.path.join(tmp_dir, 'test_cleaned.csv')

            with self.subTest(table=table_dir_path):
                # Test StatVar MCF
                test_mcf, expected_mcf = _read_files(test_mcf_path,
                                                     paths['mcf'])
                self.assertEqual(test_mcf, expected_mcf)

                # Test Column Map
                test_cmap, expected_cmap = _read_files(test_cmap_path,
                                                       paths['cmap'])
                self.assertEqual(test_cmap, expected_cmap)

                # Test CSV
                test_csv, expected_csv = _read_files(test_csv_path,
                                                     paths['csv'])
                self.assertEqual(test_csv, expected_csv)
