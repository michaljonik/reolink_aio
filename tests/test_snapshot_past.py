from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from reolink_aio.baichuan.baichuan import Baichuan
from reolink_aio.exceptions import UnexpectedDataError

FRAME = b"\x00\x00\x00\x01" + b"i-frame-data"


def _payload(stream_magic: bytes) -> bytes:
    """Build a CoverPreview payload: 32-byte stream info header + one I-frame."""
    info = stream_magic + (32).to_bytes(4, "little") + bytes(24)
    frame_header = b"00dcH264" + len(FRAME).to_bytes(4, "little") + (8).to_bytes(4, "little") + bytes(8) + bytes(8)
    return info + frame_header + FRAME + bytes(8 - len(FRAME) % 8)


class TestSnapshotPast(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.baichuan = Baichuan(
            host="127.0.0.1",
            username="user",
            password="password",
            http_api=SimpleNamespace(nvr_name="test", _updating=False),
        )

    async def _snapshot_past(self, stream_magic: bytes) -> AsyncMock:
        self.baichuan.send_payload = AsyncMock(return_value=("<ok/>", _payload(stream_magic)))  # type: ignore[method-assign]
        with patch("reolink_aio.baichuan.baichuan.i_frame_to_jpeg", AsyncMock(return_value=b"jpeg")) as to_jpeg:
            assert await self.baichuan.snapshot_past(0, datetime(2026, 11, 1, 11, 2, 32)) == b"jpeg"
        return to_jpeg

    async def test_info_v1(self) -> None:
        to_jpeg = await self._snapshot_past(b"1001")
        assert to_jpeg.call_args.args[0] == FRAME

    async def test_info_v2(self) -> None:
        to_jpeg = await self._snapshot_past(b"1002")
        assert to_jpeg.call_args.args[0] == FRAME

    async def test_unknown_header(self) -> None:
        self.baichuan.send_payload = AsyncMock(return_value=("<ok/>", _payload(b"9999")))  # type: ignore[method-assign]
        with self.assertRaises(UnexpectedDataError):
            await self.baichuan.snapshot_past(0, datetime(2026, 11, 1, 11, 2, 32))


if __name__ == "__main__":
    unittest.main()
