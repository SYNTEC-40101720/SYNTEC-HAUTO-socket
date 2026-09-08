# SYNTEC HTK TCP Server

SYNTEC 示教器 TCP 服务端和 WebView 桌面模拟端，用于测试示教器按键、MPG、IO、LED 和蜂鸣器通信。

## 当前版本

- 应用版本：`1.0.1.0`
- GitHub Release：[v1.0.1](https://github.com/SYNTEC-40101720/SYNTEC-HAUTO-socket/releases/tag/v1.0.1)
- 运行平台：Windows
- 默认 TCP 端口：`802`

## 功能

- 63 个示教器按键模拟，按键名称和颜色可由 `keys.json` 配置。
- TCP 服务启动、停止和客户端连接状态显示。
- IO 模式切换：自动、手动、远程。
- MPG 手轮正向和反向步进。
- LED 和蜂鸣器状态接收与显示。
- LED 指示灯映射到按键左上角：

| LED | 按键 |
| --- | --- |
| L1 | K11 伺服上电 |
| L2 | K12 模拟试跑 |
| L3 | K17 外部轴 |
| L4 | K18 焊接有效 |
| L5 | K20 手轮 |
| L6 | K25 单步执行 |
| L7 | K58 AUX 1 |
| L8 | K59 AUX 2 |
| L9 | K60 AUX 3 |

## 从源码运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

启动后，桌面窗口会打开示教器模拟界面。默认 Web 服务地址为 `http://127.0.0.1:8080`。

## 打包

PyInstaller 配置文件为 `SYNTEC-HTK-TCPServer.spec`。在 Windows 域控环境中，请在不含中文、空格和特殊字符的路径执行构建：

```powershell
python -m PyInstaller --clean --noconfirm SYNTEC-HTK-TCPServer.spec
```

标准输出目录：

```text
dist/SYNTEC-HTK-TCPServer/
```

请保留整个目录，运行其中的 `SYNTEC-HTK-TCPServer.exe`，不要只拷贝单个 EXE 文件。构建使用窗口模式、禁用 UPX，并写入 SYNTEC 版本元数据。

## 发布包

最新 Windows x64 发布包可从 [GitHub Releases](https://github.com/SYNTEC-40101720/SYNTEC-HAUTO-socket/releases/latest) 下载。解压 ZIP 后运行：

```text
SYNTEC-HTK-TCPServer/SYNTEC-HTK-TCPServer.exe
```

同时提供 `.sha256` 文件用于校验下载包。

## 项目文件

- `main.py`：桌面应用入口。
- `src/web_app.py`：Flask Web 应用和共享状态。
- `src/protocol.py`：示教器 TCP 帧定义和解析。
- `src/tcp_server.py`：TCP 服务端。
- `web/`：HTML、CSS 和 JavaScript 界面。
- `keys.json`：按键名称和颜色配置。
- `SYNTEC-HTK-TCPServer.spec`：PyInstaller 打包配置。
