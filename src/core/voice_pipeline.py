"""
Voice Pipeline — Async queue-based worker pattern.
From: voice-ai-engine-development skill.

Pipeline: Audio In → Transcriber → Agent → Synthesizer → Audio Out
Each worker runs independently via asyncio.Queue.
"""

import asyncio
import logging
from typing import Any, Callable, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """Audio data flowing through the pipeline."""
    data: bytes
    sample_rate: int = 16000
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class Transcript:
    text: str
    is_final: bool = True
    confidence: float = 1.0
    language: str = "es"


@dataclass
class AgentResponse:
    text: str
    gem_used: str = "director"
    tokens: int = 0


@dataclass
class SynthesizedAudio:
    data: bytes
    text: str
    duration_ms: float = 0
    voice: str = "default"


class BaseWorker:
    """Base async worker pattern from voice-ai-engine-development skill."""

    def __init__(self, name: str, input_queue: asyncio.Queue, output_queue: asyncio.Queue):
        self.name = name
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.active = False
        self._task: Optional[asyncio.Task] = None
        self.processed_count = 0

    def start(self):
        self.active = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"⚙️ [WORKER] Worker '{self.name}' started")

    async def _run_loop(self):
        while self.active:
            try:
                item = await asyncio.wait_for(self.input_queue.get(), timeout=1.0)
                result = await self.process(item)
                if result is not None:
                    await self.output_queue.put(result)
                    self.processed_count += 1
            except asyncio.TimeoutError:
                continue  # Check active flag periodically
            except Exception as e:
                logger.error(f"Worker '{self.name}' error: {e}")

    async def process(self, item: Any) -> Any:
        raise NotImplementedError

    def terminate(self):
        self.active = False
        if self._task:
            self._task.cancel()
        logger.info(f"🛑 [WORKER] Worker '{self.name}' terminated ({self.processed_count} items processed)")


class TranscriberWorker(BaseWorker):
    """Audio → Text (Whisper/Faster-Whisper)."""

    def __init__(self, input_queue: asyncio.Queue, output_queue: asyncio.Queue,
                 transcribe_fn: Optional[Callable] = None):
        super().__init__("transcriber", input_queue, output_queue)
        self.transcribe_fn = transcribe_fn
        self.is_muted = False  # Mute during TTS playback (anti-echo)

    async def process(self, chunk: AudioChunk) -> Optional[Transcript]:
        if self.is_muted:
            return None  # Skip while AI is speaking (echo prevention)

        if self.transcribe_fn:
            try:
                result = await self.transcribe_fn(chunk.data, chunk.sample_rate)
                if result and result.get("text", "").strip():
                    text = result["text"].strip()
                    logger.info(f"🎤 [TRANSCRIBER] Transcribed: '{text}' (conf: {result.get('confidence', 1.0)})")
                    return Transcript(
                        text=text,
                        is_final=result.get("is_final", True),
                        confidence=result.get("confidence", 1.0),
                        language=result.get("language", "es"),
                    )
            except Exception as e:
                logger.error(f"❌ [TRANSCRIBER] Transcription error: {e}")
        return None

    def mute(self):
        """Mute during TTS playback to prevent echo."""
        self.is_muted = True
        logger.info("🎤 [TRANSCRIBER] Muted (anti-echo mode enabled)")

    def unmute(self):
        self.is_muted = False
        logger.info("🎤 [TRANSCRIBER] Unmuted (anti-echo mode disabled)")


class AgentWorker(BaseWorker):
    """Text → Response (Director/Gema via Ollama)."""

    def __init__(self, input_queue: asyncio.Queue, output_queue: asyncio.Queue,
                 agent_fn: Optional[Callable] = None):
        super().__init__("agent", input_queue, output_queue)
        self.agent_fn = agent_fn
        self.interrupted = False

    async def process(self, transcript: Transcript) -> Optional[AgentResponse]:
        if not transcript.text or len(transcript.text) < 2:
            return None

        self.interrupted = False
        logger.info(f"🤖 [AGENT] Processing prompt: '{transcript.text}'")

        if self.agent_fn:
            try:
                result = await self.agent_fn(transcript.text)
                if self.interrupted:
                    logger.info("⚠️ [AGENT] Generation interrupted by user. Discarding output.")
                    return None  # User interrupted, discard
                reply = result.get("reply", result.get("content", ""))
                logger.info(f"🤖 [AGENT] Responded: '{reply[:100]}...' (using gem: {result.get('gem_used', 'director')})")
                return AgentResponse(
                    text=reply,
                    gem_used=result.get("gem_used", "director"),
                    tokens=result.get("tokens_used", 0),
                )
            except Exception as e:
                logger.error(f"❌ [AGENT] Agent error: {e}")
                return AgentResponse(text=f"Error: {e}")
        return None

    def interrupt(self):
        """User interrupted — discard current response."""
        self.interrupted = True
        logger.info("⚠️ [AGENT] Interruption signal received")


