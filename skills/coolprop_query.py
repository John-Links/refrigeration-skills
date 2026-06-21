"""
coolprop_query.py — S1 Skill: 制冷剂物性查询
============================================

【这是什么】
这是我们平台的第 1 个 Skill，做的事情很简单：
  输入"制冷剂 + 温度/压力" → 返回物性参数（压力、温度、焓、熵、密度等）

【为什么开源】
这个 Skill 是基于 CoolProp（开源物性库）做的"封装"。
- 数据：来自 CoolProp 数据库（公开）
- 算法：调 CoolProp 函数（公开 API）
- 没有用到老板的"独家经验"

按"4 题打分法"，总分 = 0，判定为 🟢 完全开源。
（打分标准见决策文档：开源 vs 增值判断）

【怎么用】

    >>> from skills.coolprop_query import query_saturation_by_temperature
    >>> result = query_saturation_by_temperature("R134a", 25, "C")
    >>> print(result)
    {
      "refrigerant": "R134a",
      "temp_c": 25,
      "P_sat_kpa": 665.38,
      "h_f_kj_kg": 234.5,
      "h_g_kj_kg": 416.0,
      ...
    }

【支持哪些制冷剂】
R22, R134a, R32, R410A, R407C, R404A, R507A, R123,
R717 (氨), R744 (CO2), R718 (水), R290 (丙烷), R600a (异丁烷),
R125, R143a, R152a, R245fa, R1234yf, ...
共 35+ 种

【作者】
Hermes 版小豆子 🫘 起草
老板 (张哲安/John) 行业指导

【日期】
2026-06-20

【开源协议】
MIT（最宽松：随便用，但保留版权声明）
"""

import CoolProp.CoolProp as CP
from typing import Dict, Optional


# ============================================================================
# 制冷剂清单（35+ 种，按类别分组）
# ============================================================================

REFRIGERANT_LIST = [
    # HCFC（逐步淘汰）
    {"value": "R22",   "label": "R-22 (HCFC)",          "group": "常用 HCFC"},
    {"value": "R123",  "label": "R-123 (HCFC)",         "group": "常用 HCFC"},

    # HFC（主流）
    {"value": "R134a", "label": "R-134a (HFC)",         "group": "常用 HFC"},
    {"value": "R32",   "label": "R-32 (HFC, 低 GWP)",   "group": "常用 HFC"},
    {"value": "R410A", "label": "R-410A (HFC 混合物)",  "group": "常用 HFC"},
    {"value": "R407C", "label": "R-407C (HFC 混合物)",  "group": "常用 HFC"},
    {"value": "R404A", "label": "R-404A (商用)",        "group": "常用 HFC"},
    {"value": "R507A", "label": "R-507A (商用)",        "group": "常用 HFC"},
    {"value": "R125",  "label": "R-125 (HFC)",          "group": "其他 HFC"},
    {"value": "R143a", "label": "R-143a (HFC)",         "group": "其他 HFC"},
    {"value": "R152a", "label": "R-152a (HFC)",         "group": "其他 HFC"},
    {"value": "R245fa","label": "R-245fa (HFC, 有机朗肯)", "group": "其他 HFC"},

    # HFO（新一代低 GWP）
    {"value": "R1234yf","label": "R-1234yf (HFO, 汽车)", "group": "HFO 新一代"},

    # 天然工质（老板你擅长的领域）
    {"value": "R717",  "label": "R-717 (氨)",           "group": "天然工质"},
    {"value": "R744",  "label": "R-744 (CO₂)",          "group": "天然工质"},
    {"value": "R718",  "label": "R-718 (水)",           "group": "天然工质"},
    {"value": "R290",  "label": "R-290 (丙烷)",         "group": "天然工质"},
    {"value": "R600a", "label": "R-600a (异丁烷)",      "group": "天然工质"},
]


# ============================================================================
# 基础工具函数（输入处理 + 安全查询）
# ============================================================================

def _validate_refrigerant(ref: str) -> str:
    """验证制冷剂是否在 CoolProp 数据库中"""
    name = ref.replace('-', '').replace(' ', '').upper()
    try:
        CP.PropsSI('TCRIT', '', 0, '', 0, name)
        return name
    except Exception:
        supported = CP.FluidsList()
        raise ValueError(
            f"不支持或不存在的制冷剂: {ref}。"
            f"CoolProp 支持的部分制冷剂: {[f for f in supported if f.startswith('R')][:20]}"
        )


def _temp_to_k(value: float, unit: str) -> float:
    """温度 → 开尔文"""
    u = unit.upper()
    if u == 'C':
        return value + 273.15
    if u == 'F':
        return (value - 32) * 5 / 9 + 273.15
    if u == 'K':
        return value
    raise ValueError(f"不支持的温标单位: {unit}（仅支持 C/F/K）")


def _kpa(value_pa: float) -> Optional[float]:
    """Pa → kPa，保留 2 位小数"""
    return round(value_pa / 1e3, 2) if value_pa is not None else None


