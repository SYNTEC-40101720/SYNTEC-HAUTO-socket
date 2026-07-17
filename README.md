# SYNTEC-HAUTO-socket

SYNTEC 示教器 TCP 通信协议模拟工具集，包含服务端仿真与客户端测试工具。

---

## 📦 项目结构

```
SYNTEC-HAUTO-socket/
├── HTK-TCPServer/        # 示教器 TCP 服务端模拟器
│   ├── src/              # 核心逻辑：协议解析、服务端、UI
│   ├── keys.json         # 按键配置（名称、颜色）
│   ├── main.py           # 入口
│   └── requirements.txt
│
├── CNC-TCPClient/        # 示教器 TCP 客户端（上位机模拟）
│   ├── src/              # 核心逻辑：协议解析、客户端、UI
│   ├── config.ini        # 连接配置
│   ├── main.py           # 入口
│   └── requirements.txt
│
└── .gitignore
```

## 🔌 通信协议

9 字节定长帧，首字节为功能码：

| 功能码 | 方向 | 说明 |
|--------|------|------|
| `0x01` | 服务端 → 客户端 | 版本握手 |
| `0x02` | 服务端 → 客户端 | 按键状态 |
| `0x03` | 服务端 → 客户端 | MPG 编码器 |
| `0x04` | 服务端 → 客户端 | 摇杆数据 |
| `0x05` | 服务端 → 客户端 | IO / 钥匙 |
| `0x07` | 客户端 → 服务端 | LED + 蜂鸣器控制 |

## 🚀 快速开始

### 服务端（模拟示教器）

```bash
cd HTK-TCPServer
pip install -r requirements.txt
python main.py
```

### 客户端（测试工具）

```bash
cd CNC-TCPClient
pip install -r requirements.txt
# 编辑 config.ini 设置目标 IP 和端口
python main.py
```

## 🖥️ 环境要求

- Python ≥ 3.8
- PyQt5 ≥ 5.15

## 📄 License

内部工具 · SYNTEC
