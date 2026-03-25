"""
LLM 클라이언트 래퍼
OpenAI 호환 형식으로 통일해 호출합니다.
"""

import json
import re
import logging
from typing import Optional, Dict, Any, List
from openai import OpenAI
from google import genai

from ..config import Config

logger = logging.getLogger("neofish.llm_client")


class LLMClient:
    """LLM 클라이언트"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY가 설정되지 않았습니다.")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        # Google Generative AI Client 초기화 (Embedding용)
        try:
            google_key = getattr(Config, 'GOOGLE_API_KEY', self.api_key)
            self.google_client = genai.Client(api_key=google_key)
        except Exception as e:
            logger.warning(f"Google Generative AI Client 초기화 실패: {e}")
            self.google_client = None
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        채팅 요청을 전송합니다.
        
        Args:
            messages: 메시지 목록
            temperature: 온도 파라미터
            max_tokens: 최대 토큰 수
            response_format: 응답 형식(예: JSON 모드)
            
        Returns:
            모델 응답 텍스트
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # 일부 모델(예: MiniMax M2.5)은 content에 <think>를 포함하므로 제거
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        채팅 요청을 전송하고 JSON으로 반환합니다.
        
        Args:
            messages: 메시지 목록
            temperature: 온도 파라미터
            max_tokens: 최대 토큰 수
            
        Returns:
            파싱된 JSON 객체
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        # 마크다운 코드 블록 표기 제거
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"LLM이 반환한 JSON 형식이 올바르지 않습니다: {cleaned_response}")

    def embed(self, text: str) -> List[float]:
        """
        텍스트의 임베딩 벡터를 생성합니다 (Google Gemini Embedding 사용).
        """
        if not text:
            return []
        
        if not self.google_client:
            logger.error("Google Generative AI Client가 초기화되지 않았습니다.")
            return []

        try:
            # gemini-embedding-2-preview 등 구글 모델 사용
            res = self.google_client.models.embed_content(
                model=Config.LLM_EMBEDDING_MODEL,
                contents=text
            )
            return res.embeddings[0].values
        except Exception as e:
            logger.error(f"Gemini 임베딩 생성 실패: {e}")
            return []

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        여러 텍스트의 임베딩 벡터를 한 번에 생성합니다 (Google Gemini Embedding 사용).
        """
        if not texts:
            return []
            
        if not self.google_client:
            logger.error("Google Generative AI Client가 초기화되지 않았습니다.")
            return []

        try:
            # 텍스트들을 하나의 리스트로 전달
            res = self.google_client.models.embed_content(
                model=Config.LLM_EMBEDDING_MODEL,
                contents=texts
            )
            return [e.values for e in res.embeddings]
        except Exception as e:
            logger.error(f"Gemini 배치 임베딩 생성 실패: {e}")
            return []
