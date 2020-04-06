#!/bin/bash

COVID_DATA_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd)"
COVID_DIR="$COVID_DATA_DIR/../covid"
COVID_DATA_SOURCES_DIR="$COVID_DATA_DIR/../covid-data-sources"
COVID_DATA_SOURCES_DIR_JHU="$COVID_DATA_SOURCES_DIR/COVID-19"

echo "Current time is: $(date)"

cd $COVID_DATA_SOURCES_DIR_JHU
# if /usr/bin/git pull | grep -q 'Already up to date'; then
if echo 'aaa' | grep -q 'Already up to date'; then
    echo 'Data is up-to-date, nothing to be done'
    exit 0
fi
cd $COVID_DATA_DIR
source /usr/local/bin/virtualenvwrapper.sh
workon covid-data
./mesh_covid_data.py
if [ $? -eq 0 ]
then
    rm -rf $COVID_DIR/app/data && mv data $COVID_DIR/app/data
else
    echo "mesh_covid_data command failed"
fi
echo "Now rebuilding npm to pickup latest covid data..."
nvm use 12
cd $COVID_DIR
./build.sh
echo "Done"