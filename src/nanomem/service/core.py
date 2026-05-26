from __future__ import annotations

from nanomem.pipeline.representation.base import MemoryUnitExtractor
from nanomem.pipeline.representation.heuristic import HeuristicMemoryUnitExtractor
from nanomem.pipeline.retrieval.indexes.base import MemoryUnitIndex
from nanomem.pipeline.retrieval.indexes.dense import DenseMemoryUnitIndex
from nanomem.pipeline.retrieval.indexes.rebuild import rebuild_index
from nanomem.pipeline.retrieval.ranking.base import Ranker
from nanomem.pipeline.retrieval.ranking.relevance_recency import MemoryUnitRanker
from nanomem.pipeline.utilization.base import Renderer
from nanomem.pipeline.utilization.evidence_context import EvidenceContextRenderer
from nanomem.service.capture import CapturePipeline
from nanomem.service.read import ReadPipeline
from nanomem.pipeline.storage.base import MemoryStore
from nanomem.pipeline.storage.sqlite import SQLiteMemoryUnitStore
from nanomem.core.contracts import (
    CaptureRequest,
    CaptureResult,
    FlushRequest,
    FlushResult,
    MemoryUnitSelector,
    ReadRequest,
    ReadResult,
    ReindexResult,
)


class NanoMemService:
    def __init__(
        self,
        *,
        store: MemoryStore | None = None,
        index: MemoryUnitIndex | None = None,
        extractor: MemoryUnitExtractor | None = None,
        default_recency_policy: str = "balanced",
        default_max_units: int = 10,
        max_dialogue_tokens: int = 512,
    ) -> None:
        self.store: MemoryStore = store or SQLiteMemoryUnitStore()
        self.index: MemoryUnitIndex = index or DenseMemoryUnitIndex()
        self.extractor: MemoryUnitExtractor = (
            extractor or HeuristicMemoryUnitExtractor()
        )
        self.default_recency_policy = default_recency_policy
        self.default_max_units = default_max_units
        self.max_dialogue_tokens = max_dialogue_tokens
        self.renderer: Renderer = EvidenceContextRenderer()
        self.ranker: Ranker = MemoryUnitRanker()
        self._capture_pipeline = CapturePipeline(
            store=self.store,
            index=self.index,
            extractor=self.extractor,
            max_dialogue_tokens=self.max_dialogue_tokens,
        )
        self._read_pipeline = ReadPipeline(
            store=self.store,
            index=self.index,
            ranker=self.ranker,
            renderer=self.renderer,
            default_recency_policy=self.default_recency_policy,
            default_max_units=self.default_max_units,
        )

    def capture(self, request: CaptureRequest) -> CaptureResult:
        return self._capture_pipeline.run(request)

    def flush(self, request: FlushRequest | None = None) -> FlushResult:
        return self._capture_pipeline.flush(request or FlushRequest())

    def read(self, request: ReadRequest) -> ReadResult:
        return self._read_pipeline.run(request)

    def reindex(
        self,
        selector: MemoryUnitSelector | None = None,
    ) -> ReindexResult:
        return rebuild_index(
            store=self.store,
            index=self.index,
            selector=selector,
        )
