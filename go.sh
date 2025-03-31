#!/usr/bin/env bash

rm -fr log.txt
# python roulette.py -n 10  | tee -a log.txt
# python roulette.py -c American -n 10  | tee -a log.txt
# python roulette.py -c American -g "African-American" -n 10 | tee -a log.txt
# python roulette.py -c American -g "science fiction" -n 10 | tee -a log.txt
python roulette.py -c American -g "science fiction" -s "time travel" -n 10  | tee -a log.txt