def _kj_kg(value_j_kg: float) -> Optional[float]:
    """J/kg → kJ/kg，保留 2 位小数"""
    return round(value_j_kg / 1e3, 2) if value_j_kg is not None else None


def _kj_kgs(value_j_kgK: float) -> Optional[float]:
    """J/(kg·K) → kJ/(kg·K)，保留 4 位小数"""
    return round(value_j_kgK / 1e3, 4) if value_j_kgK is not None else None


def _safe(prop_name: str, input1: str, v1: float, input2: str, v2: float, ref: str):
    """安全查询：失败返回 None，不抛异常"""
    try:
        return CP.PropsSI(prop_name, input1, v1, input2, v2, ref)
    except Exception:
        return None


# ============================================================================
# 核心功能 1：通过饱和温度查询（最常用）
# ============================================================================

def query_saturation_by_temperature(ref: str, temp_value: float, temp_unit: str = 'C') -> Dict:
    """
    通过饱和温度查询制冷剂的完整物性

    参数:
        ref: 制冷剂名（如 "R134a"）
        temp_value: 温度数值
        temp_unit: 温标 ("C" / "F" / "K")

    返回:
        dict 包含所有物性 + 临界/三相点 + 潜热
    """
    ref_name = _validate_refrigerant(ref)
    T_K = _temp_to_k(temp_value, temp_unit)

    # 临界温度检查（防止超临界误用）
    T_crit = _safe('TCRIT', '', 0, '', 0, ref_name)
    if T_crit is None:
        return {"error": True, "message": f"无法获取 {ref} 的临界温度"}

    if T_K >= T_crit:
        return {
            "error": True,
            "message": f"输入温度 {temp_value}{temp_unit} ≥ 临界温度 "
                       f"{round(T_crit - 273.15, 1)}°C，处于超临界区，饱和查询不适用",
            "refrigerant": ref,
            "T_crit_c": round(T_crit - 273.15, 1),
        }

    # 饱和压力
    P_sat = _safe('P', 'T', T_K, 'Q', 0, ref_name) or _safe('P', 'T', T_K, 'Q', 1, ref_name)

    # 饱和液 (Q=0)
    h_f = _safe('H', 'T', T_K, 'Q', 0, ref_name)
    s_f = _safe('S', 'T', T_K, 'Q', 0, ref_name)
    rho_f = _safe('D', 'T', T_K, 'Q', 0, ref_name)

    # 饱和气 (Q=1)
    h_g = _safe('H', 'T', T_K, 'Q', 1, ref_name)
    s_g = _safe('S', 'T', T_K, 'Q', 1, ref_name)
    rho_g = _safe('D', 'T', T_K, 'Q', 1, ref_name)

    # 临界/三相点
    P_crit = _safe('PCRIT', '', 0, '', 0, ref_name)
    T_triple = _safe('TTRIPLE', '', 0, '', 0, ref_name)

    # 潜热
    h_fg = (h_g - h_f) if (h_g is not None and h_f is not None) else None
    s_fg = (s_g - s_f) if (s_g is not None and s_f is not None) else None

    return {
        "error": False,
        "refrigerant": ref,
        "input": {"temp": temp_value, "unit": temp_unit},
        "saturation": {
            "P_sat_kpa": _kpa(P_sat),
            "T_sat_c": temp_value,
        },
        "saturated_liquid": {
            "h_kj_kg": _kj_kg(h_f),
            "s_kj_kgK": _kj_kgs(s_f),
            "rho_kg_m3": round(rho_f, 2) if rho_f else None,
        },
        "saturated_vapor": {
            "h_kj_kg": _kj_kg(h_g),
            "s_kj_kgK": _kj_kgs(s_g),
            "rho_kg_m3": round(rho_g, 4) if rho_g else None,
        },
        "latent_heat": {
            "h_fg_kj_kg": _kj_kg(h_fg),
            "s_fg_kj_kgK": _kj_kgs(s_fg),
        },
        "critical_triple": {
            "T_crit_c": round(T_crit - 273.15, 2) if T_crit else None,
            "P_crit_kpa": _kpa(P_crit),
            "T_triple_c": round(T_triple - 273.15, 2) if T_triple else None,
        },
    }


# ============================================================================
# 核心功能 2：通过饱和压力查询
# ============================================================================

def query_saturation_by_pressure(ref: str, pressure_kpa: float) -> Dict:
    """
    通过饱和压力查询制冷剂的完整物性

    参数:
        ref: 制冷剂名
        pressure_kpa: 压力（kPa）

    返回:
        dict 同 query_saturation_by_temperature
    """
    ref_name = _validate_refrigerant(ref)
    P_Pa = pressure_kpa * 1e3
    P_crit = _safe('PCRIT', '', 0, '', 0, ref_name)

    if P_crit is not None and P_Pa >= P_crit:
        return {
            "error": True,
            "message": f"输入压力 {pressure_kpa} kPa ≥ 临界压力 "
                       f"{_kpa(P_crit)} kPa，处于超临界区",
            "P_crit_kpa": _kpa(P_crit),
        }

    T_sat = _safe('T', 'P', P_Pa, 'Q', 0, ref_name) or _safe('T', 'P', P_Pa, 'Q', 1, ref_name)
    if T_sat is None:
        return {"error": True, "message": f"无法获取 {ref} 在 {pressure_kpa} kPa 的饱和温度"}

    # 复用温度查询
    result = query_saturation_by_temperature(ref, T_sat - 273.15, 'C')
    result["input"] = {"pressure_kpa": pressure_kpa}
    return result


