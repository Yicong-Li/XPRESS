#!/usr/bin/env bash

./build.sh

docker save xpress | gzip -c > xpress.tar.gz
