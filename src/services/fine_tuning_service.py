"""
Fine-Tuning Service for Multiple AI Providers

This service provides fine-tuning capabilities for different AI providers
including OpenAI, local models, and others that support custom training.
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.services.base_service import BaseService, ServiceStatus
from utils.logger import logger

class FineTuningService(BaseService):
    """Service for fine-tuning AI models with uploaded documents."""

    def __init__(self):
        super().__init__("fine_tuning_service")

        # Detect which AI provider is being used
        self.provider = self._detect_provider()
        self.fine_tuning_supported = self._check_fine_tuning_support()

        logger.info(f"Fine-tuning service initialized for provider: {self.provider}")
        logger.info(f"Fine-tuning supported: {self.fine_tuning_supported}")

    def _detect_provider(self) -> str:
        """Detect which AI provider is currently configured."""
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            return "anthropic"
        elif os.getenv("DEEPSEEK_API_KEY"):
            return "deepseek"
        elif "localhost" in os.getenv("LLM_BASE_URL", ""):
            return "local"
        else:
            return "unknown"

    def _check_fine_tuning_support(self) -> bool:
        """Check if the current provider supports fine-tuning."""
        fine_tuning_providers = {
            "openai": True,
            "anthropic": False,  # Limited support
            "deepseek": False,   # No public API
            "local": True,       # Full control
            "unknown": False
        }
        return fine_tuning_providers.get(self.provider, False)

    async def create_fine_tuning_dataset(
        self,
        training_guides: List[Dict],
        format_type: str = "openai"
    ) -> Tuple[str, Dict]:
        """
        Create a fine-tuning dataset from training guides.

        Args:
            training_guides: List of processed training guides
            format_type: Dataset format ("openai", "local", etc.)

        Returns:
            Tuple of (dataset_path, metadata)
        """
        try:
            with self.track_request("create_dataset"):
                logger.info(f"Creating fine-tuning dataset for {len(training_guides)} guides")

                if format_type == "openai":
                    return await self._create_openai_dataset(training_guides)
                elif format_type == "local":
                    return await self._create_local_dataset(training_guides)
                else:
                    raise ValueError(f"Unsupported dataset format: {format_type}")

        except Exception as e:
            logger.error(f"Failed to create fine-tuning dataset: {e}")
            raise

    async def _create_openai_dataset(self, training_guides: List[Dict]) -> Tuple[str, Dict]:
        """Create OpenAI fine-tuning format dataset."""
        dataset = []
        total_examples = 0

        for guide in training_guides:
            guide_content = guide.get('content', '')
            questions = guide.get('questions', [])

            for question in questions:
                # Skip non-dictionary questions
                if not isinstance(question, dict):
                    logger.warning(f"Skipping non-dictionary question in fine-tuning dataset")
                    continue

                # Create training examples in OpenAI format
                example = {
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are an expert exam grader. Grade student answers based on this marking guide:\n\n{guide_content}"
                        },
                        {
                            "role": "user",
                            "content": f"Question: {question.get('text', '')}\nStudent Answer: [STUDENT_ANSWER_PLACEHOLDER]\nMax Score: {question.get('max_score', 10)}"
                        },
                        {
                            "role": "assistant",
                            "content": f"Score: {question.get('max_score', 10)}/10\nFeedback: {question.get('criteria', 'Complete and accurate answer.')}"
                        }
                    ]
                }
                dataset.append(example)
                total_examples += 1

        # Save dataset to file
        timestamp = int(time.time())
        dataset_path = f"training_data/openai_dataset_{timestamp}.jsonl"

        os.makedirs("training_data", exist_ok=True)

        with open(dataset_path, 'w', encoding='utf-8') as f:
            for example in dataset:
                f.write(json.dumps(example) + '\n')

        metadata = {
            "format": "openai",
            "total_examples": total_examples,
            "guides_processed": len(training_guides),
            "created_at": datetime.now().isoformat(),
            "file_path": dataset_path
        }

        logger.info(f"Created OpenAI dataset with {total_examples} examples: {dataset_path}")
        return dataset_path, metadata

    async def _create_local_dataset(self, training_guides: List[Dict]) -> Tuple[str, Dict]:
        """Create local model fine-tuning format dataset."""
        dataset = {
            "training_data": [],
            "metadata": {
                "format": "local",
                "guides_count": len(training_guides),
                "created_at": datetime.now().isoformat()
            }
        }

        for guide in training_guides:
            guide_data = {
                "guide_id": guide.get('id'),
                "content": guide.get('content', ''),
                "questions": guide.get('questions', []),
                "criteria": guide.get('criteria', [])
            }
            dataset["training_data"].append(guide_data)

        # Save dataset
        timestamp = int(time.time())
        dataset_path = f"training_data/local_dataset_{timestamp}.json"

        os.makedirs("training_data", exist_ok=True)

        with open(dataset_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)

        metadata = dataset["metadata"]
        metadata["file_path"] = dataset_path

        logger.info(f"Created local dataset: {dataset_path}")
        return dataset_path, metadata

    async def start_fine_tuning(
        self,
        dataset_path: str,
        model_name: str = None,
        training_params: Dict = None
    ) -> Dict[str, Any]:
        """
        Start fine-tuning process.

        Args:
            dataset_path: Path to training dataset
            model_name: Base model to fine-tune
            training_params: Training parameters

        Returns:
            Fine-tuning job information
        """
        try:
            with self.track_request("start_fine_tuning"):
                if not self.fine_tuning_supported:
                    raise ValueError(f"Fine-tuning not supported for provider: {self.provider}")

                if self.provider == "openai":
                    return await self._start_openai_fine_tuning(dataset_path, model_name, training_params)
                elif self.provider == "local":
                    return await self._start_local_fine_tuning(dataset_path, model_name, training_params)
                else:
                    raise ValueError(f"Fine-tuning not implemented for provider: {self.provider}")

        except Exception as e:
            logger.error(f"Failed to start fine-tuning: {e}")
            raise

    async def _start_openai_fine_tuning(
        self,
        dataset_path: str,
        model_name: str = None,
        training_params: Dict = None
    ) -> Dict[str, Any]:
        """Start OpenAI fine-tuning job."""
        try:
            import openai

            # Initialize OpenAI client
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Upload training file
            logger.info(f"Uploading training file: {dataset_path}")
            with open(dataset_path, 'rb') as f:
                training_file = client.files.create(
                    file=f,
                    purpose='fine-tune'
                )

            # Start fine-tuning job
            base_model = model_name or "gpt-3.5-turbo"

            fine_tuning_job = client.fine_tuning.jobs.create(
                training_file=training_file.id,
                model=base_model,
                hyperparameters={
                    "n_epochs": training_params.get("epochs", 3) if training_params else 3,
                    "batch_size": training_params.get("batch_size", 1) if training_params else 1,
                    "learning_rate_multiplier": training_params.get("learning_rate", 0.1) if training_params else 0.1
                }
            )

            job_info = {
                "provider": "openai",
                "job_id": fine_tuning_job.id,
                "status": fine_tuning_job.status,
                "model": base_model,
                "training_file_id": training_file.id,
                "created_at": datetime.now().isoformat(),
                "estimated_completion": "20-30 minutes"
            }

            logger.info(f"Started OpenAI fine-tuning job: {fine_tuning_job.id}")
            return job_info

        except Exception as e:
            logger.error(f"OpenAI fine-tuning failed: {e}")
            raise

    async def _start_local_fine_tuning(
        self,
        dataset_path: str,
        model_name: str = None,
        training_params: Dict = None
    ) -> Dict[str, Any]:
        """Start local model fine-tuning."""
        # This would integrate with local training frameworks like:
        # - Hugging Face Transformers
        # - Ollama fine-tuning
        # - LM Studio training

        job_info = {
            "provider": "local",
            "job_id": f"local_job_{int(time.time())}",
            "status": "queued",
            "model": model_name or "local_model",
            "dataset_path": dataset_path,
            "created_at": datetime.now().isoformat(),
            "estimated_completion": "1-2 hours (depending on hardware)"
        }

        logger.info(f"Local fine-tuning job created: {job_info['job_id']}")
        logger.warning("Local fine-tuning requires manual setup with training frameworks")

        return job_info

    async def check_fine_tuning_status(self, job_id: str) -> Dict[str, Any]:
        """Check the status of a fine-tuning job."""
        try:
            if self.provider == "openai":
                client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                job = client.fine_tuning.jobs.retrieve(job_id)

                return {
                    "job_id": job.id,
                    "status": job.status,
                    "fine_tuned_model": job.fine_tuned_model,
                    "created_at": job.created_at,
                    "finished_at": job.finished_at,
                    "training_file": job.training_file,
                    "validation_file": job.validation_file,
                    "result_files": job.result_files
                }
            else:
                return {
                    "job_id": job_id,
                    "status": "not_implemented",
                    "message": f"Status checking not implemented for {self.provider}"
                }

        except Exception as e:
            logger.error(f"Failed to check fine-tuning status: {e}")
            raise

    def get_provider_instructions(self) -> Dict[str, str]:
        """Get instructions for setting up fine-tuning with different providers."""
        instructions = {
            "openai": """
