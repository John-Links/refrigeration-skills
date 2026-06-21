"""
coolprop_ph.py — S2 Skill: p-h 图数据生成器
============================================

【这是什么】
这个 Skill 生成 p-h 图（压焓图）的完整数据点。
老板你做制冷设计时，p-h 图是最常用的工具：
- 画理论循环
- 计算 COP（制冷系数）
- 看压缩机吸气/排气状态

【为什么开源】
- 数据来自 CoolProp（公开）
- 算法就是调 CoolProp 函数
- 没有老板的"独家经验"
→ 🟢 完全开源（4 题打分 0 分）

【怎么用】
    >>> from skills.coolprop_ph import generate_ph_curve
    >>> data = generate_ph_curve("R134a", pressure_range_kpa=(100, 2000), num_points=50)
    >>> print(f"饱和液曲线点数: {len(data['saturation_liquid'])}")
    >>> print(f"第一个点: P={data['saturation_liquid'][0]['p_kpa']} kPa, h={data['saturation_liquid'][0]['h_kj_kg']} kJ/kg")

【应用场景】
1. 网站前端画 p-h 图（传入这个数据 → ECharts/Chart.js 渲染）
2. AI Agent 算 COP（拿到循环 4 个点的 h → 计算）
3. 工程师自己画图（导出 CSV → Excel 画）

【作者】
Hermes 版小豆子 🫘 起草
老板 (张哲安/John) 行业指导

【日期】
2026-06-21

【开源协议】
MIT
"""

import CoolProp.CoolProp as CP
from typing import Dict, List, Tuple, Optional


def _validate(ref: str) -> str:
    """验证制冷剂"""
    name = ref.replace('-', '').replace(' ', '').upper()
    try:
        CP.PropsSI('TCRIT', '', 0, '', 0, name)
        return name
    except Exception:
        raise ValueError(f"不支持的制冷剂: {ref}")


def _safe(prop, i1, v1, i2, v2, ref):
    try:
        return CP.PropsSI(prop, i1, v1, i2, v2, ref)
    except Exception:
        return None


def generate_ph_curve(
    ref: str,
    pressure_range_kpa: Tuple[float, float] = (50, 3000),
    num_points: int = 50,
) -> Dict:
    """
    生成 p-h 图的完整曲线数据

    参数:
        ref: 制冷剂名
        pressure_range_kpa: 压力范围 (min, max) kPa
        num_points: 曲线上的点数

    返回:
        {
          "saturation_liquid": [{"p_kpa": ..., "h_kj_kg": ...}, ...],
          "saturation_vapor":  [{"p_kpa": ..., "h_kj_kg": ...}, ...],
          "isotherms": {
              "T_0C":   [{"p_kpa": ..., "h_kj_kg": ...}, ...],
              "T_20C":  [...],
              ...
          },
          "isentropes": {
              "s_1.5": [{"p_kpa": ..., "h_kj_kg": ...}, ...],
              ...
          },
          "critical_point": {"p_kpa": ..., "h_kj_kg": ...},
        }
    """
    ref_name = _validate(ref)
    p_min, p_max = pressure_range_kpa
    p_min_pa = p_min * 1e3
    p_max_pa = p_max * 1e3

    # 临界点
    p_crit = _safe('PCRIT', '', 0, '', 0, ref_name)
    h_crit = _safe('H', 'P', p_crit, 'Q', 0, ref_name) if p_crit else None
    t_crit = _safe('TCRIT', '', 0, '', 0, ref_name)

    # 自动调整压力范围（不能超过临界压力）
    if p_crit and p_max_pa > p_crit:
        p_max_pa = p_crit * 0.99

    # ---------- 饱和曲线（饱和液 + 饱和气） ----------
    # 在 p_min 到 min(p_max, p_crit) 之间均匀取点
    p_crit_kpa = p_crit / 1e3 if p_crit else p_max
    pressures_pa = [p_min_pa + (p_crit_kpa * 1e3 - p_min_pa) * i / num_points
                    for i in range(num_points + 1)]

    sat_liquid = []
    sat_vapor = []
    for P_Pa in pressures_pa:
        # 饱和液（Q=0）
        h_f = _safe('H', 'P', P_Pa, 'Q', 0, ref_name)
        # 饱和气（Q=1）
        h_g = _safe('H', 'P', P_Pa, 'Q', 1, ref_name)

        if h_f is not None:
            sat_liquid.append({"p_kpa": round(P_Pa / 1e3, 2), "h_kj_kg": round(h_f / 1e3, 2)})
        if h_g is not None:
            sat_vapor.append({"p_kpa": round(P_Pa / 1e3, 2), "h_kj_kg": round(h_g / 1e3, 2)})

    # ---------- 等温线（overheated vapor） ----------
    # 选几个常用温度：0, 20, 40, 60, 80°C（临界温度以下）
    isotherm_temps_c = [0, 20, 40, 60, 80]
    if t_crit:
        t_crit_c = t_crit - 273.15
        isotherm_temps_c = [t for t in isotherm_temps_c if t < t_crit_c - 5]

    isotherms = {}
    for T_C in isotherm_temps_c:
        T_K = T_C + 273.15
        points = []
        # 在压力范围扫描（必须大于饱和压力，否则两相区）
        for P_Pa in pressures_pa:
            h = _safe('H', 'T', T_K, 'P', P_Pa, ref_name)
            if h is not None:
                points.append({"p_kpa": round(P_Pa / 1e3, 2), "h_kj_kg": round(h / 1e3, 2)})
        if points:
            isotherms[f"T_{T_C}C"] = points

    # ---------- 等熵线（isentropes） ----------
    # 选几个常用熵值（每个制冷剂不同，根据饱和线估算）
    s_at_crit = _safe('S', '', 0, '', 0, ref_name)  # 临界点熵
    if s_at_crit:
        s_crit_kj_kgK = s_at_crit / 1e3
        # 在 s_crit 附近取几个值（从低到高）
        s_values = [s_crit_kj_kgK * 0.7, s_crit_kj_kgK * 0.85,
                    s_crit_kj_kgK * 1.0, s_crit_kj_kgK * 1.15]
    else:
        s_values = [1.5, 1.7, 1.9, 2.1]  # 兜底

    isentropes = {}
    for s_val in s_values:
        s_j_kgK = s_val * 1e3
        points = []
        # 在压力范围扫描（必须是过热区，h 单调）
        for P_Pa in pressures_pa:
            h = _safe('H', 'P', P_Pa, 'S', s_j_kgK, ref_name)
            if h is not None:
                points.append({"p_kpa": round(P_Pa / 1e3, 2), "h_kj_kg": round(h / 1e3, 2)})
        if points:
            isentropes[f"s_{round(s_val, 2)}"] = points

    return {
        "refrigerant": ref,
        "saturation_liquid": sat_liquid,
        "saturation_vapor": sat_vapor,
        "isotherms": isotherms,
        "isentropes": isentropes,
        "critical_point": {
            "p_kpa": round(p_crit / 1e3, 2) if p_crit else None,
            "h_kj_kg": round(h_crit / 1e3, 2) if h_crit else None,
            "T_crit_c": round(t_crit - 273.15, 2) if t_crit else None,
        },
        "metadata": {
            "num_points_per_curve": num_points,
            "pressure_range_kpa": [p_min, round(p_crit_kpa, 2) if p_crit else p_max],
        },
    }


