"""
示教器通信协议定义
9字节定长帧，首字节功能码
"""

from __future__ import annotations
import struct

FRAME_SIZE = 9
KEY_COUNT = 63  # 63个按键，bit 0-62


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

    def feed(self, data: bytes):
        self._buf.extend(data)

    def pop_frame(self):
        if len(self._buf) >= FRAME_SIZE:
            frame = bytes(self._buf[:FRAME_SIZE])
            del self._buf[:FRAME_SIZE]
            return frame
        return None

    def clear(self):
        self._buf.clear()


# ─── 帧构建 ──────────────────────────────────────────

def build_version_frame() -> bytes:
    return bytes([CMD.VERSION, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00])


def build_key_frame(key1: int, key2: int) -> bytes:
    return bytes([CMD.KEY]) + key1.to_bytes(4, 'little') + key2.to_bytes(4, 'little')


def build_mpg_frame(total: int, inc: int) -> bytes:
    return bytes([CMD.MPG]) + total.to_bytes(4, 'little', signed=True) + inc.to_bytes(4, 'little', signed=True)


def build_joystick_frame(x: int, y: int, z: int, key: int) -> bytes:
    return bytes([CMD.JOYSTICK]) + struct.pack('<hhhh', x, y, z, key)


def build_io_frame(io1: int, io2: int) -> bytes:
    return bytes([CMD.IO]) + io1.to_bytes(4, 'little') + io2.to_bytes(4, 'little')


def build_led_buzzer_frame(led_state: int) -> bytes:
    """
    构建LED+蜂鸣器控制帧

    参数:
        led_state: 2字节值，bit 0-8对应LED1-LED9，bit 15对应蜂鸣器

    返回:
        9字节帧数据
    """
    b0 = led_state & 0xFF
    b1 = (led_state >> 8) & 0xFF
    return bytes([CMD.LED_BUZZER, b0, b1, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


# ─── 帧解析 ──────────────────────────────────────────

def parse_frame(frame: bytes):
    if len(frame) != FRAME_SIZE:
        return None, None
    return frame[0], frame[1:9]


def parse_key_data(payload: bytes):
    return int.from_bytes(payload[0:4], 'little'), int.from_bytes(payload[4:8], 'little')


def parse_mpg_data(payload: bytes):
    return int.from_bytes(payload[0:4], 'little', signed=True), int.from_bytes(payload[4:8], 'little', signed=True)


def parse_joystick_data(payload: bytes):
    return struct.unpack('<hhhh', payload[0:8])


def parse_io_data(payload: bytes):
    return int.from_bytes(payload[0:4], 'little'), int.from_bytes(payload[4:8], 'little')


def parse_led_buzzer_byte(payload: bytes) -> int:
    """解析LED+蜂鸣器状态，返回2字节值"""
    return payload[0] | (payload[1] << 8)


# ─── LED/蜂鸣器工具 ─────────────────────────────────

def led_buzzer_decode(state: int) -> dict:
    """
    解码LED+蜂鸣器状态

    参数:
        state: 2字节值

    返回:
        字典，包含led1-led9和buzzer的布尔值
    """
    result = {}
    for i in range(1, 10):
        result[f'led{i}'] = bool(state & (1 << (i - 1)))
    result['buzzer'] = bool(state & 0x8000)
    return result


def led_buzzer_encode(
    led1=False, led2=False, led3=False, led4=False,
    led5=False, led6=False, led7=False, led8=False,
    led9=False, buzzer=False
) -> int:
    """
    编码LED+蜂鸣器状态

    参数:
        led1-led9: 9个LED的状态
        buzzer: 蜂鸣器状态（对应bit 15）

    返回:
        2字节整数值
    """
    state = 0
    if led1: state |= 0x0001
    if led2: state |= 0x0002
    if led3: state |= 0x0004
    if led4: state |= 0x0008
    if led5: state |= 0x0010
    if led6: state |= 0x0020
    if led7: state |= 0x0040
    if led8: state |= 0x0080
    if led9: state |= 0x0100
    if buzzer: state |= 0x8000
    return state


def frame_hex(frame: bytes) -> str:
    return ' '.join(f'{b:02X}' for b in frame)
