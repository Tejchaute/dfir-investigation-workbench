import base64
import gzip
from pathlib import Path

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "phase5"


def materialize_fixture(name: str, destination: Path) -> bytes:
    encoded = (FIXTURE_ROOT / name).read_text(encoding="ascii")
    content = gzip.decompress(base64.b64decode(encoded))
    destination.write_bytes(content)
    return content
