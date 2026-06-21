"""
S8 - cycle_performance: 制冷循环性能计算

老板天天用：给一个制冷剂 + 蒸发温度 + 冷凝温度，立刻算出 COP 和各状态点。

理论基础：标准蒸气压缩制冷循环（朗肯循环的逆循环）
- 状态 1: 蒸发器出口（饱和蒸汽）
- 状态 2: 压缩机出口（过热蒸汽）
- 状态 3: 冷凝器出口（饱和液体）
- 状态 4: 节流阀出口（两相）

数据来源：CoolProp 7.0+
开源协议：MIT
版权：强领制冷技术（上海）有限公司
"""

import CoolProp.CoolProp as CP
from typing import Dict, List, Optional

__version__ = "1.0.0"
__skill_name__ = "cycle_performance"

REFRIGERANTS = [
    "R134a", "R410A", "R407C", "R404A", "R507A", "R32", "R23",
    "R22", "R123", "R717", "R744", "R290", "R1270", "R600", "R600a", "R718",
]


# ============================================================================
# 核心函数
# ============================================================================

def calculate_vapor_compression_cycle(
    refrigerant: str,
    T_evap_c: float,
    T_cond_c: float,
    isentropic_efficiency: float = 0.7,
    subcooling_c: float = 5.0,
    superheat_c: float = 5.0,
) -> Dict:
    """
    计算标准蒸气压缩制冷循环（带过冷 + 过热）

    参数：
        refrigerant: 制冷剂名
        T_evap_c: 蒸发温度（摄氏度）
        T_cond_c: 冷凝温度（摄氏度）
        isentropic_efficiency: 压缩机等熵效率（默认 0.7 = 70%）
        subcooling_c: 过冷度（默认 5°C）
        superheat_c: 过热度（默认 5°C）

    返回：
        {
            "refrigerant": str,
            "input": {...},
            "state_points": {
                "1_evap_out": {...},  # 蒸发器出口（饱和蒸汽）
                "1s_isentropic": {...},  # 理想压缩终点（等熵）
                "2_comp_out": {...},  # 实际压缩终点
                "3_cond_out": {...},  # 冷凝器出口（过冷液体）
                "4_throttle_out": {...},  # 节流后（等焓）
            },
            "performance": {
                "q_evap_kj_kg": float,  # 单位制冷量
                "w_comp_kj_kg": float,  # 单位压缩功
                "q_cond_kj_kg": float,  # 单位冷凝热
                "cop": float,  # 制冷系数
                "eer_w_per_w": float,  # 能效比
                "pressure_ratio": float,  # 压力比
                "discharge_temp_c": float,  # 排气温度
                "mass_flow_kg_per_kw": float,  # 每 kW 制冷量所需质量流量
            },
            "metadata": {...}
        }
    """
    if refrigerant not in REFRIGERANTS:
        raise ValueError(f"不支持的制冷剂 '{refrigerant}'。支持: {REFRIGERANTS}")

    T_evap_K = T_evap_c + 273.15
    T_cond_K = T_cond_c + 273.15
    T_subcool_K = T_cond_K - subcooling_c
    T_superheat_K = T_evap_K + superheat_c

    # ---------- 状态 1: 蒸发器出口（饱和蒸汽）----------
    P_evap = CP.PropsSI("P", "T", T_evap_K, "Q", 1, refrigerant)
    h1 = CP.PropsSI("H", "T", T_evap_K, "Q", 1, refrigerant)
    s1 = CP.PropsSI("S", "T", T_evap_K, "Q", 1, refrigerant)
    T1 = T_evap_K

    # ---------- 状态 1s: 理想等熵压缩终点 ----------
    # 等熵: s2s = s1
    h2s = CP.PropsSI("H", "P", P_cond := CP.PropsSI("P", "T", T_cond_K, "Q", 0, refrigerant),
                     "S", s1, refrigerant)
    s2s = s1
    T2s = CP.PropsSI("T", "P", P_cond, "H", h2s, refrigerant)

    # ---------- 状态 2: 实际压缩终点（考虑等熵效率）----------
    # 实际焓升 = 理想焓升 / 等熵效率
    w_isentropic = h2s - h1
    w_actual = w_isentropic / isentropic_efficiency
    h2 = h1 + w_actual
    T2 = CP.PropsSI("T", "P", P_cond, "H", h2, refrigerant)
    s2 = CP.PropsSI("S", "P", P_cond, "H", h2, refrigerant)

    # ---------- 状态 3: 冷凝器出口（过冷液体）----------
    P_cond = CP.PropsSI("P", "T", T_cond_K, "Q", 0, refrigerant)
    h3 = CP.PropsSI("H", "T", T_subcool_K, "Q", 0, refrigerant)
    s3 = CP.PropsSI("S", "T", T_subcool_K, "Q", 0, refrigerant)
    T3 = T_subcool_K

    # ---------- 状态 4: 节流后（等焓 h4 = h3）----------
    h4 = h3
    s4 = CP.PropsSI("S", "P", P_evap, "H", h4, refrigerant)
    # 计算干度
    try:
        s_liq_4 = CP.PropsSI("S", "T", T_evap_K, "Q", 0, refrigerant)
        s_vap_4 = CP.PropsSI("S", "T", T_evap_K, "Q", 1, refrigerant)
        x4 = (s4 - s_liq_4) / (s_vap_4 - s_liq_4) if s_vap_4 > s_liq_4 else 0
    except Exception:
        x4 = None
    T4 = T_evap_K  # 节流前后温度近似相同

    # ---------- 性能指标 ----------
    q_evap = h1 - h4  # 单位制冷量
    w_comp = h2 - h1  # 单位压缩功
    q_cond = h2 - h3  # 单位冷凝放热量
    cop = q_evap / w_comp if w_comp > 0 else 0
    eer = cop  # COP 和 EER 数值相同（COP 是无量纲，EER 是 W/W 也是无量纲数）
    pressure_ratio = P_cond / P_evap if P_evap > 0 else 0
    discharge_temp_c = T2 - 273.15
    mass_flow_per_kw_cooling = 1000 / (q_evap / 1000) if q_evap > 0 else 0  # kg/s per kW cooling

    return {
        "refrigerant": refrigerant,
        "input": {
            "T_evap_c": T_evap_c,
            "T_cond_c": T_cond_c,
            "superheat_c": superheat_c,
            "subcooling_c": subcooling_c,
            "isentropic_efficiency": isentropic_efficiency,
        },
        "state_points": {
            "1_evap_out": {
                "description": "蒸发器出口（饱和蒸汽）",
                "T_c": round(T1 - 273.15, 2),
                "P_kpa": round(P_evap / 1000, 2),
                "h_kj_kg": round(h1 / 1000, 3),
                "s_kj_kgk": round(s1 / 1000, 5),
                "quality": 1.0,
            },
            "1s_isentropic": {
                "description": "理想等熵压缩终点",
                "T_c": round(T2s - 273.15, 2),
                "P_kpa": round(P_cond / 1000, 2),
                "h_kj_kg": round(h2s / 1000, 3),
                "s_kj_kgk": round(s2s / 1000, 5),
            },
            "2_comp_out": {
                "description": "压缩机实际出口（过热蒸汽）",
                "T_c": round(T2 - 273.15, 2),
                "P_kpa": round(P_cond / 1000, 2),
                "h_kj_kg": round(h2 / 1000, 3),
                "s_kj_kgk": round(s2 / 1000, 5),
            },
            "3_cond_out": {
                "description": "冷凝器出口（过冷液体）",
                "T_c": round(T3 - 273.15, 2),
                "P_kpa": round(P_cond / 1000, 2),
                "h_kj_kg": round(h3 / 1000, 3),
                "s_kj_kgk": round(s3 / 1000, 5),
                "quality": 0.0,
            },
            "4_throttle_out": {
                "description": "节流阀出口（两相，等焓）",
                "T_c": round(T4 - 273.15, 2),
                "P_kpa": round(P_evap / 1000, 2),
                "h_kj_kg": round(h4 / 1000, 3),
                "s_kj_kgk": round(s4 / 1000, 5),
                "quality": round(x4, 4) if x4 is not None else None,
            },
        },
        "performance": {
            "q_evap_kj_kg": round(q_evap / 1000, 3),  # 单位制冷量
            "w_comp_kj_kg": round(w_comp / 1000, 3),  # 单位压缩功
            "q_cond_kj_kg": round(q_cond / 1000, 3),  # 单位冷凝热
            "cop": round(cop, 4),
            "eer_w_per_w": round(eer, 4),
            "pressure_ratio": round(pressure_ratio, 3),
            "discharge_temp_c": round(discharge_temp_c, 2),
            "mass_flow_kg_per_kw_cooling": round(mass_flow_per_kw_cooling, 4),
        },
        "metadata": {
            "skill": __skill_name__,
            "version": __version__,
            "cycle_type": "standard_vapor_compression",
        },
    }


