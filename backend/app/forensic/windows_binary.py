from __future__ import annotations

import struct
from datetime import UTC, datetime, timedelta

WINDOWS_EPOCH = datetime(1601, 1, 1, tzinfo=UTC)


class StructureError(ValueError):
    """Raised when a binary structure cannot be decoded safely."""


def unpack_from(format_: str, data: bytes, offset: int) -> tuple[int, ...]:
    size = struct.calcsize(format_)
    if offset < 0 or offset + size > len(data):
        raise StructureError("structure extends beyond available bytes")
    return struct.unpack_from(format_, data, offset)


def uint16(data: bytes, offset: int) -> int:
    return unpack_from("<H", data, offset)[0]


def uint32(data: bytes, offset: int) -> int:
    return unpack_from("<I", data, offset)[0]


def uint64(data: bytes, offset: int) -> int:
    return unpack_from("<Q", data, offset)[0]


def filetime(value: int) -> tuple[datetime | None, str | None]:
    if value == 0:
        return None, None
    try:
        parsed = WINDOWS_EPOCH + timedelta(microseconds=value // 10)
    except (OverflowError, ValueError):
        return None, str(value)
    return parsed, str(value)


def utf16_fixed(data: bytes) -> str:
    end = len(data)
    for offset in range(0, len(data) - 1, 2):
        if data[offset : offset + 2] == b"\x00\x00":
            end = offset
            break
    return data[:end].decode("utf-16-le", errors="strict")


def c_string(data: bytes, offset: int, *, unicode: bool = False) -> str | None:
    if offset <= 0 or offset >= len(data):
        return None
    if unicode:
        end = offset
        while end + 1 < len(data) and data[end : end + 2] != b"\x00\x00":
            end += 2
        return data[offset:end].decode("utf-16-le", errors="strict")
    end = data.find(b"\x00", offset)
    if end < 0:
        end = len(data)
    return data[offset:end].decode("cp1252", errors="replace")
