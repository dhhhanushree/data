# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A script to process FBI Hate Crime table 5 publications."""
import os
import sys
import tempfile
import csv
import json
import pandas as pd

from absl import app
from absl import flags

# Allows the following module imports to work when running as a script
_SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_SCRIPT_PATH, '..'))  # for utils

import utils

flags.DEFINE_string(
    'output_dir', _SCRIPT_PATH, 'Directory path to write the cleaned CSV and'
    'MCF. Default behaviour is to write the artifacts in the current working'
    'directory.')
flags.DEFINE_bool(
    'gen_statvar_mcf', False, 'Generate MCF of StatVars. Default behaviour is'
    'to not generate the MCF file.')
_FLAGS = flags.FLAGS

_YEAR_INDEX = 0

# Columns in final cleaned CSV
_OUTPUT_COLUMNS = ('Year', 'StatVar', 'Quantity')

# A config that maps the year to corresponding xls file with args to be used
# with pandas.read_excel()
_YEARWISE_CONFIG = {
    '2020': {
        'type': 'xls',
        'path': '../source_data/2020/table_5.xlsx',
        'args': {
            'header': 6,
            'skipfooter': 2,
            'usecols': list(range(0, 14))
        }
    },
    '2019': {
        'type': 'xls',
        'path': '../source_data/2019/table_5.xls',
        'args': {
            'header': 5,
            'skipfooter': 2,
            'usecols': list(range(0, 14))
        }
    },
    '2018': {
        'type': 'xls',
        'path': '../source_data/2018/table_5.xls',
        'args': {
            'header': 5,
            'skipfooter': 2,
            'usecols': list(range(0, 14))
        }
    },
    '2017': {
        'type': 'xls',
        'path': '../source_data/2017/table_5.xls',
        'args': {
            'header': 5,
            'skipfooter': 2,
            'usecols': list(range(0, 14))
        }
    },
    '2016': {
        'type': 'xls',
        'path': '../source_data/2016/table_5.xls',
        'args': {
            'header': 5,
            'skipfooter': 2,
            'usecols': list(range(0, 14))
        }
    },
    '2015': {
        'type': 'xls',
        'path': '../source_data/2015/table_5.xls',
        'args': {
            'header': 5,
            'skipfooter': 2,
            'usecols': list(range(0, 14))
        }
    },
    '2014': {
        'type': 'xls',
        'path': '../source_data/2014/table_5.xls',
        'args': {
            'header': 5,
            'skipfooter': 3,
            'usecols': list(range(0, 14))
        }
    },
    '2013': {
        'type': 'xls',
        'path': '../source_data/2013/table_5.xls',
        'args': {
            'header': 5,
            'skipfooter': 3,
            'usecols': list(range(0, 14))
        }
    },
    '2012': {
        'type': 'xls',
        'path': '../source_data/2012/table_5.xls',
        'args': {
            'header': 5,
            'skipfooter': 1
        }
    },
    '2011': {
        'type': 'xls',
        'path': '../source_data/2011/table_5.xls',
        'args': {
            'header': 4,
            'skipfooter': 1
        }
    },
    '2010': {
        'type': 'xls',
        'path': '../source_data/2010/table_5.xls',
        'args': {
            'header': 3,
            'skipfooter': 1
        }
    },
    '2009': {
        'type': 'xls',
        'path': '../source_data/2009/table_5.xls',
        'args': {
            'header': 3,
            'skipfooter': 1
        }
    },
    '2008': {
        'type': 'xls',
        'path': '../source_data/2008/table_5.xls',
        'args': {
            'header': 3,
            'skipfooter': 1
        }
    },
    '2007': {
        'type': 'xls',
        'path': '../source_data/2007/table_5.xls',
        'args': {
            'header': 3,
            'skipfooter': 1
        }
    },
    '2006': {
        'type': 'xls',
        'path': '../source_data/2006/table_5.xls',
        'args': {
            'header': 3,
            'skipfooter': 1
        }
    },
    '2005': {
        'type': 'xls',
        'path': '../source_data/2005/table_5.xls',
        'args': {
            'header': 3,
            'skipfooter': 1
        }
    },
    '2004': {
        'type': 'xls',
        'path': '../source_data/2004/table_5.xls',
        'args': {
            'header': 3,
            'skipfooter': 1
        }
    }
}


