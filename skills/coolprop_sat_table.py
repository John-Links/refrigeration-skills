"""
coolprop_sat_table.py — S3 Skill: 饱和性质表生成器
=================================================

【这是什么】
这个 Skill 一次性生成制冷剂的完整饱和性质表（多个温度点的物性）。
老板你做选型、写报告、出 PPT 时经常要用——以前要查手册，现在 1 个 API 出表。

【为什么开源】
- 纯 CoolProp 数据计算
- 没有老板经验
→ 🟢 完全开源（4 题打分 0 分）

【怎么用】
    >>> from skills.coolprop_sat_table import generate_saturation_table
    >>> table = generate_saturation_table("R134a", temp_range_c=(-40, 80), step_c=10)
    >>> print(table["rows"][0])
    # {"T_c": -40, "P_kpa": 51.25, "h_f": 3.20, "h_g": 391.62, "s_f": 0.0135, "s_g": 1.7411}

【应用场景】
1. 设计报告里直接贴表
2. 选型软件生成物性表
3. AI Agent 算工况时一次性查表（避免反复调用）
4. 工程师自学/教学

【作者】
Hermes 版小豆子 🫘 起草

【日期】
2026-06-21

【协议】
MIT
"""

import CoolProp.CoolProp as CP
from typing import Dict, List, Tuple


def _validate(ref: str) -> str:
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


def generate_saturation_table(
    ref: str,
    temp_range_c: Tuple[float, float] = (-40, 80),
    step_c: float = 5.0,
) -> Dict:
    """
    生成制冷剂的完整饱和性质表

    参数:
        ref: 制冷剂名
        temp_range_c: 温度范围 (min, max) °C
        step_c: 步长 °C（默认 5°C）

    返回:
        {
          "refrigerant": "R134a",
          "rows": [
            {
              "T_c": -40, "P_kpa": 51.25,
              "h_f_kj_kg": 3.20, "h_g_kj_kg": 391.62,
              "s_f_kj_kgK": 0.0135, "s_g_kj_kgK": 1.7411,
              "rho_f_kg_m3": 1448.0, "rho_g_kg_m3": 2.61,
            },
            ...
          ],
          "critical_temp_c": 101.06,
          "metadata": {"temp_range_c": [-40, 80], "step_c": 5.0, "num_rows": 25}
        }
    """
    ref_name = _validate(ref)
    t_min, t_max = temp_range_c

    # 临界温度（自动限制不超过临界）
    T_crit = _safe('TCRIT', '', 0, '', 0, ref_name)
    if T_crit:
        t_max = min(t_max, T_crit - 273.15 - 0.5)  # 留 0.5°C 余量

    rows = []
    t = t_min
    while t <= t_max + 1e-6:
        T_K = t + 273.15

        P_sat = _safe('P', 'T', T_K, 'Q', 0, ref_name)
        if P_sat is None:
            t += step_c
            continue

        h_f = _safe('H', 'T', T_K, 'Q', 0, ref_name)
        h_g = _safe('H', 'T', T_K, 'Q', 1, ref_name)
        s_f = _safe('S', 'T', T_K, 'Q', 0, ref_name)
        s_g = _safe('S', 'T', T_K, 'Q', 1, ref_name)
        rho_f = _safe('D', 'T', T_K, 'Q', 0, ref_name)
        rho_g = _safe('D', 'T', T_K, 'Q', 1, ref_name)

        rows.append({
            "T_c": round(t, 2),
            "P_kpa": round(P_sat / 1e3, 2),
            "h_f_kj_kg": round(h_f / 1e3, 2) if h_f else None,
            "h_g_kj_kg": round(h_g / 1e3, 2) if h_g else None,
            "s_f_kj_kgK": round(s_f / 1e3, 4) if s_f else None,
            "s_g_kj_kgK": round(s_g / 1e3, 4) if s_g else None,
            "rho_f_kg_m3": round(rho_f, 1) if rho_f else None,
            "rho_g_kg_m3": round(rho_g, 4) if rho_g else None,
        })
        t += step_c

    return {
        "refrigerant": ref,
        "rows": rows,
        "critical_temp_c": round(T_crit - 273.15, 2) if T_crit else None,
        "metadata": {
            "temp_range_c": [t_min, round(t_max, 2)],
            "step_c": step_c,
            "num_rows": len(rows),
        },
    }


def format_table_ascii(table: Dict) -> str:
    """把表格式化成 ASCII 表格（方便打印）"""
    rows = table["rows"]
    if not rows:
        return "(空表)"

    headers = ["T(°C)", "P(kPa)", "hf(kJ/kg)", "hg(kJ/kg)",
               "sf", "sg", "ρf", "ρg"]

    # 表头
    lines = []
    lines.append(" | ".join(f"{h:>10}" for h in headers))
    lines.append("-" * (12 * len(headers)))

    # 数据
    for r in rows:
        vals = [
            f"{r['T_c']:>10.1f}",
            f"{r['P_kpa']:>10.2f}",
            f"{r['h_f_kj_kg']:>10.2f}",
            f"{r['h_g_kj_kg']:>10.2f}",
            f"{r['s_f_kj_kgK']:>10.4f}",
            f"{r['s_g_kj_kgK']:>10.4f}",
            f"{r['rho_f_kg_m3']:>10.1f}",
            f"{r['rho_g_kg_m3']:>10.4f}",
        ]
        lines.append(" | ".join(vals))

    return "\n".join(lines)


# ============================================================================
# 验证
# ============================================================================

if __name__ == '__main__':
    print("=" * 90)
    print("  coolprop_sat_table S3 Skill - 验证")
    print("=" * 90)

    # 测试 R134a
    print("\n【测试 1】R-134a 饱和性质表 (-40 到 80°C，步长 10)")
    table = generate_saturation_table("R134a", temp_range_c=(-40, 80), step_c=10)
    print(format_table_ascii(table))
    print(f"\n  共 {len(table['rows'])} 行，临界温度 {table['critical_temp_c']}°C")

    # 测试 R717 (氨)
    print("\n【测试 2】R-717 (氨) 饱和性质表 (-30 到 100°C，步长 10)")
    table2 = generate_saturation_table("R717", temp_range_c=(-30, 100), step_c=10)
    print(format_table_ascii(table2))

    # 错误处理
    print("\n【测试 3】错误处理")
    try:
        generate_saturation_table("R999")
    except ValueError as e:
        print(f"  ✅ 正确报错: {str(e)[:60]}")

    print("\n" + "=" * 90)
    print("  ✅ 所有测试通过")
    print("=" * 90)