class SynthesizerWorker(BaseWorker):
    """Text → Audio (Piper TTS)."""

    def __init__(self, input_queue: asyncio.Queue, output_queue: asyncio.Queue,
                 synthesize_fn: Optional[Callable] = None,
                 transcriber: Optional[TranscriberWorker] = None):
        super().__init__("synthesizer", input_queue, output_queue)
        self.synthesize_fn = synthesize_fn
        self.transcriber = transcriber  # To mute/unmute during playback

    async def process(self, response: AgentResponse) -> Optional[SynthesizedAudio]:
        if not response.text:
            return None

        logger.info(f"🔊 [SYNTHESIZER] Synthesizing text: '{response.text[:100]}...'")

        # Mute transcriber during synthesis (anti-echo pattern)
        if self.transcriber:
            self.transcriber.mute()

        try:
            if self.synthesize_fn:
                audio_data = await self.synthesize_fn(response.text)
                duration_ms = len(audio_data) / 32.0 if isinstance(audio_data, bytes) else 0.0 # heuristic for 16khz 16bit mono
                logger.info(f"🔊 [SYNTHESIZER] Synthesized {len(audio_data) if audio_data else 0} bytes of audio (~{duration_ms:.1f}ms)")
                return SynthesizedAudio(
                    data=audio_data if isinstance(audio_data, bytes) else b"",
                    text=response.text,
                    duration_ms=duration_ms,
                    voice="piper-es",
                )
        except Exception as e:
            logger.error(f"❌ [SYNTHESIZER] Synthesis error: {e}")
        finally:
            # Unmute transcriber after synthesis
            if self.transcriber:
                self.transcriber.unmute()

        return None


class VoicePipeline:
    """
    Full voice pipeline: Audio In → Transcriber → Agent → Synthesizer → Audio Out
    All workers run concurrently via asyncio queues.
    """

    def __init__(
        self,
        transcribe_fn: Optional[Callable] = None,
        agent_fn: Optional[Callable] = None,
        synthesize_fn: Optional[Callable] = None,
    ):
        # Queues connecting workers
        self.audio_in = asyncio.Queue(maxsize=50)
        self.transcripts = asyncio.Queue(maxsize=20)
        self.responses = asyncio.Queue(maxsize=10)
        self.audio_out = asyncio.Queue(maxsize=10)

        # Workers
        self.transcriber = TranscriberWorker(self.audio_in, self.transcripts, transcribe_fn)
        self.agent = AgentWorker(self.transcripts, self.responses, agent_fn)
        self.synthesizer = SynthesizerWorker(
            self.responses, self.audio_out, synthesize_fn,
            transcriber=self.transcriber,
        )

        self.running = False

    def start(self):
        """Start all pipeline workers."""
        self.running = True
        self.transcriber.start()
        self.agent.start()
        self.synthesizer.start()
        logger.info("🎙️ [PIPELINE] Voice pipeline started (3 workers)")

    def stop(self):
        """Stop all pipeline workers."""
        self.running = False
        self.transcriber.terminate()
        self.agent.terminate()
        self.synthesizer.terminate()
        logger.info("🎙️ [PIPELINE] Voice pipeline stopped")

    async def push_audio(self, audio_data: bytes, sample_rate: int = 16000):
        """Push audio chunk into the pipeline."""
        if self.running:
            await self.audio_in.put(AudioChunk(data=audio_data, sample_rate=sample_rate))

    async def get_output(self, timeout: float = 5.0) -> Optional[SynthesizedAudio]:
        """Get synthesized audio output from the pipeline."""
        try:
            return await asyncio.wait_for(self.audio_out.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def interrupt(self):
        """User interrupted — stop current response and unmute."""
        logger.info("⚠️ [PIPELINE] Interrupted! Stopping current agents and unmuting transcriber.")
        self.agent.interrupt()
        self.transcriber.unmute()
        # Drain response queue
        drained = 0
        while not self.responses.empty():
            try:
                self.responses.get_nowait()
                drained += 1
            except asyncio.QueueEmpty:
                break
        if drained > 0:
            logger.info(f"⚠️ [PIPELINE] Drained {drained} pending responses from queue.")

    def get_stats(self) -> Dict:
        return {
            "running": self.running,
            "transcriber": {"processed": self.transcriber.processed_count, "muted": self.transcriber.is_muted},
            "agent": {"processed": self.agent.processed_count},
            "synthesizer": {"processed": self.synthesizer.processed_count},
            "queues": {
                "audio_in": self.audio_in.qsize(),
                "transcripts": self.transcripts.qsize(),
                "responses": self.responses.qsize(),
                "audio_out": self.audio_out.qsize(),
            },
        }
