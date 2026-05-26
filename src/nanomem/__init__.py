"""nanomem — long-term personal memory backend for AI agents.

The top-level package exposes the public surface organized by concept:

- Contracts          — frozen dataclasses for capture/read/flush requests,
                       results, dialogue entities, and selectors
- Errors             — NanoMemError hierarchy for catchable exceptions
- Service            — NanoMemService orchestrator (sync + async)
- Capabilities       — replaceable backends behind small Protocols
                       (Store, Index, Renderer, Ranker, Extractor)
- SDK                — sync + async HTTP clients
- Adapters           — agent harness integration shims
- Config / Factory   — config schema + config-driven construction
- Admin / Control    — control-plane services for CLI / manager UI

Sub-modules (``nanomem.contracts``, ``nanomem.errors``, ...) are the
documented import paths for grouped imports. The flat ``from nanomem
import X`` form below is preserved for convenience.
"""

from __future__ import annotations

# --- Contracts ---
from nanomem.core.contracts import (
    CaptureDialogue,
    CaptureRequest,
    CaptureResult,
    CaptureSkip,
    Dialogue,
    DialogueMessage,
    DialogueRef,
    DialogueWindow,
    DialogueWindowSelector,
    FlushRequest,
    FlushResult,
    MemoryScope,
    MemoryUnit,
    OperationLogEntry,
    PackedContext,
    RankedMemoryUnit,
    ReadRequest,
    ReadResult,
    ReindexResult,
    Session,
    TimeRange,
)

# --- Errors ---
from nanomem.core.errors import (
    CaptureError,
    ConfigError,
    ContractError,
    ExtractionError,
    IndexError_,
    NanoMemError,
    RenderError,
    RetrievalError,
    StoreError,
)

# --- Service ---
from nanomem.service.async_core import AsyncNanoMemService
from nanomem.service.core import NanoMemService

# --- Capabilities (behind Protocols where applicable) ---
from nanomem.pipeline.representation.heuristic import HeuristicMemoryUnitExtractor
from nanomem.pipeline.representation.llm import LLMMemoryUnitExtractor
from nanomem.pipeline.retrieval.embeddings.cache import CachedEmbeddingModel
from nanomem.pipeline.retrieval.indexes.dense import DenseMemoryUnitIndex
from nanomem.pipeline.retrieval.indexes.hybrid import HybridMemoryUnitIndex
from nanomem.pipeline.retrieval.indexes.lexical import LexicalMemoryUnitIndex
from nanomem.pipeline.retrieval.ranking.base import Ranker
from nanomem.pipeline.utilization.base import Renderer
from nanomem.pipeline.utilization.evidence_context import EvidenceContextRenderer
from nanomem.pipeline.utilization.time_merge import TimeMergedRenderer
from nanomem.pipeline.storage.sqlite import SQLiteMemoryUnitStore

# --- SDK ---
from nanomem.transports.sdk import AsyncNanoMemClient, NanoMemClient, NanoMemClientError

# --- Adapters ---
from nanomem.hosts.adapters import (
    AgentMemoryAdapter,
    AgentMessage,
    NanoMemMCPServer,
)

# --- Config / Factory ---
from nanomem.core.config import (
    BackupConfig,
    ExportConfig,
    MaintenanceConfig,
    NanoMemConfig,
    RetentionConfig,
    load_config,
)
from nanomem.service.factory import (
    admin_from_config,
    admin_from_config_file,
    control_from_config,
    control_from_config_file,
    maintenance_from_config,
    maintenance_from_config_file,
    nanomem_service_with_defaults,
    service_from_config,
    service_from_config_file,
)

# --- Admin / Control ---
from nanomem.service.control.service import (
    BackupResult,
    DatabaseStats,
    ExportResult,
    IntegrityCheckResult,
    NanoMemAdminService,
    NanoMemControlService,
    OperationLogRetentionApplyResult,
    OperationLogRetentionPolicy,
    OperationLogRetentionPreview,
    PendingSchemaMigration,
    RetentionApplyResult,
    RetentionPolicy,
    RetentionPreview,
    SchemaMigrationRecord,
    SchemaStatus,
)
from nanomem.ops.maintenance import (
    MaintenancePlan,
    MaintenanceRunResult,
    NanoMemMaintenanceService,
)


__all__ = [
    # --- Contracts ---
    "CaptureDialogue",
    "CaptureRequest",
    "CaptureResult",
    "CaptureSkip",
    "Dialogue",
    "DialogueMessage",
    "DialogueRef",
    "DialogueWindow",
    "DialogueWindowSelector",
    "FlushRequest",
    "FlushResult",
    "MemoryScope",
    "MemoryUnit",
    "OperationLogEntry",
    "PackedContext",
    "RankedMemoryUnit",
    "ReadRequest",
    "ReadResult",
    "ReindexResult",
    "Session",
    "TimeRange",
    # --- Errors ---
    "CaptureError",
    "ConfigError",
    "ContractError",
    "ExtractionError",
    "IndexError_",
    "NanoMemError",
    "RenderError",
    "RetrievalError",
    "StoreError",
    # --- Service ---
    "AsyncNanoMemService",
    "NanoMemService",
    # --- Capabilities ---
    "CachedEmbeddingModel",
    "DenseMemoryUnitIndex",
    "EvidenceContextRenderer",
    "HeuristicMemoryUnitExtractor",
    "HybridMemoryUnitIndex",
    "LexicalMemoryUnitIndex",
    "LLMMemoryUnitExtractor",
    "Ranker",
    "Renderer",
    "SQLiteMemoryUnitStore",
    "TimeMergedRenderer",
    # --- SDK ---
    "AsyncNanoMemClient",
    "NanoMemClient",
    "NanoMemClientError",
    # --- Adapters ---
    "AgentMemoryAdapter",
    "AgentMessage",
    "NanoMemMCPServer",
    # --- Config / Factory ---
    "BackupConfig",
    "ExportConfig",
    "MaintenanceConfig",
    "NanoMemConfig",
    "RetentionConfig",
    "admin_from_config",
    "admin_from_config_file",
    "control_from_config",
    "control_from_config_file",
    "load_config",
    "maintenance_from_config",
    "maintenance_from_config_file",
    "nanomem_service_with_defaults",
    "service_from_config",
    "service_from_config_file",
    # --- Admin / Control ---
    "BackupResult",
    "DatabaseStats",
    "ExportResult",
    "IntegrityCheckResult",
    "MaintenancePlan",
    "MaintenanceRunResult",
    "NanoMemAdminService",
    "NanoMemControlService",
    "NanoMemMaintenanceService",
    "OperationLogRetentionApplyResult",
    "OperationLogRetentionPolicy",
    "OperationLogRetentionPreview",
    "PendingSchemaMigration",
    "RetentionApplyResult",
    "RetentionPolicy",
    "RetentionPreview",
    "SchemaMigrationRecord",
    "SchemaStatus",
]
