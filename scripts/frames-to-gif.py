"""Convert a directory of PNG frames into an optimized GIF."""
import sys
import glob
from PIL import Image

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 frames-to-gif.py <frames_dir> <output.gif>")
        sys.exit(1)

    frames_dir = sys.argv[1]
    output_path = sys.argv[2]

    paths = sorted(glob.glob(f"{frames_dir}/frame_*.png"))
    if not paths:
        print(f"No frames found in {frames_dir}")
        sys.exit(1)

    print(f"Loading {len(paths)} frames...")

    # Load and convert to palette mode for smaller GIF
    frames = []
    for p in paths:
        img = Image.open(p).convert("RGB")
        # Downscale from 2x retina to 1x for reasonable GIF size
        w, h = img.size
        img = img.resize((w // 2, h // 2), Image.LANCZOS)
        frames.append(img)

    print(f"Saving GIF to {output_path}...")
    # 100ms per frame = 10fps
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
        optimize=True,
    )

    import os
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done: {output_path} ({size_mb:.1f} MB)")

    # Cleanup frames
    import shutil
    shutil.rmtree(frames_dir)
    print(f"Cleaned up {frames_dir}")


if __name__ == "__main__":
    main()
