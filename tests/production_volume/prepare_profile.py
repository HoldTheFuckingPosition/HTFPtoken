"""Bind the new sale policy to the retained 2,500/500 local fixture."""

import argparse
from hashlib import sha256
from pathlib import Path
import re
from struct import pack_into


FIXTURE_PROFILE = "fixture-source/htfp-cpmm-2500-500/src/processing_profile.rs"
PROFILE_SHA256 = "d62d800a9997ddac05345935e6d74cf9292a168f0ad6d7c4f56c46469b6c7d02"
PREIMAGE_SHA256 = "1907f616b5085e5eee2aab53e3c83b1bbf3e47af3be41ab2dff1a07d44f99f16"
RETIRED = "ALPHA_NUM|ALPHA_DEN|C_BASE|SCALE_D|CAPACITY_SCALED|INITIAL_CREDIT_SCALED|REFILL_N|START_TIMESTAMP"


def pinned(path, digest):
    data = path.read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError(f"Retained fixture digest mismatch: {path.name}")
    return data


def production_preimage(fixture):
    original = pinned(fixture / "fixture-preimage.bin", PREIMAGE_SHA256)
    data = bytearray(original)
    data[:16] = b"HTFP_TAX_PRD_V02"
    pack_into("<H", data, 16, 2)
    pack_into("<QQ", data, 1080, 1, 100)
    data[1096:1128] = bytes(32)
    if len(data) != len(original):
        raise ValueError("Unexpected binding length")
    return data


def prepare(fixture, output):
    data = production_preimage(fixture)
    source = pinned(fixture / FIXTURE_PROFILE, PROFILE_SHA256).decode()
    _, source = source.split("\n", 1)
    source = "// Isolated 2,500/500 fixture with the production sale policy.\n" + source
    for name, value in (
        ("PROCESSING_PREIMAGE", data),
        ("PROCESSING_COMMITMENT", sha256(data).digest()),
    ):
        array = ", ".join(map(str, value))
        source, changed = re.subn(
            rf"pub const {name}:\[u8;\d+\]=\[[^\]]+\];",
            f"pub const {name}:[u8;{len(value)}]=[{array}];", source,
        )
        if changed != 1:
            raise ValueError(f"Unexpected syntax for {name}")
    source, changed = re.subn(rf"^pub const ({RETIRED}):[^\n]+\n", "", source, flags=re.M)
    if changed != 8:
        raise ValueError("Unexpected legacy fixture policy fields")
    with output.open("x") as target:
        target.write(source)
    return sha256(data).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.fixture_root, args.output))
