#!/usr/bin/env python3
"""Convert a PNG image to a .2dm map file.

Usage
-----
    python png_to_2dm.py INPUT.png OUTPUT.2dm
    python png_to_2dm.py INPUT.png OUTPUT.2dm --tile-size 16

Each pixel (or N×N block with --tile-size N) is mapped to the nearest
tile color defined in TILE_DEFS.  Door metadata cannot be encoded in a
PNG; all door entries in the output will be empty.
"""
import argparse
import sys

from core.codec import TwoDMapCodec
from core.config import TILE_DEFS
from core.png_importer import PngImporter


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PNG → .2dm map converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input",  help="Input PNG file")
    parser.add_argument("output", help="Output .2dm file")
    parser.add_argument(
        "--tile-size",
        type=int,
        default=0,
        metavar="N",
        help="Pixels per tile edge (default: auto-detect)",
    )
    args = parser.parse_args()

    try:
        payload = PngImporter.load(args.input, TILE_DEFS, args.tile_size)
    except Exception as exc:
        print(f"Fehler beim Lesen der PNG: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        TwoDMapCodec.save(
            args.output,
            payload["width"],
            payload["height"],
            payload["grid"],
            payload["tile_defs"],
            payload["doors"],
        )
    except Exception as exc:
        print(f"Fehler beim Schreiben der .2dm-Datei: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        f"OK: {payload['width']}×{payload['height']} Tiles"
        f" (Tile-Größe: {args.tile_size or 'auto'}) → {args.output}"
    )


if __name__ == "__main__":
    main()
