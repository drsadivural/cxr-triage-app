"""
Unified LLM service supporting Azure OpenAI, Claude, and Gemini.
"""
import re
import json
from abc import ABC, abstractmethod
from typing import Optional, List
import httpx

from app.config import LLMSettings, AzureOpenAISettings, ClaudeSettings, GeminiSettings


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    async def rewrite_report(self, template_text: str) -> str:
        """Rewrite a report template."""
        pass


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider."""
    
    def __init__(self, settings: AzureOpenAISettings):
        self.settings = settings
        self.base_url = f"{settings.endpoint}/openai/deployments/{settings.deployment_name}"
    
    async def generate(self, prompt: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "api-key": self.settings.api_key,
        }
        
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "max_tokens": self.settings.max_tokens,
        }
        
        url = f"{self.base_url}/chat/completions?api-version={self.settings.api_version}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def rewrite_report(self, template_text: str) -> str:
        prompt = f"""You are a medical report editor. Rewrite the following radiology report to improve readability and flow while maintaining all clinical findings exactly as stated. Do NOT add, remove, or change any medical findings. Only improve grammar, sentence structure, and professional tone.

Original report:
{template_text}

Rewritten report:"""
        return await self.generate(prompt)


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, settings: ClaudeSettings):
        self.settings = settings
    
    async def generate(self, prompt: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.settings.api_key,
            "anthropic-version": "2023-06-01",
        }
        
        payload = {
            "model": self.settings.model,
            "max_tokens": self.settings.max_tokens,
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "messages": [{"role": "user", "content": prompt}],
        }
        
        url = f"{self.settings.base_url}/v1/messages"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]
    
    async def rewrite_report(self, template_text: str) -> str:
        prompt = f"""You are a medical report editor. Rewrite the following radiology report to improve readability and flow while maintaining all clinical findings exactly as stated. Do NOT add, remove, or change any medical findings. Only improve grammar, sentence structure, and professional tone.

Original report:
{template_text}

Rewritten report:"""
        return await self.generate(prompt)


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""
    
    def __init__(self, settings: GeminiSettings):
        self.settings = settings
    
    async def generate(self, prompt: str) -> str:
        headers = {
            "Content-Type": "application/json",
        }
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.settings.temperature,
                "topP": self.settings.top_p,
                "maxOutputTokens": self.settings.max_output_tokens,
            },
        }
        
        url = f"{self.settings.base_url}/models/{self.settings.model}:generateContent?key={self.settings.api_key}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    
    async def rewrite_report(self, template_text: str) -> str:
        prompt = f"""You are a medical report editor. Rewrite the following radiology report to improve readability and flow while maintaining all clinical findings exactly as stated. Do NOT add, remove, or change any medical findings. Only improve grammar, sentence structure, and professional tone.

Original report:
{template_text}

Rewritten report:"""
        return await self.generate(prompt)


class LLMService:
    """Unified LLM service."""
    
    def __init__(self, settings: LLMSettings):
        self.settings = settings
        self.provider: Optional[LLMProvider] = None
        self._init_provider()
    
    def _init_provider(self):
        """Initialize the active provider."""
        if self.settings.active_provider == "azure_openai" and self.settings.azure_openai.enabled:
            self.provider = AzureOpenAIProvider(self.settings.azure_openai)
        elif self.settings.active_provider == "claude" and self.settings.claude.enabled:
            self.provider = ClaudeProvider(self.settings.claude)
        elif self.settings.active_provider == "gemini" and self.settings.gemini.enabled:
            self.provider = GeminiProvider(self.settings.gemini)
        else:
            self.provider = None
    
    def is_available(self) -> bool:
        """Check if LLM is available and enabled."""
        return self.provider is not None and self.settings.llm_rewrite_enabled
    
    async def generate(self, prompt: str) -> Optional[str]:
        """Generate text using the active provider."""
        if not self.provider:
            return None
        try:
            return await self.provider.generate(prompt)
        except Exception as e:
            print(f"LLM generation failed: {e}")
            return None
    
    async def rewrite_report(self, template_text: str, findings: List[str]) -> Optional[str]:
        """
        Rewrite a report using LLM.
        Includes verification to ensure no new findings are introduced.
        """
        if not self.is_available():
            return None
        
        try:
            rewritten = await self.provider.rewrite_report(template_text)
            
            # Verify no new findings introduced
            if self._verify_no_new_findings(rewritten, findings):
                return rewritten
            else:
                print("LLM introduced new findings, reverting to template")
                return None
        except Exception as e:
            print(f"LLM rewrite failed: {e}")
            return None
    
    def _verify_no_new_findings(self, rewritten_text: str, original_findings: List[str]) -> bool:
        """
        Verify that the rewritten text doesn't introduce new findings.
        Returns True if safe, False if new findings detected.
        """
        # List of medical findings that should not appear if not in original
        medical_terms = [
            "pneumothorax", "pleural effusion", "effusion", "consolidation",
            "atelectasis", "cardiomegaly", "edema", "pulmonary edema",
            "nodule", "mass", "tumor", "cancer", "malignancy",
            "pneumonia", "infiltrate", "opacity", "lesion",
            "fracture", "emphysema", "fibrosis", "calcification",
            "lymphadenopathy", "mediastinal widening", "aortic aneurysm"
        ]
        
        rewritten_lower = rewritten_text.lower()
        original_findings_lower = [f.lower() for f in original_findings]
        
        for term in medical_terms:
            # Check if term appears in rewritten but not in original findings
            if term in rewritten_lower:
                # Check if this term or related term was in original
                term_found_in_original = False
                for orig in original_findings_lower:
                    if term in orig or orig in term:
                        term_found_in_original = True
                        break
                
                if not term_found_in_original:
                    # Check if it's a negation
                    negation_patterns = [
                        f"no {term}", f"no evidence of {term}", f"without {term}",
                        f"negative for {term}", f"absent {term}", f"no significant {term}"
                    ]
                    is_negated = any(neg in rewritten_lower for neg in negation_patterns)
                    
                    if not is_negated:
                        print(f"New finding detected in LLM output: {term}")
                        return False
        
        return True


def get_llm_service(settings: LLMSettings) -> LLMService:
    """Factory function to create LLM service."""
    return LLMService(settings)
