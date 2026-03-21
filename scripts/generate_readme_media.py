#!/usr/bin/env python3
"""Capture real dashboard screenshots and GIF previews using headless Chrome CDP."""

from __future__ import annotations

import argparse
import base64
import contextlib
import io
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import requests
from PIL import Image, ImageOps
from websocket import create_connection


ROOT = Path(__file__).resolve().parent.parent
MEDIA_DIR = ROOT / "docs" / "media"
TARGET_SIZE = (1280, 720)
DEFAULT_DASHBOARD_URL = "http://127.0.0.1:3000/dashboard"
DEFAULT_CHROME_BINARY = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class CdpClient:
    def __init__(self, ws_url: str) -> None:
        self.ws = create_connection(ws_url, timeout=30)
        self._next_id = 0

    def close(self) -> None:
        self.ws.close()

    def call(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        payload = {"id": self._next_id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(payload))
        while True:
            response = json.loads(self.ws.recv())
            if response.get("id") != self._next_id:
                continue
            if "error" in response:
                raise RuntimeError(f"CDP error for {method}: {response['error']}")
            return response.get("result", {})

    def eval(self, expression: str):
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        return result.get("result", {}).get("value")


def _wait_for_http(url: str, timeout_seconds: float = 60.0) -> bool:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as response:
                if response.status < 500:
                    return True
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.5)
    return False


