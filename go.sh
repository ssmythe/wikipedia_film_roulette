#!/usr/bin/env bash

rm -fr log.txt
# python roulette.py -n 10 -v -d | tee log.txt
# python roulette.py -c American -n 10 -v -d | tee log.txt
# python roulette.py -c American -g "science fiction" -n 10 -v -d | tee log.txt
python roulette.py -c American -g "science fiction" -s "time travel" -n 10 -v -d | tee log.txt
