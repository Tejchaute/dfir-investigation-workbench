from collections.abc import Iterable

from app.core.exceptions import ConflictError, ValidationError
from app.domain.enums import ArtifactType
from app.forensic.evtx import EvtxParser
from app.forensic.lnk import LnkParser
from app.forensic.ntfs_mft import NtfsMftParser
from app.forensic.parser import ForensicParser
from app.forensic.prefetch import PrefetchParser
from app.forensic.registry_hive import RegistryHiveParser


class ParserRegistry:
    """Explicit, deterministic mapping from artifact type to parser instance."""

    def __init__(self, parsers: Iterable[ForensicParser] = ()) -> None:
        self._parsers: dict[ArtifactType, ForensicParser] = {}
        for parser in parsers:
            self.register(parser)

    def register(self, parser: ForensicParser) -> None:
        if not parser.name.strip() or not parser.version.strip():
            raise ValidationError("Parser name and version are required")
        if not parser.supported_artifact_types:
            raise ValidationError("Parser must declare at least one artifact type")
        conflicts = parser.supported_artifact_types.intersection(self._parsers)
        if conflicts:
            names = ", ".join(sorted(item.value for item in conflicts))
            raise ConflictError(f"Artifact types already have registered parsers: {names}")
        for artifact_type in parser.supported_artifact_types:
            self._parsers[artifact_type] = parser

    def parsers(self) -> tuple[ForensicParser, ...]:
        unique = {id(parser): parser for parser in self._parsers.values()}
        return tuple(sorted(unique.values(), key=lambda parser: (parser.name, parser.version)))

    def supports(self, artifact_type: ArtifactType) -> bool:
        return artifact_type in self._parsers

    def get(self, artifact_type: ArtifactType) -> ForensicParser:
        parser = self._parsers.get(artifact_type)
        if parser is None:
            raise ValidationError(
                f"No parser is registered for artifact type {artifact_type.value}"
            )
        return parser


parser_registry = ParserRegistry(
    [EvtxParser(), RegistryHiveParser(), PrefetchParser(), LnkParser(), NtfsMftParser()]
)
