#!/usr/bin/env python3
import argparse, json, math, os, shutil, struct, subprocess, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIEF = json.loads((ROOT / "data/brief.json").read_text())

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")

def storyboard(out):
    scenes = [{"id": i + 1, "duration": 2, **scene} for i, scene in enumerate(BRIEF["scenes"])]
    write_json(out / "storyboard.json", {"title": BRIEF["title"], "scenes": scenes})

def ppm(path, color, caption_seed, frame):
    width, height = 640, 360
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            glow = int(32 * math.sin((x + frame * 14) / 80) + 32 * math.cos(y / 65))
            band = 45 if abs(y - (caption_seed * 31 % 250 + 55)) < 8 else 0
            pixels.extend(max(0, min(255, c + glow + band)) for c in color)
    path.write_bytes(f"P6\n{width} {height}\n255\n".encode() + pixels)

def scenes(out):
    board = json.loads((out / "storyboard.json").read_text())
    count = 12 if os.getenv("AKOFLOW_PROFILE", "smoke") == "smoke" else 36
    frames = out / "frames"; frames.mkdir(exist_ok=True)
    index = 1
    for scene in board["scenes"]:
        for frame in range(count):
            ppm(frames / f"frame-{index:04d}.ppm", scene["color"], scene["id"], frame)
            index += 1
    write_json(out / "frames.json", {"fps": 6 if count == 12 else 12, "count": index - 1})

def narration(out):
    rate = 16000; seconds = len(BRIEF["scenes"]) * 2
    with wave.open(str(out / "narration.wav"), "wb") as audio:
        audio.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        for n in range(rate * seconds):
            scene = min(len(BRIEF["scenes"]) - 1, n // (rate * 2))
            hz = BRIEF["scenes"][scene]["tone_hz"]
            envelope = min(1, (n % (rate * 2)) / 2000, (rate * 2 - n % (rate * 2)) / 2000)
            audio.writeframesraw(struct.pack("<h", int(7000 * envelope * math.sin(2 * math.pi * hz * n / rate))))

def compose(out):
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required (or run inside the provided container)")
    meta = json.loads((out / "frames.json").read_text())
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(meta["fps"]),
        "-i", str(out / "frames/frame-%04d.ppm"), "-i", str(out / "narration.wav"), "-shortest",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out / "final.mp4")], check=True)

def quality(out):
    files = ["storyboard.json", "frames.json", "narration.wav", "final.mp4"]
    write_json(out / "quality-report.json", {"status": "passed", "checks": {f: (out / f).stat().st_size for f in files}})
    write_json(out / "manifest.json", {"showcase": "ai-video-studio", "status": "success", "artifacts": files + ["quality-report.json"]})

STAGES = {"storyboard": storyboard, "scenes": scenes, "narration": narration, "compose": compose, "quality-control": quality}
def main():
    p = argparse.ArgumentParser(); p.add_argument("--stage", choices=[*STAGES, "all"], default="all"); p.add_argument("--output", required=True)
    a = p.parse_args(); out = Path(a.output); out.mkdir(parents=True, exist_ok=True)
    order = list(STAGES)
    for stage in order if a.stage == "all" else [a.stage]: STAGES[stage](out)
if __name__ == "__main__": main()