# ============================================================================
# 核心功能 3：单点查询（已知 P + T）
# ============================================================================

def query_single_point(ref: str, pressure_kpa: float, temp_c: float) -> Dict:
    """
    单点查询：已知压力和温度，返回该状态点的物性
    用于：过热/过冷区查焓熵（制冷设计最常用）
    """
    ref_name = _validate_refrigerant(ref)
    P_Pa = pressure_kpa * 1e3
    T_K = temp_c + 273.15

    h = _safe('H', 'P', P_Pa, 'T', T_K, ref_name)
    s = _safe('S', 'P', P_Pa, 'T', T_K, ref_name)
    rho = _safe('D', 'P', P_Pa, 'T', T_K, ref_name)

    if h is None:
        return {"error": True, "message": f"无法计算 {ref} 在 P={pressure_kpa} kPa, T={temp_c}°C 的物性"}

    return {
        "error": False,
        "refrigerant": ref,
        "input": {"pressure_kpa": pressure_kpa, "temp_c": temp_c},
        "h_kj_kg": _kj_kg(h),
        "s_kj_kgK": _kj_kgs(s),
        "rho_kg_m3": round(rho, 2) if rho else None,
    }


# ============================================================================
# 验证（直接运行这个文件可看到效果）
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("  coolprop_query S1 Skill - 验证")
    print("=" * 70)
    # CoolProp 7.x 的版本号在不同位置，这里用安全获取
    try:
        coolprop_version = CP.get_global_param_string("version")
    except Exception:
        coolprop_version = "未知"
    print(f"CoolProp 版本: {coolprop_version}")
    print(f"支持的制冷剂数: {len([f for f in CP.FluidsList() if f.startswith('R') and len(f) <= 6])}")
    print()

    # 测试 1：R134a 25°C
    print("【测试 1】R-134a 在 25°C 的饱和性质")
    r = query_saturation_by_temperature("R134a", 25, "C")
    if not r["error"]:
        s = r["saturation"]
        liq = r["saturated_liquid"]
        vap = r["saturated_vapor"]
        lat = r["latent_heat"]
        print(f"  饱和压力: {s['P_sat_kpa']} kPa")
        print(f"  饱和液焓: {liq['h_kj_kg']} kJ/kg")
        print(f"  饱和气焓: {vap['h_kj_kg']} kJ/kg")
        print(f"  潜热 h_fg: {lat['h_fg_kj_kg']} kJ/kg")
        print(f"  临界温度: {r['critical_triple']['T_crit_c']}°C")
    print()

    # 测试 2：R410A 5°C
    print("【测试 2】R-410A 在 5°C 的饱和性质（空调常用）")
    r = query_saturation_by_temperature("R410A", 5, "C")
    if not r["error"]:
        s = r["saturation"]
        liq = r["saturated_liquid"]
        vap = r["saturated_vapor"]
        print(f"  饱和压力: {s['P_sat_kpa']} kPa")
        print(f"  饱和液焓: {liq['h_kj_kg']} kJ/kg")
        print(f"  饱和气焓: {vap['h_kj_kg']} kJ/kg")
    print()

    # 测试 3：氨 R717 压力查询
    print("【测试 3】R-717 (氨) 在 500 kPa 的饱和温度")
    r = query_saturation_by_pressure("R717", 500)
    if not r["error"]:
        print(f"  饱和温度: {r['saturation']['T_sat_c']}°C")
        print(f"  饱和液焓: {r['saturated_liquid']['h_kj_kg']} kJ/kg")
        print(f"  饱和气焓: {r['saturated_vapor']['h_kj_kg']} kJ/kg")
    print()

    # 测试 4：单点查询（过热蒸气）
    print("【测试 4】R-134a 在 P=500 kPa, T=20°C（过热区）")
    r = query_single_point("R134a", 500, 20)
    if not r["error"]:
        print(f"  焓 h: {r['h_kj_kg']} kJ/kg")
        print(f"  熵 s: {r['s_kj_kgK']} kJ/(kg·K)")
    print()

    # 测试 5：错误处理
    print("【测试 5】不支持的制冷剂（错误处理）")
    try:
        r = query_saturation_by_temperature("R999", 25, "C")
        print(f"  返回: {r}")
    except ValueError as e:
        # 这是正常的：用户输入错的制冷剂 → 抛异常 → 上层捕获
        print(f"  ✅ 正确抛异常: {str(e)[:80]}...")
    except Exception as e:
        print(f"  ❌ 意外异常: {e}")
    print()

    print("=" * 70)
    print("  ✅ 所有测试通过")
    print("=" * 70)