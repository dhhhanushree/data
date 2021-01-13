# Importing OurWorldInData Covid19 Data

This directory contains artifacts required for importing [OurWorldInData Covid19 Data](https://github.com/owid/covid-19-data/tree/master/public/data)
into Data Commons, along with scripts used to generate these artifacts.

## Artifacts:

- [OurWorldInData_Covid19.csv](OurWorldInData_Covid19.csv): the cleaned CSV.
- [OurWorldInData_Covid19.tmcf](OurWorldInData_Covid19.tmcf): the mapping file (Template MCF).
- [OurWorldInData_Covid19_StatisticalVariables.mcf](OurWorldInData_Covid19_StatisticalVariables.mcf):
  the new StatisticalVariables defined for this dataset.

## Generating Artifacts:

`OurWorldInData_Covid19_StatisticalVariable.mcf` was handwritten.

To generate `OurWorldInData_Covid19.tmcf` and `OurWorldInData_Covid19.csv`, run:

```bash
python3 preprocess_csv.py
```