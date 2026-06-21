# refrigeration-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![CoolProp 7.0+](https://img.shields.io/badge/CoolProp-7.0+-green.svg)](http://www.coolprop.org/)

> **制冷垂直 AI Agent Skills 集** — 让 ChatGPT / Claude / 任何 AI Agent 变制冷专家

---

## 这是什么

老板我做了一套**制冷行业的 AI Skills**，让大模型（ChatGPT、Claude、国产模型）能**调用专业的制冷工具和数据**。

**现状**：
- ChatGPT 答制冷问题 → 很浅
- 让它选型、算工况、查物性 → 一塌糊涂
- 让它做故障诊断 → 一本正经胡说八道

**装上我们的 Skills 后**：
- 查制冷剂物性 → 准确
- 算制冷工况 → 专业
- 故障诊断 → 基于老板 20+ 年经验

---

## 第一个 Skill：coolprop-query

**已上线** ✅（v1.0.0）

**能做什么**：
- 查询 35+ 种制冷剂（R22/R134a/R410A/R717/R744...）的物性
- 通过饱和温度/压力查物性（制冷设计最常用）
- 单点查询（过热/过冷区的焓/熵）

**示例**：
```python
from skills.coolprop_query import query_saturation_by_temperature
result = query_saturation_by_temperature("R134a", 25, "C")
print(result)
# 输出：
# {
#   "saturation": {"P_sat_kpa": 665.38, "T_sat_c": 25},
#   "saturated_liquid": {"h_kj_kg": 234.55, ...},
#   "saturated_vapor": {"h_kj_kg": 412.33, ...},
#   ...
# }
```

**判断为完全开源（4 题打分法 0 分）**：
- ✅ 没有老板 20 年经验，CoolProp 也能算
- ✅ 不查 Technical Tools 软资料
- ✅ 不需要综合判断
- ✅ 不带老板个人 IP

---

## 为什么开源

**老板的逻辑**：
- 开源 = 免费 = 有人用 = 品牌曝光 = 引流到平台 = 变现

**对开发者的好处**：
- 免费用专业制冷工具
- 不用自己写代码
- 可以集成到自己的项目

**对企业的好处**：
- 免费试用
- 后续可付费定制

---

## Roadmap

| Skill | 状态 | 类别 |
|---|---|---|
| **S1 coolprop-query** | ✅ v1.0.0 | 完全开源 |
| **S2 coolprop-p-h** | 🚧 下一步 | 基础开源 + 增值 |
| **S3 psychrometric** | 📋 计划 | 基础开源 |
| **S4 pipe-sizing** | 📋 计划 | 完全开源 |
| **S8 refrigerant-selector** | 📋 计划 | 完全增值（老板经验）|
| **S9 compressor-selector** | 📋 计划 | 完全增值 |
| **S10 fault-diagnosis** | 📋 计划 | 完全增值 |

---

## 安装

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 使用
from skills.coolprop_query import query_saturation_by_temperature
result = query_saturation_by_temperature("R134a", 25, "C")
```

**依赖**：
- CoolProp 7.0+
- Python 3.8+

---

## 路线图与贡献

**开源协议**：MIT（最宽松，随便用，标作者即可）

**欢迎贡献**：
- 加新制冷剂
- 优化算法
- 加新功能

**联系**：
- 项目维护：强领制冷技术（上海）有限公司
- GitHub：https://github.com/John-Links/refrigeration-skills

---

## License

MIT © 2026 强领制冷技术（上海）有限公司

详见 [LICENSE](LICENSE) 文件。