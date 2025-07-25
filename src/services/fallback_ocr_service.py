#!/usr/bin/env python3
"""
Fallback OCR Service Implementation
Provides free, open-source OCR solutions as fallbacks for the paid HandwritingOCR API.

This service implements multiple OCR engines with automatic fallback capabilities:
1. EasyOCR - General purpose, good balance
2. PaddleOCR - High accuracy, production ready
3. TrOCR - Handwriting specialist
4. Tesseract - Printed text specialist

Author: Augment Agent
Date: 2025-07-21
"""

import os
import logging
import time
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class FallbackOCRService:
    """
    Comprehensive fallback OCR service with multiple engines.
    Automatically selects the best OCR engine based on content type and availability.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the fallback OCR service with multiple engines."""
        self.config = config or {}
        self.available_engines = {}
        self.engine_priority = ['easyocr', 'paddleocr', 'trocr', 'tesseract']
        self.engine_availability = {}

        # Initialize available engines (lazy loading)
        self._initialize_engines()

        available_engines = self.get_available_engines()
        logger.info(f"Fallback OCR service initialized with available engines: {available_engines}")

    def _initialize_engines(self):
        """Initialize all available OCR engines with lazy loading."""
        
        # Check which engines are available without initializing them
        self.engine_availability = {}
        
        # Check EasyOCR availability (disabled by default to prevent hanging)
        if os.getenv('ENABLE_EASYOCR', '').lower() in ('true', '1', 'yes'):
            try:
                import easyocr
                self.engine_availability['easyocr'] = True
                logger.info("EasyOCR library available (enabled via ENABLE_EASYOCR)")
            except ImportError:
                self.engine_availability['easyocr'] = False
                logger.warning("EasyOCR not available. Install with: pip install easyocr")
        else:
            self.engine_availability['easyocr'] = False
            logger.info("EasyOCR disabled by default (set ENABLE_EASYOCR=true to enable)")

        # Check PaddleOCR availability (disabled by default to prevent hanging)
        if os.getenv('ENABLE_PADDLEOCR', '').lower() in ('true', '1', 'yes'):
            try:
                from paddleocr import PaddleOCR
                self.engine_availability['paddleocr'] = True
                logger.info("PaddleOCR library available (enabled via ENABLE_PADDLEOCR)")
            except ImportError:
                self.engine_availability['paddleocr'] = False
                logger.warning("PaddleOCR not available. Install with: pip install paddlepaddle paddleocr")
        else:
            self.engine_availability['paddleocr'] = False
            logger.info("PaddleOCR disabled by default (set ENABLE_PADDLEOCR=true to enable)")

        # Check TrOCR availability (disabled by default to prevent hanging)
        if os.getenv('ENABLE_TROCR', '').lower() in ('true', '1', 'yes'):
            try:
                from transformers import TrOCRProcessor, VisionEncoderDecoderModel
                self.engine_availability['trocr'] = True
                logger.info("TrOCR library available (enabled via ENABLE_TROCR)")
            except ImportError:
                self.engine_availability['trocr'] = False
                logger.warning("TrOCR not available. Install with: pip install transformers torch torchvision")
        else:
            self.engine_availability['trocr'] = False
            logger.info("TrOCR disabled by default (set ENABLE_TROCR=true to enable)")

        # Check Tesseract availability
        try:
            import pytesseract
            self.engine_availability['tesseract'] = True
            logger.info("Tesseract library available")
        except ImportError:
            self.engine_availability['tesseract'] = False
            logger.warning("Tesseract not available. Install with: pip install pytesseract")

    def _get_or_initialize_engine(self, engine_name: str):
        """Lazy initialization of OCR engines."""
        if engine_name in self.available_engines:
            return self.available_engines[engine_name]
        
        if not self.engine_availability.get(engine_name, False):
            return None
            
        try:
            if engine_name == 'easyocr':
                self.available_engines['easyocr'] = EasyOCREngine()
                logger.info("EasyOCR engine initialized successfully")
            elif engine_name == 'paddleocr':
                self.available_engines['paddleocr'] = PaddleOCREngine()
                logger.info("PaddleOCR engine initialized successfully")
            elif engine_name == 'trocr':
                self.available_engines['trocr'] = TrOCREngine()
                logger.info("TrOCR engine initialized successfully")
            elif engine_name == 'tesseract':
                self.available_engines['tesseract'] = TesseractEngine()
                logger.info("Tesseract engine initialized successfully")
            
            return self.available_engines.get(engine_name)
        except Exception as e:
            logger.error(f"Failed to initialize {engine_name}: {e}")
            return None

    def is_available(self) -> bool:
        """Check if any fallback OCR engine is available."""
        return any(self.engine_availability.values())

    def extract_text_from_image(self, file_path: Union[str, Path],
                               content_type: str = 'mixed',
                               preferred_engine: Optional[str] = None) -> str:
        """
        Extract text from image using the best available OCR engine.

        Args:
            file_path: Path to the image file
            content_type: Type of content ('printed', 'handwritten', 'mixed')
            preferred_engine: Specific engine to try first

        Returns:
            Extracted text string

        Raises:
            Exception: If no OCR engines are available or all fail
        """
        result = self.extract_text(file_path, content_type, preferred_engine)

        if result['success']:
            return result['text']
        else:
            raise Exception(f"OCR extraction failed: {result['error']}")

    def extract_text(self, image_path: Union[str, Path],
                    content_type: str = 'mixed',
                    preferred_engine: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text from image using the best available OCR engine.

        Args:
            image_path: Path to the image file
            content_type: Type of content ('printed', 'handwritten', 'mixed')
            preferred_engine: Specific engine to try first

        Returns:
            Dictionary with extraction results
        """

        if not any(self.engine_availability.values()):
            return {
                'success': False,
                'error': 'No OCR engines available. Please install at least one OCR library.',
                'text': '',
                'engine_used': None
            }

        # Determine engine priority based on content type
        engine_order = self._get_engine_priority(content_type, preferred_engine)

        # Try engines in order until one succeeds
        last_error = None
        for engine_name in engine_order:
            if not self.engine_availability.get(engine_name, False):
                continue

            try:
                logger.info(f"Attempting OCR with {engine_name}")
                start_time = time.time()

                # Lazy initialization of engine
                engine = self._get_or_initialize_engine(engine_name)
                if engine is None:
                    logger.warning(f"Failed to initialize {engine_name}")
                    continue

                result = engine.extract_text(image_path)

                processing_time = time.time() - start_time
                result['engine_used'] = engine_name
                result['processing_time'] = processing_time

                if result['success'] and result['text'].strip():
                    logger.info(f"OCR successful with {engine_name} in {processing_time:.2f}s")
                    return result
                else:
                    logger.warning(f"OCR with {engine_name} returned no text")

            except Exception as e:
                last_error = str(e)
                logger.error(f"OCR failed with {engine_name}: {e}")
                continue

        # All engines failed
        return {
            'success': False,
            'error': f'All OCR engines failed. Last error: {last_error}',
            'text': '',
            'engine_used': None
        }

    def _get_engine_priority(self, content_type: str, preferred_engine: Optional[str] = None) -> List[str]:
        """Determine the priority order of engines based on content type."""

        if preferred_engine and self.engine_availability.get(preferred_engine, False):
            priority = [preferred_engine]
            priority.extend([e for e in self.engine_priority if e != preferred_engine and self.engine_availability.get(e, False)])
            return priority

        if content_type == 'handwritten':
            base_priority = ['trocr', 'paddleocr', 'easyocr', 'tesseract']
        elif content_type == 'printed':
            base_priority = ['paddleocr', 'tesseract', 'easyocr', 'trocr']
        else:  # mixed or unknown
            base_priority = ['easyocr', 'paddleocr', 'trocr', 'tesseract']
        
        # Filter to only available engines
        return [e for e in base_priority if self.engine_availability.get(e, False)]

    def get_available_engines(self) -> List[str]:
        """Get list of available OCR engines."""
        return [engine for engine, available in self.engine_availability.items() if available]

    def test_engines(self, test_image_path: Optional[str] = None) -> Dict[str, Dict]:
        """Test all available engines with a sample image."""
        results = {}

        # Use a simple test image if none provided
        if not test_image_path:
            # Create a simple test image
            test_image_path = self._create_test_image()

        for engine_name in self.get_available_engines():
            try:
                start_time = time.time()
                
                # Lazy initialization of engine
                engine = self._get_or_initialize_engine(engine_name)
                if engine is None:
                    results[engine_name] = {
                        'success': False,
                        'error': 'Failed to initialize engine',
                        'processing_time': 0
                    }
                    continue
                
                result = engine.extract_text(test_image_path)
                processing_time = time.time() - start_time

                results[engine_name] = {
                    'success': result['success'],
                    'text': result['text'][:100] + '...' if len(result['text']) > 100 else result['text'],
                    'processing_time': processing_time,
                    'error': result.get('error', None)
                }
            except Exception as e:
                results[engine_name] = {
                    'success': False,
                    'error': str(e),
                    'processing_time': 0
                }

        return results

    def _create_test_image(self) -> str:
        """Create a simple test image with text."""
        try:
            import cv2
            import tempfile

            # Create a simple image with text
            img = np.ones((100, 400, 3), dtype=np.uint8) * 255
            cv2.putText(img, 'Test OCR Text', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            cv2.imwrite(temp_file.name, img)

            return temp_file.name
        except ImportError:
            # Fallback if cv2 not available
            import tempfile

            img = Image.new('RGB', (400, 100), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((50, 30), 'Test OCR Text', fill='black')

            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            img.save(temp_file.name)

            return temp_file.name


class BaseOCREngine:
    """Base class for OCR engines."""

    def extract_text(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """Extract text from image. Must be implemented by subclasses."""
        raise NotImplementedError


class EasyOCREngine(BaseOCREngine):
    """EasyOCR implementation."""

    def __init__(self, languages=['en']):
        import easyocr
        logger.info("Initializing EasyOCR (this may take a while on first run to download models)...")
        self.reader = easyocr.Reader(languages, gpu=False, verbose=False)
        logger.info("EasyOCR initialization completed")

    def extract_text(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """Extract text using EasyOCR."""
        try:
            results = self.reader.readtext(str(image_path))

            extracted_text = []
            for (bbox, text, confidence) in results:
                if confidence > 0.3:  # Lower threshold for better recall
                    extracted_text.append({
                        'text': text,
                        'confidence': confidence,
                        'bbox': bbox
                    })

            full_text = ' '.join([item['text'] for item in extracted_text])
            avg_confidence = np.mean([item['confidence'] for item in extracted_text]) if extracted_text else 0

            return {
                'success': True,
                'text': full_text,
                'confidence': avg_confidence,
                'details': extracted_text
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }


class PaddleOCREngine(BaseOCREngine):
    """PaddleOCR implementation."""

    def __init__(self, lang='en'):
        from paddleocr import PaddleOCR
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            use_gpu=False,
            show_log=False
        )

    def extract_text(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """Extract text using PaddleOCR."""
        try:
            results = self.ocr.ocr(str(image_path), cls=True)

            if not results or not results[0]:
                return {
                    'success': True,
                    'text': '',
                    'confidence': 0,
                    'details': []
                }

            extracted_text = []
            for line in results[0]:
                bbox, (text, confidence) = line
                if confidence > 0.3:
                    extracted_text.append({
                        'text': text,
                        'confidence': confidence,
                        'bbox': bbox
                    })

            full_text = ' '.join([item['text'] for item in extracted_text])
            avg_confidence = np.mean([item['confidence'] for item in extracted_text]) if extracted_text else 0

            return {
                'success': True,
                'text': full_text,
                'confidence': avg_confidence,
                'details': extracted_text
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }


class TrOCREngine(BaseOCREngine):
    """TrOCR implementation for handwritten text."""

    def __init__(self):
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        self.processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-handwritten')
        self.model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-handwritten')

    def extract_text(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """Extract text using TrOCR."""
        try:
            from PIL import Image

            image = Image.open(image_path).convert('RGB')
            pixel_values = self.processor(images=image, return_tensors="pt").pixel_values

            generated_ids = self.model.generate(pixel_values)
            generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

            return {
                'success': True,
                'text': generated_text,
                'confidence': 0.85,  # TrOCR doesn't provide confidence scores
                'details': [{'text': generated_text, 'confidence': 0.85}]
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }


class TesseractEngine(BaseOCREngine):
    """Tesseract OCR implementation."""

    def __init__(self):
        import pytesseract
        self.tesseract = pytesseract

    def extract_text(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """Extract text using Tesseract."""
        try:
            # Get text with confidence scores
            data = self.tesseract.image_to_data(str(image_path), output_type=self.tesseract.Output.DICT)

            extracted_text = []
            confidences = []

            for i, text in enumerate(data['text']):
                if text.strip() and int(data['conf'][i]) > 30:  # Filter low confidence
                    extracted_text.append(text)
                    confidences.append(int(data['conf'][i]) / 100.0)

            full_text = ' '.join(extracted_text)
            avg_confidence = np.mean(confidences) if confidences else 0

            return {
                'success': True,
                'text': full_text,
                'confidence': avg_confidence,
                'details': [{'text': full_text, 'confidence': avg_confidence}]
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }


# Global instance for easy access
fallback_ocr_service = None

def get_fallback_ocr_service(config: Optional[Dict] = None) -> FallbackOCRService:
    """Get or create the global fallback OCR service instance."""
    global fallback_ocr_service

    if fallback_ocr_service is None:
        fallback_ocr_service = FallbackOCRService(config)

    return fallback_ocr_service


if __name__ == "__main__":
    # Test the fallback OCR service
    service = FallbackOCRService()
    print(f"Available engines: {service.get_available_engines()}")

    # Test all engines
    test_results = service.test_engines()
    for engine, result in test_results.items():
        print(f"{engine}: {result}")
