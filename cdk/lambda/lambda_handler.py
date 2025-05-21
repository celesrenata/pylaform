import sys
import os

# Add the directory containing pylaform to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pylaform.app import app

import awsgi2

def handler(event, context):
    return awsgi2.response(app, event, context)



