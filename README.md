This package reads data from the following github repos, and writes result json files to datafolder under bayhiker/covid project.

## Folder Layout

These data source repos needs to be checked out to ../covid-data-sources/

- https://github.com/CSSEGISandData/COVID-19.git
- https://github.com/nytimes/covid-19-data.git
- https://github.com/kjhealy/fips-codes.git

## Development Setup

- Create a virtualenv covid-data: /usr/bin/python3 -m venv /home/mike/.venv/covid-data
- Create config.env from config.env.template, generate and replace SECRET_KEYs in config.env
- Flask web service is not used right now, however, it can be started with gunicorn command: gunicorn -w 1 -b 0.0.0.0:5000 wsgi
