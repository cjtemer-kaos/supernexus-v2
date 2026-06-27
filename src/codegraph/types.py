from dataclasses import dataclass, field
from typing import Any

NODE_TYPES = frozenset({"code", "document", "concept", "paper", "image", "file"})

EDGE_TYPES = frozenset({
    "contains", "calls", "imports", "imports_from", "inherits",
    "implements", "references", "defines", "similar",
    "semantic_related", "re_exports",
})

CONFIDENCE_LEVELS = frozenset({"EXTRACTED", "INFERRED", "AMBIGUOUS"})


@dataclass
class GraphNode:
    id: str
    label: str = ""
    node_type: str = "concept"
    source_file: str = ""
    file_type: str = "concept"
    body_hash: str = ""
    signature: str = ""
    docstring: str = ""
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    community: int = -1
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {"id": self.id, "label": self.label or self.id}
        if self.node_type != "concept":
            d["node_type"] = self.node_type
        if self.source_file:
            d["source_file"] = self.source_file
        if self.file_type != "concept":
            d["file_type"] = self.file_type
        if self.body_hash:
            d["body_hash"] = self.body_hash
        if self.signature:
            d["signature"] = self.signature
        if self.docstring:
            d["docstring"] = self.docstring
        if self.is_async:
            d["is_async"] = True
        if self.decorators:
            d["decorators"] = self.decorators
        if self.bases:
            d["bases"] = self.bases
        if self.imports:
            d["imports"] = self.imports
        if self.exports:
            d["exports"] = self.exports
        if self.community >= 0:
            d["community"] = self.community
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "GraphNode":
        return cls(
            id=d["id"],
            label=d.get("label", ""),
            node_type=d.get("node_type", "concept"),
            source_file=d.get("source_file", ""),
            file_type=d.get("file_type", "concept"),
            body_hash=d.get("body_hash", ""),
            signature=d.get("signature", ""),
            docstring=d.get("docstring", ""),
            is_async=d.get("is_async", False),
            decorators=d.get("decorators", []),
            bases=d.get("bases", []),
            imports=d.get("imports", []),
            exports=d.get("exports", []),
            community=d.get("community", -1),
            metadata=d.get("metadata", {}),
        )


@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str = "references"
    weight: float = 1.0
    confidence: str = "EXTRACTED"
    confidence_score: float = 1.0
    call_count: int = 1
    source_file: str = ""
    label: str = ""

    def __post_init__(self):
        if self.relation not in EDGE_TYPES and self.relation:
            pass
        if self.confidence not in CONFIDENCE_LEVELS:
            self.confidence = "EXTRACTED"

    def to_dict(self) -> dict:
        d = {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
        }
        if self.weight != 1.0:
            d["weight"] = self.weight
        if self.confidence != "EXTRACTED":
            d["confidence"] = self.confidence
        if self.confidence_score != 1.0:
            d["confidence_score"] = self.confidence_score
        if self.call_count != 1:
            d["call_count"] = self.call_count
        if self.source_file:
            d["source_file"] = self.source_file
        if self.label:
            d["label"] = self.label
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "GraphEdge":
        return cls(
            source=d.get("source", d.get("from", "")),
            target=d.get("target", d.get("to", "")),
            relation=d.get("relation", "references"),
            weight=d.get("weight", 1.0),
            confidence=d.get("confidence", "EXTRACTED"),
            confidence_score=d.get("confidence_score", 1.0),
            call_count=d.get("call_count", 1),
            source_file=d.get("source_file", ""),
            label=d.get("label", ""),
        )


LANG_FAMILY: dict[str, str] = {
    **{e: "python" for e in (".py", ".pyw", ".pyx")},
    **{e: "js" for e in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte")},
    **{e: "go" for e in (".go",)},
    **{e: "rust" for e in (".rs",)},
    **{e: "jvm" for e in (".java", ".kt", ".kts", ".scala", ".groovy")},
    **{e: "c" for e in (".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".cuh")},
    **{e: "ruby" for e in (".rb",)},
    **{e: "swift" for e in (".swift",)},
    **{e: "dotnet" for e in (".cs", ".vb")},
    **{e: "php" for e in (".php",)},
    **{e: "r" for e in (".r", ".rmd")},
}
