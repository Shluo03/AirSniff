from __future__ import annotations

import argparse
import csv
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from pygltflib import GLTF2, Material
try:
    # Most pygltflib releases use PbrMetallicRoughness (lowercase b)
    from pygltflib import PbrMetallicRoughness as PBRMetallicRoughness
except Exception:  # pragma: no cover
    # Fallback for older/alternate naming (rare)
    from pygltflib import PBRMetallicRoughness  # type: ignore


# ----------------------------
# Utility: color maps
# ----------------------------

def _interpolate_color(c0: Sequence[float], c1: Sequence[float], t: float) -> Tuple[float, float, float]:
    t = max(0.0, min(1.0, t))
    return (
        c0[0] + (c1[0] - c0[0]) * t,
        c0[1] + (c1[1] - c0[1]) * t,
        c0[2] + (c1[2] - c0[2]) * t,
    )


def _multi_stop_colormap(stops: Sequence[Tuple[float, Sequence[float]]], v: float) -> Tuple[float, float, float]:
    """Piecewise-linear interpolation through color stops.

    stops: list of (position in [0,1], (r,g,b)) sorted by position
    v: value in [0,1]
    """
    if not stops:
        return (1.0, 1.0, 1.0)
    v = max(0.0, min(1.0, v))
    for i in range(len(stops) - 1):
        x0, c0 = stops[i]
        x1, c1 = stops[i + 1]
        if v <= x0:
            return tuple(c0)  # type: ignore[return-value]
        if v <= x1:
            t = 0.0 if x1 == x0 else (v - x0) / (x1 - x0)
            return _interpolate_color(c0, c1, t)
    return tuple(stops[-1][1])  # type: ignore[return-value]


def colormap_rgb(v: float, name: str = "turbo") -> Tuple[float, float, float]:
    """Return an (r,g,b) in [0,1] for v in [0,1]. Lightweight approximations.

    Supported: 'turbo', 'viridis', 'blue-red'
    """
    v = max(0.0, min(1.0, v))
    if name == "viridis":
        # Approximate viridis via 6 stops
        stops = [
            (0.0, (0.267, 0.004, 0.329)),
            (0.25, (0.283, 0.141, 0.458)),
            (0.5, (0.254, 0.265, 0.530)),
            (0.75, (0.207, 0.372, 0.553)),
            (0.9, (0.153, 0.497, 0.558)),
            (1.0, (0.993, 0.906, 0.144)),
        ]
        return _multi_stop_colormap(stops, v)
    elif name == "blue-red":
        # Simple blue -> cyan -> yellow -> red
        stops = [
            (0.0, (0.0, 0.0, 1.0)),
            (0.33, (0.0, 1.0, 1.0)),
            (0.66, (1.0, 1.0, 0.0)),
            (1.0, (1.0, 0.0, 0.0)),
        ]
        return _multi_stop_colormap(stops, v)
    else:
        # Default: approximate Turbo via a few representative stops
        # Colors sampled from Google's Turbo colormap
        stops = [
            (0.0, (0.18995, 0.07176, 0.23217)),
            (0.13, (0.20803, 0.165, 0.47212)),
            (0.25, (0.23155, 0.31833, 0.70766)),
            (0.38, (0.26658, 0.472, 0.87137)),
            (0.5, (0.30156, 0.615, 0.90494)),
            (0.63, (0.343, 0.734, 0.78637)),
            (0.75, (0.468, 0.822, 0.498)),
            (0.88, (0.741, 0.873, 0.150)),
            (1.0, (0.987, 0.991, 0.749)),
        ]
        return _multi_stop_colormap(stops, v)


# ----------------------------
# Data classes
# ----------------------------


@dataclass
class WifiSeries:
    rssi: np.ndarray  # shape (K,)


