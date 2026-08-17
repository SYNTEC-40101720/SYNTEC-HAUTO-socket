(function () {
    "use strict";

    const serverToggle = document.getElementById("server-toggle");
    const tcpPort = document.getElementById("tcp-port");
    const serverStatusPill = document.getElementById("server-status-pill");
    const serverStatusText = document.getElementById("server-status-text");
    const clientText = document.getElementById("client-text");
    const listenPort = document.getElementById("listen-port");
    const serverMessage = document.getElementById("server-message");
    const mpgTotal = document.getElementById("mpg-total");
    const ioModeValue = document.getElementById("io-mode-value");
    const notice = document.getElementById("notice");
    const keyButtons = Array.from(document.querySelectorAll("[data-key-index]"));
    const modeButtons = Array.from(document.querySelectorAll("[data-mode]"));
    const mpgButtons = Array.from(document.querySelectorAll("[data-direction]"));
    const modeLabels = { auto: "自动", manual: "手动", remote: "远程" };

    let actionQueue = Promise.resolve();
    let noticeTimer = null;
    let lastError = null;
    let mpgHoldTimer = null;
    let mpgRepeatTimer = null;

    function showNotice(message) {
        notice.textContent = message;
        notice.classList.add("is-visible");
        window.clearTimeout(noticeTimer);
        noticeTimer = window.setTimeout(function () {
            notice.classList.remove("is-visible");
        }, 2800);
    }

    async function requestJson(path, options) {
        const response = await fetch(path, Object.assign({
            headers: { "Content-Type": "application/json" }
        }, options || {}));
        const data = await response.json();
        if (!response.ok || data.ok === false) {
            throw new Error(data.message || "请求失败");
        }
        return data;
    }

    function queueAction(path, options) {
        actionQueue = actionQueue
            .then(function () { return requestJson(path, options); })
            .then(function (data) {
                if (data.state) {
                    updateState(data.state);
                }
                return data;
            })
            .catch(function (error) {
                showNotice(error.message);
            });
        return actionQueue;
    }

    function updateState(state) {
        const server = state.server;
        const client = server.client;
        const connected = Boolean(server.listening && client);
        const listening = Boolean(server.listening);

        serverStatusPill.classList.toggle("is-listening", listening && !connected);
        serverStatusPill.classList.toggle("is-connected", connected);
        serverStatusText.textContent = connected ? "已连接" : (listening ? "监听中" : "已停止");
        clientText.textContent = client
            ? "客户端 " + client.ip + ":" + client.port
            : "客户端未连接";
        listenPort.textContent = listening ? ":" + server.port : "未监听";
        tcpPort.value = state.configured_port || 802;
        tcpPort.disabled = listening;

        serverToggle.classList.toggle("button-stop", listening);
        serverToggle.classList.toggle("button-primary", !listening);
        serverToggle.querySelector(".button-icon").textContent = listening ? "■" : "▶";
        serverToggle.querySelector("span:last-child").textContent = listening ? "停止服务" : "启动服务";

        const message = state.last_error || (connected ? "TCP 客户端已接入" : (listening ? "等待客户端连接" : "等待操作"));
        serverMessage.textContent = message;
        serverMessage.classList.toggle("is-error", Boolean(state.last_error));
        if (state.last_error && state.last_error !== lastError) {
            showNotice(state.last_error);
        }
        lastError = state.last_error || null;

        mpgTotal.textContent = state.mpg_total;
        const modeName = ["manual", "auto", "remote"][state.io_mode] || "manual";
        ioModeValue.textContent = modeLabels[modeName];
        modeButtons.forEach(function (button) {
            button.classList.toggle("is-active", button.dataset.mode === modeName);
        });

        document.querySelectorAll("[data-led-index]").forEach(function (lamp) {
            lamp.classList.toggle("is-on", Boolean(state.leds[Number(lamp.dataset.ledIndex)]));
        });
        const buzzer = document.querySelector("[data-buzzer]");
        buzzer.classList.toggle("is-on", Boolean(state.buzzer));

        keyButtons.forEach(function (button) {
            button.classList.toggle("is-pressed", Boolean(state.key_states[Number(button.dataset.keyIndex)]));
        });
    }

    async function refreshState() {
        try {
            const data = await requestJson("/api/state", { method: "GET" });
            updateState(data);
        } catch (error) {
            serverMessage.textContent = "无法读取服务状态";
            serverMessage.classList.add("is-error");
        }
    }

    serverToggle.addEventListener("click", async function () {
        try {
            if (serverStatusPill.classList.contains("is-listening")) {
                await requestJson("/api/server/stop", { method: "POST", body: "{}" });
            } else if (serverStatusPill.classList.contains("is-connected")) {
                await requestJson("/api/server/stop", { method: "POST", body: "{}" });
            } else {
                const data = await requestJson("/api/server/start", {
                    method: "POST",
                    body: JSON.stringify({ port: Number(tcpPort.value) })
                });
                updateState(data.state);
            }
            await refreshState();
        } catch (error) {
            showNotice(error.message);
            await refreshState();
        }
    });

    modeButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            queueAction("/api/io", {
                method: "POST",
                body: JSON.stringify({ mode: button.dataset.mode })
            });
        });
    });

    function sendKey(index, action) {
        return queueAction("/api/keys/" + index, {
            method: "POST",
            body: JSON.stringify({ action: action })
        });
    }

    keyButtons.forEach(function (button) {
        const index = Number(button.dataset.keyIndex);
        const modifier = button.classList.contains("is-modifier");
        let pointerActive = false;

        button.addEventListener("pointerdown", function (event) {
            if (event.button !== 0) {
                return;
            }
            event.preventDefault();
            pointerActive = true;
            button.setPointerCapture(event.pointerId);
            if (!modifier) {
                button.classList.add("is-pressed");
            }
            sendKey(index, "press");
        });

        button.addEventListener("pointerup", function (event) {
            if (!pointerActive) {
                return;
            }
            event.preventDefault();
            pointerActive = false;
            if (!modifier) {
                button.classList.remove("is-pressed");
                sendKey(index, "release");
            }
        });

        button.addEventListener("pointercancel", function () {
            if (pointerActive && !modifier) {
                sendKey(index, "release");
            }
            pointerActive = false;
            button.classList.remove("is-pressed");
        });

        button.addEventListener("keydown", function (event) {
            if ((event.code !== "Space" && event.code !== "Enter") || event.repeat) {
                return;
            }
            event.preventDefault();
            if (!modifier) {
                button.classList.add("is-pressed");
            }
            sendKey(index, "press");
        });

        button.addEventListener("keyup", function (event) {
            if (modifier || (event.code !== "Space" && event.code !== "Enter")) {
                return;
            }
            event.preventDefault();
            button.classList.remove("is-pressed");
            sendKey(index, "release");
        });
    });

    function stopMpg() {
        window.clearTimeout(mpgHoldTimer);
        window.clearInterval(mpgRepeatTimer);
        mpgHoldTimer = null;
        mpgRepeatTimer = null;
    }

    mpgButtons.forEach(function (button) {
        button.addEventListener("pointerdown", function (event) {
            if (event.button !== 0) {
                return;
            }
            event.preventDefault();
            const direction = Number(button.dataset.direction);
            button.setPointerCapture(event.pointerId);
            queueAction("/api/mpg", {
                method: "POST",
                body: JSON.stringify({ direction: direction })
            });
            stopMpg();
            mpgHoldTimer = window.setTimeout(function () {
                mpgRepeatTimer = window.setInterval(function () {
                    queueAction("/api/mpg", {
                        method: "POST",
                        body: JSON.stringify({ direction: direction })
                    });
                }, 100);
            }, 300);
        });
        button.addEventListener("pointerup", stopMpg);
        button.addEventListener("pointercancel", stopMpg);
    });

    window.addEventListener("blur", function () {
        stopMpg();
        queueAction("/api/keys/release-all", { method: "POST", body: "{}" });
    });

    refreshState();
    window.setInterval(refreshState, 700);
}());