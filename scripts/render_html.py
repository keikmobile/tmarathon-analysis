"""
render_html.py — race_data.json をHTMLテンプレートに埋め込んでHTML出力

使い方:
  python scripts/render_html.py <race_data.json> <output/race_analysis_YYYY-MM-DD.html>
"""

import sys
import json
import os


def main():
    if len(sys.argv) < 3:
        print("使い方: python scripts/render_html.py <race_data.json> <output/race_analysis_YYYY-MM-DD.html>")
        sys.exit(1)

    data_path = sys.argv[1]
    out_path = sys.argv[2]

    # テンプレートはスクリプトの2つ上のディレクトリの templates/ に置く
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "..", "templates", "race_template.html")

    print(f"テンプレート読み込み: {template_path}")
    with open(template_path, encoding="utf-8") as f:
        template = f.read()

    print(f"データ読み込み: {data_path}")
    with open(data_path, encoding="utf-8") as f:
        race_data = json.load(f)

    # サマリー表示値を30秒単位に丸めてぼかす（個人特定防止）
    rs = race_data["race_summary"]
    blurred_sec = round(rs["total_time_sec"] / 30) * 30
    m, s = blurred_sec // 60, blurred_sec % 60
    rs["total_time_str"] = f"{m}'{s:02d}\""
    if rs.get("total_distance_km", 0) > 0:
        avg = (blurred_sec / 60) / rs["total_distance_km"]
        pm, ps = int(avg), round((avg - int(avg)) * 60)
        rs["avg_pace"] = round(avg, 2)
        rs["avg_pace_str"] = f"{pm}'{ps:02d}\""

    # JSON文字列に変換（HTMLの</script>タグをエスケープ）
    json_str = json.dumps(race_data, ensure_ascii=False)
    json_str = json_str.replace("</script>", "<\\/script>")

    html = template.replace("__RACE_DATA__", json_str)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"出力: {out_path}")


if __name__ == "__main__":
    main()
