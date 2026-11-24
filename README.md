# 中转行李清分台

中转主管用扫描原件、航段窗口和转运清单确认行李末态。航班号可以跨日复用，撤下也可能发生在另一航段。

## 启动

`docker compose up --build` 后打开 `http://localhost:18464`。本机可执行 `pip install -r requirements.txt` 和 `flask --app app.main run -p 18464`。运行测试用 `pytest -q`。归档位于 SQLite，默认 `var/transfer.sqlite3`，可用 `LUGGAGE_DB` 配置。要从空库演示可指定新文件。

## 演示

1. 默认打开跨日转运样例，核对清单 12 件、已装 3 件、待证 8 件、明确未装 1 件，另见错装 2 件。
2. 航段候选查 `000103`。扫件回放查 `000101` 的迟到撤下。错载与漏扫可以按行李牌筛选。
3. 点击归档复算，在批次留档复算本批，在联程证据下载原件、逐阶段行证和散列。
4. API 支持 `POST /api/archive`，提交 `{"sample":"dirty"}` 或 `{"files":{"scans.csv":"…","legs.csv":"…","manifest.csv":"…"}}`。前五阶段可用 `GET /api/stage/<key>`，键为 `scans`、`legs`、`replay`、`exceptions`、`ledger`。用 `?run=<id>` 查归档，用 `?sample=clean` 查净样例。

字段与边界见 [数据定义](docs/DATA-DICTIONARY.md)，入口和可执行反例见 [深度登记](docs/DEPTH.md)。

前五阶段也接受 `POST /api/stage/<key>`，提交同样的样例或原件，按依赖顺序只计算到选中阶段。
