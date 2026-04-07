"""
merge_csv.py — gpx_data.json + running_workouts.csv + splits.json → race_data.json

使い方:
  python scripts/merge_csv.py <gpx_data.json> <running_workouts.csv> <splits.json|none> <output/race_data.json>
"""

import sys
import json
import csv
import os
import math


def load_gpx_data(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_csv_record(csv_path, date_str):
    """running_workouts.csv から指定日のレコードを返す（距離最大を選択）"""
    best = None
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            start = row.get("startDate", "")
            if start[:10] != date_str:
                continue
            # Running のみ対象
            if "Running" not in row.get("type", ""):
                continue
            try:
                dist = float(row.get("distance_km") or 0)
            except ValueError:
                dist = 0
            if best is None or dist > float(best.get("distance_km") or 0):
                best = row
    return best


def load_splits(splits_path):
    """スプリットJSONを読み込む。ファイルがなければ空リストを返す"""
    if not splits_path or splits_path.lower() == "none" or not os.path.exists(splits_path):
        return []
    with open(splits_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("splits", [])


def format_pace(pace_float):
    """6.37 → '6\'22\"' 形式の文字列"""
    if not pace_float:
        return "N/A"
    m = int(pace_float)
    s = round((pace_float - m) * 60)
    return f"{m}'{s:02d}\""


def format_time(total_sec):
    """秒 → 'MM\'SS\"' 形式"""
    m = total_sec // 60
    s = total_sec % 60
    return f"{m}'{s:02d}\""


def main():
    if len(sys.argv) < 5:
        print("使い方: python scripts/merge_csv.py <gpx_data.json> <running_workouts.csv> <splits.json|none> <output/race_data.json>")
        sys.exit(1)

    gpx_path = sys.argv[1]
    csv_path = sys.argv[2]
    splits_path = sys.argv[3]
    out_path = sys.argv[4]

    print(f"GPXデータ読み込み: {gpx_path}")
    gpx = load_gpx_data(gpx_path)
    date_str = gpx["date"]

    print(f"CSV検索 ({date_str}): {csv_path}")
    csv_row = load_csv_record(csv_path, date_str)
    if csv_row:
        print(f"  マッチ: {csv_row.get('startDate')} / {csv_row.get('distance_km')} km")
    else:
        print(f"  マッチなし（CSVデータはスキップ）")

    print(f"スプリット読み込み: {splits_path}")
    splits = load_splits(splits_path)
    splits_by_km = {s["km"]: s for s in splits}
    print(f"  {len(splits)} 区間のスプリットデータ")

    # km_summariesにスプリットデータをマージ
    for km_s in gpx["km_summaries"]:
        km = km_s["km"]
        sp = splits_by_km.get(km, {})
        km_s["hr"] = sp.get("hr")
        km_s["power"] = sp.get("power")
        km_s["comment"] = sp.get("comment", "")
        km_s["pace_str"] = format_pace(km_s.get("pace"))

    # CSVからレースサマリーを構築
    race_summary = {
        "date": date_str,
        "total_distance_km": gpx["total_distance_km"],
        "total_time_sec": gpx["total_time_sec"],
        "total_time_str": format_time(gpx["total_time_sec"]),
        "max_speed_kmh": gpx["max_speed_kmh"],
    }

    if gpx["total_distance_km"] > 0 and gpx["total_time_sec"] > 0:
        avg_pace = (gpx["total_time_sec"] / 60) / gpx["total_distance_km"]
        race_summary["avg_pace"] = round(avg_pace, 2)
        race_summary["avg_pace_str"] = format_pace(avg_pace)
    else:
        race_summary["avg_pace"] = None
        race_summary["avg_pace_str"] = "N/A"

    if csv_row:
        try:
            race_summary["hr_avg"] = round(float(csv_row.get("hr_avg") or 0), 1) or None
        except ValueError:
            race_summary["hr_avg"] = None
        try:
            race_summary["hr_min"] = round(float(csv_row.get("hr_min") or 0)) or None
        except ValueError:
            race_summary["hr_min"] = None
        try:
            race_summary["hr_max"] = round(float(csv_row.get("hr_max") or 0)) or None
        except ValueError:
            race_summary["hr_max"] = None
        try:
            race_summary["calories"] = round(float(csv_row.get("calories") or 0)) or None
        except ValueError:
            race_summary["calories"] = None
        race_summary["source"] = csv_row.get("source", "")
    else:
        race_summary["hr_avg"] = None
        race_summary["hr_min"] = None
        race_summary["hr_max"] = None
        race_summary["calories"] = None
        race_summary["source"] = ""

    # 獲得標高の合計
    total_gain = sum(s.get("eleGain", 0) for s in gpx["km_summaries"])
    total_loss = sum(s.get("eleLoss", 0) for s in gpx["km_summaries"])
    race_summary["total_ele_gain"] = round(total_gain)
    race_summary["total_ele_loss"] = round(total_loss)

    result = {
        "race_summary": race_summary,
        "route": gpx["route"],
        "elevation_profile": gpx["elevation_profile"],
        "km_summaries": gpx["km_summaries"],
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"出力: {out_path}")
    print(f"  距離: {race_summary['total_distance_km']:.3f} km")
    print(f"  タイム: {race_summary['total_time_str']}")
    print(f"  平均ペース: {race_summary['avg_pace_str']}/km")
    if race_summary.get("hr_avg"):
        print(f"  平均心拍: {race_summary['hr_avg']} bpm")
    print(f"  獲得標高: +{race_summary['total_ele_gain']}m / -{race_summary['total_ele_loss']}m")


if __name__ == "__main__":
    main()
