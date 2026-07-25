"""
CLARIUS Backend - Ollama Client Interface

This module provides direct interaction with the local Ollama LLM service
without requiring heavy external dependencies (ADR-004).
"""

import json
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError
from app.core.config import settings

class OllamaClient:
    """Offline HTTP client for communicating with local Ollama runtime."""
    
    def __init__(self, host: str = None, model: str = None):
        self.host = host or settings.OLLAMA_HOST
        self.model = model or settings.OLLAMA_MODEL

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2) -> str:
        """Call Ollama's generation endpoint synchronously."""
        url = f"{self.host}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
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
                            res_text = '\n'.join(clean_lines).strip()
                            
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
