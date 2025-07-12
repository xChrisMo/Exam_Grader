#!/usr/bin/env python3
"""
Test script to verify the refactored AI processing system.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Test imports
    print("Testing imports...")
    
    # Test OCR service
    from src.services.ocr_service import OCRService
    print("✓ OCR service imported successfully")
    
    # Test Progress Tracker
    from src.services.progress_tracker import ProgressTracker
    print("✓ Progress Tracker imported successfully")
    
    # Test Refactored AI Service
    from src.services.refactored_unified_ai_service import RefactoredUnifiedAIService
    print("✓ Refactored Unified AI Service imported successfully")
    
    # Test Refactored AI Endpoints (Blueprint and ProgressTracker class)
    from src.api.refactored_ai_endpoints import refactored_ai_bp, ProgressTracker as EndpointProgressTracker
    print("✓ Refactored AI Endpoints imported successfully")
    
    # Test Blueprint from webapp
    from webapp.refactored_routes import refactored_bp
    print("✓ Refactored Blueprint imported successfully")
    
    print("\n=== All imports successful! ===")
    
    # Test basic initialization
    print("\nTesting basic initialization...")
    
    # Initialize OCR service
    ocr_service = OCRService()
    print("✓ OCR service initialized")
    
    # Initialize Progress Tracker
    progress_tracker = ProgressTracker()
    print("✓ Progress Tracker initialized")
    
    # Initialize Endpoint Progress Tracker
    endpoint_progress_tracker = EndpointProgressTracker()
    print("✓ Endpoint Progress Tracker initialized")
    
    print("\n=== Refactored AI processing system is ready! ===")
    
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)