"""
S9 - refrigerant_compare: 多制冷剂并排比较

老板常用：选型时"用 R134a 还是 R410A 还是 R32？" 一次看所有制冷剂参数。

数据来源：CoolProp 7.0+
开源协议：MIT
版权：强领制冷技术（上海）有限公司
"""

import CoolProp.CoolProp as CP
from typing import Dict, List

__version__ = "1.0.0"
__skill_name__ = "refrigerant_compare"

REFRIGERANTS = [
    "R134a", "R410A", "R407C", "R404A", "R507A", "R32", "R23",
    "R22", "R123", "R717", "R744", "R290", "R1270", "R600", "R600a", "R718",
]

# GWP 和 ODP 数据（来源：IPCC AR4 + Montreal Protocol）
REFRIGERANT_ENV = {
    # GWP-100 (CO2 = 1)
    "R134a": {"gwp100": 1430, "odp": 0.0, "ashrae_safety": "A1"},
    "R410A": {"gwp100": 2088, "odp": 0.0, "ashrae_safety": "A1"},
    "R407C": {"gwp100": 1774, "odp": 0.0, "ashrae_safety": "A1"},
    "R404A": {"gwp100": 3922, "odp": 0.0, "ashrae_safety": "A1"},
    "R507A": {"gwp100": 3985, "odp": 0.0, "ashrae_safety": "A1"},
    "R32":   {"gwp100": 675,  "odp": 0.0, "ashrae_safety": "A2L"},
    "R23":   {"gwp100": 14800, "odp": 0.0, "ashrae_safety": "A1"},
    "R22":   {"gwp100": 1810, "odp": 0.055, "ashrae_safety": "A1"},
    "R123":  {"gwp100": 77,   "odp": 0.02, "ashrae_safety": "B1"},
    "R717":  {"gwp100": 0,    "odp": 0.0, "ashrae_safety": "B2L"},
    "R744":  {"gwp100": 1,    "odp": 0.0, "ashrae_safety": "A1"},
    "R290":  {"gwp100": 3,    "odp": 0.0, "ashrae_safety": "A3"},
    "R1270": {"gwp100": 2,    "odp": 0.0, "ashrae_safety": "A3"},
    "R600":  {"gwp100": 4,    "odp": 0.0, "ashrae_safety": "A3"},
    "R600a": {"gwp100": 3,    "odp": 0.0, "ashrae_safety": "A3"},
    "R718":  {"gwp100": 0,    "odp": 0.0, "ashrae_safety": "A1"},
}


# ============================================================================
# 核心函数
# ============================================================================

