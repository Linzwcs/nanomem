from __future__ import annotations

from nanomem.pipeline.representation.base import MemoryUnitExtractor
from nanomem.pipeline.representation.heuristic import HeuristicMemoryUnitExtractor
from nanomem.index.base import MemoryUnitIndex
from nanomem.index.dense import DenseMemoryUnitIndex
from nanomem.index.rebuild import rebuild_index
from nanomem.ranking.base import Ranker
from nanomem.ranking.ranker import MemoryUnitRanker
from nanomem.render.base import Renderer
from nanomem.render.context import EvidenceContextRenderer
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
