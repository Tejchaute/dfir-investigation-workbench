from __future__ import annotations

import struct
import uuid
from datetime import UTC, datetime

SHELL_LINK_CLSID = bytes.fromhex("0114020000000000c000000000000046")
WINDOWS_EPOCH = datetime(1601, 1, 1, tzinfo=UTC)


def filetime(value: datetime) -> int:
    return int((value - WINDOWS_EPOCH).total_seconds() * 10_000_000)


def prefetch_fixture(version: int = 30) -> bytes:
    data = bytearray(512)
    struct.pack_into("<I4sI", data, 0, version, b"SCCA", 0)
    struct.pack_into("<I", data, 12, len(data))
    name = "APP.EXE".encode("utf-16-le")
    data[16 : 16 + len(name)] = name
    struct.pack_into("<I", data, 76, 0x1234ABCD)
    paths = "\\DEVICE\\HARDDISKVOLUME1\\APP.EXE\x00C:\\WINDOWS\\SYSTEM32\\KERNEL32.DLL\x00"
    encoded_paths = paths.encode("utf-16-le")
    data[224 : 224 + len(encoded_paths)] = encoded_paths
    struct.pack_into("<II", data, 100, 224, len(encoded_paths))
    struct.pack_into("<II", data, 108, 368, 1)
    timestamps = [
        datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC),
        datetime(2024, 1, 1, 3, 4, 5, tzinfo=UTC),
    ]
    execution_offset = 120 if version == 17 else 128
    execution_count = 1 if version in {17, 23} else 8
    for index, timestamp in enumerate(timestamps[:execution_count]):
        struct.pack_into("<Q", data, execution_offset + index * 8, filetime(timestamp))
    run_count_offset = {17: 144, 23: 152, 26: 208, 30: 208, 31: 208}.get(version, 208)
    struct.pack_into("<I", data, run_count_offset, 7)
    volume_path = "\\DEVICE\\HARDDISKVOLUME1".encode("utf-16-le")
    struct.pack_into(
        "<IIQI", data, 368, 96, len(volume_path) // 2, filetime(timestamps[1]), 0xA1B2C3D4
    )
    data[464 : 464 + len(volume_path)] = volume_path
    return bytes(data)


def lnk_fixture(*, network: bool = False) -> bytes:
    flags = 0x01 | 0x02 | 0x04 | 0x08 | 0x10 | 0x20 | 0x40 | 0x80
    header = bytearray(76)
    struct.pack_into("<I", header, 0, 76)
    header[4:20] = SHELL_LINK_CLSID
    struct.pack_into("<II", header, 20, flags, 0x20)
    times = [
        datetime(2024, 2, 1, tzinfo=UTC),
        datetime(2024, 2, 2, tzinfo=UTC),
        datetime(2024, 2, 3, tzinfo=UTC),
    ]
    for index, timestamp in enumerate(times):
        struct.pack_into("<Q", header, 28 + index * 8, filetime(timestamp))
    struct.pack_into("<III", header, 52, 12345, 0, 1)
    id_item = struct.pack("<HB3s", 6, 0x31, b"abc") + b"\x00\x00"
    id_list = struct.pack("<H", len(id_item)) + id_item
    link_info = _network_link_info() if network else _local_link_info()
    strings = b"".join(
        _unicode_string(value)
        for value in (
            "Synthetic link",
            ".\\app.exe",
            "C:\\Tools",
            "--safe-test",
            "C:\\Icons\\app.ico",
        )
    )
    tracker = bytearray(96)
    struct.pack_into("<II", tracker, 0, 96, 0xA0000003)
    tracker[16:28] = b"TEST-MACHINE"
    for offset, value in zip((32, 48, 64, 80), range(1, 5), strict=True):
        tracker[offset : offset + 16] = uuid.UUID(int=value).bytes_le
    return bytes(header) + id_list + link_info + strings + bytes(tracker) + b"\x00\x00\x00\x00"


def _unicode_string(value: str) -> bytes:
    encoded = value.encode("utf-16-le")
    return struct.pack("<H", len(value)) + encoded


def _local_link_info() -> bytes:
    volume_label = b"TESTVOL\x00"
    volume = bytearray(16 + len(volume_label))
    struct.pack_into("<IIII", volume, 0, len(volume), 3, 0xA1B2C3D4, 16)
    volume[16:] = volume_label
    local = b"C:\\Tools\\app.exe\x00"
    suffix = b"app.exe\x00"
    volume_offset = 28
    local_offset = volume_offset + len(volume)
    suffix_offset = local_offset + len(local)
    block = bytearray(suffix_offset + len(suffix))
    struct.pack_into(
        "<IIIIIII",
        block,
        0,
        len(block),
        28,
        1,
        volume_offset,
        local_offset,
        0,
        suffix_offset,
    )
    block[volume_offset : volume_offset + len(volume)] = volume
    block[local_offset : local_offset + len(local)] = local
    block[suffix_offset:] = suffix
    return bytes(block)


