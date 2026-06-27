import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict

from src.research.utils import is_low_quality

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("data/deep_research")


def _bounded_int(value, *, default: int, minimum: int, maximum: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, n))


class ResearchHandler:

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or DEFAULT_DATA_DIR
        self._active_tasks: Dict[str, dict] = {}
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def start_research(
        self,
        session_id: str,
        query: str,
        llm_endpoint: str,
        llm_model: str,
        max_time: int = 300,
        hard_timeout: int = 600,
        llm_headers: dict = None,
        on_complete: callable = None,
        prior_report: str = "",
        prior_findings: list = None,
        prior_urls: set = None,
        max_rounds: int = 20,
        search_provider: str = None,
        category: str = None,
        extraction_timeout: int = None,
        extraction_concurrency: int = None,
        owner: str = "",
        web_researcher=None,
    ) -> dict:
        if session_id in self._active_tasks:
            existing = self._active_tasks[session_id]
            if existing.get("status") == "running":
                self.cancel_research(session_id)

        entry = {
            "task": None,
            "researcher": None,
            "query": query,
            "status": "running",
            "progress": {},
            "result": None,
            "started_at": time.time(),
            "category": category,
            "owner": owner or "",
        }
        self._active_tasks[session_id] = entry

        def on_progress(event):
            entry["progress"] = event

        _completed = False

        def _guarded_complete(*args, **kwargs):
            nonlocal _completed
            if _completed:
                return
            _completed = True
            if on_complete:
                on_complete(*args, **kwargs)

        async def _run():
            try:
                result = await asyncio.wait_for(
                    self._call_research_service(
                        query, llm_endpoint, llm_model,
                        max_time=max_time,
                        progress_callback=on_progress,
                        _task_entry=entry,
                        llm_headers=llm_headers,
                        prior_report=prior_report,
                        prior_findings=prior_findings,
                        prior_urls=prior_urls,
                        max_rounds=max_rounds,
                        search_provider=search_provider,
                        category=category,
                        extraction_timeout=extraction_timeout,
                        extraction_concurrency=extraction_concurrency,
                        web_researcher=web_researcher,
                    ),
                    timeout=hard_timeout,
                )
                entry["result"] = result
                entry["status"] = "done"
                self._save_result(session_id, entry)
                try:
                    researcher = entry.get("researcher")
                    findings = self._extract_raw_findings(researcher.findings) if researcher and researcher.findings else []
                    sources = entry.get("sources", [])
                    _guarded_complete(session_id, result, sources, findings)
                except Exception as cb_err:
                    logger.error(f"on_complete callback failed: {cb_err}")
            except asyncio.TimeoutError:
                logger.error(f"Research hard timeout ({hard_timeout}s) for session {session_id}")
                entry["status"] = "error"
                researcher = entry.get("researcher")
                if researcher and researcher.evolving_report:
                    entry["result"] = self._format_research_report(
                        query, researcher.evolving_report,
                        researcher.get_stats(), hard_timeout,
                    )
                    entry["status"] = "done"
                    self._save_result(session_id, entry)
                    try:
                        findings = self._extract_raw_findings(researcher.findings) if researcher.findings else []
                        sources = self._extract_sources(researcher.findings) if researcher.findings else []
                        _guarded_complete(session_id, entry["result"], sources, findings)
                    except Exception as e:
                        logger.warning(f"on_complete callback failed in timeout branch: {e}")
                else:
                    entry["result"] = f"Research timed out after {hard_timeout}s. The model may be too slow for deep research."
                on_progress({"phase": "error", "message": f"Research timed out after {hard_timeout}s"})
            except asyncio.CancelledError:
                entry["status"] = "cancelled"
                raise
            except Exception as e:
                logger.error(f"Background research failed: {e}", exc_info=True)
                entry["result"] = str(e)
                entry["status"] = "error"

        task = asyncio.create_task(_run())
        entry["task"] = task
        return {"session_id": session_id, "status": "running", "query": query}

    async def _call_research_service(
        self, query: str, llm_endpoint: str, llm_model: str,
        max_time: int = 300, progress_callback=None, _task_entry=None,
        llm_headers=None, prior_report="", prior_findings=None,
        prior_urls=None, max_rounds=20, search_provider=None,
        category=None, extraction_timeout=None, extraction_concurrency=None,
        web_researcher=None,
    ) -> str:
        from src.research.deep_researcher import DeepResearcher

        researcher = DeepResearcher(
            llm_endpoint=llm_endpoint,
            llm_model=llm_model,
            llm_headers=llm_headers or {},
            max_rounds=_bounded_int(max_rounds, default=8, minimum=1, maximum=30),
            max_time=_bounded_int(max_time, default=300, minimum=30, maximum=1800),
            max_urls_per_round=3,
            max_content_chars=15000,
            max_report_tokens=8192,
            extraction_timeout=_bounded_int(extraction_timeout, default=90, minimum=15, maximum=600),
            extraction_concurrency=_bounded_int(extraction_concurrency, default=3, minimum=1, maximum=12),
            min_rounds=2,
            max_empty_rounds=2,
            synthesis_window=10,
            progress_callback=progress_callback,
            search_provider=search_provider,
            category=category,
            web_researcher=web_researcher,
        )

        if _task_entry is not None:
            _task_entry["researcher"] = researcher

        try:
            result = await researcher.research(
                query,
                prior_report=prior_report,
                prior_findings=prior_findings,
                prior_urls=prior_urls,
            )
            return result
        finally:
            await researcher.close()

    def get_status(self, session_id: str) -> Optional[dict]:
        if session_id in self._active_tasks:
            entry = self._active_tasks[session_id]
            return {
                "status": entry["status"],
                "progress": entry["progress"],
                "query": entry["query"],
                "started_at": entry["started_at"],
            }
        path = self._data_dir / f"{session_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("consumed"):
                    return None
                return {
                    "status": data.get("status", "done"),
                    "progress": {},
                    "query": data.get("query", ""),
                    "started_at": data.get("started_at", 0),
                }
            except Exception:
                pass
        return None

    def cancel_research(self, session_id: str) -> bool:
        if session_id not in self._active_tasks:
            return False
        entry = self._active_tasks[session_id]
        if entry["status"] != "running":
            return False
        researcher = entry.get("researcher")
        if researcher:
            researcher.cancel()
        task = entry.get("task")
        if task and not task.done():
            task.cancel()
        entry["status"] = "cancelled"
        return True

    def get_result(self, session_id: str) -> Optional[str]:
        if session_id in self._active_tasks:
            entry = self._active_tasks[session_id]
            if entry["status"] in ("done", "error", "cancelled"):
                return entry.get("result")
        path = self._data_dir / f"{session_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("consumed"):
                    return None
                return data.get("result")
            except Exception:
                pass
        return None

    def get_sources(self, session_id: str) -> Optional[list]:
        if session_id in self._active_tasks:
            entry = self._active_tasks[session_id]
            if entry.get("sources"):
                return entry["sources"]
            researcher = entry.get("researcher")
            if researcher and researcher.findings:
                return self._extract_sources(researcher.findings)
        path = self._data_dir / f"{session_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data.get("sources")
            except Exception:
                pass
        return None

    def get_raw_findings(self, session_id: str) -> Optional[list]:
        if session_id in self._active_tasks:
            entry = self._active_tasks[session_id]
            researcher = entry.get("researcher")
            if researcher and researcher.findings:
                return self._extract_raw_findings(researcher.findings)
        path = self._data_dir / f"{session_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data.get("raw_findings")
            except Exception:
                pass
        return None

    @staticmethod
    def _extract_sources(findings: list) -> list:
        seen = set()
        sources = []
        for f in findings:
            url = f.get("url", "")
            title = f.get("title", "") or url
            summary = f.get("summary", "") or f.get("evidence", "")
            if url and url not in seen and not is_low_quality(summary):
                seen.add(url)
                entry = {"url": url, "title": title}
                og_img = f.get("og_image", "")
                if og_img:
                    entry["image"] = og_img
                sources.append(entry)
        return sources

    @staticmethod
    def _extract_raw_findings(findings: list) -> list:
        try:
            items = []
            for f in findings:
                url = f.get("url", "")
                title = f.get("title", "") or "Untitled"
                summary = f.get("summary", "")
                evidence = f.get("evidence", "")
                content = summary if summary else (evidence[:2000] if evidence else "")
                if url and content and not is_low_quality(content):
                    items.append({"url": url, "title": title, "summary": content})
            return items
        except Exception:
            return []

    def _save_result(self, session_id: str, entry: dict):
        try:
            sources = []
            raw_findings = []
            researcher = entry.get("researcher")
            if researcher and researcher.findings:
                sources = self._extract_sources(researcher.findings)
                raw_findings = self._extract_raw_findings(researcher.findings)
            entry["sources"] = sources

            path = self._data_dir / f"{session_id}.json"
            data = {
                "query": entry["query"],
                "status": entry["status"],
                "result": entry["result"],
                "raw_report": entry.get("raw_report", ""),
                "sources": sources,
                "raw_findings": raw_findings,
                "stats": entry.get("stats"),
                "category": entry.get("category"),
                "started_at": entry["started_at"],
                "completed_at": time.time(),
                "owner": entry.get("owner", ""),
            }
            path.write_text(json.dumps(data), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save research result: {e}")

    def clear_result(self, session_id: str):
        self._active_tasks.pop(session_id, None)
        path = self._data_dir / f"{session_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                data["consumed"] = True
                path.write_text(json.dumps(data), encoding="utf-8")
            except Exception:
                pass

    @staticmethod
    def _format_research_report(query: str, report: str, stats: dict, hard_timeout: int) -> str:
        parts = [f"# Research: {query}\n"]
        if stats:
            parts.append("> " + " · ".join(f"{k}: {v}" for k, v in stats.items()))
        parts.append(f"\n> ⚠️ Partial results (timeout after {hard_timeout}s)\n")
        parts.append(report)
        return "\n".join(parts)
