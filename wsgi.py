import os
import sys

# Adjust this path to your PythonAnywhere home path when deploying
# Example: '/home/<username>/CCP-Comparison-Engine'
PROJECT_PATH = os.path.dirname(__file__)

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

os.environ.setdefault('FLASK_ENV', 'production')

from app import app as application
