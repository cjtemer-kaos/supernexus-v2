"""
SkillIndexer - Lightweight skill indexing system for fast search and discovery.

Features:
- Categorizes 1,600+ skills by topics/themes
- Creates lightweight manifests (name, description, category, tags)
- Fast keyword search without loading full skill content
- Memory-efficient: only loads manifests, not full skills
- Periodic refresh to catch new skills

Architecture:
1. Scan skills directory → extract manifests (first 20 lines)
2. Categorize by keywords → assign topics
3. Build inverted index for fast search
4. Serve via API: /api/skills/index, /api/skills/search
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

logger = logging.getLogger("nexus-skill-indexer")

# ============================================================================
# TOPIC CATEGORIES - Map skills to high-level topics
# ============================================================================

TOPIC_KEYWORDS: Dict[str, List[str]] = {
    # Development
    "frontend": ["react", "vue", "angular", "svelte", "nextjs", "nuxt", "css", "tailwind", "ui", "ux", "html", "javascript", "typescript"],
    "backend": ["node", "express", "fastapi", "django", "flask", "laravel", "spring", "nestjs", "api", "rest", "graphql"],
    "mobile": ["ios", "android", "flutter", "react-native", "swift", "kotlin", "mobile", "app"],
    "desktop": ["electron", "tauri", "desktop", "windows", "macos", "linux"],
    
    # Languages
    "python": ["python", "pip", "conda", "pandas", "numpy", "scikit", "pytorch", "tensorflow"],
    "javascript": ["javascript", "js", "node", "npm", "yarn", "bun", "deno"],
    "typescript": ["typescript", "ts", "nextjs", "nestjs"],
    "rust": ["rust", "cargo", "wasm", "webassembly"],
    "go": ["golang", "go", "goroutine"],
    "java": ["java", "spring", "maven", "gradle"],
    "php": ["php", "laravel", "symfony", "wordpress"],
    "ruby": ["ruby", "rails", "sinatra"],
    
    # Infrastructure
    "devops": ["docker", "kubernetes", "k8s", "terraform", "ansible", "ci", "cd", "pipeline", "deploy", "aws", "azure", "gcp"],
    "cloud": ["aws", "azure", "gcp", "cloud", "serverless", "lambda", "s3", "ec2"],
    "security": ["security", "pentest", "vulnerability", "owasp", "auth", "encrypt", "firewall", "audit"],
    "monitoring": ["monitoring", "logging", "metrics", "prometheus", "grafana", "observability", "alerting"],
    
    # Data
    "database": ["sql", "postgres", "mysql", "mongo", "redis", "database", "db", "orm", "prisma"],
    "ai-ml": ["ai", "ml", "machine-learning", "deep-learning", "neural", "llm", "gpt", "transformer", "embedding"],
    "data-science": ["data", "analytics", "visualization", "pandas", "numpy", "jupyter", "notebook"],
    
    # Business
    "marketing": ["marketing", "seo", "content", "social", "email", "campaign", "growth"],
    "sales": ["sales", "crm", "lead", "pipeline", "conversion", "funnel"],
    "finance": ["finance", "accounting", "invoice", "payment", "stripe", "paypal"],
    "ecommerce": ["ecommerce", "shopify", "woocommerce", "store", "product", "inventory"],
    
    # Tools & Integrations
    "automation": ["automation", "workflow", "n8n", "zapier", "make", "trigger", "schedule"],
    "communication": ["slack", "discord", "telegram", "whatsapp", "email", "notification"],
    "productivity": ["notion", "trello", "asana", "linear", "github", "gitlab"],
    
    # Creative
    "design": ["design", "figma", "sketch", "photoshop", "ui", "ux", "prototype", "wireframe"],
    "video": ["video", "ffmpeg", "remotion", "animation", "motion", "editing"],
    "audio": ["audio", "music", "podcast", "voice", "tts", "stt"],
    "image": ["image", "photo", "illustration", "midjourney", "dall-e", "stable-diffusion"],
    
    # Gaming
    "gaming": ["game", "unity", "unreal", "godot", "rust-server", "rcon", "plugin"],
    
    # Security specialized
    "penetration-testing": ["pentest", "penetration", "exploit", "metasploit", "burp", "nmap"],
    "cryptography": ["crypto", "encryption", "hash", "certificate", "ssl", "tls"],
    
    # Soft skills
    "writing": ["writing", "documentation", "blog", "article", "copywriting", "content"],
    "research": ["research", "analysis", "report", "paper", "literature"],
    "management": ["management", "leadership", "team", "project", "agile", "scrum"],
}


@dataclass
class SkillManifest:
    """Lightweight skill manifest - no full content loaded."""
    name: str
    description: str
    category: str = "general"
    topics: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    path: str = ""
    last_modified: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SkillIndexer:
    """
    Fast, memory-efficient skill indexer.
    
    Usage:
        indexer = SkillIndexer(skills_dir=Path("src/skills/hub"))
        indexer.build_index()
        
        # Search
        results = indexer.search("react component")
        
        # Get by topic
        results = indexer.get_by_topic("frontend")
        
        # Get stats
        stats = indexer.get_stats()
    """
    
    def __init__(self, skills_dir: Path, max_workers: int = 4):
        self.skills_dir = skills_dir
        self.max_workers = max_workers
        self.manifests: Dict[str, SkillManifest] = {}
        self.topic_index: Dict[str, List[str]] = defaultdict(list)  # topic -> [skill_names]
        self.tag_index: Dict[str, List[str]] = defaultdict(list)    # tag -> [skill_names]
        self.name_index: Dict[str, str] = {}  # lowercase_name -> actual_name
        self._build_time: float = 0.0
        self._last_build: float = 0.0
    
    def build_index(self) -> Dict:
        """Build the skill index from disk. Returns stats."""
        start = time.time()
        logger.info(f"Building skill index from {self.skills_dir}")
        
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return {"error": "Directory not found", "count": 0}
        
        # Clear existing indexes
        self.manifests.clear()
        self.topic_index.clear()
        self.tag_index.clear()
        self.name_index.clear()
        
        # Get all skill directories
        skill_dirs = [d for d in self.skills_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
        logger.info(f"Scanning {len(skill_dirs)} skill directories")
        
        # Parallel scan
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._extract_manifest, d): d
                for d in skill_dirs
            }
            for future in as_completed(futures):
                try:
                    manifest = future.result()
                    if manifest:
                        self.manifests[manifest.name] = manifest
                        self.name_index[manifest.name.lower()] = manifest.name
                        
                        # Index by topic
                        for topic in manifest.topics:
                            self.topic_index[topic].append(manifest.name)
                        
                        # Index by tag
                        for tag in manifest.tags:
                            self.tag_index[tag.lower()].append(manifest.name)
                except Exception as e:
                    logger.warning(f"Failed to extract manifest: {e}")
        
        self._build_time = time.time() - start
        self._last_build = time.time()
        
        stats = {
            "total_skills": len(self.manifests),
            "topics": len(self.topic_index),
            "tags": len(self.tag_index),
            "build_time_ms": round(self._build_time * 1000, 1),
        }
        logger.info(f"Skill index built: {stats}")
        return stats
    
    def _extract_manifest(self, skill_dir: Path) -> Optional[SkillManifest]:
        """Extract lightweight manifest from a skill directory."""
        # Find SKILL.md
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            skill_file = skill_dir / "skill.md"
        if not skill_file.exists():
            return None
        
        try:
            # Read only first 30 lines for manifest
            header = ""
            with open(skill_file, "r", encoding="utf-8", errors="ignore") as f:
                for _ in range(30):
                    line = f.readline()
                    if not line:
                        break
                    header += line
            
            name = skill_dir.name
            description = ""
            category = "general"
            topics = []
            tags = []
            
            # Parse header
            for line in header.split("\n"):
                line = line.strip()
                if line.startswith("# "):
                    name = line[2:].strip()
                elif line.lower().startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip('"')
                elif line.lower().startswith("category:"):
                    category = line.split(":", 1)[1].strip()
                elif line.lower().startswith("tags:"):
                    tags = [t.strip().strip('"') for t in line.split(":", 1)[1].split(",")]
            
            # Auto-categorize by keywords
            topics = self._categorize_topics(name, description, tags, skill_dir.name)
            
            # Get modification time
            mtime = skill_dir.stat().st_mtime
            
            return SkillManifest(
                name=name,
                description=description[:200],  # Truncate long descriptions
                category=category,
                topics=topics,
                tags=[t for t in tags if t],  # Filter empty tags
                path=str(skill_dir),
                last_modified=mtime,
            )
        except Exception as e:
            logger.debug(f"Failed to parse {skill_dir.name}: {e}")
            return None
    
    def _categorize_topics(self, name: str, description: str, tags: List[str], dirname: str) -> List[str]:
        """Auto-categorize skill based on keywords."""
        # Combine all text for matching
        text = f"{name} {description} {' '.join(tags)} {dirname}".lower()
        
        matched_topics = []
        for topic, keywords in TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    matched_topics.append(topic)
                    break
        
        return matched_topics[:5]  # Limit to 5 topics
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Fast keyword search across all skill manifests.
        
        Args:
            query: Search terms (e.g., "react component", "security audit")
            limit: Max results to return
        
        Returns:
            List of matching skill manifests
        """
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        # Score each skill
        scored = []
        for name, manifest in self.manifests.items():
            score = 0
            text = f"{manifest.name} {manifest.description} {' '.join(manifest.topics)} {' '.join(manifest.tags)}".lower()
            
            # Exact name match (highest score)
            if query_lower in manifest.name.lower():
                score += 100
            
            # Term matches
            for term in query_terms:
                if term in text:
                    score += 10
                if term in manifest.name.lower():
                    score += 20
                if term in [t.lower() for t in manifest.topics]:
                    score += 15
                if term in [t.lower() for t in manifest.tags]:
                    score += 5
            
            if score > 0:
                scored.append((score, manifest))
        
        # Sort by score and return top results
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m.to_dict() for _, m in scored[:limit]]
    
    def get_by_topic(self, topic: str) -> List[Dict]:
        """Get all skills for a specific topic."""
        skill_names = self.topic_index.get(topic.lower(), [])
        return [self.manifests[n].to_dict() for n in skill_names if n in self.manifests]
    
    def get_by_tag(self, tag: str) -> List[Dict]:
        """Get all skills with a specific tag."""
        skill_names = self.tag_index.get(tag.lower(), [])
        return [self.manifests[n].to_dict() for n in skill_names if n in self.manifests]
    
    def get_skill(self, name: str) -> Optional[Dict]:
        """Get a specific skill by name."""
        # Try exact match
        if name in self.manifests:
            return self.manifests[name].to_dict()
        
        # Try case-insensitive
        actual_name = self.name_index.get(name.lower())
        if actual_name and actual_name in self.manifests:
            return self.manifests[actual_name].to_dict()
        
        return None
    
    def get_topics(self) -> Dict[str, int]:
        """Get all topics with skill counts."""
        return {topic: len(skills) for topic, skills in self.topic_index.items()}
    
    def get_stats(self) -> Dict:
        """Get index statistics."""
        return {
            "total_skills": len(self.manifests),
            "total_topics": len(self.topic_index),
            "total_tags": len(self.tag_index),
            "build_time_ms": round(self._build_time * 1000, 1),
            "last_build": self._last_build,
            "skills_dir": str(self.skills_dir),
            "top_topics": sorted(
                [(t, len(s)) for t, s in self.topic_index.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10],
        }
    
    def suggest_for_task(self, task_description: str, limit: int = 5) -> List[Dict]:
        """
        Suggest skills for a given task description.
        Uses topic matching + keyword search.
        """
        # First, find matching topics
        task_lower = task_description.lower()
        matched_topics = []
        
        for topic, keywords in TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in task_lower:
                    matched_topics.append(topic)
                    break
        
        # Get skills from matched topics
        candidates = []
        for topic in matched_topics[:3]:  # Top 3 topics
            skill_names = self.topic_index.get(topic, [])
            for name in skill_names[:5]:  # Top 5 per topic
                if name in self.manifests:
                    candidates.append(self.manifests[name])
        
        # Also do keyword search
        search_results = self.search(task_description, limit=10)
        for result in search_results:
            # Avoid duplicates
            if not any(c.name == result["name"] for c in candidates):
                manifest = self.manifests.get(result["name"])
                if manifest:
                    candidates.append(manifest)
        
        # Return top candidates
        return [c.to_dict() for c in candidates[:limit]]


# ============================================================================
# GLOBAL INDEXER INSTANCE
# ============================================================================

_indexer: Optional[SkillIndexer] = None


def get_indexer(skills_dir: Optional[Path] = None) -> SkillIndexer:
    """Get or create the global skill indexer."""
    global _indexer
    if _indexer is None:
        if skills_dir is None:
            skills_dir = Path(__file__).parent / "hub"
        _indexer = SkillIndexer(skills_dir)
        _indexer.build_index()
    return _indexer


def rebuild_index():
    """Force rebuild the skill index."""
    global _indexer
    if _indexer:
        _indexer.build_index()
