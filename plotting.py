import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os
from .loader import get_data_mine, get_data_truck, MineParam, TruckParam, truck_file_name
from datetime import datetime
from matplotlib.lines import Line2D

POWER_KEYS = ["P_ec", "P_ce", "P_ed", "P_de"]

TECH_COLORS = {
    "diesel":   "#0072B2",  # blue
    "battery":  "#009E73",  # bluish green
    "hydrogen": "#D55E00",  # vermillion
    "trolley":  "#CC79A7",  # reddish purple
}

KEY_TITLES = {
    "cost_specific_USD_tkm":  "Specific costs [USD/t·km]",
    "cost_specific_USD_t":    "Specific costs [USD/t]",
    "cost_annual_USD":        "Annual costs [USD/a]",
    "E_specific_kWh_tkm":     "Specific energy [kWh/t·km]",
    "E_specific_kWh_t":       "Specific energy [kWh/t]",
    "E_annual_GWh":           "Annual energy [GWh/a]",
}

def pretty_metric_name(key: str) -> str:
    return KEY_TITLES.get(key, key)

def plot_power_per_mine(mine_base, mine_name, plot1_data):
    """
    For each power key:
    - light vertical line from 0 to progressive value
    - dark vertical line from 0 to conservative value
    Similar style to relative comparison plots.
    """
    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, 'figures')
    os.makedirs(folder_path, exist_ok=True)

    technologies = ["diesel", "battery", "hydrogen", "trolley"]
    step         = 0.8
    group_gap    = 1.8
    line_dx      = 0.08   # horizontal offset between prog and cons

    fig, ax = plt.subplots(figsize=(16, 6))

    x_positions = []
    x_labels    = []
    x_offset    = 0

    for tech in technologies:
        for key in POWER_KEYS:
            low   = plot1_data[tech][key]["low"]  / 1e6   # progressive
            high  = plot1_data[tech][key]["high"] / 1e6   # conservative
            color = TECH_COLORS[tech]

            x_prog = x_offset - line_dx
            x_cons = x_offset + line_dx

            # progressive = light line from 0 to low
            ax.vlines(
                x=x_prog,
                ymin=0,
                ymax=low,
                colors=color,
                linewidth=2.5,
                alpha=0.35,
            )
            ax.plot(
                x_prog, low,
                marker="_",
                markersize=16,
                markeredgewidth=2.0,
                color=color,
                alpha=0.35,
                linestyle="None",
            )

            # conservative = dark line from 0 to high
            ax.vlines(
                x=x_cons,
                ymin=0,
                ymax=high,
                colors=color,
                linewidth=3.0,
                alpha=0.95,
            )
            ax.plot(
                x_cons, high,
                marker="_",
                markersize=16,
                markeredgewidth=2.2,
                color=color,
                alpha=0.95,
                linestyle="None",
            )

            x_positions.append(x_offset)
            x_labels.append(key)
            x_offset += step

        x_offset += group_gap

    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Power [MW]")
    ax.set_title(
        f"Power Requirements – {mine_name}\n"
        f"(light line = progressive, dark line = conservative)"
    )

    all_vals = []
    for tech in technologies:
        for key in POWER_KEYS:
            low  = plot1_data[tech][key]["low"] / 1e6
            high = plot1_data[tech][key]["high"] / 1e6
            all_vals.extend([low, high])

    if all_vals:
        vmin = min(all_vals)
        vmax = max(all_vals)
        span = vmax - vmin if vmax != vmin else max(abs(vmax), 1.0)
        padding = 0.1 * span
        ymin = min(0.0, vmin - padding)
        ymax = vmax + padding
        ax.set_ylim(ymin, ymax)

    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.axhline(0, color="black", linewidth=0.8)

    legend_elements = [
        mpatches.Patch(facecolor=TECH_COLORS["diesel"],   alpha=0.8, label="Diesel"),
        mpatches.Patch(facecolor=TECH_COLORS["battery"],  alpha=0.8, label="Battery"),
        mpatches.Patch(facecolor=TECH_COLORS["hydrogen"], alpha=0.8, label="Hydrogen"),
        mpatches.Patch(facecolor=TECH_COLORS["trolley"],  alpha=0.8, label="Trolley"),
        Line2D([0], [0], color="black", linewidth=2.5, alpha=0.35, label="Progressive"),
        Line2D([0], [0], color="black", linewidth=3.0, alpha=0.95, label="Conservative"),
    ]
    ax.legend(handles=legend_elements, fontsize=7, ncol=2)

    group_centers = []
    x_offset = 0
    for tech in technologies:
        start  = x_offset
        x_offset += len(POWER_KEYS) * step
        center = start + (len(POWER_KEYS) - 1) * step / 2
        group_centers.append(center)
        x_offset += group_gap

    y_top = ax.get_ylim()[1]
    for i, tech in enumerate(technologies):
        ax.text(
            group_centers[i], y_top * 0.97,
            tech.upper(),
            ha="center", va="top", fontsize=9, fontweight="bold",
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_path, f'power_per_mine_{mine_base}_{timestamp}.png')

    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    plt.show()
    plt.close()


def plot_mine_comparison(all_mines_data, mine_name_map, compare_key="P_max"):
    """
    Comparison of all mines for a selected parameter (default: P_max).
    x-axis: mines (display names from config), per mine 4 lines (Diesel, Battery, H2, Trolley).
    Each key: light vertical line from 0 to progressive, dark line from 0 to conservative.
    """
    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, 'figures')
    os.makedirs(folder_path, exist_ok=True)

    technologies  = ["diesel", "battery", "hydrogen", "trolley"]
    mine_keys     = list(all_mines_data.keys())
    display_names = [mine_name_map.get(m, m) for m in mine_keys]
    n_mines       = len(mine_keys)

    group_spacing = 1.5
    step          = 0.28   # Abstand zwischen Technologien innerhalb einer Mine
    line_dx       = 0.04   # Versatz zwischen prog- und cons-Linie
    offsets = {
        "diesel":   -1.5 * step,
        "battery":  -0.5 * step,
        "hydrogen":  0.5 * step,
        "trolley":   1.5 * step,
    }

    index = np.arange(n_mines) * group_spacing

    fig, ax = plt.subplots(figsize=(12, 6))

    for tech in technologies:
        color = TECH_COLORS[tech]

        lows  = np.array(
            [all_mines_data[m][tech][compare_key]["low"]  for m in mine_keys],
            dtype=float
        ) / 1e6
        highs = np.array(
            [all_mines_data[m][tech][compare_key]["high"] for m in mine_keys],
            dtype=float
        ) / 1e6

        x_prog = index + offsets[tech] - line_dx
        x_cons = index + offsets[tech] + line_dx

        # progressive: helle Linie von 0 bis low
        ax.vlines(
            x=x_prog,
            ymin=0,
            ymax=lows,
            colors=color,
            linewidth=2.5,
            alpha=0.35,
        )
        ax.plot(
            x_prog, lows,
            marker="_",
            markersize=16,
            markeredgewidth=2.0,
            color=color,
            alpha=0.35,
            linestyle="None",
        )

        # conservative: dunkle Linie von 0 bis high
        ax.vlines(
            x=x_cons,
            ymin=0,
            ymax=highs,
            colors=color,
            linewidth=3.0,
            alpha=0.95,
        )
        ax.plot(
            x_cons, highs,
            marker="_",
            markersize=16,
            markeredgewidth=2.2,
            color=color,
            alpha=0.95,
            linestyle="None",
        )

    ax.set_xticks(index)
    ax.set_xticklabels(display_names, rotation=15, ha="right")
    ax.set_xlabel("Mines")
    ax.set_ylabel(f"{compare_key} [MW]")
    ax.set_title(
        f"Mine Comparison – {compare_key}\n"
        f"(light line = progressive, dark line = conservative)"
    )
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.axhline(0, color="black", linewidth=0.8)

    legend_elements = [
        mpatches.Patch(facecolor=TECH_COLORS["diesel"],   alpha=0.8, label="Diesel"),
        mpatches.Patch(facecolor=TECH_COLORS["battery"],  alpha=0.8, label="Battery"),
        mpatches.Patch(facecolor=TECH_COLORS["hydrogen"], alpha=0.8, label="Hydrogen"),
        mpatches.Patch(facecolor=TECH_COLORS["trolley"],  alpha=0.8, label="Trolley"),
        Line2D([0], [0], color="black", linewidth=2.5, alpha=0.35, label="Progressive"),
        Line2D([0], [0], color="black", linewidth=3.0, alpha=0.95, label="Conservative"),
    ]
    ax.legend(handles=legend_elements, fontsize=7, ncol=2)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_path, f'mine_comparison_{compare_key}_{timestamp}.png')
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    plt.show()
    plt.close()


