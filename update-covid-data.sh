#!/bin/bash

FORCE=0
WGET=/usr/bin/wget

while getopts ":f" opt; do
    case ${opt} in 
        f )  FORCE=1
            ;;
        \? ) echo "Usage: update-covid-data.sh [-f]"
            ;;
    esac
done

COVID_DATA_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd)"
COVID_DATA_SOURCES_DIR="$COVID_DATA_DIR/../covid-data-sources"
COVID_DATA_SOURCES_DIR_JHU="$COVID_DATA_SOURCES_DIR/COVID-19"
COVID_DATA_SOURCES_DIR_DL="$COVID_DATA_SOURCES_DIR/DL-COVID-19"
COVID_DATA_SOURCES_DIR_CTD="$COVID_DATA_SOURCES_DIR/covid-tracking-data"

echo "Current time is: $(date)"

UPDATE_FOUND="no"
cd $COVID_DATA_SOURCES_DIR_JHU
if /usr/bin/git pull | grep -q 'Already up to date'; then
    echo 'JHU cases data is up-to-date'
else
    UPDATE_FOUND="yes"
fi
cd $COVID_DATA_SOURCES_DIR_DL
if /usr/bin/git pull | grep -q 'Already up to date'; then
    echo 'DL mobility data is up-to-date'
else
    UPDATE_FOUND="yes"
fi
if [ "${UPDATE_FOUND}" = "no" ]; then
    if [ "${FORCE}" -eq "0" ]; then
        echo 'Nothing to be done'
        exit 0
    else
        echo "Forcing data update without source data updates"
    fi
fi
# Update covid-tracking-data with API (moved to api since mid Aug)
${WGET} https://api.covidtracking.com/v1/us/daily.csv -O ${COVID_DATA_SOURCES_DIR_CTD}/data/us_daily.csv
${WGET} https://api.covidtracking.com/v1/states/daily.csv -O ${COVID_DATA_SOURCES_DIR_CTD}/data/states_daily_4pm_et.csv

source ~/.profile
workon covid-data
cd $COVID_DATA_DIR
./mesh_covid_data.py
if [ $? -ne 0 ]
then
    echo "mesh_covid_data command failed"
fi
echo "Done"
