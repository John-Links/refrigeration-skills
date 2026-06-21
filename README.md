# refrigeration-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![CoolProp 7.0+](https://img.shields.io/badge/CoolProp-7.0+-green.svg)](http://www.coolprop.org/)

> **制冷垂直 AI Agent Skills 集** — 让 ChatGPT / Claude / 任何 AI Agent 变制冷专家

---

## 这是什么

一套**制冷行业的 AI Skills**，让大模型（ChatGPT、Claude、国产模型）能**调用专业的制冷工具和数据**。

**现状**：
- ChatGPT 答制冷问题 → 很浅
- 让它选型、算工况、查物性 → 一塌糊涂
- 让它做故障诊断 → 一本正经胡说八道

**装上我们的 Skills 后**：
- 查制冷剂物性 → 准确
- 算制冷工况 → 专业
- 算管道压降 → 靠谱
- 单位换算 → 不出错

---

## Skills 清单（v1.1.0）

| # | Skill | 类别 | 状态 | 描述 |
|---|---|---|---|---|
| **S1** | `coolprop_query` | 物性查询 | ✅ v1.0 | 制冷剂物性查询（饱和/单点） |
| **S2** | `coolprop_ph` | 图数据生成 | ✅ v1.1 | p-h 图完整数据点 |
| **S3** | `coolprop_sat_table` | 表生成 | ✅ v1.1 | 完整饱和性质表 |
| **S4** | `unit_converter` | 单位换算 | ✅ v1.1 | 制冷常用单位换算（13 类） |
| **S5** | `psychrometric` | 湿空气 | ✅ v1.1 | 焓湿图 6 参数互算 |
| **S6** | `pipe_pressure_drop` | 水力计算 | ✅ v1.1 | 管道沿程压降 |

**全部 6 个 Skills = 🟢 完全开源（4 题打分法 0 分）**

---

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 使用

```python
from skills import (
    query_saturation_by_temperature,
    generate_ph_curve,
    generate_saturation_table,
    convert,
    query_state,
    calc_pressure_drop,
)

# S1：制冷剂物性查询
result = query_saturation_by_temperature("R134a", 25, "C")
print(result["saturation"]["P_sat_kpa"])  # 665.38 kPa

# S2：p-h 图数据生成
ph = generate_ph_curve("R410A", pressure_range_kpa=(200, 4000))
print(f"饱和液点数: {len(ph['saturation_liquid'])}")

# S3：饱和性质表
table = generate_saturation_table("R717", temp_range_c=(-30, 100), step_c=10)

# S4：单位换算
print(convert("100", "°C", "°F"))    # 212.0
print(convert("1", "MPa", "psi"))    # 145.04

# S5：焓湿图
state = query_state(T_db_c=25, RH=0.5)
print(state["T_dp_c"])  # 13.9

# S6：管道压降
dp = calc_pressure_drop(pipe_dn_mm=50, length_m=100,
                        fluid="water", velocity_m_s=2.0)
print(dp["pressure_drop_kpa"])  # ~25.7
```

---

## 应用场景

| 用户 | 用什么 | 解决什么问题 |
|---|---|---|
| **维修师傅** | S1/S4/S5 | 现场查物性、换单位、查焓湿图 |
| **设计工程师** | S1/S2/S3/S6 | 选型、算工况、画 p-h 图、水力计算 |
| **学生** | 全部 | 学习、自学、做作业 |
| **AI Agent** | 全部 | 调用工具回答制冷问题 |

---

## Roadmap

| Skill | 类别 | 状态 |
|---|---|---|
| **S7** `coolprop_t-s` | T-s 图数据 | 📋 计划 |
| **S8** `refrigerant-selector` | 制冷剂选择（增值） | 📋 计划（要老板经验）|
| **S9** `compressor-selector` | 压缩机选型（增值） | 📋 计划（要老板经验）|
| **S10** `fault-diagnosis` | 故障诊断（增值） | 📋 计划（要老板经验）|

---

## 路线图与贡献

**开源协议**：MIT（最宽松，随便用，标作者即可）

**欢迎贡献**：
- 加新制冷剂
- 优化算法
- 加新功能
- 提 Issue / PR

**联系**：
- 项目维护：强领制冷技术（上海）有限公司
- GitHub：https://github.com/John-Links/refrigeration-skills

---

## License

MIT © 2026 强领制冷技术（上海）有限公司

详见 [LICENSE](LICENSE) 文件。