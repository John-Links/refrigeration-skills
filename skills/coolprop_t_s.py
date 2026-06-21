"""
S7 - coolprop_t_s: T-s 图数据生成器

类似 S2 (p-h 图)，但生成 T-s 图（温-熵图）的所有数据点。

T-s 图的工程意义：
- p-h 图看"循环形状"（设计工况）
- T-s 图看"效率"（曲线越平 = 越接近卡诺循环 = 效率越高）
- T-s 图上的面积 = 热量（朗肯循环分析必备）

数据来源：CoolProp 7.0+
开源协议：MIT
版权：强领制冷技术（上海）有限公司
"""

import CoolProp.CoolProp as CP
from typing import Dict, List, Optional, Tuple

__version__ = "1.0.0"
__skill_name__ = "coolprop_t_s"

# 支持的制冷剂（与 S1 保持一致）
REFRIGERANTS = [
    # 氢氟碳（HFC）
    "R134a", "R410A", "R407C", "R404A", "R507A", "R32", "R23",
    # 氢氯氟碳（HCFC）
    "R22", "R123",
    # 自然制冷剂
    "R717",   # 氨 NH3
    "R744",   # 二氧化碳 CO2
    "R290",   # 丙烷
    "R1270",  # 丙烯
    "R600",   # 丁烷
    "R600a",  # 异丁烷
    "R718",   # 水 H2O
]


# ============================================================================
# 核心函数 1: 饱和曲线（两相区边界）
# ============================================================================

def generate_saturation_curve(
    refrigerant: str,
    temp_range_c: Optional[Tuple[float, float]] = None,
    n_points: int = 50
) -> Dict:
    """
    生成 T-s 图的饱和曲线（饱和液线 + 饱和蒸汽线）

    参数：
        refrigerant: 制冷剂名（如 "R134a", "R410A"）
        temp_range_c: 温度范围 (T_min, T_max)，默认三相点到临界点
        n_points: 采样点数（默认 50）

    返回：
        {
            "refrigerant": str,
            "saturation_liquid": [{"T_K", "T_C", "s_kJ_kgK", "P_kpa", "h_kJ_kg"}],
            "saturation_vapor":  [{...同上...}],
            "critical_point": {"T_K", "s_kJ_kgK", "P_kpa"},
            "triple_point": {"T_K", "s_kJ_kgK", "P_kpa"},
            "metadata": {...}
        }
    """
    if refrigerant not in REFRIGERANTS:
        raise ValueError(
            f"不支持的制冷剂 '{refrigerant}'。\n"
            f"支持的制冷剂: {REFRIGERANTS}"
        )

    # 默认温度范围：三相点 → 临界点
    if temp_range_c is None:
        T_triple_K = CP.PropsSI("Ttriple", refrigerant)
        T_crit_K = CP.PropsSI("Tcrit", refrigerant)
        temp_range_c = (T_triple_K - 273.15, T_crit_K - 273.15)

    T_min_C, T_max_C = temp_range_c
    T_min_K = T_min_C + 273.15
    T_max_K = T_max_C + 273.15

    # 边界检查
    T_crit_K = CP.PropsSI("Tcrit", refrigerant)
    if T_max_K > T_crit_K:
        T_max_K = T_crit_K - 0.1  # 临界点附近 CoolProp 不稳定，留 0.1K 余量

    T_triple_K = CP.PropsSI("Ttriple", refrigerant)
    if T_min_K < T_triple_K:
        T_min_K = T_triple_K + 0.1

    sat_liquid = []
    sat_vapor = []

    for i in range(n_points):
        T_K = T_min_K + (T_max_K - T_min_K) * i / (n_points - 1)
        T_C = T_K - 273.15

        try:
            # 饱和液
            s_liq = CP.PropsSI("S", "T", T_K, "Q", 0, refrigerant)
            P_sat = CP.PropsSI("P", "T", T_K, "Q", 0, refrigerant)
            h_liq = CP.PropsSI("H", "T", T_K, "Q", 0, refrigerant)

            # 饱和蒸汽
            s_vap = CP.PropsSI("S", "T", T_K, "Q", 1, refrigerant)
            h_vap = CP.PropsSI("H", "T", T_K, "Q", 1, refrigerant)

            sat_liquid.append({
                "T_K": round(T_K, 3),
                "T_C": round(T_C, 3),
                "s_kJ_kgK": round(s_liq / 1000, 5),  # J/(kg·K) → kJ/(kg·K)
                "P_kpa": round(P_sat / 1000, 3),
                "h_kJ_kg": round(h_liq / 1000, 3),
            })

            sat_vapor.append({
                "T_K": round(T_K, 3),
                "T_C": round(T_C, 3),
                "s_kJ_kgK": round(s_vap / 1000, 5),
                "P_kpa": round(P_sat / 1000, 3),
                "h_kJ_kg": round(h_vap / 1000, 3),
            })
        except Exception:
            # 临界点附近可能失败，跳过
            continue

    # 临界点
    try:
        s_crit = CP.PropsSI("S", "T", T_crit_K, "Q", 0, refrigerant)
        P_crit = CP.PropsSI("Pcrit", refrigerant)
        critical_point = {
            "T_K": round(T_crit_K, 3),
            "T_C": round(T_crit_K - 273.15, 3),
            "s_kJ_kgK": round(s_crit / 1000, 5),
            "P_kpa": round(P_crit / 1000, 3),
        }
    except Exception:
        critical_point = None

    # 三相点
    try:
        s_triple_l = CP.PropsSI("S", "T", T_triple_K, "Q", 0, refrigerant)
        P_triple = CP.PropsSI("ptriple", refrigerant)
        triple_point = {
            "T_K": round(T_triple_K, 3),
            "T_C": round(T_triple_K - 273.15, 3),
            "s_kJ_kgK": round(s_triple_l / 1000, 5),
            "P_kpa": round(P_triple / 1000, 5),
        }
    except Exception:
        triple_point = None

    return {
        "refrigerant": refrigerant,
        "saturation_liquid": sat_liquid,
        "saturation_vapor": sat_vapor,
        "critical_point": critical_point,
        "triple_point": triple_point,
        "metadata": {
            "skill": __skill_name__,
            "version": __version__,
            "n_points": len(sat_liquid),
            "T_range_C": [round(T_min_K - 273.15, 2), round(T_max_K - 273.15, 2)],
        }
    }


