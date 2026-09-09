# Phase 6 binary regression fixtures

Phase 6 tests generate deterministic, synthetic binary structures in
`tests/support/phase6_fixtures.py`. They are structurally encoded Prefetch, Shell Link, MFT record,
and minimal NTFS volume inputs—not JSON stand-ins. They contain only generic labels such as
`APP.EXE`, `example.txt`, `TESTVOL`, and `TEST-MACHINE`.

The builders exercise:

- an uncompressed Prefetch version 30 header, execution history, referenced-path strings, and
  volume entry;
- local and network Shell Link LinkInfo structures, StringData, an IDList item, and TrackerData;
- a fixed-up 1,024-byte FILE record with `$STANDARD_INFORMATION`, `$FILE_NAME`, resident `$DATA`,
  and non-resident `$DATA` run metadata;
- an NTFS boot sector whose geometry locates that MFT record without fixed sector, cluster, or
  record-size assumptions.

Malformed and unsupported variants are derived deterministically from these structures in tests.
The fixtures are generated only in memory or pytest temporary storage, and no personal evidence,
malware, confidential data, recovered file content, or forensic conclusion is included.
