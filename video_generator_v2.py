
#!/usr/bin/env python3
"""Generate a narrated video from locally stored scene images."""

import argparse
import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts


async def make_voice(text, voice, destination):
    await edge_tts.Communicate(text, voice).save(str(destination))


def run(command):
    subprocess.run(command, check=True)


def parse_script(path):
    content = Path(path).read_text(encoding="utf-8")
    blocks = content.split("---")
    voice = "en-US-GuyNeural"

    for line in blocks[0].splitlines():
        if line.strip().upper().startswith("VOICE:"):
            voice = line.split(":", 1)[1].strip()

    scenes = []
    for block in blocks[1:]:
        lines = [
            line.strip()
            for line in block.splitlines()
            if line.strip()
        ]
        narration = " ".join(
            line for line in lines
            if not line.upper().startswith("IMAGE:")
        )
        if narration:
            scenes.append(narration)

    if not scenes:
        raise ValueError("No scenes found in script.")

    return voice, scenes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--out", default="output/final_video.mp4")
    args = parser.parse_args()

    voice, scenes = parse_script(args.script)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)

    image_dir = Path("assets/scenes")

    with tempfile.TemporaryDirectory() as folder:
        temp = Path(folder)
        clips = []

        for index, narration in enumerate(scenes, 1):
            image = image_dir / f"scene_{index:03}.png"
            if not image.exists():
                raise FileNotFoundError(
                    f"Missing scene image: {image}"
                )

            audio = temp / f"audio_{index}.mp3"
            clip = temp / f"clip_{index}.mp4"

            asyncio.run(make_voice(narration, voice, audio))

            run([
                "ffmpeg", "-y",
                "-loop", "1",
                "-framerate", "25",
                "-i", str(image),
                "-i", str(audio),
                "-vf",
                "scale=1920:1080:force_original_aspect_ratio=increase,"
                "crop=1920:1080,format=yuv420p",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-c:a", "aac",
                "-ar", "44100",
                "-shortest",
                "-movflags", "+faststart",
                str(clip)
            ])

            clips.append(clip)

        concat_file = temp / "clips.txt"
        concat_file.write_text(
            "\n".join(
                f"file '{clip.resolve()}'"
                for clip in clips
            ),
            encoding="utf-8"
        )

        run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output)
        ])

    print(f"Video created: {output}")


if __name__ == "__main__":
    main()

