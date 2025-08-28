#!/usr/bin/env python3
"""
image_to_color_text.py

Convert an image into colored text pixels for Roblox (RichText).
Each pixel becomes a chosen glyph (default '█') wrapped in <font color="#RRGGBB">...</font>.

Outputs a single text file (default: output_all.txt).

Requirements:
    pip install pillow
"""

import argparse
import os
import sys
from PIL import Image

def ensure_hex_color(s):
    s = s.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) not in (3, 6):
        raise ValueError("Background color must be hex like '#fff' or '#ffffff'")
    if len(s) == 3:
        s = "".join(2*c for c in s)
    return "#" + s.lower()

def composite_over_bg(img, bg_hex):
    """If image has alpha, composite over background color."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        bg_rgb = tuple(int(bg_hex[i:i+2], 16) for i in (1,3,5))
        bg = Image.new("RGBA", img.size, bg_rgb + (255,))
        return Image.alpha_composite(bg, img.convert("RGBA")).convert("RGB")
    return img.convert("RGB")

def image_to_color_text(
    image_path,
    scale_percent=25.0,
    aspect_ratio=0.5,
    glyph="█",
    rich_text=True,
    background="#ffffff",
    output_path="output_all.txt",
    verbose=True,
):
    if verbose:
        print(f"[+] Loading image: {image_path}")
    img = Image.open(image_path)

    # Handle background compositing for images with alpha
    if background is not None:
        bg_hex = ensure_hex_color(background)
        img = composite_over_bg(img, bg_hex)
    else:
        img = img.convert("RGB")

    orig_w, orig_h = img.width, img.height
    if scale_percent <= 0:
        raise ValueError("scale_percent must be > 0")
    scale = scale_percent / 100.0

    # compute scaled size
    new_w = max(1, int(orig_w * scale))
    new_h = max(1, int(orig_h * scale))

    if verbose:
        print(f"[+] Original: {orig_w}x{orig_h}. Resizing -> {new_w}x{new_h} (scale {scale_percent}%).")

    # Resize color image (we sample color from this)
    color_img = img.resize((new_w, new_h), resample=Image.LANCZOS)

    # Rendered text height after aspect correction (how many character rows)
    rendered_h = max(1, int(new_h * aspect_ratio))
    if verbose:
        print(f"[+] Aspect ratio correction: aspect={aspect_ratio}. Render rows = {rendered_h}")

    # Grayscale image used to optionally modulate glyph brightness; not needed for pure color, but kept in case
    gray_img = color_img.convert("L").resize((new_w, rendered_h), resample=Image.LANCZOS)

    lines = []
    for y in range(rendered_h):
        row_parts = []
        # map the text-row y back to the color_img y (inverse of aspect scaling)
        mapped_y = min(new_h - 1, max(0, int(round(y / aspect_ratio))))
        for x in range(new_w):
            # sample color
            r, g, b = color_img.getpixel((x, mapped_y))
            ch = glyph
            if rich_text:
                row_parts.append(f'<font color="#{r:02x}{g:02x}{b:02x}">{ch}</font>')
            else:
                row_parts.append(ch)
        lines.append("".join(row_parts))
    final_text = "\n".join(lines) + "\n"

    # save
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_text)

    # info
    total_chars = len(final_text)
    if verbose:
        print(f"[+] Saved -> {output_path}")
        print(f"[+] Output char dimensions: {new_w} x {rendered_h} (width x height in characters)")
        print(f"[+] Approx total characters: {total_chars}")
        # warn about Roblox label limits
        if total_chars > 32768:
            print("WARNING: Output exceeds a single Roblox TextLabel's safe limit (32k chars).",
                  "Consider using chunking or multiple TextLabels.")

    return output_path

def main():
    parser = argparse.ArgumentParser(description="Convert image to colored text pixels (Roblox RichText friendly).")
    parser.add_argument("input", help="Input image path.")
    parser.add_argument("--scale", "-s", type=float, default=25.0, help="Scale percent (e.g., 25 -> 25%%). Default=25")
    parser.add_argument("--aspect", "-a", type=float, default=0.5, help="Height multiplier for aspect correction. Default=0.5")
    parser.add_argument("--glyph", "-g", default="█", help="Glyph to use for each pixel. Default '█'")
    parser.add_argument("--no-rich", dest="rich", action="store_false", help="Disable RichText tags (plain glyphs).")
    parser.add_argument("--bg", default="#ffffff", help="Background hex color for alpha images (e.g. '#000000'). Use 'none' to keep alpha (not recommended). Default='#ffffff'")
    parser.add_argument("--out", "-o", default="output_all.txt", help="Output text file path.")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode.")
    args = parser.parse_args()

    bg = None if args.bg.lower() in ("none", "transparent") else args.bg
    try:
        image_to_color_text(
            args.input,
            scale_percent=args.scale,
            aspect_ratio=args.aspect,
            glyph=args.glyph,
            rich_text=args.rich,
            background=bg,
            output_path=args.out,
            verbose=(not args.quiet),
        )
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
