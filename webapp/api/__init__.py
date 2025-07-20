"""
API package for LLM Training Page
"""

from flask import Blueprint

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import route modules
from . import models
from . import documents
from . import training
from . import reports