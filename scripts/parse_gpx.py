"""
parse_gpx.py — GPXファイルをパースしてkm区間集計JSONを出力

使い方:
  python scripts/parse_gpx.py <route.gpx> <output/gpx_data.json>
"""

import sys
import json
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

NS = "http://www.topografix.com/GPX/1/1"
R_EARTH = 6371000  # meters


def haversine(lat1, lon1, lat2, lon2):
    """2点間の距離をメートルで返す"""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R_EARTH * math.asin(math.sqrt(a))


def parse_gpx(gpx_path):
    """GPXをパースして全ポイントのリストを返す"""
    tree = ET.parse(gpx_path)
    root = tree.getroot()

    points = []
    for trkpt in root.iter(f"{{{NS}}}trkpt"):
        lat = float(trkpt.get("lat"))
        lon = float(trkpt.get("lon"))
        ele_el = trkpt.find(f"{{{NS}}}ele")
        time_el = trkpt.find(f"{{{NS}}}time")
        # speed は extensions 直下（名前空間なし）
        speed = None
        ext = trkpt.find(f"{{{NS}}}extensions")
        if ext is not None:
            speed_el = ext.find("speed")
            if speed_el is None:
                speed_el = ext.find(f"{{{NS}}}speed")
            if speed_el is not None:
                speed = float(speed_el.text)

        points.append({
            "lat": lat,
            "lon": lon,
            "ele": float(ele_el.text) if ele_el is not None else 0.0,
            "time": time_el.text if time_el is not None else None,
            "speed": speed,  # m/s
        })

    return points


def compute_cumulative_distance(points):
    """各ポイントに累積距離(m)を付与して返す"""
    cum = 0.0
    for i, p in enumerate(points):
        if i == 0:
            p["dist_m"] = 0.0
        else:
            prev = points[i - 1]
            d = haversine(prev["lat"], prev["lon"], p["lat"], p["lon"])
            cum += d
            p["dist_m"] = cum
    return points


def assign_km_index(points):
    """各ポイントに累積km区間インデックス（1始まり）を付与"""
    for p in points:
        p["km_idx"] = int(p["dist_m"] / 1000) + 1
    return points


def compute_km_summaries(points):
    """km区間ごとにペース・標高変化を集計"""
    max_km = max(p["km_idx"] for p in points)
    summaries = []

    for km in range(1, max_km + 1):
        seg = [p for p in points if p["km_idx"] == km]
        if len(seg) < 2:
            continue

        # 距離
        dist_m = seg[-1]["dist_m"] - seg[0]["dist_m"]
        if dist_m < 10:
            continue

        # 時間
        t_start = seg[0]["time"]
        t_end = seg[-1]["time"]
        if t_start and t_end:
            try:
                dt_start = datetime.fromisoformat(t_start.replace("Z", "+00:00"))
                dt_end = datetime.fromisoformat(t_end.replace("Z", "+00:00"))
                elapsed_sec = (dt_end - dt_start).total_seconds()
                pace_min_per_km = (elapsed_sec / 60) / (dist_m / 1000) if dist_m > 0 else 0
            except Exception:
                pace_min_per_km = 0
        else:
            pace_min_per_km = 0

        # 標高
        ele_values = [p["ele"] for p in seg]
        ele_net = ele_values[-1] - ele_values[0]
        ele_gain = sum(max(0, ele_values[i] - ele_values[i - 1]) for i in range(1, len(ele_values)))
        ele_loss = sum(max(0, ele_values[i - 1] - ele_values[i]) for i in range(1, len(ele_values)))

        # km境界ラベル座標（区間の中間点）
        mid = seg[len(seg) // 2]

        summaries.append({
            "km": km,
            "pace": round(pace_min_per_km, 2),
            "eleNet": round(ele_net, 1),
            "eleGain": round(ele_gain, 1),
            "eleLoss": round(ele_loss, 1),
            "km_label": {"lat": mid["lat"], "lon": mid["lon"]},
        })

    return summaries


def build_route(points):
    """地図描画用ルート座標（間引き: 約20点/kmになるよう）"""
    total = len(points)
    # 全距離の0.05km（50m）ごとに1点
    step = max(1, total // 200)
    sampled = points[::step]
    # 最終点を必ず含む
    if sampled[-1] is not points[-1]:
        sampled.append(points[-1])
    return [[p["lat"], p["lon"], p["km_idx"]] for p in sampled]


def build_elevation_profile(points):
    """標高プロファイル: 約100点になるようサンプリング"""
    total = len(points)
    step = max(1, total // 100)
    sampled = points[::step]
    total_dist_m = points[-1]["dist_m"]
    return [
        [round(p["dist_m"] / 1000, 3), round(p["ele"], 1)]
        for p in sampled
    ]


def main():
    if len(sys.argv) < 3:
        print("使い方: python scripts/parse_gpx.py <route.gpx> <output/gpx_data.json>")
        sys.exit(1)

    gpx_path = sys.argv[1]
    out_path = sys.argv[2]

    print(f"GPXパース中: {gpx_path}")
    points = parse_gpx(gpx_path)
    print(f"  {len(points):,} ポイント読み込み完了")

    points = compute_cumulative_distance(points)
    points = assign_km_index(points)

    total_dist_km = points[-1]["dist_m"] / 1000

    # 総時間
    t_start = points[0]["time"]
    t_end = points[-1]["time"]
    total_time_sec = 0
    if t_start and t_end:
        try:
            dt_s = datetime.fromisoformat(t_start.replace("Z", "+00:00"))
            dt_e = datetime.fromisoformat(t_end.replace("Z", "+00:00"))
            total_time_sec = int((dt_e - dt_s).total_seconds())
        except Exception:
            pass

    # 最高速度
    speeds = [p["speed"] for p in points if p["speed"] is not None]
    max_speed_kmh = round(max(speeds) * 3.6, 1) if speeds else 0

    # 日付をGPXのtimeから取得
    date_str = ""
    if t_start:
        try:
            dt = datetime.fromisoformat(t_start.replace("Z", "+00:00"))
            # ローカル時刻に変換（JST = UTC+9）
            import os
            # GPXのtimeはUTC、ファイル名の日付を優先
            date_str = gpx_path.split("/")[-1][:16].replace("route_", "")[:10]
            if not date_str or not date_str[0].isdigit():
                date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            date_str = ""

    km_summaries = compute_km_summaries(points)
    route = build_route(points)
    elevation_profile = build_elevation_profile(points)

    result = {
        "date": date_str,
        "total_distance_km": round(total_dist_km, 3),
        "total_time_sec": total_time_sec,
        "max_speed_kmh": max_speed_kmh,
        "route": route,
        "elevation_profile": elevation_profile,
        "km_summaries": km_summaries,
    }

    import os
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  総距離: {total_dist_km:.3f} km")
    print(f"  総時間: {total_time_sec // 60}分{total_time_sec % 60}秒")
    print(f"  最高速度: {max_speed_kmh} km/h")
    print(f"  km区間数: {len(km_summaries)}")
    print(f"出力: {out_path}")


if __name__ == "__main__":
    main()
