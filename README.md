# 口岸冷藏余量盘

冷藏监管库管理员核对调位、查验冻结、开门及温度记录。工作台按货批重建实际占位和暴露时间，独立列出缺少温度、门态或槽位的时段。

## 启动与核对

`docker compose up --build` 后访问 `http://localhost:18470`。本机安装 `requirements.txt` 后使用 `flask --app 'app.main:build()' run -p 18470`，测试用 `pytest -q`。归档用 SQLite，`ICE_STOCK_DB` 指定文件位置，默认 `var/receipts.sqlite3`。

- 默认展示港区临检样例。选择泳道上的 F03，查看 X9 缺证的 15 分钟及先后调位的原行。切换净样例可以对比闭门下的暴露分类。
- 查验占位核对 F01 迟补封条与撤销的顺序。余量对账查看普通占用、查验冻结、空余和待定位件数。
- 归档后可回到批次留档复算，并在冷库证据下载原件、规则版本、逐阶段结论和行证。

## 输入与接口

`POST /api/receipts` 传入 `{"sample":"dirty"}` 或 `{"sample":"clean"}`。自有原件需要 `moves`、`slots`、`doors`、`temperatures`、`lots`、`window` 六个文本字段，前五项为 CSV，最后一项为 JSON 文本。

`GET /api/observe/<view>` 支持 `intake`、`registry`、`custody`、`exposure`、`capacity`，参数 `sample` 选择样例，`receipt` 查询归档。`GET /api/receipts/<id>` 查看归档，`POST /api/receipts/<id>/refresh` 复算，`GET /api/certificate/<id>/export` 下载证据。

[数据定义](docs/DATA-DICTIONARY.md) · [深度登记](docs/DEPTH.md) · [序列复算](docs/SHIFT-EXAMPLE.md)

也可以向前五个业务入口发送 `POST /api/observe/<view>`，直接试算自有原件，不写入档案。
