import subprocess
import sys
import time
import shutil
import os
import re
import socket
import threading

os.makedirs("log", exist_ok=True)
start_time = time.strftime("%Y%m%d-%H%M%S")
LOG_FILE = f"log/colxfce_lxqt_{start_time}_startup.log"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== COLXFCE STARTUP LOG ===\n")
    f.write(f"Start time: {time.ctime()}\n\n")

def stream_log(p, cmd):
    try:
        for line in iter(p.stdout.readline, ''):
            if not line:
                break
            log(f"[BG] {cmd}: {line.strip()}")
    except Exception as e:
        log(f"[STREAM ERROR] {cmd}: {e}")

def rotate_log_if_needed():
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 10_000_000:
        print("i: Log file rotated")
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("=== LOG ROTATED ===\n")

log_lock = threading.Lock()

def log(text):
    with log_lock:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 10_000_000:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("=== LOG ROTATED ===\n")

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(text + "\n")

def wait_port(port, timeout=40):
    for _ in range(timeout):
        try:
            s = socket.create_connection(("127.0.0.1", port), 1)
            s.close()
            return True
        except Exception:
            time.sleep(1)
    return False

def run(cmd, desc):
    print(f"[RUN] {cmd} ({desc})")
    log(f"[RUN] {cmd} ({desc})")

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )

    if result.stdout:
        log(f"[RUN] {cmd} msg:")
        log(result.stdout)

    if result.stderr:
        log("[ERR] " + result.stderr)

    return result

def run_bg(cmd, desc):
    log(f"[BG] {cmd} ({desc})")

    p = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True
    )

    threading.Thread(target=stream_log, args=(p, cmd), daemon=True).start()

    return p

def run_bg_cloud(cmd, desc):
    log(f"[BG] {cmd} ({desc})")

    p = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in p.stdout:
        line = line.strip()
        log(line)

        match = re.search(r"https://[^\s]+trycloudflare\.com[^\s]*", line)
        if match:
            url = match.group(0)
            print("for-everyone link:", url)
            log("for-everyone link: " + url)

    return p

def run_bg_env(cmd, desc, env):
    log(f"[BG] {cmd} ({desc})")

    p = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
        env=env
    )

    threading.Thread(target=stream_log, args=(p, cmd), daemon=True).start()

    return p

def install():
    print("colxfce: the necessary equipment is starting to be installed")
    log(f"\n=== COLXFCE INSTALL START {time.ctime()} ===\n")

    cloudflared_rc = 0

    r1 = run("apt-get update", "packages are being updated")

    r2 = run("apt-get install -y lxqt-core lxqt-session openbox x11vnc xvfb dbus-x11 wget curl novnc websockify", "almost all the necessary equipment is being installed")


    if not shutil.which("cloudflared"):
        print("colxfce: installing cloudflared")
        r3 = run("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared", "install cloudflared")
        run("chmod +x cloudflared", "grant permission to execute")
        run("mv cloudflared /usr/local/bin/", "move cloudflared to path")
        print("colxfce: cloudflared installed");

        cloudflared_rc = r3.returncode

    print("colxfce: installation of the necessary tools is completed")
    log(f"\n=== COLXFCE INSTALL STOP {time.ctime()} ===\n")

    return max(r1.returncode, r2.returncode, cloudflared_rc)

def start_core():
    print("colxfce: starting core")
    log(f"\n=== COLXFCE CORE START {time.ctime()} ===\n")

    run_bg("Xvfb :1 -screen 0 1280x720x24", "virtual screen")
    time.sleep(3)

    env = os.environ.copy()
    env["DISPLAY"] = ":1"

    run_bg_env("dbus-launch startlxqt", "LXQt starter", env)
    time.sleep(5)

    run_bg("x11vnc -display :1 -nopw -forever -shared", "VNC")
    time.sleep(3)
    wait_port(5900, 40)

    run_bg("websockify --web /usr/share/novnc 6080 localhost:5900", "noVNC")
    wait_port(6080, 40)

    log(f"\n=== COLXFCE CORE STOP {time.ctime()} ===\n")

def for_session():
    log(f"\n=== COLXFCE FOR-SESSION START {time.ctime()} ===\n")
    from google.colab.output import eval_js
    url = eval_js("google.colab.kernel.proxyPort(6080)")
    print("for-session link:", url)

def for_everyone():
    log(f"\n=== COLXFCE FOR-EVERYONE START {time.ctime()} ===\n")
    run_bg_cloud("cloudflared tunnel --url http://localhost:6080", "cloudflared tunnel is being launched")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: colxfce [for-session | for-everyone]")
        sys.exit()

    mode = sys.argv[1]

    print("colxfce: ColXFCE is starting...")
    print(f"i: Log file is log/colxfce_lxqt_{start_time}_startup.log")
    install_code = install()

    if install_code != 0:
        print("Install failed")
        sys.exit()

    start_core()

    if mode == "for-session":
        for_session()

    elif mode == "for-everyone":
        for_everyone()

    else:
        print("colxfce: invalid parameter")
