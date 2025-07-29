"""
Model Performance Monitoring and Alerting Service
Provides continuous monitoring, degradation detection, and automated alerts
Addresses requirements 7.6, 7.7 for model lifecycle management
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import json
import threading
import time

from src.database.models import LLMTrainingJob, LLMModelTest, db
from src.services.model_validation_service import ModelValidationService

logger = logging.g