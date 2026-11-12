#!/usr/bin/env python3
"""
make_lut.py — generate the "CRISP-POP" 33³ .cube LUT (Rec.709 in → Rec.709 out).

Target look (derived from evidence/measurements.json, image_stats_44_cover_frames):
  mean saturation ≈ 40 % (101/255), mid exposure (V≈118/255), luma std ≈ 60 → punchy but not crushed.
Operations (in order):
  1. gentle S-curve: blacks kept above 0.015, highlights roll off at 0.97 (no hard clipping)
  2. saturation × 1.18 around Rec.709 luma, with skin-hue protection (hue 15–45° gets × 1.06 only)
  3. tiny green-cyan separation: greens +3 % sat (foliage / water pops like the reference B-roll)
Apply at 60–100 % opacity after a neutral balance pass. Values are a RECOMMENDATION built to hit the
measured statistics, not an extraction of the channel's (unknown) grade.
Usage: python3 make_lut.py [out.cube] [--sat 1.18] [--contrast 0.18]
"""
import argparse, colorsys, math

def s_curve(x, k):
    """Mid-contrast S-curve, black floor 0.015, soft shoulder above 0.92 (monotonic)."""
    y = x + k * (x - 0.5) * (1 - abs(2 * x - 1))          # extra contrast in the mids only
    if y > 0.92:                                           # soft shoulder → max 0.985
        y = 0.92 + 0.065 * (1 - math.exp(-(y - 0.92) / 0.065))
    return 0.015 + y * (1 - 0.015)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="crisp_pop_709.cube")
    ap.add_argument("--sat", type=float, default=1.18)
    ap.add_argument("--contrast", type=float, default=0.18)
    ap.add_argument("--size", type=int, default=33)
    a = ap.parse_args()
    N = a.size
    lines = ['TITLE "CRISP-POP 709 (Shorts podcast-clip look)"', f"LUT_3D_SIZE {N}", "DOMAIN_MIN 0 0 0", "DOMAIN_MAX 1 1 1"]
    for b in range(N):
        for g in range(N):
            for r in range(N):
                R, G, B = r / (N - 1), g / (N - 1), b / (N - 1)
                R, G, B = (s_curve(c, a.contrast) for c in (R, G, B))
                Y = 0.2126 * R + 0.7152 * G + 0.0722 * B
                h, l, s = colorsys.rgb_to_hls(R, G, B)
                deg = h * 360
                sat = a.sat
                if 15 <= deg <= 45:
                    sat = 1 + (a.sat - 1) * 0.35        # skin protection
                elif 80 <= deg <= 190:
                    sat = a.sat * 1.03                  # foliage / water
                R, G, B = (Y + (c - Y) * sat for c in (R, G, B))
                lines.append("%.6f %.6f %.6f" % tuple(min(1, max(0, c)) for c in (R, G, B)))
    open(a.out, "w").write("\n".join(lines) + "\n")
    print("wrote", a.out)

if __name__ == "__main__":
    main()