def plot_base_mine_comparison(config):
    """
    Compares base data of all four reference mines across four metrics:
      1. Annual material throughput [Mt/a]
      2. Strip ratio [-]
      3. Maximum pit depth [m]
      4. Average gradients E→Crusher and E→Dump [°]

    One separate figure per metric.
    Progressive value = solid bar (bottom), conservative = range (light, top).
    Mine names are read from config["scenarios"].
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, "figures")
    os.makedirs(folder_path, exist_ok=True)

    # ── 1. Collect data from YAMLs ────────────────────────────────────────────
    mine_names  = []
    throughput  = {"con": [], "prog": []}
    strip_ratio = {"con": [], "prog": []}
    pit_depth   = {"con": [], "prog": []}
    grad_ec     = {"con": [], "prog": []}
    #grad_ed     = {"con": [], "prog": []}

    for entry in config["scenarios"]:
        mine_base = entry["mine"]
        mine_name = entry.get("name", mine_base)
        mine_names.append(mine_name)

        con  = get_data_mine(f"{mine_base}_conservative")
        prog = get_data_mine(f"{mine_base}_progressive")

        throughput["con"].append( con[MineParam.ORE_THROUGHPUT]  / 1e6)
        throughput["prog"].append(prog[MineParam.ORE_THROUGHPUT] / 1e6)

        strip_ratio["con"].append( con[MineParam.STRIP_RATIO])
        strip_ratio["prog"].append(prog[MineParam.STRIP_RATIO])

        pit_depth["con"].append( con[MineParam.MAX_MINE_DEPTH])
        pit_depth["prog"].append(prog[MineParam.MAX_MINE_DEPTH])

        grad_ec["con"].append( con[MineParam.GRAD_DEG_EC])
        grad_ec["prog"].append(prog[MineParam.GRAD_DEG_EC])

    # ── 2. Helper: single grouped bar plot ────────────────────────────────────
    MINE_COLOR = "#4c72b0"

    def _plot_metric(prog_vals, con_vals, title, ylabel, filename):
        n     = len(mine_names)
        index = np.arange(n)
        width = 0.45

        fig, ax = plt.subplots(figsize=(10, 5))

        prog_arr = np.array(prog_vals, dtype=float)
        con_arr  = np.array(con_vals,  dtype=float)

        ax.bar(index, prog_arr, width,
               color=MINE_COLOR, alpha=0.9,
               label="Progressive scenario")
        ax.bar(index, con_arr - prog_arr, width,
               bottom=prog_arr,
               color=MINE_COLOR, alpha=0.35,
               label="Conservative range")

        ax.set_xticks(index)
        ax.set_xticklabels(mine_names, rotation=15, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.legend(fontsize=8)

        fig.tight_layout()
        path = os.path.join(folder_path, filename)
        plt.savefig(path, dpi=300, bbox_inches="tight")
        plt.show()
        plt.close()
        print(f"  → Saved: {path}")

    # ── 3. Metric plots ───────────────────────────────────────────────────────
    _plot_metric(
        throughput["prog"], throughput["con"],
        title="Annual Material Throughput – Reference Mines",
        ylabel="Ore throughput [Mt/a]",
        filename=f"base_throughput_{timestamp}.png",
    )
    _plot_metric(
        strip_ratio["prog"], strip_ratio["con"],
        title="Strip Ratio – Reference Mines",
        ylabel="Strip ratio [-]",
        filename=f"base_strip_ratio_{timestamp}.png",
    )
    _plot_metric(
        pit_depth["prog"], pit_depth["con"],
        title="Maximum Pit Depth – Reference Mines",
        ylabel="Max. pit depth [m]",
        filename=f"base_pit_depth_{timestamp}.png",
    )

    # ── 4. Gradients: two routes per mine, side-by-side ───────────────────────
    DUMP_COLOR = "#55a868"
    n     = len(mine_names)
    index = np.arange(n)
    width = 0.45

    fig, ax = plt.subplots(figsize=(10, 5))

    ec_prog = np.array(grad_ec["prog"], dtype=float)
    ec_con  = np.array(grad_ec["con"],  dtype=float)


    # Progressive bars (solid)
    ax.bar(index, ec_prog, width,
           color=MINE_COLOR,  alpha=0.9, label="E→Crusher progressive")

    # Conservative range (light, stacked on top)
    ax.bar(index, ec_con - ec_prog, width,
           bottom=ec_prog,
           color=MINE_COLOR,  alpha=0.35, label="E→Crusher range")


    ax.set_xticks(index)
    ax.set_xticklabels(mine_names, rotation=0, ha="center", fontsize=10)
    ax.set_ylabel("Average gradient [°]", fontsize=10)
    ax.set_ylim(0, max(ec_con) * 1.20)
    ax.set_title(
        "Average Haul Road Gradients – Reference Mines\n"
        "(solid = progressive, light = conservative range)", fontsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend(fontsize=8)

    fig.tight_layout()
    path = os.path.join(folder_path, "base_gradients.png")
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.show()
    plt.close()
    print(f"  → Saved: {path}")

def plot_energy_per_mine(mine_base, mine_name, plot1_data, h2_as_electricity=False):
    """
    3 Subplots pro Mine:
    - Links:   E_annual [GWh/a]
    - Mitte:   E_specific [kWh/t]
    - Rechts:  E_specific_tkm [kWh/(t·km)]

    h2_as_electricity=False  → H2-Balken zeigen Wasserstoff-Energieinhalt (Standard-Plot)
    h2_as_electricity=True   → H2-Balken zeigen äquivalenten Strombedarf inkl. Elektrolyse
    """
    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, 'figures')
    os.makedirs(folder_path, exist_ok=True)

    technologies = ["diesel", "battery", "hydrogen", "trolley"]
    bar_width    = 0.5
    index        = np.arange(len(technologies))

    keys_labels = [
        ("E_annual_GWh",       "Annual Energy [GWh/a]",         "Total Annual Energy"),
        ("E_specific_kWh_t",   "Specific Energy [kWh/t]",       "Specific Energy per Tonne Ore"),
        ("E_specific_kWh_tkm", "Specific Energy [kWh/(t·km)]",  "Specific Energy per Tonne Ore·km"),
    ]

    data_key  = "energy_elec_view" if h2_as_electricity else "energy"
    h2_label  = "H₂: electricity demand incl. electrolysis" if h2_as_electricity \
                else "H₂: hydrogen energy content"
    file_tag  = "elec_view" if h2_as_electricity else "h2_basis"

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle(
        f"Annual Energy – {mine_name}\n"
        f"(solid = progressive, light = conservative range | {h2_label})"
    )

    for ax, (key, ylabel, title) in zip(axes, keys_labels):
        for i, tech in enumerate(technologies):
            color = TECH_COLORS[tech]
            low   = plot1_data[tech][data_key][key]["low"]
            high  = plot1_data[tech][data_key][key]["high"]

            ax.bar(i, low, bar_width,
                   color=color, alpha=0.9, edgecolor="none", linewidth=0)
            ax.bar(i, high - low, bar_width, bottom=low,
                   color=color, alpha=0.35, edgecolor="none", linewidth=0)

        ax.set_xticks(index)
        ax.set_xticklabels([t.capitalize() for t in technologies])
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.axhline(0, color="black", linewidth=0.8)

    handles = [
        mpatches.Patch(color=TECH_COLORS[t], alpha=0.9,  label=f"{t.capitalize()} – progressive")
        for t in technologies
    ] + [
        mpatches.Patch(facecolor=TECH_COLORS[t], alpha=0.35, label=f"{t.capitalize()} – range")
        for t in technologies
    ]
    axes[1].legend(handles=handles, fontsize=7, ncol=2, loc="upper right")

    fig.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(
        folder_path,
        f'energy_per_mine_{mine_base}_{file_tag}_{timestamp}.png'
    )
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    plt.show()
    plt.close()


def plot_energy_mine_comparison(all_mines_data, mine_name_map, key="E_annual_GWh"):
    """
    Minenvergleich für Energiekennzahlen.
    Analog zu plot_mine_comparison().
    """
    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, 'figures')
    os.makedirs(folder_path, exist_ok=True)

    technologies  = ["diesel", "battery", "hydrogen", "trolley"]
    mine_keys     = list(all_mines_data.keys())
    display_names = [mine_name_map.get(m, m) for m in mine_keys]
    n_mines       = len(mine_keys)
    group_spacing = 1.2
    index         = np.arange(n_mines) * group_spacing
    bar_width     = 0.25
    offsets = {
    "diesel":   -1.5 * bar_width,
    "battery":  -0.5 * bar_width,
    "hydrogen":  0.5 * bar_width,
    "trolley":   1.5 * bar_width,
    }


    ylabel_map = {
        "E_annual_GWh":    "Annual Energy [GWh/a]",
        "E_specific_kWh_t": "Specific Energy [kWh/t ore]",
        "E_specific_kWh_tkm": "Specific Energy [kWh/(t ore·km)]",
    }

    fig, ax = plt.subplots(figsize=(12, 6))

    for tech in technologies:
        color = TECH_COLORS[tech]
        lows  = np.array(
            [all_mines_data[m][tech]["energy"][key]["low"]  for m in mine_keys],
            dtype=float)
        highs = np.array(
            [all_mines_data[m][tech]["energy"][key]["high"] for m in mine_keys],
            dtype=float)

        ax.bar(index + offsets[tech], lows, bar_width,
               color=color, alpha=0.9, label=f"{tech.capitalize()} – progressive")
        ax.bar(index + offsets[tech], highs - lows, bar_width,
               bottom=lows, color=color, alpha=0.35,
               label=f"{tech.capitalize()} – range")

    ax.set_xticks(index)
    #ax.set_xlim(-0.5, index[-1] + 0.5)   
    ax.set_xticklabels(display_names, rotation=15, ha="right")
    ax.set_xlabel("Mines")
    ax.set_ylabel(ylabel_map.get(key, key))
    metric_label = pretty_metric_name(key)
    
    ax.set_title(f"Mine Comparison – {metric_label}\n"
                 f"(solid = progressive, light = conservative range)")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend(fontsize=7, ncol=2)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_path, f'energy_comparison_{key}_{timestamp}.png')
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    plt.show()
    plt.close()

def plot_h2_breakdown_per_mine(mine_base, mine_name, plot1_data):
    """
    Stacked Bar Chart per Mine:
    shows yearly energy for H2 - trucks. differenciates between:
    - FC-share (direct H2-energy)
    - share that directly comes from battery
    - electricity that comes on top for electrolysis

    for comparison: BEV - and diesel - total energies as a bar next to the H2-bars.
    """
    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, 'figures')
    os.makedirs(folder_path, exist_ok=True)

    technologies = ["diesel", "battery", "hydrogen"]
    scenarios    = ["low", "high"]   # low=progressive, high=conservative
    bar_width    = 0.35
    index        = np.arange(len(technologies))

    # colours for stacked H2-shares
    COLOR_H2_FC      = "#D55E00"  # red: H2- engine
    COLOR_H2_BAT     = "#F4C7B5"   # light red: direct battery share
    COLOR_H2_ELECTRO = "#962A00"   # dark red: extra electricity for electrolysis
    COLOR_BEV        = "#009E73"
    COLOR_DIESEL     = "#0072B2"

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=False)
    fig.suptitle(
        f"H2 Energy Breakdown – {mine_name}\n"
        f"(left: energy through motors | right: total electricity incl. electrolysis)"
    )

    for ax_idx, scenario in enumerate(scenarios):
        ax    = axes[ax_idx]
        label = "Progressive" if scenario == "low" else "Conservative"
        ax.set_title(f"{label} Scenario")

        for i, tech in enumerate(technologies):
            energy = plot1_data[tech]["energy"]

            if tech == "diesel":
                val = energy["E_annual_GWh"][scenario]
                ax.bar(i, val, bar_width, color=COLOR_DIESEL, alpha=0.9,
                       label="Diesel – fuel energy" if ax_idx == 0 else "")

            elif tech == "battery":
                val = energy["E_annual_GWh"][scenario]
                ax.bar(i, val, bar_width, color=COLOR_BEV, alpha=0.9,
                       label="BEV – electricity" if ax_idx == 0 else "")

            elif tech == "hydrogen":
                h2 = plot1_data[tech]["h2_breakdown"][scenario]

                if ax_idx == 0:
                    # Linker Plot: Energie durch Motoren
                    # FC-Anteil (H2)
                    ax.bar(i, h2["E_h2_drive_GWh"], bar_width,
                           color=COLOR_H2_FC, alpha=0.9,
                           label="H2 – FC drive energy" if ax_idx == 0 else "")
                    # Batterie-Direktanteil
                    ax.bar(i, h2["E_elec_direct_GWh"], bar_width,
                           bottom=h2["E_h2_drive_GWh"],
                           color=COLOR_H2_BAT, alpha=0.9,
                           label="H2 – battery direct" if ax_idx == 0 else "")
                else:
                    # Rechter Plot: Gesamtstrom inkl. Elektrolyse
                    ax.bar(i, h2["E_elec_direct_GWh"], bar_width,
                           color=COLOR_H2_BAT, alpha=0.9,
                           label="H2 – battery direct" if ax_idx == 1 else "")
                    ax.bar(i, h2["E_elec_for_h2_GWh"], bar_width,
                           bottom=h2["E_elec_direct_GWh"],
                           color=COLOR_H2_ELECTRO, alpha=0.9,
                           label="H2 – electrolysis electricity" if ax_idx == 1 else "")

                    # BEV zum Vergleich (Linie)
                    bev_val = plot1_data["battery"]["energy"]["E_annual_GWh"][scenario]
                    ax.axhline(bev_val, color=COLOR_BEV, linewidth=1.5,
                               linestyle="--", alpha=0.8,
                               label="BEV electricity (reference)" if ax_idx == 1 else "")

        ax.set_xticks(index)
        ax.set_xticklabels([t.capitalize() for t in technologies])
        ax.set_ylabel("Energy [GWh/a]")
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.axhline(0, color="black", linewidth=0.8)

    legend_elements = [
        mpatches.Patch(facecolor=COLOR_DIESEL, alpha=0.9, label="Diesel – fuel energy"),
        mpatches.Patch(facecolor=COLOR_BEV, alpha=0.9, label="BEV – electricity"),
        mpatches.Patch(facecolor=COLOR_H2_FC, alpha=0.9, label="H2 – FC drive energy"),
        mpatches.Patch(facecolor=COLOR_H2_BAT, alpha=0.9, label="H2 – battery direct"),
        mpatches.Patch(facecolor=COLOR_H2_ELECTRO, alpha=0.9, label="H2 – electrolysis electricity"),
        plt.Line2D([0], [0], color=COLOR_BEV, linewidth=1.5, linestyle="--",
                   label="BEV electricity (reference)"),
    ]

    fig.legend(
        handles=legend_elements,
        fontsize=7,
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.88)
    )

    fig.tight_layout(rect=[0, 0, 1, 0.9])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_path, f'h2_breakdown_{mine_base}_{timestamp}.png')
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    plt.show()
    plt.close()


def plot_h2_breakdown_mine_comparison(all_mines_data, mine_name_map):
    """
    Comparison of all the mines: total energy demand (inkl. Electrolysis for H2) vs BEV-electricity-demand
    Vergleich aller Minen: Gesamtstrom-Bedarf (inkl. Elektrolyse) für H2
    vs. BEV-Strombedarf
    """
    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, 'figures')
    os.makedirs(folder_path, exist_ok=True)

    mine_keys     = list(all_mines_data.keys())
    display_names = [mine_name_map.get(m, m) for m in mine_keys]
    n_mines       = len(mine_keys)
    index         = np.arange(n_mines)
    bar_width     = 0.3

    COLOR_H2_FC      = "#D55E00"
    COLOR_H2_ELECTRO = "#962A00"
    COLOR_H2_BAT     = "#F4C7B5"
    COLOR_BEV        = "#009E73"

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(
        "Mine Comparison – H2 Energy Breakdown vs. BEV\n"
        "(left: progressive | right: conservative)"
    )

    for ax_idx, scenario in enumerate(["low", "high"]):
        ax    = axes[ax_idx]
        label = "Progressive" if scenario == "low" else "Conservative"
        ax.set_title(label)

        bev_vals = np.array(
            [all_mines_data[m]["battery"]["energy"]["E_annual_GWh"][scenario]
             for m in mine_keys], dtype=float)

        h2_fc    = np.array(
            [all_mines_data[m]["hydrogen"]["h2_breakdown"][scenario]["E_h2_drive_GWh"]
             for m in mine_keys], dtype=float)
        h2_bat   = np.array(
            [all_mines_data[m]["hydrogen"]["h2_breakdown"][scenario]["E_elec_direct_GWh"]
             for m in mine_keys], dtype=float)
        h2_el    = np.array(
            [all_mines_data[m]["hydrogen"]["h2_breakdown"][scenario]["E_elec_for_h2_GWh"]
             for m in mine_keys], dtype=float)

        # BEV-Balken
        ax.bar(index - bar_width / 2, bev_vals, bar_width,
               color=COLOR_BEV, alpha=0.9, label="BEV – electricity")

        # H2-Balken gestackt: FC + Batterie + Elektrolyse
        ax.bar(index + bar_width / 2, h2_fc, bar_width,
               color=COLOR_H2_FC, alpha=0.9, label="H2 – FC drive energy")
        ax.bar(index + bar_width / 2, h2_bat, bar_width,
               bottom=h2_fc, color=COLOR_H2_BAT, alpha=0.9,
               label="H2 – battery direct")
        ax.bar(index + bar_width / 2, h2_el, bar_width,
               bottom=h2_fc + h2_bat, color=COLOR_H2_ELECTRO, alpha=0.9,
               label="H2 – electrolysis electricity")

        ax.set_xticks(index)
        ax.set_xticklabels(display_names, rotation=15, ha="right")
        ax.set_ylabel("Energy [GWh/a]")
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.legend(fontsize=7)

    fig.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_path, f'h2_breakdown_comparison_{timestamp}.png')
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    plt.show()
    plt.close()


def plot_cost_per_mine(mine_base, mine_name, plot1_data):
    """
    3 Subplots pro Mine:
    - Left side:  cost_annual_USD [M$/a]
    - Middle: cost_specific_USD_t [$/t Ore]
    - Rechts: cost_specific_USD_tkm [$/t·km] 
    """
    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, 'figures')
    os.makedirs(folder_path, exist_ok=True)

    technologies = ["diesel", "battery", "hydrogen", "trolley"]
    bar_width    = 0.5
    index        = np.arange(len(technologies))

    keys_labels = [
        ("cost_annual_USD",      "Annual Cost [M$/a]",         1e6,  "Total Annual Cost"),
        ("cost_specific_USD_t",  "Specific Cost [$/t ore]",    1.0,  "Cost per Tonne Ore"),
        ("cost_specific_USD_tkm","Specific Cost [$/t·km]",     1.0,  "Cost per Tonne Ore·km"),
    ]
    
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle(
        f"Annual Energy Costs – {mine_name}\n"
        f"(solid = progressive, light = conservative range)"
    )

    for ax, (key, ylabel, scale, title) in zip(axes, keys_labels):
        for i, tech in enumerate(technologies):
            low   = plot1_data[tech]["cost"][key]["low"]  / scale
            high  = plot1_data[tech]["cost"][key]["high"] / scale
            color = TECH_COLORS[tech]

            ax.bar(i, low, bar_width,
                   color=color, alpha=0.9,
                   edgecolor="none", linewidth=0)
            ax.bar(i, high - low, bar_width,
                   bottom=low,
                   color=color, alpha=0.35,
                   edgecolor="none", linewidth=0)

        ax.set_xticks(index)
        ax.set_xticklabels([t.capitalize() for t in technologies])
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.axhline(0, color="black", linewidth=0.8)

    legend_elements = [
        mpatches.Patch(facecolor=TECH_COLORS[t], alpha=0.9,
                       label=f"{t.capitalize()} – progressive")
        for t in technologies
    ] + [
        mpatches.Patch(facecolor=TECH_COLORS[t], alpha=0.35,
                       label=f"{t.capitalize()} – range")
        for t in technologies
    ]
    axes[1].legend(handles=legend_elements, fontsize=7, ncol=2)

    fig.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_path, f'cost_per_mine_{mine_base}_{timestamp}.png')
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    plt.show()
    plt.close()


def plot_cost_mine_comparison(all_mines_data, mine_name_map, key="cost_specific_USD_t"):
    """
    Mine comparison for cost comparison
    Analog zu plot_energy_mine_comparison().
    """
    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, 'figures')
    os.makedirs(folder_path, exist_ok=True)

    technologies  = ["diesel", "battery", "hydrogen", "trolley"]
    mine_keys     = list(all_mines_data.keys())
    display_names = [mine_name_map.get(m, m) for m in mine_keys]
    n_mines       = len(mine_keys)
    group_spacing = 1.2
    index         = np.arange(n_mines) * group_spacing
    bar_width     = 0.25
    offsets = {
    "diesel":   -1.5 * bar_width,
    "battery":  -0.5 * bar_width,
    "hydrogen":  0.5 * bar_width,
    "trolley":   1.5 * bar_width,
    }


    scale_map = {
        "cost_annual_USD":     (1e6,  "Annual Cost [M$/a]"),
        "cost_specific_USD_t": (1.0,  "Specific Cost [$/t ore]"),
        "cost_specific_USD_tkm": (1.0, "Specific Cost [$/t·km]"),
    }
    scale, ylabel = scale_map.get(key, (1.0, key))

    fig, ax = plt.subplots(figsize=(12, 6))

    for tech in technologies:
        color = TECH_COLORS[tech]
        lows  = np.array(
            [all_mines_data[m][tech]["cost"][key]["low"]  for m in mine_keys],
            dtype=float) / scale
        highs = np.array(
            [all_mines_data[m][tech]["cost"][key]["high"] for m in mine_keys],
            dtype=float) / scale

        ax.bar(index + offsets[tech], lows, bar_width,
               color=color, alpha=0.9,
               label=f"{tech.capitalize()} – progressive")
        ax.bar(index + offsets[tech], highs - lows, bar_width,
               bottom=lows, color=color, alpha=0.35,
               label=f"{tech.capitalize()} – range")

    ax.set_xticks(index)
    #ax.set_xlim(-0.5, index[-1] + 0.5)   # optional: Rand links/rechts trimmen
    ax.set_xticklabels(display_names, rotation=15, ha="right")
    ax.set_xlabel("Mines")
    ax.set_ylabel(ylabel)
    metric_label = pretty_metric_name(key)
    
    ax.set_title(
        f"Mine Comparison – {metric_label}\n"
        f"(solid = progressive, light = conservative range)"
    )
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend(fontsize=7, ncol=2)

    fig.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_path, f'cost_comparison_{key}_{timestamp}.png')
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    plt.show()
    plt.close()

def plot_speeds_per_mine(mine_base, mine_name, data):
    """
    Zeigt die Fahrgeschwindigkeiten einer Mine pro Segment.
    Da Geschwindigkeiten für alle Technologien identisch sind,
    wird nur noch zwischen conservativem und progressivem Szenario
    unterschieden — kein Technologie-Split mehr.

    data = {
        'conservative': {'V_ec': ..., 'V_flat_loaded': ..., 'V_flat_empty': ..., 'V_ce': ...},
        'progressive':  {'V_ec': ..., 'V_flat_loaded': ..., 'V_flat_empty': ..., 'V_ce': ...},
    }
    Alle Werte in m/s; Plot in km/h.
    """
    import matplotlib.patches as mpatches

    segments   = ["V_ec", "V_flat_loaded", "V_flat_empty", "V_ce"]
    seg_labels = [
        "ec\n(uphill, loaded)",
        "flat\n(loaded)",
        "flat\n(empty)",
        "ce\n(downhill, empty)",
    ]

    con  = data["conservative"]
    prog = data["progressive"]

    vals_con  = [con[s]  * 3.6 for s in segments]
    vals_prog = [prog[s] * 3.6 for s in segments]

    x     = np.arange(len(segments))
    width = 0.35
    COLOR = "#4c72b0"   # einheitliche Mine-Farbe

    fig, ax = plt.subplots(figsize=(9, 5))

    # Progressive: voller Balken
    bars_prog = ax.bar(
        x - width / 2, vals_prog, width,
        color=COLOR, alpha=0.9,
        label="Progressive",
        edgecolor="none", linewidth=0,
    )
    # Conservative: heller Range-Anteil on top (gestapelt)
    bars_con = ax.bar(
        x + width / 2, vals_con, width,
        color=COLOR, alpha=0.40,
        label="Conservative",
        edgecolor="none", linewidth=0,
    )

    # Werte über den Balken
    for bar in bars_prog:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2, h + 0.3,
            f"{h:.1f}", ha="center", va="bottom", fontsize=8,
        )
    for bar in bars_con:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2, h + 0.3,
            f"{h:.1f}", ha="center", va="bottom", fontsize=8,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(seg_labels, fontsize=9)
    ax.set_ylabel("Speed [km/h]")
    ax.set_title(
        f"Speeds – {mine_name}\n"
    )
    ax.set_ylim(0, max(vals_con + vals_prog) * 1.20)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.axhline(0, color="black", linewidth=0.8)

    legend_elements = [
        mpatches.Patch(facecolor=COLOR, alpha=0.9,  label="Progressive"),
        mpatches.Patch(facecolor=COLOR, alpha=0.40, label="Conservative"),
    ]
    ax.legend(handles=legend_elements, fontsize=9)

    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, "figures")
    os.makedirs(folder_path, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_path, f"speeds_{mine_base}_{timestamp}.png")
    plt.savefig(file_path, dpi=300, bbox_inches="tight")
    plt.show()
    plt.close(fig)

def plot_relative_to_diesel(all_mines_data, mine_name_map, key, data_subkey,
                             scenario="progressive", h2_as_electricity=False):
    """
    Zeigt den prozentualen Unterschied von Battery, H2 und Trolley
    relativ zu Diesel, wobei das gewählte 'scenario' NUR die Diesel-Referenz festlegt.

    Darstellung:
    - Diesel-Referenz:
        scenario="progressive"  -> Diesel low
        scenario="conservative" -> Diesel high
    - Andere Technologien:
        progressive  = transparente Linie mit Endkappe
        conservative = kräftige Linie mit Endkappe
    - Beide Werte werden beschriftet
    """
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, 'figures')
    os.makedirs(folder_path, exist_ok=True)

    diesel_ref_key = "low" if scenario == "progressive" else "high"

    if h2_as_electricity and data_subkey == "energy":
        h2_data_subkey = "energy_elec_view"
    else:
        h2_data_subkey = data_subkey

    h2_label = " | H₂: electricity basis incl. electrolysis" \
        if (h2_as_electricity and data_subkey == "energy") else ""
    file_tag = "_elec_view" \
        if (h2_as_electricity and data_subkey == "energy") else ""

    technologies_rel = ["battery", "hydrogen", "trolley"]
    mine_keys = list(all_mines_data.keys())
    display_names = [mine_name_map.get(m, m) for m in mine_keys]

    n_mines = len(mine_keys)
    group_spacing = 1.2
    index = np.arange(n_mines) * group_spacing
    bar_width = 0.25

    offsets = {
        "battery": -1.0 * bar_width,
        "hydrogen": 0.0 * bar_width,
        "trolley": 1.0 * bar_width,
    }

    cap = 0.06  # halbe Breite der horizontalen Endkappe

    fig, ax = plt.subplots(figsize=(12, 6))

    for tech in technologies_rel:
        color = TECH_COLORS[tech]
        effective_subkey = h2_data_subkey if tech == "hydrogen" else data_subkey

        prog_vals = []
        cons_vals = []

        for m in mine_keys:
            diesel_val = all_mines_data[m]["diesel"][data_subkey][key][diesel_ref_key]

            tech_prog = all_mines_data[m][tech][effective_subkey][key]["low"]
            tech_cons = all_mines_data[m][tech][effective_subkey][key]["high"]

            pct_prog = (tech_prog / diesel_val - 1.0) * 100.0
            pct_cons = (tech_cons / diesel_val - 1.0) * 100.0

            prog_vals.append(pct_prog)
            cons_vals.append(pct_cons)

        prog_vals = np.array(prog_vals, dtype=float)
        cons_vals = np.array(cons_vals, dtype=float)

        x = index + offsets[tech]

        for i in range(len(x)):
            xi = x[i]
            prog_val = prog_vals[i]
            cons_val = cons_vals[i]

            # Progressive: transparent / dünner
            ax.vlines(
                xi, 0, prog_val,
                color=color, alpha=0.35, linewidth=2.0, zorder=1
            )
            ax.hlines(
                prog_val, xi - cap, xi + cap,
                color=color, alpha=0.35, linewidth=2.0, zorder=2
            )

            # Conservative: deckender / stärker
            ax.vlines(
                xi, 0, cons_val,
                color=color, alpha=0.95, linewidth=3.0, zorder=3
            )
            ax.hlines(
                cons_val, xi - cap, xi + cap,
                color=color, alpha=0.95, linewidth=3.0, zorder=4
            )

            # Label-Positionen
            diff = abs(cons_val - prog_val)

            if diff < 1.0:
                prog_offset = 0.35 if prog_val >= 0 else -0.35
                cons_offset = 1.0 if cons_val >= 0 else -1.0
            else:
                prog_offset = 0.35 if prog_val >= 0 else -0.35
                cons_offset = 0.75 if cons_val >= 0 else -0.75

            prog_va = "bottom" if prog_val >= 0 else "top"
            cons_va = "bottom" if cons_val >= 0 else "top"

            # Progressive Label
            ax.text(
                xi,
                prog_val + prog_offset,
                f"{prog_val:+.1f}%",
                ha="center",
                va=prog_va,
                fontsize=7,
                fontweight="normal",
                color="black",
                zorder=5,
            )

            # Conservative Label
            ax.text(
                xi,
                cons_val + cons_offset,
                f"{cons_val:+.1f}%",
                ha="center",
                va=cons_va,
                fontsize=7,
                fontweight="bold",
                color="black",
                zorder=6,
            )

    ax.axhline(
        0, color="black", linewidth=1.2, linestyle="--",
        label="Diesel (= 0%)", zorder=0
    )

    ax.set_xticks(index)
    ax.set_xticklabels(display_names, rotation=15, ha="right")
    ax.set_xlabel("Mines")
    ax.set_ylabel("Difference to Diesel [%]")
    metric_label = pretty_metric_name(key)

    ax.set_title(
        f"Relative Comparison to Diesel – {metric_label}\n"
        f"Diesel reference: {scenario.capitalize()} | "
        f"light line = technology progressive, solid line = technology conservative{h2_label}"
    )
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    handles = [
        plt.Line2D([0], [0], color=TECH_COLORS["battery"],  lw=2, alpha=0.35,
                   label="Battery – progressive"),
        plt.Line2D([0], [0], color=TECH_COLORS["battery"],  lw=3, alpha=0.95,
                   label="Battery – conservative"),

        plt.Line2D([0], [0], color=TECH_COLORS["hydrogen"], lw=2, alpha=0.35,
                   label="Hydrogen – progressive"),
        plt.Line2D([0], [0], color=TECH_COLORS["hydrogen"], lw=3, alpha=0.95,
                   label="Hydrogen – conservative"),

        plt.Line2D([0], [0], color=TECH_COLORS["trolley"],  lw=2, alpha=0.35,
                   label="Trolley – progressive"),
        plt.Line2D([0], [0], color=TECH_COLORS["trolley"],  lw=3, alpha=0.95,
                   label="Trolley – conservative"),

        plt.Line2D([0], [0], color="black", linestyle="--", linewidth=1.2,
                   label="Diesel (= 0%)"),
    ]
    ax.legend(handles=handles, fontsize=8)

    fig.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(
        folder_path,
        f"relative_to_diesel_{key}_{scenario}{file_tag}_{timestamp}.png"
    )
    plt.savefig(file_path, dpi=300, bbox_inches="tight")
    plt.show()
    plt.close()
    
def plot_lcoe_bar(lcoe_data):
    techs = list(lcoe_data.keys())
    values = list(lcoe_data.values())
    plt.bar(techs, values, color=['gray','blue','orange','green'])
    plt.ylabel('LCOE [USD/t Ore]')
    plt.title('Full-LCOE (Diesel Baseline CAPEX-free)')
    plt.savefig('lcoe_bar.png')

def plot_phasing(phases, phased_lcoe):
    plt.plot([p*100 for p in phases], phased_lcoe, 'o-', lw=3)
    plt.axhline(y=lcoe_data['diesel'], color='gray', ls='--', lw=2, label='Diesel')
    plt.xlabel('Austausch [%]'); plt.ylabel('LCOE [USD/t]')
    plt.title('Fleet-Shift Battery'); plt.legend()
    plt.grid(alpha=0.3); plt.savefig('phasing.png')

def plot_phased_transition(phased_results, technology, mine_name):
    scriptdir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folderpath = os.path.join(scriptdir, 'figures')
    os.makedirs(folderpath, exist_ok=True)

    phases = [r['phase_pct'] for r in phased_results]
    lcoe   = [r['phased_lcoe_usd_t'] for r in phased_results]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(phases, lcoe, 'o-', linewidth=3, color=TECH_COLORS[technology],
            label=f'{technology.capitalize()} Phasing')
    ax.set_xlabel('Level of Fleet Shift [%]')
    ax.set_ylabel('LCOE [USD/t Ore]')
    ax.set_title(f'Transition costs Diesel → {technology.capitalize()} | {mine_name}')
    ax.legend(); ax.grid(True, alpha=0.3)

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filepath = os.path.join(folderpath, f'phasing_{technology}_{mine_name}_{timestamp}.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.show(); plt.close()

def plot_regen_efficiency_by_mine(config):
    """
    Zeigt eta_regen je Mine und Technologie.
    Progressive Wert = voller Balken
    Conservative Wert = heller Range-Anteil oben drauf
    """
    scriptdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folderpath = os.path.join(scriptdir, "figures")
    os.makedirs(folderpath, exist_ok=True)

    technologies = ["battery", "hydrogen", "trolley"]
    minekeys = []
    minenames = []

    eta_prog = {tech: [] for tech in technologies}
    eta_con  = {tech: [] for tech in technologies}

    for entry in config["scenarios"]:
        mine_base = entry["mine"]
        mine_name = entry.get("name", mine_base)
        truck_sets = entry["truck_sets"]

        if not truck_sets:
            continue

        truck_set = truck_sets[0]

        minekeys.append(mine_base)
        minenames.append(mine_name)

        for tech in technologies:
            truck_prog = get_data_truck(truck_file_name(truck_set, tech, "progressive"))
            truck_con  = get_data_truck(truck_file_name(truck_set, tech, "conservative"))

            eta_prog[tech].append(truck_prog[TruckParam.REGEN_EFFICIENCY])
            eta_con[tech].append(truck_con[TruckParam.REGEN_EFFICIENCY])

    index = np.arange(len(minekeys)) * 1.2
    barwidth = 0.25
    offsets = {
        "battery": -barwidth,
        "hydrogen": 0.0,
        "trolley": barwidth,
    }

    fig, ax = plt.subplots(figsize=(12, 6))

    for tech in technologies:
        color = TECH_COLORS[tech]
        lows  = np.array(eta_prog[tech], dtype=float)
        highs = np.array(eta_con[tech], dtype=float)

        ax.bar(index + offsets[tech], lows, barwidth,
               color=color, alpha=0.9, label=f"{tech.capitalize()} – progressive")
        ax.bar(index + offsets[tech], highs - lows, barwidth, bottom=lows,
               color=color, alpha=0.35, label=f"{tech.capitalize()} – range")

    ax.set_xticks(index)
    ax.set_xticklabels(minenames, rotation=15, ha="right")
    ax.set_ylabel("Rekuperationswirkungsgrad η_regen [-]")
    ax.set_xlabel("Mines")
    ax.set_title("Mine Comparison – Regenerative Braking Efficiency\nsolid = progressive, light = conservative range")
    ax.set_ylim(0, 1.0)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.axhline(0, color="black", linewidth=0.8)

    legend_elements = [
        mpatches.Patch(facecolor=TECH_COLORS["battery"],  alpha=0.9,  label="Battery – progressive"),
        mpatches.Patch(facecolor=TECH_COLORS["battery"],  alpha=0.35, label="Battery – range"),
        mpatches.Patch(facecolor=TECH_COLORS["hydrogen"], alpha=0.9,  label="Hydrogen – progressive"),
        mpatches.Patch(facecolor=TECH_COLORS["hydrogen"], alpha=0.35, label="Hydrogen – range"),
        mpatches.Patch(facecolor=TECH_COLORS["trolley"],  alpha=0.9,  label="Trolley – progressive"),
        mpatches.Patch(facecolor=TECH_COLORS["trolley"],  alpha=0.35, label="Trolley – range"),
    ]
    ax.legend(handles=legend_elements, fontsize=8, ncol=2)

    fig.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(folderpath, f"regen_efficiency_comparison_{timestamp}.png")
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.show()
    plt.close()

def plot_truck_assumptions(config):
    """
    Erzeugt zwei separate Plots zur Dokumentation der Truck-Annahmen:
      1. Idle Power [kW] pro Technologie und Mine
      2. Loading + Unloading Time [s] pro Technologie und Mine
         (gestapelt: Loading unten, Unloading oben)

    Daten kommen aus den Truck-YAMLs (progressive + conservative),
    Zuordnung Mine ↔ Truck-Set aus config["scenarios"].
    """
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, "figures")
    os.makedirs(folder_path, exist_ok=True)

    technologies = ["diesel", "battery", "hydrogen", "trolley"]

    # ── 1. Daten sammeln ─────────────────────────────────────────────────────
    mine_names    = []
    idle_data     = {tech: {"prog": [], "con": []} for tech in technologies}
    t_load_data   = {tech: {"prog": [], "con": []} for tech in technologies}
    t_unload_data = {tech: {"prog": [], "con": []} for tech in technologies}

    for entry in config["scenarios"]:
        truck_set = entry["truck_sets"][0]
        mine_names.append(entry.get("name", entry["mine"]))

        for tech in technologies:
            truck_prog = get_data_truck(f"reference_truck_{truck_set}_{tech}_progressive")
            truck_con  = get_data_truck(f"reference_truck_{truck_set}_{tech}_conservative")

            idle_data[tech]["prog"].append(truck_prog[TruckParam.IDLE_POWER_KW])
            idle_data[tech]["con"].append(truck_con[TruckParam.IDLE_POWER_KW])

            t_load_data[tech]["prog"].append(truck_prog[TruckParam.T_LOAD_S])
            t_load_data[tech]["con"].append(truck_con[TruckParam.T_LOAD_S])

            t_unload_data[tech]["prog"].append(truck_prog[TruckParam.T_UNLOAD_S])
            t_unload_data[tech]["con"].append(truck_con[TruckParam.T_UNLOAD_S])

    n     = len(mine_names)
    index = np.arange(n)
    width = 0.18
    offsets = {
        "diesel":   -1.5 * width,
        "battery":  -0.5 * width,
        "hydrogen":  0.5 * width,
        "trolley":   1.5 * width,
    }

    # ── 2. Plot 1: Idle Power (einfacher gruppierter Balkenplot) ─────────────
    def _plot_grouped(data_dict, title, ylabel, filename):
        fig, ax = plt.subplots(figsize=(12, 5))

        for tech in technologies:
            color     = TECH_COLORS[tech]
            prog_vals = np.array(data_dict[tech]["prog"], dtype=float)
            con_vals  = np.array(data_dict[tech]["con"],  dtype=float)

            ax.bar(index + offsets[tech], prog_vals, width,
                   color=color, alpha=0.9)
            ax.bar(index + offsets[tech], con_vals - prog_vals, width,
                   bottom=prog_vals, color=color, alpha=0.35)

        ax.set_xticks(index)
        ax.set_xticklabels(mine_names, rotation=15, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.axhline(0, color="black", linewidth=0.8)

        handles = [
            mpatches.Patch(color=TECH_COLORS[t], alpha=0.9,
                           label=f"{t.capitalize()} – progressive")
            for t in technologies
        ] + [
            mpatches.Patch(facecolor=TECH_COLORS[t], alpha=0.35,
                           label=f"{t.capitalize()} – range")
            for t in technologies
        ]
        ax.legend(handles=handles, fontsize=7, ncol=2)

        fig.tight_layout()
        path = os.path.join(folder_path, filename)
        plt.savefig(path, dpi=300, bbox_inches="tight")
        plt.show()
        plt.close()
        print(f"  → Saved: {path}")

    _plot_grouped(
        data_dict = idle_data,
        title     = "Truck Assumptions – Idle Power per Technology and Mine\n"
                    "(solid = progressive, light = conservative range)",
        ylabel    = "Idle Power [kW]",
        filename  = f"truck_assumptions_idle_power_{timestamp}.png",
    )

        # ── 3. Plot 2: Loading Time ───────────────────────────────────────────────
    _plot_grouped(
        data_dict = t_load_data,
        title     = "Truck Assumptions – Loading Time per Technology and Mine\n"
                    "(solid = progressive, light = conservative range)",
        ylabel    = "Loading Time [s]",
        filename  = f"truck_assumptions_loading_time_{timestamp}.png",
    )

    # ── 4. Plot 3: Unloading Time ─────────────────────────────────────────────
    _plot_grouped(
        data_dict = t_unload_data,
        title     = "Truck Assumptions – Unloading Time per Technology and Mine\n"
                    "(solid = progressive, light = conservative range)",
        ylabel    = "Unloading Time [s]",
        filename  = f"truck_assumptions_unloading_time_{timestamp}.png",
    )


def plot_payload_gvw(config):
    """
    Payload vs. Gross Vehicle Weight (GVW) per mine and technology.

    X-axis: four reference mines (display names from config).
    Per mine: four grouped bars, one per technology.
      - Solid (alpha=0.9):  0 → payload [t]
      - Transparent (alpha=0.35): payload → GVW (= empty weight share)

    Truck YAMLs: reference_truck_<set>_<tech>_progressive.yml
    Set is read from config["scenarios"][i]["truck_sets"][0].
    """
    import os
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from datetime import datetime
    from .loader import get_data_truck, TruckParam

    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, "figures")
    os.makedirs(folder_path, exist_ok=True)

    technologies = ["diesel", "battery", "hydrogen", "trolley"]
    TECH_COLORS = {
        "diesel":   "#0072B2",  # blue
        "battery":  "#009E73",  # bluish green
        "hydrogen": "#D55E00",  # vermillion
        "trolley":  "#CC79A7",  # reddish purple
    }

    # ── 1. Collect payload / GVW per mine × technology ────────────────────────
    mine_names = []
    payloads   = {tech: [] for tech in technologies}
    gvws       = {tech: [] for tech in technologies}

    for entry in config["scenarios"]:
        mine_name = entry.get("name", entry["mine"])
        truck_set = entry["truck_sets"][0]          # e.g. "set2"
        mine_names.append(mine_name)

        for tech in technologies:
            # Filename: reference_truck_set2_diesel_progressive.yml
            fname = f"reference_truck_{truck_set}_{tech}_progressive"
            truck = get_data_truck(fname)

            payload_t = truck[TruckParam.PAYLOAD_T]
            empty_t   = truck[TruckParam.EMPTY_WEIGHT_T]
            payloads[tech].append(payload_t)
            gvws[tech].append(payload_t + empty_t)

    # ── 2. Layout ─────────────────────────────────────────────────────────────
    n_mines     = len(mine_names)
    n_techs     = len(technologies)
    bar_width   = 0.18
    group_gap   = 0.08
    group_width = n_techs * bar_width + group_gap
    index       = np.arange(n_mines) * group_width
    offsets     = {
        technologies[i]: (i - (n_techs - 1) / 2) * bar_width
        for i in range(n_techs)
    }

    fig, ax = plt.subplots(figsize=(13, 6))

    for tech in technologies:
        color   = TECH_COLORS[tech]
        pay_arr = np.array(payloads[tech], dtype=float)
        gvw_arr = np.array(gvws[tech],     dtype=float)
        x_pos   = index + offsets[tech]

        # Solid: 0 → payload
        ax.bar(x_pos, pay_arr, bar_width,
               color=color, alpha=0.9,
               edgecolor="none", linewidth=0)
        # Transparent: payload → GVW
        ax.bar(x_pos, gvw_arr - pay_arr, bar_width,
               bottom=pay_arr,
               color=color, alpha=0.35,
               edgecolor="none", linewidth=0)
        # GVW label on top of each bar
        for xp, gv in zip(x_pos, gvw_arr):
            ax.text(xp, gv + 2, f"{gv:.0f}",
                    ha="center", va="bottom", fontsize=6.5,
                    color=color, fontweight="bold")

    # ── 3. Axes & labels ──────────────────────────────────────────────────────
    ax.set_xticks(index)
    ax.set_xticklabels(mine_names, rotation=15, ha="right", fontsize=9)
    ax.set_ylabel("Mass [t]")
    ax.set_xlabel("Reference Mines")
    ax.set_title(
        "Payload & Gross Vehicle Weight (GVW) – Reference Mines\n"
        "(solid = payload | transparent = empty weight share up to GVW)",
        fontsize=11,
    )
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.axhline(0, color="black", linewidth=0.8)

    # ── 4. Legend ─────────────────────────────────────────────────────────────
    legend_elements = []
    for tech in technologies:
        c = TECH_COLORS[tech]
        legend_elements.append(
            mpatches.Patch(facecolor=c, alpha=0.9,
                           label=f"{tech.capitalize()} – Payload"))
        legend_elements.append(
            mpatches.Patch(facecolor=c, alpha=0.35,
                           label=f"{tech.capitalize()} – Empty weight (→ GVW)"))
    ax.legend(handles=legend_elements, fontsize=7, ncol=2, loc="upper left")

    # ── 5. Tech-Kürzel über jedem Balken ──────────────────────────────────────
    y_top = ax.get_ylim()[1]
    for mine_x in index:
        for tech in technologies:
            xp = mine_x + offsets[tech]
            ax.text(xp, y_top * 0.995, tech[:3].upper(),
                    ha="center", va="top", fontsize=6,
                    color=TECH_COLORS[tech], fontweight="bold")

    # ── 6. Save ───────────────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_path, f"payload_gvw_{timestamp}.png")
    plt.tight_layout()
    plt.savefig(file_path, dpi=300, bbox_inches="tight")
    plt.show()
    plt.close()
    print(f"  → Saved: {file_path}")


def plot_energy_cost_assumptions(config):
    """
    Energy carrier cost assumptions per mine and technology.

    4 subplots (one per technology): Diesel [$/l], Battery [$/kWh],
    Hydrogen [$/kg], Trolley [$/kWh].
    Per subplot, x-axis = mines, two bars per mine:
      - solid (alpha=0.9):  progressive value
      - transparent (alpha=0.35): conservative value (range on top)

    Truck YAMLs: reference_truck_<set>_<tech>_<scenario>.yml
    """
    import os
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from datetime import datetime
    from .loader import get_data_truck, TruckParam

    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, "figures")
    os.makedirs(folder_path, exist_ok=True)

    technologies = ["diesel", "battery", "hydrogen", "trolley"]
    TECH_COLORS = {
        "diesel":   "#0072B2",  # blue
        "battery":  "#009E73",  # bluish green
        "hydrogen": "#D55E00",  # vermillion
        "trolley":  "#CC79A7",  # reddish purple
    }
    UNITS = {
        "diesel":   "$/l",
        "battery":  "$/kWh",
        "hydrogen": "$/kg",
        "trolley":  "$/kWh",
    }

    def get_cost(truck, tech):
        """Extract energy carrier cost from truck dict."""
        if tech == "diesel":
            return truck[TruckParam.FUEL_COST_PER_L]
        elif tech == "hydrogen":
            return truck[TruckParam.HYDROGEN_COST_PER_KG]
        else:  # battery, trolley
            return truck[TruckParam.ELECTRICITY_COST_PER_KWH]

    # ── 1. Collect data ───────────────────────────────────────────────────────
    mine_names = []
    # costs[tech]["prog" / "cons"] = list of values per mine
    costs = {tech: {"prog": [], "cons": []} for tech in technologies}

    for entry in config["scenarios"]:
        mine_names.append(entry.get("name", entry["mine"]))
        truck_set = entry["truck_sets"][0]

        for tech in technologies:
            for scenario, key in [("progressive", "prog"), ("conservative", "cons")]:
                fname = f"reference_truck_{truck_set}_{tech}_{scenario}"
                truck = get_data_truck(fname)
                costs[tech][key].append(get_cost(truck, tech))

    # ── 2. Plot – 4 subplots ──────────────────────────────────────────────────
    n_mines   = len(mine_names)
    bar_width = 0.35
    index     = np.arange(n_mines)

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))
    fig.suptitle(
        "Energy Carrier Cost Assumptions – Reference Mines\n"
        "(solid = progressive | transparent = conservative range)",
        fontsize=11,
    )

    for ax, tech in zip(axes, technologies):
        color    = TECH_COLORS[tech]
        prog_arr = np.array(costs[tech]["prog"], dtype=float)
        cons_arr = np.array(costs[tech]["cons"], dtype=float)

        # Solid: progressive value
        ax.bar(index, prog_arr, bar_width,
               color=color, alpha=0.9,
               edgecolor="none", linewidth=0,
               label="Progressive")
        # Transparent: conservative − progressive (range on top)
        ax.bar(index, cons_arr - prog_arr, bar_width,
               bottom=prog_arr,
               color=color, alpha=0.35,
               edgecolor="none", linewidth=0,
               label="Conservative range")

        # Value labels
        for i, (pv, cv) in enumerate(zip(prog_arr, cons_arr)):
            ax.text(i, pv * 0.5, f"{pv:.3f}",
                    ha="center", va="center", fontsize=7,
                    color="white", fontweight="bold")
            if cv > pv:
                ax.text(i, pv + (cv - pv) * 0.5, f"{cv:.3f}",
                        ha="center", va="center", fontsize=6.5,
                        color=color, fontweight="bold")

        ax.set_title(f"{tech.capitalize()}\n[{UNITS[tech]}]", fontsize=9)
        ax.set_xticks(index)
        ax.set_xticklabels(mine_names, rotation=20, ha="right", fontsize=7.5)
        ax.set_ylabel(f"Cost [{UNITS[tech]}]", fontsize=8)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.axhline(0, color="black", linewidth=0.6)

        # y-axis: start slightly below min value for visual clarity
        y_max = max(cons_arr) * 1.20
        ax.set_ylim(0, y_max)

    # ── 3. Shared legend ──────────────────────────────────────────────────────
    legend_elements = [
        mpatches.Patch(facecolor="grey", alpha=0.9,  label="Progressive"),
        mpatches.Patch(facecolor="grey", alpha=0.35, label="Conservative range"),
    ]
    fig.legend(handles=legend_elements, fontsize=8, ncol=2,
               loc="lower center", bbox_to_anchor=(0.5, -0.04))

    # ── 4. Save ───────────────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_path, f"cost_assumptions_{timestamp}.png")
    plt.tight_layout()
    plt.savefig(file_path, dpi=300, bbox_inches="tight")
    plt.show()
    plt.close()
    print(f"  → Saved: {file_path}")

def plot_energy_cost_assumptions_per_mine(config):
    """
    Energy carrier cost assumptions per mine – normalised to $/kWh.
    One figure per mine, 4 bars (technologies), progressive + conservative.
    Y-axis: $/kWh (no unit label on axis).
    Unit label '$/kWh' shown above each bar.
    """
    import os
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from datetime import datetime
    from .loader import get_data_truck, TruckParam

    script_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(script_dir, "figures")
    os.makedirs(folder_path, exist_ok=True)

    technologies = ["diesel", "battery", "hydrogen", "trolley"]
    TECH_COLORS = {
        "diesel":   "#0072B2",  # blue
        "battery":  "#009E73",  # bluish green
        "hydrogen": "#D55E00",  # vermillion
        "trolley":  "#CC79A7",  # reddish purple
    }

    def cost_per_kwh(truck, tech):
        """Convert native cost unit → $/kWh using YAML energy density values."""
        if tech == "diesel":
            cost   = truck[TruckParam.FUEL_COST_PER_L]           # $/l
            mj_l   = truck[TruckParam.FUEL_ENERGY_DENSITY_MJ_PER_L]  # MJ/l
            kwh_l  = mj_l / 3.6                                   # kWh/l
            return cost / kwh_l                                   # $/kWh

        elif tech == "hydrogen":
            cost   = truck[TruckParam.HYDROGEN_COST_PER_KG]      # $/kg
            mj_kg  = truck[TruckParam.HYDROGEN_LHV_MJ_PER_KG]    # MJ/kg
            kwh_kg = mj_kg / 3.6                                  # kWh/kg
            return cost / kwh_kg                                  # $/kWh

        else:  # battery, trolley
            return truck[TruckParam.ELECTRICITY_COST_PER_KWH]    # already $/kWh

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for entry in config["scenarios"]:
        mine_name = entry.get("name", entry["mine"])
        mine_base = entry["mine"]
        truck_set = entry["truck_sets"][0]

        prog_vals = []
        cons_vals = []

        for tech in technologies:
            truck_prog = get_data_truck(f"reference_truck_{truck_set}_{tech}_progressive")
            truck_cons = get_data_truck(f"reference_truck_{truck_set}_{tech}_conservative")
            prog_vals.append(cost_per_kwh(truck_prog, tech))
            cons_vals.append(cost_per_kwh(truck_cons, tech))

        prog_arr = np.array(prog_vals, dtype=float)
        cons_arr = np.array(cons_vals, dtype=float)

        # ── Plot ──────────────────────────────────────────────────────────────
        bar_width = 0.5
        index     = np.arange(len(technologies))

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.set_title(
            f"Energy Carrier Cost Assumptions – {mine_name}\n"
            f"(normalised to $/kWh | solid = progressive | transparent = conservative)",
            fontsize=10,
        )

        for i, tech in enumerate(technologies):
            color = TECH_COLORS[tech]
            pv    = prog_arr[i]
            cv    = cons_arr[i]

            # Solid: progressive
            ax.bar(i, pv, bar_width,
                   color=color, alpha=0.9,
                   edgecolor="none", linewidth=0)
            # Transparent: conservative range on top
            ax.bar(i, cv - pv, bar_width,
                   bottom=pv,
                   color=color, alpha=0.35,
                   edgecolor="none", linewidth=0)

            # Value labels
            ax.text(i, pv * 0.5, f"{pv:.4f}",
                    ha="center", va="center", fontsize=8,
                    color="white", fontweight="bold")
            if cv > pv:
                ax.text(i, pv + (cv - pv) * 0.5, f"{cv:.4f}",
                        ha="center", va="center", fontsize=7.5,
                        color=color, fontweight="bold")

        ax.set_xticks(index)
        ax.set_xticklabels([t.capitalize() for t in technologies], fontsize=9)
        ax.set_ylabel("$/kWh", fontsize=9)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.4f}"))
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_ylim(0, max(cons_arr) * 1.20)

        legend_elements = [
            mpatches.Patch(facecolor="grey", alpha=0.9,  label="Progressive"),
            mpatches.Patch(facecolor="grey", alpha=0.35, label="Conservative range"),
        ]
        ax.legend(handles=legend_elements, fontsize=8, loc="upper right")

        plt.tight_layout()
        file_path = os.path.join(
            folder_path, f"cost_kwh_{mine_base}_{timestamp}.png"
        )
        plt.savefig(file_path, dpi=300, bbox_inches="tight")
        plt.show()
        plt.close()
        print(f"  → Saved: {file_path}")
