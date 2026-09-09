# Phase 5 parser fixtures

These fixtures contain no case data and are used only in isolated automated tests. They are stored
as deterministic gzip/base64 text so repository tooling can handle the binary formats safely.

- `evtx_issue38.evtx.gz.b64` is the one-record `issue_38.evtx` regression fixture from
  `williballenthin/python-evtx`, Apache-2.0. It contains intentionally generic test identities and
  was selected because it is the smallest valid upstream EVTX fixture. Decoded size: 69,632 bytes;
  SHA-256: `becab64455866f8fae5583fbaa5dab901115e4397ea7abe14f37ad732d5d7eb9`.
- `registry_issue22.hive.gz.b64` is the 8 KiB `issue22.hive` regression fixture from
  `williballenthin/python-registry`, Apache-2.0. It contains a `REG_SZ` `TimeZoneKeyName` value and
  exercises the explicit unknown-hive-type behavior. Decoded size: 8,192 bytes; SHA-256:
  `8c07023d99090b354194b319264762a3107e2e5d0614f03368de64e8ca5db11e`.

Tests decode fixtures into pytest temporary directories. Decoded files are never written into the
repository or application evidence storage.