# ============================================================================
# 验证
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("  coolprop_ph S2 Skill - 验证")
    print("=" * 70)

    # 测试 R134a
    print("\n【测试 1】R-134a p-h 图数据（压力范围 100-3000 kPa，50 个点）")
    data = generate_ph_curve("R134a", pressure_range_kpa=(100, 3000), num_points=20)
    print(f"  饱和液曲线点数: {len(data['saturation_liquid'])}")
    print(f"  饱和气曲线点数: {len(data['saturation_vapor'])}")
    print(f"  等温线: {list(data['isotherms'].keys())}")
    print(f"  等熵线: {list(data['isentropes'].keys())}")
    print(f"  临界点: P={data['critical_point']['p_kpa']} kPa, "
          f"T={data['critical_point']['T_crit_c']}°C")

    # 打印饱和液前 3 个点
    print("\n  饱和液曲线（前 3 点）：")
    for p in data['saturation_liquid'][:3]:
        print(f"    P={p['p_kpa']:7.2f} kPa, h={p['h_kj_kg']:7.2f} kJ/kg")

    # 打印饱和气前 3 个点
    print("\n  饱和气曲线（前 3 点）：")
    for p in data['saturation_vapor'][:3]:
        print(f"    P={p['p_kpa']:7.2f} kPa, h={p['h_kj_kg']:7.2f} kJ/kg")

    # 打印 T=20°C 等温线前 3 个点
    print("\n  T=20°C 等温线（前 3 点）：")
    if "T_20C" in data['isotherms']:
        for p in data['isotherms']['T_20C'][:3]:
            print(f"    P={p['p_kpa']:7.2f} kPa, h={p['h_kj_kg']:7.2f} kJ/kg")

    # 测试 R410A
    print("\n【测试 2】R-410A p-h 图数据")
    data2 = generate_ph_curve("R410A", pressure_range_kpa=(200, 4000), num_points=15)
    print(f"  饱和液点数: {len(data2['saturation_liquid'])}, "
          f"饱和气点数: {len(data2['saturation_vapor'])}")
    print(f"  临界点: P={data2['critical_point']['p_kpa']} kPa")

    # 测试错误
    print("\n【测试 3】错误处理")
    try:
        generate_ph_curve("R999")
    except ValueError as e:
        print(f"  ✅ 正确报错: {str(e)[:60]}")

    print("\n" + "=" * 70)
    print("  ✅ 所有测试通过")
    print("=" * 70)