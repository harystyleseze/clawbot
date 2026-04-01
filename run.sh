#!/bin/bash
cd /opt/code
pip install -r requirements.txt
python -m src.db.seed
python -m src