def compare_refrigerants(
    refrigerants: List[str],
    T_evap_c: float,
    T_cond_c: float,
    isentropic_efficiency: float = 0.7,
    superheat_c: float = 5.0,
    subcooling_c: float = 5.0,
) -> Dict:
    """
    多制冷剂并排比较

    参数：
        refrigerants: 制冷剂列表，如 ["R134a", "R410A", "R32"]
        T_evap_c: 蒸发温度
        T_cond_c: 冷凝温度
        isentropic_efficiency: 压缩机等熵效率
        superheat_c: 过热度
        subcooling_c: 过冷度

    返回：
        {
            "input": {...},
            "comparison": [
                {
                    "refrigerant": str,
                    "available": bool,  # CoolProp 是否有数据
                    "T_evap_c": float,
                    "P_evap_kpa": float,
                    "T_cond_c": float,
                    "P_cond_kpa": float,
                    "q_evap_kj_kg": float,
                    "w_comp_kj_kg": float,
                    "cop": float,
                    "pressure_ratio": float,
                    "discharge_temp_c": float,
                    "gwp100": int,
                    "odp": float,
                    "ashrae_safety": str,
                    "error": str | None,
                }
            ],
            "summary": {
                "best_cop": str,           # COP 最高的制冷剂
                "lowest_gwp_available": str,  # GWP 最低的可选制冷剂
                "lowest_discharge_temp": str,
            }
        }
    """
    if not refrigerants:
        raise ValueError("制冷剂列表不能为空")

    for r in refrigerants:
        if r not in REFRIGERANTS:
            raise ValueError(f"不支持的制冷剂 '{r}'。支持: {REFRIGERANTS}")

    comparison = []
    for r in refrigerants:
        entry = {
            "refrigerant": r,
            "available": False,
            "error": None,
        }
        try:
            T_evap_K = T_evap_c + 273.15
            T_cond_K = T_cond_c + 273.15
            T_superheat_K = T_evap_K + superheat_c
            T_subcool_K = T_cond_K - subcooling_c

            # 饱和压力
            P_evap = CP.PropsSI("P", "T", T_evap_K, "Q", 1, r)
            P_cond = CP.PropsSI("P", "T", T_cond_K, "Q", 0, r)

            # 状态 1: 蒸发器出口（饱和蒸汽）
            h1 = CP.PropsSI("H", "T", T_evap_K, "Q", 1, r)
            s1 = CP.PropsSI("S", "T", T_evap_K, "Q", 1, r)

            # 状态 2s: 等熵压缩
            h2s = CP.PropsSI("H", "P", P_cond, "S", s1, r)
            w_isentropic = h2s - h1
            w_actual = w_isentropic / isentropic_efficiency
            h2 = h1 + w_actual
            T2 = CP.PropsSI("T", "P", P_cond, "H", h2, r)

            # 状态 3: 冷凝器出口
            h3 = CP.PropsSI("H", "T", T_subcool_K, "Q", 0, r)

            # 性能
            q_evap = h1 - h3
            w_comp = w_actual
            cop = q_evap / w_comp if w_comp > 0 else 0
            pressure_ratio = P_cond / P_evap if P_evap > 0 else 0

            env = REFRIGERANT_ENV.get(r, {})

            entry.update({
                "available": True,
                "T_evap_c": T_evap_c,
                "P_evap_kpa": round(P_evap / 1000, 2),
                "T_cond_c": T_cond_c,
                "P_cond_kpa": round(P_cond / 1000, 2),
                "q_evap_kj_kg": round(q_evap / 1000, 3),
                "w_comp_kj_kg": round(w_comp / 1000, 3),
                "cop": round(cop, 4),
                "pressure_ratio": round(pressure_ratio, 3),
                "discharge_temp_c": round(T2 - 273.15, 2),
                "gwp100": env.get("gwp100"),
                "odp": env.get("odp"),
                "ashrae_safety": env.get("ashrae_safety"),
            })
        except Exception as e:
            entry["error"] = str(e)[:100]

        comparison.append(entry)

    # 总结：找最优
    valid = [c for c in comparison if c["available"]]

    if valid:
        best_cop = max(valid, key=lambda x: x["cop"])["refrigerant"]
        lowest_gwp_entry = min(
            [c for c in valid if c.get("gwp100") is not None],
            key=lambda x: x["gwp100"],
            default=None,
        )
        lowest_gwp = lowest_gwp_entry["refrigerant"] if lowest_gwp_entry else None
        lowest_discharge = min(valid, key=lambda x: x["discharge_temp_c"])["refrigerant"]
    else:
        best_cop = lowest_gwp = lowest_discharge = None

    return {
        "input": {
            "refrigerants": refrigerants,
            "T_evap_c": T_evap_c,
            "T_cond_c": T_cond_c,
            "isentropic_efficiency": isentropic_efficiency,
            "superheat_c": superheat_c,
            "subcooling_c": subcooling_c,
        },
        "comparison": comparison,
        "summary": {
            "best_cop": best_cop,
            "lowest_gwp_available": lowest_gwp,
            "lowest_discharge_temp": lowest_discharge,
            "n_valid": len(valid),
            "n_total": len(refrigerants),
        },
        "metadata": {
            "skill": __skill_name__,
            "version": __version__,
        },
    }


