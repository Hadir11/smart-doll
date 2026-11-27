#!/bin/zsh
cd /Volumes/My_Disk/dev/smart-doll
~/.venvs/smart-doll/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
