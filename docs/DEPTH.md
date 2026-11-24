# 深度登记 口岸冷藏余量盘

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 出入库原件采信 | 查看收件、重报和隔离 | `/view/intake` `/api/observe/intake` | `app/modules/intake/service.py` | `tests/test_intake.py` |
| M2 货批与槽位版本 | 核对容量和门区生效窗 | `/view/registry` `/api/observe/registry` | `app/modules/registry/service.py` `app/modules/registry/versions.py` | `tests/test_registry.py` |
| M3 查验占位回放 | 逐批回看入出库、调位及冻结 | `/view/custody` `/api/observe/custody` | `app/modules/custody/service.py` `app/modules/custody/transitions.py` | `tests/test_custody.py` |
| M4 暴露分钟归属 | 按货批核查开门温度及缺证 | `/` `/api/observe/exposure` | `app/modules/exposure/service.py` `app/modules/exposure/doors.py` | `tests/test_exposure.py` |
| M5 件数和占位对账 | 核对时间与收盘库存守恒 | `/view/capacity` `/api/observe/capacity` | `app/modules/capacity/service.py` | `tests/test_capacity.py` |
| M6 批次留档复跑 | 归档原件并复算 | `/view/history` `POST /api/receipts` | `app/modules/history/service.py` `app/modules/history/storage.py` | `tests/test_history.py` |
| M7 冷库证据签发 | 校验摘要并下载原件及依据 | `/view/certificate` `/api/certificate/<key>/export` | `app/modules/certificate/service.py` | `tests/test_certificate.py` |

## 陷阱登记

| TRAP | 现象 | 朴素实现 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-02 | 脏日志 BOM | 首字段不匹配 | 首列去 BOM | `app/modules/intake/csv_rows.py` | `tests/test_intake.py::test_bom_column` |
| TRAP-04 | 调位日志重复表头 | 算成一次动作 | 单记表头 | `app/modules/intake/csv_rows.py` | `tests/test_intake.py::test_repeated_header` |
| TRAP-05 | BADC 多余尾列 | 错位采信 | 原值隔离 | `app/modules/intake/csv_rows.py` | `tests/test_intake.py::test_width_and_sentinel` |
| TRAP-07 | BAD 生效时刻 N/A | 错配到起始窗 | 未知直接隔离 | `app/modules/intake/contracts.py` | `tests/test_intake.py::test_width_and_sentinel` |
| TRAP-11 | E02 同时刻两种偏移 | 当两次冻结 | 统一 UTC 再比较 | `app/modules/intake/contracts.py` | `tests/test_intake.py::test_offset_equivalence` |
| TRAP-13 | A06 封条补到晚于撤销 | 当作无效单据 | 标迟到按生效时刻回放 | `app/modules/custody/service.py` | `tests/test_custody.py::test_late_seal_before_cancel` |
| TRAP-14 | K01 两个查验号 | 后写覆盖 | 全组隔离 | `app/modules/intake/service.py` | `tests/test_intake.py::test_conflicting_packet` |
| TRAP-19 | F03 在 X9 无槽位及门温证据 | 时间重复计到多个缺证类型 | 先按槽位定义，再判门温 | `app/modules/exposure/service.py` | `tests/test_exposure.py::test_priority_keeps_gaps_mutually_exclusive` |
| TRAP-23 | A2 改门恰逢 08:40 | 归到两个门区 | 左闭右开版本 | `app/modules/registry/versions.py` | `tests/test_registry.py::test_adjacent_versions` |

## 勾稽与范围

收盘 27 件 = 4 普通占用 + 4 查验冻结 + 19 空余。230 货批分钟 = 135 闭门 + 30 超限 + 43 温度合格 + 7 缺温 + 15 缺槽位。固定门区阈值，货批整批搬移，窗口最长七天。
