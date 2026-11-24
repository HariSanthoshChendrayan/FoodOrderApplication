#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt
python mealmate/manage.py collectstatic --no-input
python mealmate/manage.py migrate
