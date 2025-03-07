# Copyright 2024 Google LLC
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
"""
This Python Script Load the datasets, cleans it and generates 
cleaned CSV, MCF, TMCF file.
"""
import os
import pandas as pd
import numpy as np

import requests
import shutil
import time
import json
from absl import logging

from absl import app
from absl import flags
from national_1900_1959 import national1900
from national_1960_1979 import national1960
from national_1980_1989 import national1980
from national_2000_2010 import national2000
from national_2010_2019 import national2010
from national_2020_2029 import national2029
from state_1970_1979 import state1970
from state_1990_2000 import state1990
from state_2000_2010 import state2000
from state_2010_2020 import state2010
from state_2020_2029 import state2029
from county_1970_1979 import county1970
from county_1980_1989 import county1980
from county_1990_2000 import county1990
from county_2000_2010 import county2000
from county_2010_2020 import county2010
from county_2020_2029 import county2029

FLAGS = flags.FLAGS
DEFAULT_INPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "input_data")
flags.DEFINE_string('mode', '', 'Options: download or process')
flags.DEFINE_string("input_path", DEFAULT_INPUT_PATH, "Import Data File's List")
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_INPUT_FILE_PATH = os.path.join(_MODULE_DIR, 'input_files')
_FILES_TO_DOWNLOAD = []


# This method will generate URLs for the years 2020 to 2029
def add_future_year_urls():
    global _FILES_TO_DOWNLOAD
    urls_to_scan = [
        "https://www2.census.gov/programs-surveys/popest/datasets/2020-{YEAR}/counties/asrh/cc-est{YEAR}-alldata.csv",
        "https://www2.census.gov/programs-surveys/popest/datasets/2020-{YEAR}/national/asrh/nc-est{YEAR}-agesex-res.csv",
        "https://www2.census.gov/programs-surveys/popest/datasets/2020-{YEAR}/state/asrh/sc-est{YEAR}-alldata6.csv"
    ]
    #To check the latest available year
    for url in urls_to_scan:
        for YEAR in range(2030, 2020, -1):
            url_to_check = url.format(YEAR=YEAR)
            try:
                check_url = requests.head(url_to_check)
                if check_url.status_code == 200:
                    _FILES_TO_DOWNLOAD.append({"download_path": url_to_check})
                    break

            except:
                logging.error(f"URL is not accessable {url_to_check}")


MCF_TEMPLATE = ("Node: dcid:{pv1}\n"
                "typeOf: dcs:StatisticalVariable\n"
                "populationType: dcs:Person{pv2}{pv3}{pv4}\n"
                "statType: dcs:measuredValue\n"
                "measuredProperty: dcs:count\n")

TMCF_TEMPLATE = ("Node: E:usa_population_asr->E0\n"
                 "typeOf: dcs:StatVarObservation\n"
                 "variableMeasured: C:usa_population_asr->SVs\n"
                 "measurementMethod: C:usa_population_asr->Measurement_Method\n"
                 "observationAbout: C:usa_population_asr->geo_ID\n"
                 "observationDate: C:usa_population_asr->Year\n"
                 "observationPeriod: \"P1Y\"\n"
                 "value: C:usa_population_asr->observation\n")


def _measurement_conditions(x: str, y: str) -> str:
    """
    Divides the Races before and after 2000, by using different measurement
    methods.

    Args:
        x (str) : String from DataFrame Values in a Column.
        x (str) : String from DataFrame Values in a Column.
    Returns:
        str
    """
    if (not x.lower().endswith('male')) and y >= 2000:
        return "_Race2000Onwards"
    elif (not x.lower().endswith('male')) and y < 2000:
        return "_RaceUpto1999"
    else:
        return ""


def _measurement_aggregate(df: pd.DataFrame) -> list:
    """
    Checks for aggregations done and makes all the years of that race and area
    as Aggregated

    Args:
        df (Pandas Dataframe) : Divided Dataframe to check
    Returns:
        list
    """
    derived_df = df[df['Measurement_Method'].str.contains('dcAggregate')]
    aggregated_rows = list(derived_df['SVs'] + derived_df['geo_ID'])
    df['info'] = df['SVs'] + df['geo_ID']
    aggregate_list = np.where(df['info'].isin(aggregated_rows),
                              'dcAggregate/CensusPEPSurvey_PartialAggregate',
                              'CensusPEPSurvey')
    df.drop(columns=['info'], inplace=True)
    return aggregate_list.tolist()