# ============================================================================
# 核心函数 2: 等温线（在过热区）
# ============================================================================

def generate_isotherm(
    refrigerant: str,
    T_c: float,
    s_range_kJ_kgK: Optional[Tuple[float, float]] = None,
    n_points: int = 30
) -> Dict:
    """
    生成 T-s 图的等温线（恒温线，常用于过热区）

    参数：
        refrigerant: 制冷剂名
        T_c: 温度（摄氏度）
        s_range_kJ_kgK: 熵范围，默认饱和液熵 → 1.5倍饱和蒸汽熵
        n_points: 采样点数

    返回：
        {
            "refrigerant": str,
            "isotherm": [{"s_kJ_kgK", "P_kpa", "h_kJ_kg", "phase"}],
            "T_C": float,
            "metadata": {...}
        }
    """
    if refrigerant not in REFRIGERANTS:
        raise ValueError(f"不支持的制冷剂 '{refrigerant}'")

    T_K = T_c + 273.15

    # 默认熵范围：饱和液熵 ~ 1.5倍饱和蒸汽熵
    if s_range_kJ_kgK is None:
        try:
            s_liq = CP.PropsSI("S", "T", T_K, "Q", 0, refrigerant) / 1000
            s_vap = CP.PropsSI("S", "T", T_K, "Q", 1, refrigerant) / 1000
            s_range_kJ_kgK = (s_liq - 0.1, s_vap * 1.5)
        except Exception:
            raise ValueError(f"T={T_c}°C 超出 {refrigerant} 有效范围")

    s_min, s_max = s_range_kJ_kgK

    points = []
    for i in range(n_points):
        s_J_kgK = (s_min + (s_max - s_min) * i / (n_points - 1)) * 1000

        try:
            # 检查是否在两相区
            try:
                P_sat = CP.PropsSI("P", "T", T_K, "Q", 0, refrigerant)
                P_at_s = CP.PropsSI("P", "T", T_K, "S", s_J_kgK, refrigerant)
                # 在两相区时 CoolProp 会警告
                if abs(P_at_s - P_sat) < 1 and s_min < (s_vap := CP.PropsSI("S", "T", T_K, "Q", 1, refrigerant) / 1000) * 1000:
                    phase = "two_phase"
                else:
                    phase = "superheated" if P_at_s < P_sat else "compressed_liquid"
            except Exception:
                P_at_s = CP.PropsSI("P", "T", T_K, "S", s_J_kgK, refrigerant)
                phase = "unknown"

            h = CP.PropsSI("H", "T", T_K, "S", s_J_kgK, refrigerant)

            points.append({
                "s_kJ_kgK": round(s_J_kgK / 1000, 5),
                "P_kpa": round(P_at_s / 1000, 3),
                "h_kJ_kg": round(h / 1000, 3),
                "phase": phase,
            })
        except Exception:
            # 跳过 CoolProp 计算失败的点
            continue

    return {
        "refrigerant": refrigerant,
        "isotherm": points,
        "T_C": T_c,
        "metadata": {
            "skill": __skill_name__,
            "version": __version__,
            "n_points": len(points),
            "s_range_kJ_kgK": [round(s_min, 3), round(s_max, 3)],
        }
    }


