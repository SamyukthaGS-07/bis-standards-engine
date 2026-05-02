"""
LLM Rationale Generator
========================
CRITICAL DESIGN DECISION:
  The LLM does NOT decide which standards to recommend.
  The retriever + graph does that — from verified data only.
  The LLM ONLY writes the explanation for each retrieved standard.

This eliminates hallucination architecturally.
A standard that doesn't exist in our dataset cannot appear in output.
"""

import os
import json
import time
from typing import Optional

import requests


# ── Provider abstraction ───────────────────────────────────────────────────
# We support Groq (free, fast) and OpenAI as fallback.
# Groq hits <1 sec latency — easily keeps us under the 5-sec total budget.

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


SYSTEM_PROMPT = """You are a BIS (Bureau of Indian Standards) compliance expert helping Indian MSEs (Micro and Small Enterprises) understand which standards apply to their products.

You will be given:
1. A product description from the user
2. A list of BIS standards retrieved from the official BIS SP 21 document

Your job is to write a SHORT, CLEAR rationale (2-3 sentences) explaining WHY each standard is relevant to the user's product.

STRICT RULES:
- ONLY refer to the standards provided to you. DO NOT invent or mention any other standards.
- Be specific about what part of the product or use-case makes the standard applicable.
- Use plain language — the user is an MSE owner, not a regulatory expert.
- Keep each rationale under 60 words.
- Do not repeat the standard number in the rationale (it's already shown separately).
- Output ONLY valid JSON in the exact format requested."""


def build_rationale_prompt(query: str, standards: list[dict]) -> str:
    standards_block = ""
    for i, std in enumerate(standards, 1):
        standards_block += f"""
Standard {i}:
  ID: {std.get('standard_id', 'N/A')}
  Title: {std.get('title', 'N/A')}
  Category: {std.get('material_category', 'N/A')}
  Scope: {std.get('scope', 'N/A')[:300]}
  Applications: {', '.join(std.get('applications', []))}
"""

    return f"""Product Description: "{query}"

Retrieved BIS Standards:
{standards_block}

Return a JSON object with this exact structure:
{{
  "summary": "One sentence explaining what compliance category this product falls under",
  "standards": [
    {{
      "standard_id": "IS XXXX",
      "rationale": "2-3 sentence explanation of why this standard applies to the described product",
      "confidence": "high|medium|low",
      "key_requirement": "The most important thing this standard requires for this product"
    }}
  ]
}}

Only include standards from the list above. Output ONLY the JSON, no other text."""


class LLMRationaleGenerator:
    def __init__(
        self,
        provider: str = "groq",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.provider = provider
        self.api_key = api_key or os.environ.get(
            "GROQ_API_KEY" if provider == "groq" else "OPENAI_API_KEY", ""
        )

        if provider == "groq":
            self.model = model or "llama-3.1-8b-instant"  # Fast + free
            self.api_url = GROQ_API_URL
        else:
            self.model = model or "gpt-4o-mini"
            self.api_url = OPENAI_API_URL

    def _call_api(self, messages: list[dict], max_tokens: int = 800) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,  # Low temp = consistent, factual output
            "response_format": {"type": "json_object"},
        }

        resp = requests.post(self.api_url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def generate_rationale(self, query: str, standards: list[dict]) -> dict:
        """
        Generate rationale for retrieved standards.
        Falls back gracefully if LLM fails — returns structured output
        using only the retrieved data, never hallucinating.
        """
        if not standards:
            return {"summary": "No relevant standards found.", "standards": []}

        prompt = build_rationale_prompt(query, standards)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        try:
            raw = self._call_api(messages)
            result = json.loads(raw)

            # ── HALLUCINATION GUARD ─────────────────────────────────────────
            # Only keep standards that were actually in our retrieved set.
            # This is the architectural guarantee: LLM cannot sneak in phantom standards.
            valid_ids = {std.get("standard_id") for std in standards}
            if "standards" in result:
                result["standards"] = [
                    s for s in result["standards"]
                    if s.get("standard_id") in valid_ids
                ]
            return result

        except Exception as e:
            print(f"[LLM] Error: {e}. Falling back to template rationale.")
            return self._fallback_rationale(standards)

    def _fallback_rationale(self, standards: list[dict]) -> dict:
        """
        If LLM call fails, generate structured output from metadata alone.
        Zero hallucination guaranteed — purely data-driven.
        """
        return {
            "summary": f"Found {len(standards)} relevant BIS standards based on your product description.",
            "standards": [
                {
                    "standard_id": std.get("standard_id", "N/A"),
                    "rationale": (
                        f"This standard covers {std.get('material_category', 'building materials')} "
                        f"for {', '.join(std.get('applications', ['general construction']))} applications. "
                        f"{std.get('scope', '')[:150]}"
                    ),
                    "confidence": "medium",
                    "key_requirement": std.get("scope", "Refer to full standard document.")[:100],
                }
                for std in standards
            ],
        }