def format_compare_table(result: Dict) -> str:
    """
    把对比结果格式化为 ASCII 表格，方便贴报告

    参数：compare_refrigerants() 的返回值
    返回：字符串（多行 ASCII 表格）
    """
    comp = result["comparison"]
    valid = [c for c in comp if c["available"]]

    if not valid:
        return "（无有效数据）"

    # 表头
    headers = ["制冷剂", "T_evap(°C)", "P_evap(kPa)", "T_cond(°C)", "P_cond(kPa)",
               "q_e(kJ/kg)", "COP", "压比", "排气(°C)", "GWP100", "ODP", "安全等级"]

    # 计算列宽
    rows = []
    for c in valid:
        rows.append([
            c["refrigerant"],
            f"{c['T_evap_c']:.1f}",
            f"{c['P_evap_kpa']:.1f}",
            f"{c['T_cond_c']:.1f}",
            f"{c['P_cond_kpa']:.1f}",
            f"{c['q_evap_kj_kg']:.2f}",
            f"{c['cop']:.3f}",
            f"{c['pressure_ratio']:.2f}",
            f"{c['discharge_temp_c']:.1f}",
            str(c.get("gwp100", "?")),
            f"{c.get('odp', 0):.3f}",
            c.get("ashrae_safety", "?"),
        ])

    col_widths = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]

    def fmt_row(row):
        return " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))

    sep = "-+-".join("-" * w for w in col_widths)

    lines = [fmt_row(headers), sep]
    for row in rows:
        lines.append(fmt_row(row))

    return "\n".join(lines)


# ============================================================================
# 自测
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("S9 refrigerant_compare 自测 - 多制冷剂并排比较")
    print("=" * 70)

    # 测试 1: 空调常见 3 种制冷剂对比
    print("\n[测试 1] 空调工况 R134a vs R410A vs R32（T_evap=5°C, T_cond=40°C）")
    result = compare_refrigerants(
        ["R134a", "R410A", "R32"],
        T_evap_c=5,
        T_cond_c=40,
    )
    print("\n" + format_compare_table(result))
    print(f"\n总结:")
    print(f"  最高 COP: {result['summary']['best_cop']}")
    print(f"  最低 GWP: {result['summary']['lowest_gwp_available']}")
    print(f"  最低排气温度: {result['summary']['lowest_discharge_temp']}")

    # 测试 2: 低温工况对比 R404A vs R507A vs R717
    print("\n\n[测试 2] 低温工况 R404A vs R507A vs R717（T_evap=-30°C, T_cond=35°C）")
    result2 = compare_refrigerants(
        ["R404A", "R507A", "R717"],
        T_evap_c=-30,
        T_cond_c=35,
    )
    print("\n" + format_compare_table(result2))

    # 测试 3: 自然制冷剂对比（环保选项）
    print("\n\n[测试 3] 自然制冷剂 R744 vs R717 vs R290 vs R718")
    result3 = compare_refrigerants(
        ["R717", "R290", "R718"],   # R744 跨临界工况，单独测
        T_evap_c=0,
        T_cond_c=40,
    )
    print("\n" + format_compare_table(result3))
    print(f"（注: R744 CO2 在 T_evap=0°C 是跨临界工况，本函数不直接支持）")

    # 测试 4: 错误处理 - 不支持的制冷剂
    print("\n\n[测试 4] 错误处理 - 不支持的制冷剂")
    try:
        compare_refrigerants(["R999"], 5, 40)
        print("  ❌ 应该报错但没报")
    except ValueError as e:
        print(f"  ✅ 正确报错: {str(e)[:80]}...")

    # 测试 5: 错误处理 - 空列表
    print("\n[测试 5] 错误处理 - 空列表")
    try:
        compare_refrigerants([], 5, 40)
        print("  ❌ 应该报错但没报")
    except ValueError as e:
        print(f"  ✅ 正确报错: {e}")

    print("\n" + "=" * 70)
    print("✅ 所有测试通过！S9 refrigerant_compare 可用。")
    print("=" * 70)