# ============================================================================
# 核心函数 3: 等压线（在过热区）
# ============================================================================

def generate_isobar(
    refrigerant: str,
    P_kpa: float,
    s_range_kJ_kgK: Optional[Tuple[float, float]] = None,
    n_points: int = 30
) -> Dict:
    """
    生成 T-s 图的等压线（恒压线）

    参数：
        refrigerant: 制冷剂名
        P_kpa: 压力（kPa）
        s_range_kJ_kgK: 熵范围，默认饱和液熵 → 1.5倍饱和蒸汽熵
        n_points: 采样点数

    返回：
        {
            "refrigerant": str,
            "isobar": [{"s_kJ_kgK", "T_K", "T_C", "h_kJ_kg"}],
            "P_kpa": float,
            "metadata": {...}
        }
    """
    if refrigerant not in REFRIGERANTS:
        raise ValueError(f"不支持的制冷剂 '{refrigerant}'")

    P_Pa = P_kpa * 1000

    # 默认熵范围
    if s_range_kJ_kgK is None:
        try:
            T_sat = CP.PropsSI("T", "P", P_Pa, "Q", 0, refrigerant)
            s_liq = CP.PropsSI("S", "P", P_Pa, "Q", 0, refrigerant) / 1000
            s_vap = CP.PropsSI("S", "P", P_Pa, "Q", 1, refrigerant) / 1000
            s_range_kJ_kgK = (s_liq - 0.1, s_vap * 1.5)
        except Exception:
            raise ValueError(f"P={P_kpa} kPa 超出 {refrigerant} 有效范围")

    s_min, s_max = s_range_kJ_kgK

    points = []
    for i in range(n_points):
        s_J_kgK = (s_min + (s_max - s_min) * i / (n_points - 1)) * 1000

        try:
            T_K = CP.PropsSI("T", "P", P_Pa, "S", s_J_kgK, refrigerant)
            h = CP.PropsSI("H", "P", P_Pa, "S", s_J_kgK, refrigerant)

            points.append({
                "s_kJ_kgK": round(s_J_kgK / 1000, 5),
                "T_K": round(T_K, 3),
                "T_C": round(T_K - 273.15, 3),
                "h_kJ_kg": round(h / 1000, 3),
            })
        except Exception:
            continue

    return {
        "refrigerant": refrigerant,
        "isobar": points,
        "P_kpa": P_kpa,
        "metadata": {
            "skill": __skill_name__,
            "version": __version__,
            "n_points": len(points),
            "s_range_kJ_kgK": [round(s_min, 3), round(s_max, 3)],
        }
    }


# ============================================================================
# 便捷函数：完整 T-s 图（饱和 + 等温线 + 等压线）
# ============================================================================

def generate_full_ts_chart(
    refrigerant: str,
    temp_range_c: Optional[Tuple[float, float]] = None,
    isotherm_temps_c: Optional[List[float]] = None,
    isobar_pressures_kpa: Optional[List[float]] = None,
    n_points_sat: int = 50,
    n_points_lines: int = 20
) -> Dict:
    """
    一键生成完整 T-s 图所有数据

    参数：
        refrigerant: 制冷剂名
        temp_range_c: 温度范围
        isotherm_temps_c: 等温线温度列表（如 [0, 20, 40, 60]）
        isobar_pressures_kpa: 等压线压力列表（如 [101.325, 500, 1000]）
        n_points_sat: 饱和曲线点数
        n_points_lines: 等温/等压线点数

    返回：
        {
            "refrigerant": str,
            "saturation_curve": {...},
            "isotherms": [...],
            "isobars": [...],
            "metadata": {...}
        }
    """
    # 默认等温线：临界点附近到低温段，每 20°C 一条
    if isotherm_temps_c is None:
        sat = generate_saturation_curve(refrigerant, temp_range_c, n_points_sat)
        T_crit_C = sat["critical_point"]["T_C"]
        T_min_C = sat["metadata"]["T_range_C"][0]

        # 在 [T_min+10, T_crit-20] 区间每 20°C 一条
        isotherm_temps_c = []
        T = T_min_C + 10
        while T < T_crit_C - 20:
            isotherm_temps_c.append(round(T, 1))
            T += 20

    # 默认等压线：101.325 kPa（大气压） + 2-3 个常用压力
    if isobar_pressures_kpa is None:
        isobar_pressures_kpa = [101.325, 500, 1000, 2000]

    # 生成饱和曲线
    sat_curve = generate_saturation_curve(refrigerant, temp_range_c, n_points_sat)

    # 生成等温线
    isotherms = []
    for T_c in isotherm_temps_c:
        try:
            iso = generate_isotherm(refrigerant, T_c, n_points=n_points_lines)
            isotherms.append(iso)
        except Exception as e:
            # 跳过不可行的温度
            continue

    # 生成等压线
    isobars = []
    for P in isobar_pressures_kpa:
        try:
            iso = generate_isobar(refrigerant, P, n_points=n_points_lines)
            isobars.append(iso)
        except Exception:
            continue

    return {
        "refrigerant": refrigerant,
        "saturation_curve": sat_curve,
        "isotherms": isotherms,
        "isobars": isobars,
        "metadata": {
            "skill": __skill_name__,
            "version": __version__,
            "n_isotherms": len(isotherms),
            "n_isobars": len(isobars),
            "description": "完整 T-s 图数据，可直接用于绘图或 AI 推理",
        }
    }


