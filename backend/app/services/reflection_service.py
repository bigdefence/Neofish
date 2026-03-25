import logging
from typing import List, Dict, Any
import uuid
from datetime import datetime, timezone

from . import neo4j_store
from ..utils.llm_client import LLMClient

logger = logging.getLogger("neofish.reflection")

class ReflectionService:
    def __init__(self, llm: LLMClient = None):
        self.llm = llm or LLMClient()

    def reflect_on_episodes(self, graph_id: str, limit: int = 20):
        """
        최근의 구체적인 에피소드 기억(SimEpisode)들을 모아서
        일반화된 의미 기억(Semantic Memory)으로 변환(Consolidation)합니다.
        """
        logger.info(f"Triggering Memory Reflection for graph {graph_id}...")
        
        episodes = neo4j_store.fetch_unreflected_episodes(graph_id, limit)
        if not episodes or len(episodes) < 3:
            logger.info("Not enough new episodes for reflection.")
            return

        episode_texts = [f"- {ep['text']}" for ep in episodes if ep.get('text')]
        episode_uuids = [ep['uuid'] for ep in episodes]
        
        if not episode_texts:
            return

        insights = self._generate_semantic_insights(episode_texts)
        if insights:
            logger.info(f"Generated {len(insights)} semantic insights.")
            neo4j_store.store_semantic_memories(graph_id, insights, episode_uuids)
            logger.info("Reflection complete.")
        else:
            logger.info("No significant insights generated.")
            # Mark them as reflected anyway so we don't retry forever
            neo4j_store.mark_episodes_reflected(graph_id, episode_uuids)

    def _generate_semantic_insights(self, episode_texts: List[str]) -> List[str]:
        system = "You are a cognitive memory system. Extract high-level, generalized semantic facts from the given specific episodic events."
        user = f"""
Analyze the following recent episodic memories of an agent or system.
Extract generalized rules, long-term preferences, overarching behavioral patterns, or systemic facts that are true beyond a single event.
Do NOT just summarize the events. Infer the underlying semantic knowledge.

Recent Episodes:
{chr(10).join(episode_texts)}

Return ONLY a JSON list of strings, where each string is a distinct semantic insight.
If there are no meaningful overarching insights, return an empty list [].
"""
        try:
            result = self.llm.chat_json([
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ], temperature=0.3)
            
            if isinstance(result, list):
                return [str(item) for item in result if isinstance(item, str)]
            return []
        except Exception as e:
            logger.error(f"Reflection LLM failed: {e}")
            return []