def _network_link_info() -> bytes:
    share = b"\\\\SERVER\\SHARE\x00"
    device = b"Z:\x00"
    network = bytearray(20 + len(share) + len(device))
    struct.pack_into("<IIIII", network, 0, len(network), 3, 20, 20 + len(share), 0x20000)
    network[20 : 20 + len(share)] = share
    network[20 + len(share) :] = device
    suffix = b"folder\\target.txt\x00"
    network_offset = 28
    suffix_offset = network_offset + len(network)
    block = bytearray(suffix_offset + len(suffix))
    struct.pack_into(
        "<IIIIIII",
        block,
        0,
        len(block),
        28,
        2,
        0,
        0,
        network_offset,
        suffix_offset,
    )
    block[network_offset : network_offset + len(network)] = network
    block[suffix_offset:] = suffix
    return bytes(block)


def mft_record_fixture(*, valid_fixup: bool = True) -> bytes:
    record = bytearray(1024)
    record[:4] = b"FILE"
    struct.pack_into("<HHQHHHHIIQHHI", record, 4, 48, 3, 0, 5, 1, 56, 3, 0, 1024, 0, 1, 0, 42)
    record[48:54] = b"\xaa\xbb\x11\x22\x33\x44"
    record[510:512] = b"\xaa\xbb" if valid_fixup else b"\x00\x00"
    record[1022:1024] = b"\xaa\xbb"
    offset = 56
    si_times = [datetime(2020, 1, day, tzinfo=UTC) for day in range(1, 5)]
    si = bytearray(72)
    for index, timestamp in enumerate(si_times):
        struct.pack_into("<Q", si, index * 8, filetime(timestamp))
    struct.pack_into("<I", si, 32, 0x20)
    offset = _resident_attribute(record, offset, 0x10, bytes(si), 1)
    name = "example.txt"
    fn = bytearray(66 + len(name) * 2)
    struct.pack_into("<Q", fn, 0, 5 | (2 << 48))
    fn_times = [datetime(2021, 1, day, tzinfo=UTC) for day in range(1, 5)]
    for index, timestamp in enumerate(fn_times):
        struct.pack_into("<Q", fn, 8 + index * 8, filetime(timestamp))
    struct.pack_into("<QQI", fn, 40, 4096, 1234, 0x20)
    fn[64] = len(name)
    fn[65] = 1
    fn[66:] = name.encode("utf-16-le")
    offset = _resident_attribute(record, offset, 0x30, bytes(fn), 2)
    offset = _resident_attribute(record, offset, 0x80, b"abc", 3)
    runlist = b"\x11\x03\x05\x00"
    length = 72
    struct.pack_into(
        "<IIBBHHHQQHHIQQQ",
        record,
        offset,
        0x80,
        length,
        1,
        0,
        0,
        0,
        4,
        0,
        2,
        64,
        0,
        0,
        12288,
        9000,
        9000,
    )
    record[offset + 64 : offset + 64 + len(runlist)] = runlist
    offset += length
    struct.pack_into("<I", record, offset, 0xFFFFFFFF)
    offset += 8
    struct.pack_into("<I", record, 24, offset)
    return bytes(record)


def ntfs_volume_fixture() -> bytes:
    boot = bytearray(512)
    boot[3:11] = b"NTFS    "
    struct.pack_into("<HB", boot, 11, 512, 1)
    struct.pack_into("<Q", boot, 48, 1)
    struct.pack_into("<b", boot, 64, -10)
    struct.pack_into("<Q", boot, 72, 0x123456789ABCDEF0)
    boot[510:512] = b"\x55\xaa"
    return bytes(boot) + mft_record_fixture()


def _resident_attribute(
    record: bytearray, offset: int, type_code: int, value: bytes, attribute_id: int
) -> int:
    length = (24 + len(value) + 7) & ~7
    struct.pack_into(
        "<IIBBHHHIHBB",
        record,
        offset,
        type_code,
        length,
        0,
        0,
        0,
        0,
        attribute_id,
        len(value),
        24,
        0,
        0,
    )
    record[offset + 24 : offset + 24 + len(value)] = value
    return offset + length
