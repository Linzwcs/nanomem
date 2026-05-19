from __future__ import annotations

from nanomem.extraction.base import MemoryUnitExtractor
from nanomem.extraction.heuristic import HeuristicMemoryUnitExtractor
from nanomem.index.base import MemoryUnitIndex
from nanomem.index.dense import DenseMemoryUnitIndex
from nanomem.render.context import EvidenceContextRenderer
from nanomem.ranking.ranker import MemoryUnitRanker
from nanomem.service.capture import CapturePipeline
from nanomem.service.read import ReadPipeline
from nanomem.store.base import MemoryStore
from nanomem.store.sqlite import SQLiteMemoryUnitStore
from nanomem.contracts import CaptureRequest, CaptureResult, ReadRequest, ReadResult


class NanoMemService:
    def __init__(
        self,
        *,
        store: MemoryStore | None = None,
        index: MemoryUnitIndex | None = None,
        extractor: MemoryUnitExtractor | None = None,
        default_recency_policy: str = "balanced",
        default_max_units: int = 10,
    ) -> None:
        self.store = store or SQLiteMemoryUnitStore()
        self.index = index or DenseMemoryUnitIndex()
        self.extractor = extractor or HeuristicMemoryUnitExtractor()
        self.default_recency_policy = default_recency_policy
        self.default_max_units = default_max_units
        self.renderer = EvidenceContextRenderer()
        self.ranker = MemoryUnitRanker()
        self._capture_pipeline = CapturePipeline(
            store=self.store,
            index=self.index,
            extractor=self.extractor,
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

    def read(self, request: ReadRequest) -> ReadResult:
        return self._read_pipeline.run(request)