def read_wifi_csv(csv_path: str | Path, ssid_filter: str | None = None) -> WifiSeries:
    rssi_values: List[float] = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        # Expect a column named 'rssi'
        fieldnames = reader.fieldnames or []
        if "rssi" not in fieldnames:
            raise ValueError("CSV must contain a 'rssi' column")
        has_ssid = "ssid" in fieldnames
        if ssid_filter is not None and not has_ssid:
            raise ValueError("SSID filter provided but CSV has no 'ssid' column")

        ssid_expected = ssid_filter if ssid_filter is not None else None
        for row in reader:
            if ssid_expected is not None:
                rv = row.get("ssid", "")
                if not rv or rv != ssid_expected:
                    continue
            try:
                val = float(row["rssi"])  # dBm (negative values typical)
            except Exception:
                continue
            if math.isnan(val):
                continue
            rssi_values.append(val)
    if not rssi_values:
        if ssid_filter is not None:
            raise ValueError(f"No valid RSSI values found in CSV for SSID {ssid_filter}")
        raise ValueError("No valid RSSI values found in CSV")
    return WifiSeries(rssi=np.asarray(rssi_values, dtype=np.float32))


def moving_average(x: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return x
    window = int(window)
    window = max(1, window)
    if window == 1 or len(x) == 0:
        return x
    kernel = np.ones(window, dtype=np.float32) / float(window)
    # pad edges to preserve length
    pad_left = window // 2
    pad_right = window - 1 - pad_left
    xpad = np.pad(x, (pad_left, pad_right), mode="edge")
    y = np.convolve(xpad, kernel, mode="valid")
    return y.astype(np.float32)


def normalize_rssi(x: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    if vmax <= vmin:
        raise ValueError("rssi-max must be greater than rssi-min")
    y = (x - vmin) / (vmax - vmin)
    return np.clip(y, 0.0, 1.0)


def proportional_index_map(n_targets: int, n_sources: int) -> List[int]:
    """Return indices j (0..K-1) for each i in 0..N-1 using proportional mapping.

    j = round(i * (K-1) / max(1, N-1))
    """
    if n_sources <= 0:
        raise ValueError("n_sources must be > 0")
    if n_targets <= 0:
        return []
    if n_targets == 1:
        return [0]
    denom = max(1, n_targets - 1)
    K_1 = max(0, n_sources - 1)
    result: List[int] = []
    for i in range(n_targets):
        j = int(round(float(i) * float(K_1) / float(denom)))
        j = max(0, min(n_sources - 1, j))
        result.append(j)
    return result


def find_geometry_nodes(gltf: GLTF2, pattern: str) -> List[Tuple[int, int]]:
    """Find nodes whose names match 'geometry_<num>'.

    Returns list of tuples: (node_index, geometry_number) sorted by geometry_number.
    Skips geometry_0 by design (world scene per problem statement).
    """
    if gltf.nodes is None:
        return []
    regex = re.compile(pattern)
    matches: List[Tuple[int, int]] = []
    for idx, node in enumerate(gltf.nodes):
        name = getattr(node, "name", None)
        if not name:
            continue
        m = regex.match(name)
        if not m:
            continue
        try:
            num = int(m.group(1))
        except Exception:
            continue
        if num == 0:
            continue
        matches.append((idx, num))
    matches.sort(key=lambda x: x[1])
    return matches


def ensure_materials_list(gltf: GLTF2) -> None:
    if gltf.materials is None:
        gltf.materials = []


def add_material(gltf: GLTF2, name: str, rgb: Tuple[float, float, float]) -> int:
    ensure_materials_list(gltf)
    mat = Material(
        name=name,
        pbrMetallicRoughness=PBRMetallicRoughness(
            baseColorFactor=[float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0],
            metallicFactor=0.0,
            roughnessFactor=1.0,
        ),
        doubleSided=True,
    )
    gltf.materials.append(mat)
    return len(gltf.materials) - 1


def assign_material_to_node_mesh(gltf: GLTF2, node_index: int, material_index: int) -> None:
    node = gltf.nodes[node_index]
    mesh_index = getattr(node, "mesh", None)
    if mesh_index is None:
        return
    if gltf.meshes is None or mesh_index >= len(gltf.meshes):
        return
    mesh = gltf.meshes[mesh_index]
    if mesh.primitives is None:
        return
    for prim in mesh.primitives:
        prim.material = material_index


def main() -> None:
    ap = argparse.ArgumentParser(description="Colorize DA3 GLB camera nodes by WiFi RSSI")
    ap.add_argument("--glb", required=True, help="Path to input .glb file")
    ap.add_argument("--csv", required=True, help="Path to WiFi CSV with an 'rssi' column")
    ap.add_argument("--output", default=None, help="Path to output .glb (default: <input>_wifi.glb)")
    ap.add_argument(
        "--node-regex",
        default=r"^geometry_(\d+)$",
        help="Regex to match geometry nodes with a capturing group for the index",
    )
    ap.add_argument("--rssi-min", type=float, default=-90.0, help="RSSI min (dBm) -> color 0")
    ap.add_argument("--rssi-max", type=float, default=-30.0, help="RSSI max (dBm) -> color 1")
    ap.add_argument(
        "--colormap",
        choices=["turbo", "viridis", "blue-red"],
        default="turbo",
        help="Colormap to map normalized RSSI to RGB",
    )
    ap.add_argument("--smooth", type=int, default=0, help="Moving average window over RSSI (0=off)")
    ap.add_argument("--report", default=None, help="Optional path to write mapping_report.csv")
    ap.add_argument("--ssid", default=None, help="Filter CSV rows to a specific SSID (network name)")
    args = ap.parse_args()

    glb_path = Path(args.glb)
    if args.output is None:
        out_path = glb_path.with_name(glb_path.stem + "_wifi.glb")
    else:
        out_path = Path(args.output)

    report_path = (
        Path(args.report)
        if args.report is not None
        else glb_path.with_name(glb_path.stem + "_mapping_report.csv")
    )

    # Read WiFi
    wifi = read_wifi_csv(args.csv, ssid_filter=args.ssid)
    rssi = wifi.rssi
    if args.smooth and args.smooth > 1:
        rssi = moving_average(rssi, args.smooth)

    # Normalize RSSI
    norm = normalize_rssi(rssi, args.rssi_min, args.rssi_max)

    # Load GLB
    gltf = GLTF2().load(str(glb_path))
    matches = find_geometry_nodes(gltf, args.node_regex)

    if not matches:
        raise SystemExit("No geometry_* nodes found in GLB using pattern: %s" % args.node_regex)

    N = len(matches)
    K = len(norm)
    index_map = proportional_index_map(N, K)

    # Summary
    if args.ssid:
        print(f"Filtering by SSID: {args.ssid}")
    print(f"Found {N} geometry nodes; {K} WiFi samples")
    print(f"RSSI range: min={float(np.min(rssi)):.1f} dBm, max={float(np.max(rssi)):.1f} dBm")
    print(f"Normalization: [{args.rssi_min}, {args.rssi_max}] dBm -> [0,1]")
    print(f"Colormap: {args.colormap}; Smooth window: {args.smooth}")

    # Assign colors per node
    ensure_materials_list(gltf)

    # Write mapping report
    try:
        rep_f = open(report_path, "w", newline="")
        rep_writer = csv.writer(rep_f)
        rep_writer.writerow(["geometry_index", "node_index", "wifi_index", "rssi", "normalized", "r", "g", "b"])
    except Exception:
        rep_f = None
        rep_writer = None

    for i, (node_idx, geom_num) in enumerate(matches):
        j = index_map[i]
        v = float(norm[j])
        r, g, b = colormap_rgb(v, name=args.colormap)
        mat_name = f"wifi_color_geometry_{geom_num}"
        mat_idx = add_material(gltf, mat_name, (r, g, b))
        assign_material_to_node_mesh(gltf, node_idx, mat_idx)

        if rep_writer is not None:
            rep_writer.writerow([geom_num, node_idx, j, float(rssi[j]), v, r, g, b])

    if rep_f is not None:
        rep_f.close()
        print(f"Wrote mapping report: {report_path}")

    # Save GLB (binary)
    gltf.save_binary(str(out_path))
    print(f"Wrote colored GLB: {out_path}")


if __name__ == "__main__":
    main()