def _start_dashboard_process(port: int) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{env['PYTHONPATH']}" if env.get("PYTHONPATH") else src_path
    )
    runner = (
        "from dashboard.app import app; "
        f"app.run_server(debug=False, host='127.0.0.1', port={port})"
    )
    return subprocess.Popen(
        [sys.executable, "-c", runner],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _start_web_process(port: int) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        ["npm", "--prefix", "apps/web", "run", "dev", "--", "--port", str(port)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _start_chrome_process(chrome_binary: str, debug_port: int) -> subprocess.Popen[bytes]:
    chrome_profile = ROOT / ".tmp" / "chrome_profile"
    chrome_profile.mkdir(parents=True, exist_ok=True)
    cmd = [
        chrome_binary,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--remote-allow-origins=*",
        f"--remote-debugging-port={debug_port}",
        "--window-size=1600,1000",
        f"--user-data-dir={chrome_profile}",
        "about:blank",
    ]
    return subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _stop_process(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=2)


def _fit_image(png_bytes: bytes) -> Image.Image:
    with Image.open(io.BytesIO(png_bytes)) as img:
        rgb = img.convert("RGB")
    return ImageOps.fit(rgb, TARGET_SIZE, method=Image.Resampling.LANCZOS)


def _save_png(path: Path, png_bytes: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fitted = _fit_image(png_bytes)
    fitted.save(path, format="PNG", optimize=True)


def _save_gif(path: Path, frames: list[Image.Image], duration_ms: int = 160) -> None:
    if not frames:
        raise ValueError("No GIF frames provided")
    path.parent.mkdir(parents=True, exist_ok=True)
    first = frames[0].convert("P", palette=Image.Palette.ADAPTIVE)
    rest = [frame.convert("P", palette=Image.Palette.ADAPTIVE) for frame in frames[1:]]
    first.save(path, format="GIF", save_all=True, append_images=rest, duration=duration_ms, loop=0)


def _cdp_png(client: CdpClient, *, full_page: bool = False, clip: dict | None = None) -> bytes:
    params: dict = {"format": "png", "fromSurface": True}
    if full_page:
        params["captureBeyondViewport"] = True
    if clip:
        params["clip"] = clip
    result = client.call("Page.captureScreenshot", params)
    return base64.b64decode(result["data"])


def _wait_for_selector(client: CdpClient, selector: str, timeout_seconds: float = 60.0) -> None:
    selector_json = json.dumps(selector)
    script = f"Boolean(document.querySelector({selector_json}))"
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if client.eval(script):
            return
        time.sleep(0.4)
    raise TimeoutError(f"Selector not found: {selector}")


def _get_bbox(client: CdpClient, selector: str) -> dict[str, float] | None:
    selector_json = json.dumps(selector)
    script = (
        "(() => {"
        f"  const el = document.querySelector({selector_json});"
        "  if (!el) return null;"
        "  const r = el.getBoundingClientRect();"
        "  return {"
        "    x: r.left + window.scrollX,"
        "    y: r.top + window.scrollY,"
        "    width: Math.max(1, r.width),"
        "    height: Math.max(1, r.height)"
        "  };"
        "})()"
    )
    value = client.eval(script)
    if not value:
        return None
    return {
        "x": float(value["x"]),
        "y": float(value["y"]),
        "width": float(value["width"]),
        "height": float(value["height"]),
    }


def _crop_box(image: Image.Image, bbox: dict[str, float], pad: int = 18) -> Image.Image:
    x0 = max(0, int(bbox["x"]) - pad)
    y0 = max(0, int(bbox["y"]) - pad)
    x1 = min(image.width, int(bbox["x"] + bbox["width"]) + pad)
    y1 = min(image.height, int(bbox["y"] + bbox["height"]) + pad)
    if x1 <= x0 or y1 <= y0:
        return image.copy()
    return image.crop((x0, y0, x1, y1))


def _capture_stills(client: CdpClient) -> None:
    client.eval("window.scrollTo(0, 0)")
    time.sleep(1.0)

    full_png = _cdp_png(client, full_page=True)
    with Image.open(io.BytesIO(full_png)) as full:
        full_rgb = full.convert("RGB")

    overview_crop = full_rgb.crop((0, 0, min(1600, full_rgb.width), min(1020, full_rgb.height)))
    ImageOps.fit(overview_crop, TARGET_SIZE, method=Image.Resampling.LANCZOS).save(
        MEDIA_DIR / "dashboard_overview.png", format="PNG", optimize=True
    )

    selector_map = {
        "risk_controls.png": ".summary-row",
        "performance_snapshot.png": ".column-left .chart-container:nth-of-type(1)",
        "architecture_layers.png": ".main-content",
        "canary_progress.png": ".column-right .table-container:nth-of-type(3)",
        "execution_pipeline.png": ".column-right .table-container:nth-of-type(2)",
        "ops_health.png": ".column-right .table-container:nth-of-type(5)",
        "simulation_leaderboard.png": ".column-right .table-container:nth-of-type(4)",
    }

    for filename, selector in selector_map.items():
        bbox = _get_bbox(client, selector)
        if not bbox:
            _save_png(MEDIA_DIR / filename, full_png)
            continue
        cropped = _crop_box(full_rgb, bbox)
        fitted = ImageOps.fit(cropped, TARGET_SIZE, method=Image.Resampling.LANCZOS)
        fitted.save(MEDIA_DIR / filename, format="PNG", optimize=True)


def _capture_gif(client: CdpClient, name: str, positions: list[int], duration_ms: int) -> None:
    frames: list[Image.Image] = []
    for pos in positions:
        client.eval(f"window.scrollTo(0, {pos})")
        time.sleep(0.6)
        viewport_png = _cdp_png(client)
        frames.append(_fit_image(viewport_png))
    _save_gif(MEDIA_DIR / name, frames, duration_ms=duration_ms)


def _connect_cdp(debug_port: int, target_url: str) -> CdpClient:
    base = f"http://127.0.0.1:{debug_port}"
    for _ in range(80):
        try:
            requests.get(f"{base}/json/version", timeout=1.0)
            break
        except requests.RequestException:
            time.sleep(0.25)
    else:
        raise RuntimeError("Chrome remote debugging endpoint did not become ready")

    try:
        response = requests.put(f"{base}/json/new?{target_url}", timeout=3.0)
        if response.status_code >= 400:
            response = requests.get(f"{base}/json/new?{target_url}", timeout=3.0)
    except requests.RequestException as exc:
        raise RuntimeError(f"Unable to create CDP target: {exc}") from exc

    target = response.json()
    ws_url = target.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError("CDP target did not return webSocketDebuggerUrl")
    return CdpClient(ws_url)


def _capture_media(base_url: str, chrome_binary: str, debug_port: int, surface: str) -> None:
    chrome_proc = _start_chrome_process(chrome_binary=chrome_binary, debug_port=debug_port)
    client: CdpClient | None = None
    try:
        print("Connecting to Chrome DevTools...")
        client = _connect_cdp(debug_port=debug_port, target_url=base_url)
        client.call("Page.enable")
        client.call("Runtime.enable")
        client.call(
            "Emulation.setDeviceMetricsOverride",
            {
                "mobile": False,
                "width": 1600,
                "height": 1000,
                "deviceScaleFactor": 1,
            },
        )
        time.sleep(2.0)
        if surface == "dash":
            _wait_for_selector(client, "#equity-chart", timeout_seconds=60.0)
            _wait_for_selector(client, "#price-chart", timeout_seconds=60.0)
            _wait_for_selector(client, "#simulation-leaderboard-table", timeout_seconds=60.0)
        else:
            _wait_for_selector(client, ".summary-row", timeout_seconds=60.0)
            _wait_for_selector(client, ".main-content", timeout_seconds=60.0)
            _wait_for_selector(client, ".table-container", timeout_seconds=60.0)
        time.sleep(1.5)

        print("Capturing screenshots...")
        _capture_stills(client)

        print("Capturing GIF previews...")
        _capture_gif(
            client,
            name="dashboard_pulse.gif",
            positions=[0, 0, 0, 0, 0, 0, 80, 0, 80, 0, 0, 0],
            duration_ms=180,
        )
        _capture_gif(
            client,
            name="leaderboard_cycle.gif",
            positions=[850, 1050, 1250, 1450, 1650, 1450, 1250, 1050, 850],
            duration_ms=180,
        )
        _capture_gif(
            client,
            name="risk_alert_flash.gif",
            positions=[500, 700, 900, 1100, 900, 700, 500, 300],
            duration_ms=160,
        )
    finally:
        if client:
            with contextlib.suppress(Exception):
                client.close()
        _stop_process(chrome_proc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_DASHBOARD_URL, help="Dashboard URL to capture.")
    parser.add_argument("--port", type=int, default=3000, help="Surface port when launching locally.")
    parser.add_argument(
        "--surface",
        choices=["web", "dash"],
        default="web",
        help="Capture source surface.",
    )
    parser.add_argument(
        "--chrome-binary",
        default=DEFAULT_CHROME_BINARY,
        help="Chrome binary path for headless capture.",
    )
    parser.add_argument(
        "--debug-port",
        type=int,
        default=9222,
        help="Chrome remote debugging port.",
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Assume dashboard is already running and do not launch it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dashboard_proc: subprocess.Popen[bytes] | None = None
    try:
        if not args.no_launch:
            if args.surface == "dash":
                print("Starting Dash process...")
                dashboard_proc = _start_dashboard_process(args.port)
            else:
                print("Starting web process...")
                dashboard_proc = _start_web_process(args.port)

        print(f"Waiting for dashboard at {args.url} ...")
        if not _wait_for_http(args.url):
            raise RuntimeError(f"Dashboard did not become ready at {args.url}")

        _capture_media(
            base_url=args.url,
            chrome_binary=args.chrome_binary,
            debug_port=args.debug_port,
            surface=args.surface,
        )
        print(f"Generated real dashboard media in {MEDIA_DIR}")
        return 0
    finally:
        _stop_process(dashboard_proc)


if __name__ == "__main__":
    raise SystemExit(main())
