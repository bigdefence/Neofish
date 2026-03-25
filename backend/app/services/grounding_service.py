"""
Gemini Grounding (Google Search) 서비스
"""
from typing import Optional, List
import json
import requests
from requests.exceptions import RequestException
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('neofish.grounding')

class GroundingService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.LLM_API_KEY
        # 현실적인 최상위 추론 모델인 gemini-3.1-flash-lite 사용 (안정적이고 복합 지시 이행에 탁월)
        self.model = "gemini-3.1-flash-lite-preview"
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def generate_grounded_text(self, requirements: str) -> str:
        """
        Google Search를 활용하여 요구사항에 대한 다각도 검색을 수행하고 실시간 배경지식을 수집하여 반환한다.
        """
        prompt = f"""
        당신은 최고 수준의 '심층 전략 리서치 에이전트'입니다.
        당신의 임무는 아래 시뮬레이션 요구사항을 바탕으로 **최소 5개 이상의 서로 다른 관점의 검색 쿼리를 생성**하고, 
        이를 통해 수집된 방대한 정보를 통합하여 압도적인 디테일의 '현실 시드(Seed) 문서'를 작성하는 것입니다.

        [시뮬레이션 요구사항]
        {requirements}

        [단계별 작업 지침]
        1. **다각도 검색 전략 수립 (Multi-Query Generation)**:
           요구사항을 분석하여 아래 영역들에 대해 각각 최적화된 검색 쿼리를 생성하고 검색 도구를 호출하세요.
           - **정치/법적 관점**: 관련 규제, 정부 정책, 법적 쟁점, 정치적 대립 구도
           - **경제/산업 관점**: 시장 규모, 기업 동향, 자본의 흐름, 경제적 이해관계
           - **사회/문화적 관점**: 여론의 흐름, 대중의 심리, 소셜 미디어 트렌드, 문화적 배경
           - **기술/과학적 관점**: 핵심 기술 수준, 최신 혁신 사례, 기술적 한계 및 가능성
           - **핵심 인물 및 조직**: 실존하는 주요 인물, 기업, 단체의 최근 행보 및 발언

        2. **정보 수집 및 교차 분석**:
           생성된 각 쿼리에 대해 검색 도구를 실행하고, 각 검색 결과 사이의 연관성과 모순점을 파악하세요. 
           단편적인 정보가 아닌, 'A 사건이 B 산업에 미치는 영향'과 같은 입체적인 정보를 추출해야 합니다.

        3. **최종 현실 시드(Seed) 리포트 작성**:
           수집된 모든 정보를 바탕으로 시뮬레이션 엔진이 완벽하게 작동할 수 있도록 5000자 이상의 매우 상세한 리포트를 작성하세요.

        [리포트 필수 포함 내용]
        - **## 1. 쿼리별 리서치 결과 요약**: 어떤 관점에서 어떤 정보를 조사했는지 명시
        - **## 2. 입체적 상황 분석 (Context Deep-Dive)**: 거시/미시 경제 및 정치적 상황
        - **## 3. 핵심 엔터티 마스터 리스트**: 최소 15개 이상의 인물/조직에 대한 상세 프로필과 숨겨진 야망
        - **## 4. 실시간 이슈 및 여론 흐름**: Twitter, Reddit 등에서의 실제 반응과 대립 구조
        - **## 5. 시뮬레이션 트리거 및 변수**: 시뮬레이션 도중 발생할 수 있는 주요 사건(Events) 후보

        [작성 원칙]
        - 반드시 `google_search` 도구를 반복적으로 활용하여 최신 데이터를 확보할 것.
        - 정보의 소스가 명확해야 하며, 수치와 고유 명사를 구체적으로 기입할 것.
        - 시뮬레이션 에이전트들이 자신의 페르소나를 구축할 때 충분한 근거 자료가 될 수 있도록 서술할 것.
        """

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "tools": [{"google_search": {}}]
        }

        try:
            logger.info(f"요청 중: Gemini Grounding API (Multi-Query Mode)...")
            response = requests.post(self.base_url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                content = data["candidates"][0]["content"]["parts"][0].get("text", "")
                
                # Check for grounding metadata
                grounding_metadata = data["candidates"][0].get("groundingMetadata", {})
                web_search_queries = grounding_metadata.get("webSearchQueries", [])
                if web_search_queries:
                    logger.info(f"사용된 검색 쿼리 목록: {web_search_queries}")
                
                return content
            else:
                logger.error(f"응답에 문제가 있습니다: {json.dumps(data)}")
                return f"검색 결과 또는 생성 내용을 가져오지 못했습니다. 원본 프롬프트 내용으로 기반 텍스트를 구성합니다.\n\n요구사항: {requirements}"
                
        except RequestException as e:
            logger.error(f"Gemini Grounding API 호출 실패: {str(e)}")
            if e.response is not None:
                logger.error(f"Error Body: {e.response.text}")
            raise e
        except Exception as e:
            logger.error(f"예상치 못한 오류: {str(e)}")
            raise e
