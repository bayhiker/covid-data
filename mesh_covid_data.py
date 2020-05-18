#!/usr/bin/env python

from collector import CovidMesher

if __name__ == "__main__":
    covidMesher = CovidMesher("../covid-data-sources", "./data/covid")
    covidMesher.mesh()