# ============================================================================
# 自测代码（python skills/coolprop_t_s.py 运行）
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("S7 coolprop_t_s 自测 - T-s 图数据生成")
    print("=" * 70)

    # 测试 1: R134a 饱和曲线
    print("\n[测试 1] R134a 饱和曲线（30 个点）")
    sat = generate_saturation_curve("R134a", n_points=30)
    print(f"  制冷剂: {sat['refrigerant']}")
    print(f"  饱和液点: {len(sat['saturation_liquid'])}")
    print(f"  饱和蒸汽点: {len(sat['saturation_vapor'])}")
    print(f"  临界点: T={sat['critical_point']['T_C']}°C, "
          f"s={sat['critical_point']['s_kJ_kgK']} kJ/(kg·K)")
    print(f"  三相点: T={sat['triple_point']['T_C']}°C, "
          f"s={sat['triple_point']['s_kJ_kgK']} kJ/(kg·K)")
    # 显示几个样本点
    print(f"  样本点（饱和蒸汽）：")
    for i in [0, len(sat['saturation_vapor'])//2, -1]:
        pt = sat['saturation_vapor'][i]
        print(f"    T={pt['T_C']:7.2f}°C, s={pt['s_kJ_kgK']:7.4f} kJ/(kg·K), "
              f"P={pt['P_kpa']:8.2f} kPa")

    # 测试 2: R134a 等温线（30°C）
    print("\n[测试 2] R134a 30°C 等温线")
    iso_T = generate_isotherm("R134a", 30, n_points=20)
    print(f"  点数: {len(iso_T['isotherm'])}")
    print(f"  样本点：")
    for i in [0, len(iso_T['isotherm'])//2, -1]:
        pt = iso_T['isotherm'][i]
        print(f"    s={pt['s_kJ_kgK']:7.4f} kJ/(kg·K), "
              f"P={pt['P_kpa']:8.2f} kPa, phase={pt['phase']}")

    # 测试 3: R134a 等压线（101.325 kPa）
    print("\n[测试 3] R134a 101.325 kPa 等压线")
    iso_P = generate_isobar("R134a", 101.325, n_points=20)
    print(f"  点数: {len(iso_P['isobar'])}")
    print(f"  样本点：")
    for i in [0, len(iso_P['isobar'])//2, -1]:
        pt = iso_P['isobar'][i]
        print(f"    s={pt['s_kJ_kgK']:7.4f} kJ/(kg·K), "
              f"T={pt['T_C']:7.2f}°C")

    # 测试 4: R717（氨）饱和曲线 - 验证多制冷剂支持
    print("\n[测试 4] R717 氨饱和曲线（验证多制冷剂）")
    sat_nh3 = generate_saturation_curve("R717", n_points=20)
    print(f"  R717 临界点: T={sat_nh3['critical_point']['T_C']}°C")
    print(f"  R717 三相点: T={sat_nh3['triple_point']['T_C']}°C")

    # 测试 5: 完整 T-s 图（一键生成）
    print("\n[测试 5] R134a 完整 T-s 图（一键生成）")
    full = generate_full_ts_chart(
        "R134a",
        isotherm_temps_c=[0, 20, 40],
        isobar_pressures_kpa=[101.325, 500, 1000]
    )
    print(f"  饱和曲线: {len(full['saturation_curve']['saturation_liquid'])} 点")
    print(f"  等温线: {full['metadata']['n_isotherms']} 条")
    print(f"  等压线: {full['metadata']['n_isobars']} 条")

    # 测试 6: 错误处理
    print("\n[测试 6] 错误处理（不支持的制冷剂）")
    try:
        generate_saturation_curve("R999")
        print("  ❌ 应该报错但没报")
    except ValueError as e:
        print(f"  ✅ 正确报错: {str(e)[:80]}...")

    # 测试 7: 制冷剂列表
    print("\n[测试 7] 支持的制冷剂列表")
    print(f"  共支持 {len(REFRIGERANTS)} 种制冷剂:")
    print(f"  {', '.join(REFRIGERANTS)}")

    print("\n" + "=" * 70)
    print("✅ 所有测试通过！S7 coolprop_t_s 可用。")
    print("=" * 70)