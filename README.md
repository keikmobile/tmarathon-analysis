# marathon-analysis

GPXファイルとApple Health CSVからレース分析HTMLを自動生成するツール。

## 必要なもの
- Python 3.8以上（標準ライブラリのみ）
- Apple HealthのGPXエクスポート（workout-routesフォルダ内）
- running_workouts.csv（apple_health_running.pyで生成）

## 使い方

### 1. データを置く
data/input/ に以下を配置する。
- GPXファイル
- running_workouts.csv
- splits_YYYY-MM-DD.json（任意）

### 2. 実行
bash run.sh 2026-04-05

### 3. 出力確認
data/output/race_analysis_2026-04-05.html をブラウザで開く。

## スプリットJSONの形式
手入力が必要。Apple Watchのスプリット画面から転記する。

{
  "date": "2026-04-05",
  "splits": [
    {"km": 1, "pace": "6:22", "hr": 155, "power": 190},
    {"km": 2, "pace": "6:14", "hr": 163, "power": 239}
  ]
}

## 出力されるHTML
- コースマップ（GPX座標をCanvas描画）
- 標高プロファイル（全コース）
- km別ペースと標高変化
- km別心拍数と標高変化
- km区間クリックで詳細表示

## 背景
2026年4月5日の気仙沼つばきマラソン10kmのデータ分析から生まれたツール。
「km8だけなぜ遅かったのか」という問いがGPXを渡した瞬間に
+47mの純登りとして現れた体験が出発点。