def _measurement_method(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates measurement method based on provided guidelines.

    Args:
        df (Pandas Dataframe) : Dataframe to add columns
    Returns:
        df (Pandas Dataframe) : Dataframe with added columns
    """
    df_lt_2000 = df[df['Year'] < 2000]
    df_gt_2000 = df[df['Year'] >= 2000]
    aggregate_list = _measurement_aggregate(df_lt_2000)
    aggregate_list = aggregate_list + _measurement_aggregate(df_gt_2000)
    func = np.vectorize(_measurement_conditions)
    race_year = func(df['SVs'], df['Year'])
    df['Measurement_Method'] = aggregate_list
    df['Measurement_Method'] = df['Measurement_Method'] + race_year

    return df


class USCensusPEPByASR:
    """
    This Class has requried methods to generate Cleaned CSV,
    MCF and TMCF Files.
    """

    def __init__(self, input_files: list, csv_file_path: str,
                 mcf_file_path: str, tmcf_file_path: str) -> None:
        self._input_files = input_files
        self._cleaned_csv_file_path = csv_file_path
        self._mcf_file_path = mcf_file_path
        self._tmcf_file_path = tmcf_file_path

    def _generate_mcf(self, sv_list) -> None:
        """
        This method generates MCF file w.r.t
        dataframe headers and defined MCF template.
        Args:
            df_cols (list) : List of DataFrame Columns
        Returns:
            None
        """

        final_mcf_template = ""
        for sv in sv_list:
            if "Total" in sv:
                continue
            age = ''
            gender = ''
            race = ''
            sv_prop = sv.split("_")
            for prop in sv_prop:
                if prop in ["Count", "Person"]:
                    continue
                if "Years" in prop:
                    if "OrMoreYears" in prop:
                        age = "\nage: [" + prop.replace("OrMoreYears",
                                                        "") + " - Years]" + "\n"
                    elif "To" in prop:
                        age = "\nage: [" + prop.replace("Years", "").replace(
                            "To", " ") + " Years]" + "\n"
                    else:
                        age = "\nage: [Years " + prop.replace("Years",
                                                              "") + "]" + "\n"
                elif "Male" in prop or "Female" in prop:
                    gender = "gender: dcs:" + prop
                else:

                    if "race" in race:
                        race = race.strip() + "__" + prop + "\n"
                    else:
                        race = "race: dcs:" + prop + "\n"
            if gender == "":
                race = race.strip()
            final_mcf_template += MCF_TEMPLATE.format(
                pv1=sv, pv2=age, pv3=race, pv4=gender) + "\n"
        # Writing Genereated MCF to local path.
        with open(self._mcf_file_path, 'w+', encoding='utf-8') as f_out:
            f_out.write(final_mcf_template.rstrip('\n'))

    def _generate_tmcf(self) -> None:
        """
        This method generates TMCF file w.r.t
        dataframe headers and defined TMCF template.
        Args:
            df_cols (list) : List of DataFrame Columns
        Returns:
            None
        """

        # Writing Genereated TMCF to local path.
        with open(self._tmcf_file_path, 'w+', encoding='utf-8') as f_out:
            f_out.write(TMCF_TEMPLATE.rstrip('\n'))

    def process(self):
        """
        This Method calls the required methods to generate cleaned CSV,
        MCF, and TMCF file
        """

        final_df = pd.DataFrame()
        # Creating Output Directory.
        output_path = os.path.dirname(self._cleaned_csv_file_path)
        if not os.path.exists(output_path):
            os.mkdir(output_path)
        processed_count = 0
        total_files_to_process = len(self._input_files)
        if total_files_to_process == 0:
            logging.fatal(
                f"No input files found in the directory: {self._input_files}")
        logging.info(
            f"Number of files to be processed {len(self._input_files)}")
        sv_list = []
        # data_df is used to read every single file which has been generated.
        # final_df concatenates all these files.
        expected_columns = [
            'geo_ID', 'Year', 'observation', 'Measurement_Method', 'SVs'
        ]
        for file_path in self._input_files:
            logging.info(f"Processing --- {file_path}")
            data_df = pd.read_csv(file_path)
            for column in expected_columns:
                if column not in data_df.columns:
                    logging.fatal(
                        f"Error: {file_path} is missing column {column}")
            if not data_df.empty:
                processed_count += 1
                final_df = pd.concat([final_df, data_df])
                sv_list += data_df["SVs"].to_list()
            else:
                logging.fatal(f"Failed to process {file_path}")

        logging.info(f"Number of files processed {processed_count}")
        # After processing all files, ensure all files were processed
        if processed_count == total_files_to_process & total_files_to_process > 0:
            # Drop the unwanted columns and NA.
            logging.info(f"Dropping unwanted columns and NA")
            final_df.drop(columns=['Unnamed: 0'], inplace=True)
            final_df = final_df.dropna()
            final_df['Year'] = final_df['Year'].astype(float).astype(int)
            logging.info(f"Sorting data {final_df.shape} by year, geo-id")
            final_df = final_df.sort_values(by=['Year', 'geo_ID'])
            logging.info(f"Setting measurement method")
            final_df = _measurement_method(final_df)
            logging.info(
                f"Writing data {final_df.shape} to {self._cleaned_csv_file_path}"
            )
            final_df.to_csv(self._cleaned_csv_file_path, index=False)
            sv_list = list(set(sv_list))
            logging.info(f"Generating MCF for {len(sv_list)}")
            sv_list.sort()
            self._generate_mcf(sv_list)
            logging.info(f"Generating TMCF")
            self._generate_tmcf()
        else:
            logging.fatal(
                f"File processing mismatch: Expected {total_files_to_process} files, but processed {processed_count}. Output file generation aborted"
            )


def download_files():
    """
    This method calls the download functions for state, county and country for each year
    Returns:
    True if there was no errors
    """
    national_url_file = "national.json"
    state_url_file = "state.json"
    county_url_file = "county.json"
    output_folder = "input_data"
    logging.info("Download starts")
    try:
        add_future_year_urls()
        national1900(output_folder)
        national1960(output_folder)
        national1980(national_url_file, output_folder)
        national2000(national_url_file, output_folder)
        national2010(national_url_file, output_folder)

        state1970(state_url_file, output_folder)
        state1990(state_url_file, output_folder)
        state2000(state_url_file, output_folder)
        state2010(state_url_file, output_folder)

        county1970(county_url_file, output_folder)
        county1980(county_url_file, output_folder)
        county1990(output_folder)
        county2000(output_folder)
        county2010(county_url_file, output_folder)

        global _FILES_TO_DOWNLOAD
        for file in _FILES_TO_DOWNLOAD:
            url = file['download_path']
            if 'national' in url:
                national2029(url, output_folder)
            if 'state' in url:
                state2029(url, output_folder)
            if 'counties' in url:
                county2029(url, output_folder)
    except Exception as e:
        logging.fatal(f"Error while downloading : {e}")


def main(_):
    mode = FLAGS.mode
    input_path = FLAGS.input_path
    if not os.path.exists(input_path):
        os.mkdir(input_path)
    data_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "output")
    # Defining Output Files.
    cleaned_csv_path = os.path.join(data_file_path, "usa_population_asr.csv")
    mcf_path = os.path.join(data_file_path, "usa_population_asr.mcf")
    tmcf_path = os.path.join(data_file_path, "usa_population_asr.tmcf")
    # Running the fuctions in individual files by Year and Area
    if mode == "" or mode == "download":
        #Creating folder to store the raw data from source
        raw_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "raw_data")
        if not os.path.exists(raw_data_path):
            os.mkdir(raw_data_path)
        add_future_year_urls()
        download_files()
    if mode == "" or mode == "process":
        ip_files = os.listdir(input_path)
        ip_files = [input_path + os.sep + file for file in ip_files]
        loader = USCensusPEPByASR(ip_files, cleaned_csv_path, mcf_path,
                                  tmcf_path)
        loader.process()
    logging.info("Task completed!")


if __name__ == "__main__":
    app.run(main)
