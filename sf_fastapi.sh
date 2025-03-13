#!/bin/bash
# Simple script to start SpiderFoot with FastAPI interface

python3 sf.py -F -l 127.0.0.1:5001 "$@"
