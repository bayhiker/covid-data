This package reads data from the following github repos, and writes result json files to datafolder under bayhiker/covid project.

## Folder Layout

These data source repos needs to be checked out to ../covid-data-sources/

- https://github.com/CSSEGISandData/COVID-19.git
- https://github.com/nytimes/covid-19-data.git
- https://github.com/kjhealy/fips-codes.git

## Development Setup

- Create a virtualenv covid-data: mkvirtualenv -a /home/mike/code/covid-data -p /usr/bin/python3 covid-data
