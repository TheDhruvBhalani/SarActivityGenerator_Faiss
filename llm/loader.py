"""
LLM Loader
Handles loading and configuration of language models
"""
import os
from typing import Optional, Dict, Any


class LLMLoader:
    """
    Loads and configures language models for SAR generation

    Supports:
    - HuggingFace InferenceClient (Mistral-7B) - Primary
    - Local model loading with quantization - Fallback
    """

    def __init__(
        self,
        model_name: str = "mistralai/Mistral-7B-Instruct-v0.2",
        use_api: bool = True,
        quantization: str = None
    ):
        self.model_name = model_name
        self.use_api = use_api
        self.quantization = quantization
        self.model = None
        self.tokenizer = None
        self.client = None

        self._initialize()

    def _initialize(self):
        """Initialize the model or API connection"""
        if self.use_api:
            self._init_api()
        else:
            self._init_local()

    def _init_api(self):
        """Initialize HuggingFace InferenceClient"""
        try:
            from huggingface_hub import InferenceClient

            self.api_key = os.environ.get("HUGGINGFACE_API_KEY")
            if not self.api_key:
                print("Warning: HUGGINGFACE_API_KEY not found in environment")
                print("Falling back to local mode")
                self.use_api = False
                self._init_local()
                return

            self.client = InferenceClient(token=self.api_key)
            print(f"LLM Loader: Using HuggingFace InferenceClient for {self.model_name}")

        except ImportError:
            print("huggingface_hub not installed, falling back to local mode")
            self.use_api = False
            self._init_local()
        except Exception as e:
            print(f"API initialization error: {e}")
            print("Falling back to local mode")
            self.use_api = False
            self._init_local()

    def _init_local(self):
        """Initialize local model with optional quantization"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch

            print(f"Loading local model: {self.model_name}")

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

            load_kwargs = {"torch_dtype": torch.float16, "device_map": "auto"}

            if self.quantization == "4bit":
                from transformers import BitsAndBytesConfig
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16
                )

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                **load_kwargs
            )
            print("Local model loaded successfully")

        except Exception as e:
            print(f"Error loading local model: {e}")
            raise RuntimeError(f"Cannot initialize LLM: {e}")

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 2048,
        temperature: float = 0.3,
        top_p: float = 0.9
    ) -> str:
        """Generate text from prompt"""
        if self.use_api:
            return self._generate_api(prompt, max_new_tokens, temperature, top_p)
        else:
            return self._generate_local(prompt, max_new_tokens, temperature, top_p)

    def _generate_api(
        self,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
        top_p: float
    ) -> str:
        """Generate using HuggingFace InferenceClient"""
        print(f"LLM: Starting API generation (prompt length: {len(prompt)} chars)")

        if not self.client:
            print("LLM ERROR: No client initialized!")
            return ""

        try:
            # Use chat_completion for instruction-tuned models
            messages = [{"role": "user", "content": prompt}]

            print(f"LLM: Calling chat_completion with max_tokens={max_new_tokens}")
            response = self.client.chat_completion(
                messages=messages,
                model=self.model_name,
                max_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p
            )

            if response and response.choices:
                result = response.choices[0].message.content
                print(f"LLM: Generated {len(result)} chars")
                return result
            print("LLM: Empty response from API")
            return ""

        except Exception as e:
            print(f"API generation error: {e}")
            # Try fallback to text_generation if chat fails
            try:
                return self._generate_api_text(prompt, max_new_tokens, temperature, top_p)
            except Exception as e2:
                print(f"Fallback generation also failed: {e2}")
                return ""

    def _generate_api_text(
        self,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
        top_p: float
    ) -> str:
        """Fallback: Generate using text_generation endpoint"""
        try:
            response = self.client.text_generation(
                prompt=prompt,
                model=self.model_name,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p
            )
            return response if isinstance(response, str) else ""
        except Exception as e:
            print(f"Text generation error: {e}")
            return ""

    def _generate_local(
        self,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
        top_p: float
    ) -> str:
        """Generate using local model"""
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

            generated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return generated[len(prompt):]

        except Exception as e:
            print(f"Local generation error: {e}")
            return ""

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return {
            "model_name": self.model_name,
            "mode": "api" if self.use_api else "local",
            "quantization": self.quantization,
            "client_ready": self.client is not None if self.use_api else self.model is not None
        }
