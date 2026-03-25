import io
import json
import os
import re
import threading
import time

from google import genai
from google.genai import types
from pydub import AudioSegment

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger("neofish.services.podcast")

_MAX_RETRIES = 2
_RETRY_DELAY = 2.0
_MIN_TTS_REQUEST_INTERVAL = 6.5
_RATE_LIMIT_BUFFER_SECONDS = 0.5
_SILENCE_MS = 500
_PCM_SAMPLE_RATE = 24000
_PCM_SAMPLE_WIDTH = 2
_PCM_CHANNELS = 1
_MAX_REPORT_CHARS_FOR_SCRIPT = 12000
_MAX_SCRIPT_TURNS = 8

TTS_VOICE_SPEAKER_A = "Aoede"
TTS_VOICE_SPEAKER_B = "Sadaltager"
TTS_VOICE_FALLBACK = TTS_VOICE_SPEAKER_A


class PodcastGenerator:
    """Generate a dialogue-style podcast script and audio from a report."""

    _tts_rate_lock = threading.Lock()
    _tts_next_request_at = 0.0

    def __init__(
        self,
        api_key=None,
        model_name="gemini-2.5-flash-preview-tts",
        script_model_name="gemini-3.1-flash-lite-preview",
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.model_name = self._normalize_model_name(model_name)
        self.script_model_name = self._normalize_model_name(script_model_name)

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or LLM_API_KEY is not configured.")

    @staticmethod
    def _normalize_model_name(model_name: str) -> str:
        if model_name.startswith("models/"):
            return model_name.split("/", 1)[1]
        return model_name

    def _create_client(self) -> genai.Client:
        return genai.Client(api_key=self.api_key)

    @staticmethod
    def _extract_text(response) -> str:
        if getattr(response, "text", None):
            return response.text

        texts = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                if getattr(part, "text", None):
                    texts.append(part.text)
        return "".join(texts).strip()

    @staticmethod
    def _extract_inline_audio(response) -> tuple[bytes, str | None]:
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                inline_data = getattr(part, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    return inline_data.data, getattr(inline_data, "mime_type", None)
        raise RuntimeError("Audio generation failed: no inline audio was returned.")

    @staticmethod
    def _build_audio_segment(audio_bytes: bytes, mime_type: str | None) -> AudioSegment:
        normalized_mime_type = (mime_type or "").lower()
        buffer = io.BytesIO(audio_bytes)

        if "wav" in normalized_mime_type:
            return AudioSegment.from_file(buffer, format="wav")
        if "mpeg" in normalized_mime_type or "mp3" in normalized_mime_type:
            return AudioSegment.from_file(buffer, format="mp3")
        if "ogg" in normalized_mime_type:
            return AudioSegment.from_file(buffer, format="ogg")

        return AudioSegment.from_raw(
            buffer,
            sample_width=_PCM_SAMPLE_WIDTH,
            frame_rate=_PCM_SAMPLE_RATE,
            channels=_PCM_CHANNELS,
        )

    @staticmethod
    def _parse_retry_delay_seconds(error: Exception) -> float | None:
        message = str(error)
        patterns = [
            r"Please retry in ([0-9]+(?:\.[0-9]+)?)s",
            r"'retryDelay': '([0-9]+(?:\.[0-9]+)?)s'",
            r'"retryDelay": "([0-9]+(?:\.[0-9]+)?)s"',
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return float(match.group(1))
        return None

    @staticmethod
    def _is_rate_limit_error(error: Exception) -> bool:
        message = str(error).upper()
        return "429" in message or "RESOURCE_EXHAUSTED" in message or "QUOTA" in message

    @classmethod
    def _wait_for_tts_slot(cls) -> None:
        while True:
            with cls._tts_rate_lock:
                now = time.monotonic()
                wait_seconds = cls._tts_next_request_at - now
                if wait_seconds <= 0:
                    cls._tts_next_request_at = now + _MIN_TTS_REQUEST_INTERVAL
                    return
            time.sleep(wait_seconds)

    @classmethod
    def _defer_tts_requests(cls, delay_seconds: float) -> None:
        target_time = time.monotonic() + max(0.0, delay_seconds)
        with cls._tts_rate_lock:
            cls._tts_next_request_at = max(cls._tts_next_request_at, target_time)

    @staticmethod
    def _trim_script(script: list) -> list:
        if len(script) <= _MAX_SCRIPT_TURNS:
            return script

        head_count = max(_MAX_SCRIPT_TURNS - 2, 1)
        trimmed_script = script[:head_count] + script[-2:]
        logger.warning(
            "Generated podcast script was trimmed from %s turns to %s turns to stay within the TTS quota.",
            len(script),
            len(trimmed_script),
        )
        return trimmed_script

    def generate_script(self, report_text: str) -> list:
        body = (report_text or "").strip()
        if len(body) > _MAX_REPORT_CHARS_FOR_SCRIPT:
            body = body[:_MAX_REPORT_CHARS_FOR_SCRIPT] + "\n\n[중략]"

        prompt = f"""
당신은 시사 분석 오디오 PD이자 스크립트 작가입니다. 아래 보고서를 실제 방송용 대화형 팟캐스트처럼 자연스럽게 재구성하세요.

[화자 역할]
- A: 진행자. 핵심을 짧게 정리하고 다음 질문으로 흐름을 만든다.
- B: 해설자. 보고서의 근거와 의미를 설명한다.

[작성 규칙]
1. 각 발화는 한 명이 말하는 자연스러운 문장으로 쓴다.
2. 과장된 감탄, 불필요한 군더더기, 마크다운 기호는 쓰지 않는다.
3. 각 turn의 text는 TTS에 바로 넣을 수 있도록 2~5문장, 400자 이내로 유지한다.
4. 숫자나 시계열 변화가 중요하면 짧게 짚되, 읽기 쉬운 문장으로 푼다.
5. 시작은 오늘 다룰 핵심 주제를 소개하고, 마지막은 실무적 시사점이나 관전 포인트로 마무리한다.

[분량]
- 전체는 JSON 배열 기준 6~8개의 turn으로 작성한다.
- A와 B가 번갈아 말하되, 필요하면 같은 화자가 최대 2번까지 연속으로 말할 수 있다.

보고서 원문:
{body}

반환은 설명 없이 JSON 배열만 출력하세요.
[
  {{"speaker": "A", "text": "..." }},
  {{"speaker": "B", "text": "..." }}
]
"""

        with self._create_client() as client:
            response = client.models.generate_content(
                model=self.script_model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )

        try:
            script = json.loads(self._extract_text(response))
            if not isinstance(script, list):
                if "script" in script and isinstance(script["script"], list):
                    script = script["script"]
                elif "dialogue" in script and isinstance(script["dialogue"], list):
                    script = script["dialogue"]
                else:
                    raise ValueError("Podcast script JSON must be a list.")
            if not script:
                raise ValueError("Generated podcast script is empty.")
            return self._trim_script(script)
        except Exception as error:
            logger.error("스크립트 파싱 오류: %s", error)
            raise Exception("스크립트 생성 또는 파싱에 실패했습니다.") from error

    def generate_audio_for_line(self, text: str, voice_name: str) -> tuple[bytes, str | None]:
        last_error = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                self._wait_for_tts_slot()
                with self._create_client() as client:
                    response = client.models.generate_content(
                        model=self.model_name,
                        contents=text,
                        config=types.GenerateContentConfig(
                            response_modalities=["AUDIO"],
                            speech_config=types.SpeechConfig(
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                                )
                            ),
                        ),
                    )
                return self._extract_inline_audio(response)
            except Exception as error:
                last_error = error
                if attempt >= _MAX_RETRIES:
                    break

                delay_seconds = _RETRY_DELAY * (attempt + 1)
                if self._is_rate_limit_error(error):
                    parsed_delay = self._parse_retry_delay_seconds(error)
                    if parsed_delay is not None:
                        delay_seconds = parsed_delay + _RATE_LIMIT_BUFFER_SECONDS
                    self._defer_tts_requests(delay_seconds)

                logger.warning(
                    "오디오 생성 재시도 %s/%s: %s (sleep %.1fs)",
                    attempt + 1,
                    _MAX_RETRIES,
                    error,
                    delay_seconds,
                )
                time.sleep(delay_seconds)

        raise last_error or RuntimeError("Audio generation failed for an unknown reason.")

    def create_podcast(self, report_text: str, output_path: str, progress_callback=None):
        try:
            if progress_callback:
                progress_callback(10, "스크립트 구성을 시작합니다...")

            script = self.generate_script(report_text)
            voice_map = {
                "A": TTS_VOICE_SPEAKER_A,
                "B": TTS_VOICE_SPEAKER_B,
            }

            total_lines = len(script)
            if total_lines == 0:
                raise RuntimeError("생성된 스크립트가 비어 있습니다.")

            audio_segments = [None] * total_lines
            silence = AudioSegment.silent(duration=_SILENCE_MS)
            failed_lines = []

            def _generate_line(idx: int, line: dict):
                raw_speaker = line.get("speaker", "A")
                speaker_key = str(raw_speaker).strip().upper()
                speaker = "B" if speaker_key == "B" or speaker_key.startswith("B") else "A"
                text = (line.get("text") or "").strip()
                if not text:
                    return idx, None

                voice = voice_map.get(speaker, TTS_VOICE_FALLBACK)
                audio_bytes, mime_type = self.generate_audio_for_line(text, voice)
                return idx, self._build_audio_segment(audio_bytes, mime_type)

            completed = 0
            for index, line in enumerate(script):
                try:
                    idx, segment = _generate_line(index, line)
                    audio_segments[idx] = segment
                except Exception as error:
                    failed_lines.append(index)
                    logger.error("오디오 변환 최종 실패 (line %s): %s", index, error)

                completed += 1
                if progress_callback:
                    progress_callback(
                        10 + int(completed / total_lines * 80),
                        f"음성 생성 중 ({completed}/{total_lines})...",
                    )

            if failed_lines:
                raise RuntimeError(f"오디오 생성에 실패한 대사가 있습니다: {failed_lines}")

            if progress_callback:
                progress_callback(95, "오디오 병합 및 저장 중...")

            combined_audio = AudioSegment.empty()
            for segment in audio_segments:
                if segment is not None:
                    combined_audio += segment + silence

            if len(combined_audio) == 0:
                raise RuntimeError("생성된 오디오 길이가 0입니다.")

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            combined_audio.export(output_path, format="wav")

            if progress_callback:
                progress_callback(100, "팟캐스트 생성이 완료되었습니다.")
            return True
        except Exception as error:
            logger.error("팟캐스트 오디오 생성 전체 실패: %s", error)
            if progress_callback:
                progress_callback(-1, str(error))
            raise
