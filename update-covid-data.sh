#!/bin/bash

FORCE=0

while getopts ":f" opt; do
    case ${opt} in 
        f )  FORCE=1
            ;;
        \? ) echo "Usage: update-covid-data.sh [-f]"
            ;;
    esac
done

COVID_DATA_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd)"
COVID_DIR="$COVID_DATA_DIR/../covid"
COVID_DATA_SOURCES_DIR="$COVID_DATA_DIR/../covid-data-sources"
COVID_DATA_SOURCES_DIR_JHU="$COVID_DATA_SOURCES_DIR/COVID-19"

echo "Current time is: $(date)"

cd $COVID_DATA_SOURCES_DIR_JHU
if /usr/bin/git pull | grep -q 'Already up to date'; then
    echo 'Data is up-to-date'
    if [ "${FORCE}" -eq "0" ]; then
        echo 'Nothing to be done'
        exit 0
    else
        echo "Forcing data update"
    fi
fi
cd $COVID_DATA_DIR
source ~/.profile
workon covid-data
./mesh_covid_data.py
if [ $? -ne 0 ]
then
    echo "mesh_covid_data command failed"
fi
echo "Done"
