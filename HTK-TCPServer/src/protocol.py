"""
示教器通信协议定义
9字节定长帧，首字节功能码
"""

from __future__ import annotations
from typing import Optional

FRAME_SIZE = 9


class CMD:
    """功能码"""
    VERSION = 0x01       # 版本握手（服务端→客户端）
    KEY = 0x02           # 按键状态（服务端→客户端）
    MPG = 0x03           # MPG编码器（服务端→客户端）
    JOYSTICK = 0x04      # 摇杆数据（服务端→客户端）
    IO = 0x05            # IO/钥匙（服务端→客户端）
    LED_BUZZER = 0x07    # LED+蜂鸣器控制（客户端→服务端）

    NAMES = {0x01: "VERSION", 0x02: "KEY", 0x03: "MPG",
             0x04: "JOYSTICK", 0x05: "IO", 0x07: "LED_BUZZER"}


class FrameBuffer:
    """粘包/拆包帧缓冲区"""

    def __init__(self):
        self._buf = bytearray()

    def feed(self, data: bytes) -> None:
        self._buf.extend(data)

    def pop_frame(self) -> Optional[bytes]:
        if len(self._buf) >= FRAME_SIZE:
            frame = bytes(self._buf[:FRAME_SIZE])
            del self._buf[:FRAME_SIZE]
            return frame
        return None

    def clear(self) -> None:
        self._buf.clear()


# ─── 帧构建 ──────────────────────────────────────────

def build_version_frame() -> bytes:
    return bytes([CMD.VERSION, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00])


def build_key_frame(key1: int, key2: int) -> bytes:
    return bytes([CMD.KEY]) + key1.to_bytes(4, 'little') + key2.to_bytes(4, 'little')


def build_mpg_frame(total: int, inc: int) -> bytes:
    return bytes([CMD.MPG]) + total.to_bytes(4, 'little', signed=True) + inc.to_bytes(4, 'little', signed=True)



def build_io_frame(io1: int, io2: int) -> bytes:
    return bytes([CMD.IO]) + io1.to_bytes(4, 'little') + io2.to_bytes(4, 'little')


# ─── 帧解析 ──────────────────────────────────────────

def parse_frame(frame: bytes) -> tuple[int, bytes]:
    if len(frame) != FRAME_SIZE:
        raise ValueError(f"Expected {FRAME_SIZE} bytes, got {len(frame)}")
    return frame[0], frame[1:9]


def parse_led_buzzer_byte(payload: bytes) -> int:
    """解析LED+蜂鸣器状态，返回2字节值"""
    return payload[0] | (payload[1] << 8)