To enable OpenAI fine-tuning:
1. Set OPENAI_API_KEY in your .env file
2. Change LLM_MODEL to 'gpt-3.5-turbo' or 'gpt-4'
3. Upload training documents and start fine-tuning
4. Fine-tuned models will be available in 20-30 minutes
            """,
            "local": """
To enable local fine-tuning:
1. Set LLM_BASE_URL to your local server (e.g., http://localhost:11434)
2. Install training frameworks (Ollama, LM Studio, etc.)
3. Upload training documents to create datasets
4. Manual training setup required with your chosen framework
            """,
            "anthropic": """
Anthropic Claude has limited fine-tuning support:
1. Set ANTHROPIC_API_KEY in your .env file
2. Use constitutional AI and prompt engineering instead
3. Custom instructions can be configured per conversation
            """,
            "deepseek": """
DeepSeek currently doesn't support public fine-tuning:
1. Consider switching to OpenAI for fine-tuning capabilities
2. Or use local models for full control
3. Current setup only supports prompt engineering
            """
        }

        return {
            "current_provider": self.provider,
            "fine_tuning_supported": self.fine_tuning_supported,
            "instructions": instructions.get(self.provider, "Unknown provider"),
            "all_instructions": instructions
        }

# Global fine-tuning service instance
fine_tuning_service = FineTuningService()