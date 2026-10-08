"""
CLARIUS Backend - Ollama Client Interface

This module provides direct interaction with the local Ollama LLM service
without requiring heavy external dependencies (ADR-004).
"""

import time
import json
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError
from app.core.config import settings
from app.core.performance_logger import get_current_timer

class OllamaClient:
    """Offline HTTP client for communicating with local Ollama runtime."""

    def __init__(self, host: str = None, model: str = None):
        self.host = host or settings.OLLAMA_HOST
        self.model = model or settings.OLLAMA_MODEL
        self._resolved_model: Optional[str] = None

    def get_active_model(self) -> str:
        """Resolve available Ollama model tag, falling back to any installed Qwen/Llama model if needed."""
        if self._resolved_model:
            return self._resolved_model

        target = self.model
        try:
            req = Request(f"{self.host}/api/tags", method="GET")
            with urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    installed_models = [m.get("name", "") for m in data.get("models", [])]
                    
                    if target in installed_models or any(target in m for m in installed_models):
                        self._resolved_model = target
                        return target
                        
                    # Match candidate model names
                    for candidate in ["qwen2.5:3b", "qwen2.5:7b", "qwen3:4b-instruct", "qwen2.5-coder", "qwen"]:
                        for inst in installed_models:
                            if candidate in inst:
                                self._resolved_model = inst
                                return inst
                                
                    if installed_models:
                        self._resolved_model = installed_models[0]
                        return installed_models[0]
        except Exception:
            pass

        self._resolved_model = target
        return target

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2, fast_mode: bool = False, purpose: str = "general") -> str:
        """Call Ollama's generation endpoint synchronously with timing instrumentation."""
        timer = get_current_timer()
        t_start = time.perf_counter()
        url = f"{self.host}/api/generate"
        active_model = self.get_active_model()
        
        payload = {
            "model": active_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0 if fast_mode else temperature,
                "top_p": 0.85,
                # SQL statements are 30-80 tokens; capping num_predict prevents long runaway generation
                "num_predict": 160 if fast_mode else 512,
                "stop": ["```\n\n", "Question:", "User:"] if fast_mode else ["Question:", "User:"]
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        data = json.dumps(payload).encode("utf-8")
        
        try:
            req = Request(
                url, 
                data=data, 
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlopen(req, timeout=240.0) as response:
                if response.status == 200:
                    resp_json = json.loads(response.read().decode("utf-8"))
                    res_text = resp_json.get("response", "").strip()
                    
                    # Strip <think>...</think> blocks
                    import re
                    res_text = re.sub(r'(?i)<think>.*?</think>', '', res_text, flags=re.DOTALL).strip()
                    
                    # Strip custom thinking blocks starting with 'Thinking...'
                    if res_text.lower().startswith("thinking"):
                        parts = re.split(r'\n\s*\n', res_text, 1)
                        if len(parts) > 1:
                            res_text = parts[1].strip()
                        else:
                            lines = res_text.split('\n')
                            clean_lines = []
                            in_thinking = True
                            for line in lines:
                                l_strip = line.strip()
                                if in_thinking:
                                    if l_strip.lower().startswith("thinking") or l_strip.startswith("- ") or l_strip.startswith("* ") or not l_strip:
                                        continue
                                    else:
                                        in_thinking = False
                                clean_lines.append(line)
                    duration = time.perf_counter() - t_start
                    if timer:
                        timer.log(f"Ollama LLM call completed (purpose: {purpose}, duration: {duration:.2f}s)")
                    return res_text
        except URLError as e:
            raise RuntimeError(f"Failed to reach local Ollama host at {self.host}. Is Ollama running? Details: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {str(e)}")
            
        raise RuntimeError("Empty response received from Ollama service.")


# Global client instance
ollama_client = OllamaClient()

def get_ollama_client() -> OllamaClient:
    """FastAPI Dependency."""
    return ollama_client
