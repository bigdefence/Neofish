"""
시뮬레이션 액션을 Neo4j 그래프 메모리(SimEpisode)에 반영한다.
"""

import time
import threading
import json
import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from queue import Queue, Empty

from ..utils.logger import get_logger
from .neo4j_store import add_sim_memory_episode_batch

logger = get_logger('neofish.graph_memory_updater')

IGNORED_ACTION_TYPES = {"DO_NOTHING", "REFRESH", "TREND"}


@dataclass
class AgentActivity:
    """Agent"""
    platform: str           # twitter / reddit
    agent_id: int
    agent_name: str
    action_type: str        # CREATE_POST, LIKE_POST, etc.
    action_args: Dict[str, Any]
    round_num: int
    timestamp: str
    
    def to_episode_text(self) -> str:
        """액션을 자연어 한 줄로 요약한다."""
        # 타입생성
        action_descriptions = {
            "CREATE_POST": self._describe_create_post,
            "LIKE_POST": self._describe_like_post,
            "DISLIKE_POST": self._describe_dislike_post,
            "REPOST": self._describe_repost,
            "QUOTE_POST": self._describe_quote_post,
            "FOLLOW": self._describe_follow,
            "CREATE_COMMENT": self._describe_create_comment,
            "LIKE_COMMENT": self._describe_like_comment,
            "DISLIKE_COMMENT": self._describe_dislike_comment,
            "SEARCH_POSTS": self._describe_search,
            "SEARCH_USER": self._describe_search_user,
            "MUTE": self._describe_mute,
        }
        
        describe_func = action_descriptions.get(self.action_type, self._describe_generic)
        description = describe_func()
        
        # 최종 표시 형식: "AgentName: 행동 설명"
        return f"{self.agent_name}: {description}"

    def to_memory_payload(self) -> Dict[str, Any]:
        text = self.to_episode_text().strip()
        signature = self._build_memory_signature()
        return {
            "text": text,
            "summary": text,
            "memory_key": hashlib.sha1(signature.encode("utf-8")).hexdigest(),
            "signature": signature,
            "agent_name": (self.agent_name or "").strip(),
            "action_type": (self.action_type or "").strip().upper(),
            "round_num": self.round_num or 0,
            "importance_score": self._estimate_importance_score(),
        }

    def _build_memory_signature(self) -> str:
        keys_by_action = {
            "CREATE_POST": ["content"],
            "CREATE_COMMENT": ["content", "post_author_name", "post_content"],
            "LIKE_POST": ["post_author_name", "post_content"],
            "DISLIKE_POST": ["post_author_name", "post_content"],
            "REPOST": ["original_author_name", "original_content"],
            "QUOTE_POST": ["original_author_name", "original_content", "quote_content", "content"],
            "FOLLOW": ["target_user_name"],
            "MUTE": ["target_user_name"],
            "LIKE_COMMENT": ["comment_author_name", "comment_content"],
            "DISLIKE_COMMENT": ["comment_author_name", "comment_content"],
            "SEARCH_POSTS": ["query", "keyword"],
            "SEARCH_USER": ["query", "username"],
        }
        parts = [
            (self.platform or "").strip().lower(),
            (self.agent_name or "").strip().lower(),
            (self.action_type or "").strip().upper(),
        ]
        for key in keys_by_action.get(self.action_type, []):
            normalized = self._normalize_signature_value(self.action_args.get(key))
            if normalized:
                parts.append(normalized)

        if len(parts) == 3:
            fallback = self._normalize_signature_value(
                json.dumps(self.action_args or {}, sort_keys=True, ensure_ascii=False)
            )
            if fallback:
                parts.append(fallback)

        return "|".join(parts)

    def _estimate_importance_score(self) -> float:
        base_scores = {
            "CREATE_POST": 90.0,
            "QUOTE_POST": 86.0,
            "CREATE_COMMENT": 76.0,
            "REPOST": 70.0,
            "FOLLOW": 60.0,
            "MUTE": 60.0,
            "LIKE_POST": 52.0,
            "DISLIKE_POST": 52.0,
            "LIKE_COMMENT": 44.0,
            "DISLIKE_COMMENT": 44.0,
            "SEARCH_POSTS": 30.0,
            "SEARCH_USER": 28.0,
        }
        score = base_scores.get(self.action_type, 40.0)

        content = self._normalize_signature_value(
            self.action_args.get("content")
            or self.action_args.get("quote_content")
            or self.action_args.get("post_content")
            or self.action_args.get("original_content")
            or self.action_args.get("comment_content")
        )
        if content:
            score += min(len(content) / 18.0, 10.0)

        if any(
            self.action_args.get(key)
            for key in ("post_author_name", "target_user_name", "original_author_name", "comment_author_name")
        ):
            score += 4.0

        return max(10.0, min(100.0, round(score, 2)))

    @staticmethod
    def _normalize_signature_value(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip().lower()
        if not text:
            return ""
        text = " ".join(text.split())
        return text[:160]
    
    def _describe_create_post(self) -> str:
        content = self.action_args.get("content", "")
        if content:
            return f"게시글 '{content}'"
        return "게시글 작성"
    
    def _describe_like_post(self) -> str:
        """좋아요 대상 게시글 정보를 정리한다."""
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if post_content and post_author:
            return f"{post_author}의 게시글 '{post_content}'"
        if post_content:
            return f"게시글 '{post_content}'"
        if post_author:
            return f"{post_author}의 게시글"
        return "게시글"
    
    def _describe_dislike_post(self) -> str:
        """비추천 대상 게시글 정보를 정리한다."""
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if post_content and post_author:
            return f"{post_author}의 게시글 '{post_content}'"
        if post_content:
            return f"게시글 '{post_content}'"
        if post_author:
            return f"{post_author}의 게시글"
        return "게시글"
    
    def _describe_repost(self) -> str:
        """리포스트 대상 원문 정보를 정리한다."""
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")
        
        if original_content and original_author:
            return f"{original_author}의 원문 '{original_content}'"
        if original_content:
            return f"원문 '{original_content}'"
        if original_author:
            return f"{original_author}의 원문"
        return "원문"
    
    def _describe_quote_post(self) -> str:
        """인용 대상 원문과 인용문을 함께 정리한다."""
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")
        quote_content = self.action_args.get("quote_content", "") or self.action_args.get("content", "")
        
        base = ""
        if original_content and original_author:
            base = f"{original_author}의 원문 '{original_content}'"
        elif original_content:
            base = f"원문 '{original_content}'"
        elif original_author:
            base = f"{original_author}의 원문"
        else:
            base = "원문"

        if quote_content:
            base += f", 인용문 '{quote_content}'"
        return base
    
    def _describe_follow(self) -> str:
        """팔로우 대상 사용자를 정리한다."""
        target_user_name = self.action_args.get("target_user_name", "")
        
        if target_user_name:
            return f"사용자 '{target_user_name}'"
        return "사용자"
    
    def _describe_create_comment(self) -> str:
        """댓글 내용과 대상 게시글 정보를 정리한다."""
        content = self.action_args.get("content", "")
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if content:
            if post_content and post_author:
                return f"{post_author}의 게시글 '{post_content}'에 댓글 '{content}'"
            elif post_content:
                return f"게시글 '{post_content}'에 댓글 '{content}'"
            elif post_author:
                return f"{post_author}에게 댓글 '{content}'"
            return f"댓글 '{content}'"
        return "댓글 작성"
    
    def _describe_like_comment(self) -> str:
        """좋아요 대상 댓글 정보를 정리한다."""
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")
        
        if comment_content and comment_author:
            return f"{comment_author}의 댓글 '{comment_content}'"
        if comment_content:
            return f"댓글 '{comment_content}'"
        if comment_author:
            return f"{comment_author}의 댓글"
        return "댓글"
    
    def _describe_dislike_comment(self) -> str:
        """비추천 대상 댓글 정보를 정리한다."""
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")
        
        if comment_content and comment_author:
            return f"{comment_author}의 댓글 '{comment_content}'"
        if comment_content:
            return f"댓글 '{comment_content}'"
        if comment_author:
            return f"{comment_author}의 댓글"
        return "댓글"
    
    def _describe_search(self) -> str:
        """검색 쿼리를 설명 텍스트로 변환한다."""
        query = self.action_args.get("query", "") or self.action_args.get("keyword", "")
        return f"검색 '{query}'" if query else "검색"
    
    def _describe_search_user(self) -> str:
        """사용자 검색 쿼리를 설명 텍스트로 변환한다."""
        query = self.action_args.get("query", "") or self.action_args.get("username", "")
        return f"검색 '{query}'" if query else "검색"
    
    def _describe_mute(self) -> str:
        """뮤트 대상 사용자를 정리한다."""
        target_user_name = self.action_args.get("target_user_name", "")
        
        if target_user_name:
            return f"사용자 '{target_user_name}'"
        return "사용자"
    
    def _describe_generic(self) -> str:
        # 알 수 없는 타입은 원본 action_type 사용
        return f"{self.action_type}"


class GraphMemoryUpdater:
    """
    시뮬레이션 액션 로그를 읽어 Neo4j SimEpisode 메모리를 업데이트한다.

    - 플랫폼별 액션을 배치로 처리
    - action_args의 핵심 맥락을 요약해 메모리 텍스트 생성
    - 재시도/중단 로직 포함
    """
    
    # 플랫폼별 배치 크기
    BATCH_SIZE = 5
    
    # 플랫폼(콘솔)
    PLATFORM_DISPLAY_NAMES = {
        'twitter': '1',
        'reddit': '2',
    }
    
    # (), 요청
    SEND_INTERVAL = 0.5
    
    # 설정
    MAX_RETRIES = 3
    RETRY_DELAY = 2  #초
    
    def __init__(self, graph_id: str):
        """
        Args:
            graph_id: Neo4j 그래프 ID(graph_id)
        """
        self.graph_id = graph_id
        self._activity_queue: Queue = Queue()
        
        # 플랫폼(플랫폼BATCH_SIZE)
        self._platform_buffers: Dict[str, List[AgentActivity]] = {
            'twitter': [],
            'reddit': [],
        }
        self._buffer_lock = threading.Lock()
        
        # 
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # 
        self._total_activities = 0
        self._total_sent = 0
        self._total_items_sent = 0
        self._failed_count = 0
        self._skipped_count = 0

        logger.info(
            "GraphMemoryUpdater 준비: graph_id=%s, batch_size=%s",
            graph_id,
            self.BATCH_SIZE,
        )
    
    def _get_platform_display_name(self, platform: str) -> str:
        """플랫폼"""
        return self.PLATFORM_DISPLAY_NAMES.get(platform.lower(), platform)
    
    def start(self):
        """시작"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"GraphMemoryUpdater-{self.graph_id[:8]}",
        )
        self._worker_thread.start()
        logger.info("GraphMemoryUpdater 시작: graph_id=%s", self.graph_id)
    
    def stop(self):
        """중지"""
        self._running = False
        
        # 
        self._flush_remaining()
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)
        
        logger.info(
            "GraphMemoryUpdater 중지: graph_id=%s, total_activities=%s, "
            "batches_sent=%s, items_sent=%s, failed=%s, skipped=%s",
            self.graph_id,
            self._total_activities,
            self._total_sent,
            self._total_items_sent,
            self._failed_count,
            self._skipped_count,
        )
    
    def add_activity(self, activity: AgentActivity):
        if activity.action_type in IGNORED_ACTION_TYPES:
            self._skipped_count += 1
            return

        """
        agent
        
        , :
        - CREATE_POST()
        - CREATE_COMMENT()
        - QUOTE_POST()
        - SEARCH_POSTS(검색)
        - SEARCH_USER(검색)
        - LIKE_POST/DISLIKE_POST(/)
        - REPOST()
        - FOLLOW()
        - MUTE()
        - LIKE_COMMENT/DISLIKE_COMMENT(/)
        
        action_args상세 정보(, ).
        
        Args:
            activity: Agent
        """
        # DO_NOTHING타입
        if activity.action_type == "DO_NOTHING":
            self._skipped_count += 1
            return
        
        self._activity_queue.put(activity)
        self._total_activities += 1
        logger.debug("메모리 큐: %s - %s", activity.agent_name, activity.action_type)
    
    def add_activity_from_dict(self, data: Dict[str, Any], platform: str):
        if not data.get("success", True):
            self._skipped_count += 1
            return

        """
        
        
        Args:
            data: actions.jsonl
            platform: 플랫폼 (twitter/reddit)
        """
        # 타입
        if "event_type" in data:
            return
        
        activity = AgentActivity(
            platform=platform,
            agent_id=data.get("agent_id", 0),
            agent_name=data.get("agent_name", ""),
            action_type=data.get("action_type", ""),
            action_args=data.get("action_args", {}),
            round_num=data.get("round", 0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )
        
        self.add_activity(activity)
    
    def _worker_loop(self):
        """플랫폼별 버퍼에 쌓인 액션을 배치로 전송한다."""
        while self._running or not self._activity_queue.empty():
            try:
                # (1)
                try:
                    activity = self._activity_queue.get(timeout=1)
                    
                    # 플랫폼
                    platform = activity.platform.lower()
                    with self._buffer_lock:
                        if platform not in self._platform_buffers:
                            self._platform_buffers[platform] = []
                        self._platform_buffers[platform].append(activity)
                        
                        # 플랫폼
                        if len(self._platform_buffers[platform]) >= self.BATCH_SIZE:
                            batch = self._platform_buffers[platform][:self.BATCH_SIZE]
                            self._platform_buffers[platform] = self._platform_buffers[platform][self.BATCH_SIZE:]
                            # 
                            self._send_batch_activities(batch, platform)
                            # , 요청
                            time.sleep(self.SEND_INTERVAL)
                    
                except Empty:
                    pass
                    
            except Exception as e:
                logger.error(f": {e}")
                time.sleep(1)
    
    def _send_batch_activities(self, activities: List[AgentActivity], platform: str):
        """배치를 Neo4j SimEpisode로 저장한다."""
        if not activities:
            return

        episode_texts = [activity.to_episode_text() for activity in activities]
        combined_text = "\n".join(episode_texts)
        memory_items = [activity.to_memory_payload() for activity in activities]

        for attempt in range(self.MAX_RETRIES):
            try:
                add_sim_memory_episode_batch(
                    self.graph_id,
                    combined_text,
                    platform,
                    memory_items,
                )
                self._total_sent += 1
                self._total_items_sent += len(activities)
                display_name = self._get_platform_display_name(platform)
                logger.info(
                    "Neo4j SimEpisode %s건 %s graph_id=%s",
                    len(activities),
                    display_name,
                    self.graph_id,
                )
                
                # --- 메모리 회고 (Cognitive Reflection) ---
                if self._total_sent % 5 == 0:  # 5번 배치 보낼 때마다 회고 트리거 (임의의 주기)
                    try:
                        from .reflection_service import ReflectionService
                        import threading
                        # 회고는 시간이 오래 걸릴 수 있으므로 별도 스레드에서 실행
                        threading.Thread(
                            target=ReflectionService().reflect_on_episodes,
                            args=(self.graph_id,),
                            daemon=True
                        ).start()
                    except Exception as e:
                        logger.warning(f"Failed to start reflection thread: {e}")
                        
                return
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(
                        "Neo4j 메모리 저장 실패 (%s/%s): %s",
                        attempt + 1,
                        self.MAX_RETRIES,
                        e,
                    )
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    logger.error("Neo4j 메모리 저장 최종 실패: %s", e)
                    self._failed_count += 1
    
    def _flush_remaining(self):
        """진행 중"""
        # 진행 중, 
        while not self._activity_queue.empty():
            try:
                activity = self._activity_queue.get_nowait()
                platform = activity.platform.lower()
                with self._buffer_lock:
                    if platform not in self._platform_buffers:
                        self._platform_buffers[platform] = []
                    self._platform_buffers[platform].append(activity)
            except Empty:
                break
        
        # 플랫폼진행 중(BATCH_SIZE)
        with self._buffer_lock:
            for platform, buffer in self._platform_buffers.items():
                if buffer:
                    display_name = self._get_platform_display_name(platform)
                    logger.info(f"{display_name}플랫폼 {len(buffer)}건")
                    self._send_batch_activities(buffer, platform)
            # 
            for platform in self._platform_buffers:
                self._platform_buffers[platform] = []
    
    def get_stats(self) -> Dict[str, Any]:
        """정보"""
        with self._buffer_lock:
            buffer_sizes = {p: len(b) for p, b in self._platform_buffers.items()}
        
        return {
            "graph_id": self.graph_id,
            "batch_size": self.BATCH_SIZE,
            "total_activities": self._total_activities,  # 
            "batches_sent": self._total_sent,            # 
            "items_sent": self._total_items_sent,        # 
            "failed_count": self._failed_count,          # 실패
            "skipped_count": self._skipped_count,        # (DO_NOTHING)
            "queue_size": self._activity_queue.qsize(),
            "buffer_sizes": buffer_sizes,                # 플랫폼
            "running": self._running,
        }


class GraphMemoryManager:
    """시뮬레이션별 GraphMemoryUpdater 생명주기 관리."""

    _updaters: Dict[str, GraphMemoryUpdater] = {}
    _lock = threading.Lock()
    
    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str) -> GraphMemoryUpdater:
        """
        Args:
            simulation_id: 시뮬레이션 ID
            graph_id: Neo4j 그래프 ID

        Returns:
            GraphMemoryUpdater
        """
        with cls._lock:
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()

            updater = GraphMemoryUpdater(graph_id)
            updater.start()
            cls._updaters[simulation_id] = updater
            
            logger.info(f"그래프: simulation_id={simulation_id}, graph_id={graph_id}")
            return updater
    
    @classmethod
    def get_updater(cls, simulation_id: str) -> Optional[GraphMemoryUpdater]:
        """시뮬레이션"""
        return cls._updaters.get(simulation_id)
    
    @classmethod
    def stop_updater(cls, simulation_id: str):
        """중지시뮬레이션"""
        with cls._lock:
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
                del cls._updaters[simulation_id]
                logger.info(f"중지그래프: simulation_id={simulation_id}")
    
    #  stop_all 호출
    _stop_all_done = False
    
    @classmethod
    def stop_all(cls):
        """중지"""
        # 호출
        if cls._stop_all_done:
            return
        cls._stop_all_done = True
        
        with cls._lock:
            if cls._updaters:
                for simulation_id, updater in list(cls._updaters.items()):
                    try:
                        updater.stop()
                    except Exception as e:
                        logger.error(f"중지실패: simulation_id={simulation_id}, error={e}")
                cls._updaters.clear()
            logger.info("중지그래프")
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """정보"""
        return {
            sim_id: updater.get_stats() 
            for sim_id, updater in cls._updaters.items()
        }