def _write_row(year: int, statvar_dcid: str, quantity: str,
               writer: csv.DictWriter):
    """A wrapper to write data to the cleaned CSV."""
    processed_dict = {
        'Year': year,
        'StatVar': statvar_dcid,
        'Quantity': quantity
    }
    writer.writerow(processed_dict)


def _write_output_csv(reader: csv.DictReader, writer: csv.DictWriter,
                      config: dict) -> list:
    """Reads each row of a CSV and creates statvars for counts of
    Incidents, Offenses, Victims and Known Offenders with different bias
    motivations.

    Args:
        reader: CSV dict reader.
        writer: CSV dict writer of final cleaned CSV.
        config: A dict which maps constraint props to the statvar based on
          values in the CSV. See scripts/fbi/hate_crime/table2/config.json for
          an example.

    Returns:
        A list of statvars.
    """
    statvars = []
    columns = list(reader.fieldnames)
    columns.remove('bias motivation')
    columns.remove('Year')
    for crime in reader:
        bias_motivation = crime['bias motivation']
        bias_motivation_key_value = config['pvs'][bias_motivation]

        statvar_list = []
        for c in columns:
            statvar = {**config['populationType'][c]}
            statvar_list.append(statvar)

        utils.update_statvars(statvar_list, bias_motivation_key_value)
        utils.update_statvar_dcids(statvar_list, config)

        for idx, c in enumerate(columns):
            if crime[c] != '':
                _write_row(crime['Year'], statvar_list[idx]['Node'], crime[c],
                           writer)

        statvars.extend(statvar_list)

    return statvars


def _clean_dataframe(df: pd.DataFrame, year: str):
    """Clean the column names and offense type values in a dataframe."""
    if year in ['2020', '2019', '2018', '2017', '2016', '2015', '2014', '2013']:
        df.columns = [
            'bias motivation', 'total offenses', 'white',
            'black or african american', 'american indian or alaska native',
            'asian', 'native hawaiian or other pacific islander',
            'multiple races', 'unknown race', 'hispanic or latino',
            'not hispanic or latino', 'group of multiple ethnicities',
            'unknown ethnicity', 'unknown offender'
        ]
    else:  # 2012, 2011, 2010, 2009, 2008, 2007, 2006, 2005, 2004
        df.columns = [
            'bias motivation', 'total offenses', 'white',
            'black or african american', 'american indian or alaska native',
            'asian or pacific islander', 'multiple races', 'unknown race',
            'unknown offender'
        ]

    df['bias motivation'] = df['bias motivation'].replace(r'[\d:]+',
                                                          '',
                                                          regex=True)
    df['bias motivation'] = df['bias motivation'].replace(r'\s+',
                                                          ' ',
                                                          regex=True)
    df['bias motivation'] = df['bias motivation'].str.strip()
    return df


def main(argv):
    csv_files = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        for year, config in _YEARWISE_CONFIG.items():
            xls_file_path = os.path.join(_SCRIPT_PATH, config['path'])
            csv_file_path = os.path.join(tmp_dir, year + '.csv')

            read_file = pd.read_excel(xls_file_path, **config['args'])
            read_file = _clean_dataframe(read_file, year)
            read_file.insert(_YEAR_INDEX, 'Year', year)
            read_file.to_csv(csv_file_path, header=True, index=False)
            csv_files.append(csv_file_path)

        config_path = os.path.join(_SCRIPT_PATH, 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        cleaned_csv_path = os.path.join(_FLAGS.output_dir, 'cleaned.csv')
        statvars = utils.create_csv_mcf(csv_files, cleaned_csv_path, config,
                                        _OUTPUT_COLUMNS, _write_output_csv)
        if _FLAGS.gen_statvar_mcf:
            mcf_path = os.path.join(_FLAGS.output_dir, 'output.mcf')
            utils.create_mcf(statvars, mcf_path)


if __name__ == '__main__':
    app.run(main)