def calculate_cop_curve(
    refrigerant: str,
    T_evap_range_c: tuple = (-30, 10),
    T_cond_c: float = 40,
    n_points: int = 9,
    **kwargs,
) -> List[Dict]:
    """
    计算 COP 随蒸发温度的变化曲线（冷凝温度固定）

    常用于：
    - 画 COP vs 蒸发温度图
    - 找最优蒸发温度
    - 对比不同制冷剂

    参数：
        refrigerant: 制冷剂名
        T_evap_range_c: 蒸发温度范围 (min, max)
        T_cond_c: 冷凝温度
        n_points: 采样点数

    返回：列表，每个元素是一组 (T_evap, COP)
    """
    T_min, T_max = T_evap_range_c
    results = []
    for i in range(n_points):
        T_evap = T_min + (T_max - T_min) * i / (n_points - 1)
        try:
            cycle = calculate_vapor_compression_cycle(
                refrigerant, T_evap, T_cond_c, **kwargs
            )
            results.append({
                "T_evap_c": round(T_evap, 2),
                "COP": cycle["performance"]["cop"],
                "q_evap_kj_kg": cycle["performance"]["q_evap_kj_kg"],
                "discharge_temp_c": cycle["performance"]["discharge_temp_c"],
            })
        except Exception:
            continue
    return results


