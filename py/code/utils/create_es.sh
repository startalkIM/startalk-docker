#!/bin/bash
export PYTHONPATH=/home/q/www/python/backend-python:$PYTHONPATH
/home/q/www/python/.venv/backendvenv/bin/python3.7 /home/q/www/python/backend-python/service/kafka2es/create_index.py

#cd /home/q/python/backend-python/
#source /home/q/python/.venv/backendvenv/bin/activate
#export PYTHONPATH=/home/q/python/backend-python:$PYTHONPATH
#/home/q/python/.venv/backendvenv/bin/python3 /home/q/python/backend-python/service/kafka2es/create_index.py 