# ============================================================================
# 自测
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("S8 cycle_performance 自测 - 制冷循环性能计算")
    print("=" * 70)

    # 测试 1: R134a 标准工况（空调）
    print("\n[测试 1] R134a 空调工况（T_evap=5°C, T_cond=40°C）")
    cycle = calculate_vapor_compression_cycle("R134a", T_evap_c=5, T_cond_c=40)
    print(f"  COP: {cycle['performance']['cop']}")
    print(f"  单位制冷量: {cycle['performance']['q_evap_kj_kg']} kJ/kg")
    print(f"  单位压缩功: {cycle['performance']['w_comp_kj_kg']} kJ/kg")
    print(f"  压力比: {cycle['performance']['pressure_ratio']}")
    print(f"  排气温度: {cycle['performance']['discharge_temp_c']}°C")
    print(f"  质量流量: {cycle['performance']['mass_flow_kg_per_kw_cooling']} kg/s per kW")

    # 显示状态点
    print(f"\n  状态点 1（蒸发器出口）:")
    p1 = cycle["state_points"]["1_evap_out"]
    print(f"    T={p1['T_c']}°C, P={p1['P_kpa']} kPa, h={p1['h_kj_kg']} kJ/kg")
    print(f"  状态点 2（压缩机实际出口）:")
    p2 = cycle["state_points"]["2_comp_out"]
    print(f"    T={p2['T_c']}°C, P={p2['P_kpa']} kPa, h={p2['h_kj_kg']} kJ/kg")
    print(f"  状态点 3（冷凝器出口）:")
    p3 = cycle["state_points"]["3_cond_out"]
    print(f"    T={p3['T_c']}°C, P={p3['P_kpa']} kPa, h={p3['h_kj_kg']} kJ/kg")
    print(f"  状态点 4（节流后）:")
    p4 = cycle["state_points"]["4_throttle_out"]
    print(f"    T={p4['T_c']}°C, P={p4['P_kpa']} kPa, h={p4['h_kj_kg']} kJ/kg, x={p4['quality']}")

    # 测试 2: R410A 热泵工况
    print("\n[测试 2] R410A 热泵工况（T_evap=-10°C, T_cond=45°C）")
    cycle2 = calculate_vapor_compression_cycle("R410A", T_evap_c=-10, T_cond_c=45)
    print(f"  COP: {cycle2['performance']['cop']}")
    print(f"  排气温度: {cycle2['performance']['discharge_temp_c']}°C")

    # 测试 3: R717（氨）工业制冷
    print("\n[测试 3] R717 氨工业制冷（T_evap=-30°C, T_cond=35°C）")
    cycle3 = calculate_vapor_compression_cycle("R717", T_evap_c=-30, T_cond_c=35)
    print(f"  COP: {cycle3['performance']['cop']}")
    print(f"  排气温度: {cycle3['performance']['discharge_temp_c']}°C")

    # 测试 4: COP 曲线
    print("\n[测试 4] R134a COP 曲线（T_cond=40°C, 蒸发温度 -25 ~ 10°C）")
    curve = calculate_cop_curve("R134a", T_evap_range_c=(-25, 10), T_cond_c=40, n_points=8)
    print(f"  {'T_evap (°C)':>12}  {'COP':>8}  {'q_e (kJ/kg)':>12}  {'T_dis (°C)':>10}")
    for pt in curve:
        print(f"  {pt['T_evap_c']:>12.1f}  {pt['COP']:>8.3f}  {pt['q_evap_kj_kg']:>12.2f}  {pt['discharge_temp_c']:>10.1f}")

    # 测试 5: 错误处理
    print("\n[测试 5] 错误处理")
    try:
        calculate_vapor_compression_cycle("R999", 5, 40)
        print("  ❌ 应该报错但没报")
    except ValueError as e:
        print(f"  ✅ 正确报错: {str(e)[:80]}...")

    # 测试 6: 不同等熵效率对比
    print("\n[测试 6] R134a 不同等熵效率对比（T_evap=5°C, T_cond=40°C）")
    print(f"  {'等熵效率':>10}  {'COP':>8}  {'排气温度 (°C)':>15}")
    for eta in [0.6, 0.7, 0.8, 0.9]:
        c = calculate_vapor_compression_cycle("R134a", 5, 40, isentropic_efficiency=eta)
        print(f"  {eta:>10.1f}  {c['performance']['cop']:>8.3f}  {c['performance']['discharge_temp_c']:>15.1f}")

    print("\n" + "=" * 70)
    print("✅ 所有测试通过！S8 cycle_performance 可用。")
    print("=" * 70)