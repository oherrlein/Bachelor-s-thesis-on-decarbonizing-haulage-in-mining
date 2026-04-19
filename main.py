from src.loader import (
    get_data_mine, get_data_truck, get_config, load_capex,
    TECHNOLOGIES, SCENARIOS, truck_file_name, TruckParam,
)
from src.model import (
    calculate_power_excavator_to_crusher,
    calculate_power_crusher_to_excavator,
    calculate_power_excavator_to_dump,
    calculate_power_dump_to_excavator,
    calculate_annual_energy,
    calculate_h2_energy_breakdown,
    calculate_annual_cost,
    derive_speeds,
    calculate_lcoe,
    calculate_phased_lcoe,
    convert_h2_energy_to_electricity
)
from src.plotting import (
    plot_power_per_mine,
    plot_mine_comparison,
    plot_base_mine_comparison,
    plot_energy_per_mine,
    plot_energy_mine_comparison,
    plot_h2_breakdown_per_mine,
    plot_h2_breakdown_mine_comparison,
    plot_cost_per_mine,
    plot_cost_mine_comparison,
    plot_speeds_per_mine,
    plot_relative_to_diesel,
    plot_phased_transition,
    plot_regen_efficiency_by_mine,
    plot_truck_assumptions,
    plot_payload_gvw,
    plot_energy_cost_assumptions,
    plot_energy_cost_assumptions_per_mine
)

import traceback


def compute_powers(mine, truck):
    P_ec = calculate_power_excavator_to_crusher(mine, truck)
    P_ce = calculate_power_crusher_to_excavator(mine, truck)
    P_ed = calculate_power_excavator_to_dump(mine, truck)
    P_de = calculate_power_dump_to_excavator(mine, truck)



    return {
        "P_ec":  P_ec,
        "P_ce":  P_ce,
        "P_ed":  P_ed,
        "P_de":  P_de,

    }


def compute_energy(mine, truck):
    return calculate_annual_energy(mine, truck)


def compute_cost(mine, truck, energy_result):
    return calculate_annual_cost(mine, truck, energy_result)


def main():
    config = get_config()
    CAPEX = load_capex()
    all_mines_data = {}
    mine_name_map  = {}

    for scenario_entry in config["scenarios"]:
        try:
            mine_base  = scenario_entry["mine"]
            mine_name  = scenario_entry.get("name", mine_base)
            truck_sets = scenario_entry["truck_sets"]

            print(f"\n--- Processing mine: {mine_name} ({mine_base}) ---")

            mine_con  = get_data_mine(f"{mine_base}_conservative")
            mine_prog = get_data_mine(f"{mine_base}_progressive")

            plot1_data = {}

            for truck_set in truck_sets:
                for technology in TECHNOLOGIES:
                    try:
                        truck_con = get_data_truck(
                            truck_file_name(truck_set, technology, "conservative")
                        )
                        truck_prog = get_data_truck(
                            truck_file_name(truck_set, technology, "progressive")
                        )

                        powers_con  = compute_powers(mine_con,  truck_con)
                        powers_prog = compute_powers(mine_prog, truck_prog)

                        speeds_con  = derive_speeds(mine_con,  truck_con)
                        speeds_prog = derive_speeds(mine_prog, truck_prog)

                        if "speeds" not in plot1_data:
                            plot1_data["speeds"] = {
                                "conservative": {k: speeds_con[k]  for k in ("V_ec", "V_flat_loaded", "V_flat_empty", "V_ce")},
                                "progressive":  {k: speeds_prog[k] for k in ("V_ec", "V_flat_loaded", "V_flat_empty", "V_ce")},
                        }
                        
                        energy_con  = compute_energy(mine_con,  truck_con)
                        energy_prog = compute_energy(mine_prog, truck_prog)

                        energy_con_elec  = convert_h2_energy_to_electricity(energy_con,  truck_con)
                        energy_prog_elec = convert_h2_energy_to_electricity(energy_prog, truck_prog)

                        cost_con  = compute_cost(mine_con,  truck_con,  energy_con)
                        cost_prog = compute_cost(mine_prog, truck_prog, energy_prog)
                        lcoe_prog = calculate_lcoe(mine_prog, truck_prog, energy_prog, CAPEX, technology, 'progressive')
                        lcoe_con = calculate_lcoe(mine_con, truck_con, energy_con, CAPEX, technology, 'conservative')

                        
                                            
                        print(f"  {technology}: LCOE "
                              f"{lcoe_prog['lcoe_usd_per_t']:.3f}–"
                              f"{lcoe_con['lcoe_usd_per_t']:.3f} USD/t")
                        
                        

                        # ── Powers ──────────────────────────────────────────
                        plot1_data[technology] = {
                            key: {
                                "low":  powers_prog[key],
                                "high": powers_con[key],
                            }
                            for key in ["P_ec", "P_ce", "P_ed", "P_de"]
                        }

                        # ── Energy ──────────────────────────────────────────
                        plot1_data[technology]["energy"] = {
                            key: {
                                "low":  energy_prog[key],
                                "high": energy_con[key],
                            }
                            for key in ["E_annual_GWh", "E_specific_kWh_t", "E_specific_kWh_tkm"]
                        }
                        
                        plot1_data[technology]["energy_elec_view"] = {
                            key: {
                                "low":  energy_prog_elec[key],
                                "high": energy_con_elec[key],
                            }
                            for key in ["E_annual_GWh", "E_specific_kWh_t", "E_specific_kWh_tkm"]
                        }

                        # ── Cost ────────────────────────────────────────────
                        plot1_data[technology]["cost"] = {
                            key: {
                                "low":  cost_prog[key],
                                "high": cost_con[key],
                            }
                            for key in ["cost_annual_USD", "cost_specific_USD_t", "cost_specific_USD_tkm"]
                        }
                        
                        plot1_data[technology]["lcoe"] = {
                            "low":  lcoe_prog,
                            "high": lcoe_con,
                        }
                        
                        print(f"  ✓ {technology} ({truck_set}): "

                              f"E_annual = [{energy_prog['E_annual_GWh']:.2f}, "
                              f"{energy_con['E_annual_GWh']:.2f}] GWh/a | "
                              f"Cost = [{cost_prog['cost_specific_USD_t']:.3f}, "
                              f"{cost_con['cost_specific_USD_t']:.3f}] $/t Erz")
                        print(
                            f"    Speeds ({technology}): "
                            f"V_ec=[{speeds_prog['V_ec']*3.6:.1f}, {speeds_con['V_ec']*3.6:.1f}] km/h"
                            )

                        # ── H2 Breakdown ─────────────────────────────────────
                        if technology == "hydrogen":
                            h2_breakdown_con  = calculate_h2_energy_breakdown(
                                mine_con,  truck_con,  energy_con
                            )
                            h2_breakdown_prog = calculate_h2_energy_breakdown(
                                mine_prog, truck_prog, energy_prog
                            )

                            plot1_data[technology]["h2_breakdown"] = {
                                "low":  h2_breakdown_prog,
                                "high": h2_breakdown_con,
                            }

                            print(f"  ✓ H2 breakdown: "
                                  f"h2_mass = [{h2_breakdown_prog['h2_mass_t_per_a']:.0f}, "
                                  f"{h2_breakdown_con['h2_mass_t_per_a']:.0f}] t/a | "
                                  f"E_elec_total = [{h2_breakdown_prog['E_elec_total_GWh']:.2f}, "
                                  f"{h2_breakdown_con['E_elec_total_GWh']:.2f}] GWh/a")

                    except Exception as e:
                        print(f"  ✗ FEHLER bei {technology} ({truck_set}): {e}")
                        traceback.print_exc()
                        continue

                try:
                    truck_diesel_prog = get_data_truck(truck_file_name(truck_set, 'diesel', 'progressive'))
                    energy_diesel_prog = compute_energy(mine_prog, truck_diesel_prog)

                    for tech in ['battery', 'hydrogen', 'trolley']:
                        truck_new  = get_data_truck(truck_file_name(truck_set, tech, 'progressive'))
                        energy_new = compute_energy(mine_prog, truck_new)
                        phased = calculate_phased_lcoe(
                            mine_prog, truck_new, energy_new,
                            truck_diesel_prog, energy_diesel_prog,
                            CAPEX, tech, 'progressive'
                        )
                        plot_phased_transition(phased, tech, mine_name)
                        
                except Exception as e:
                    print(f"  ✗ FEHLER bei Phased Transition: {e}")
                    traceback.print_exc()

            if plot1_data:
                plot_power_per_mine(mine_base, mine_name, plot1_data)
                plot_energy_per_mine(mine_base, mine_name, plot1_data, h2_as_electricity=False)
                plot_energy_per_mine(mine_base, mine_name, plot1_data, h2_as_electricity=True)
                plot_h2_breakdown_per_mine(mine_base, mine_name, plot1_data)
                plot_cost_per_mine(mine_base, mine_name, plot1_data)

                if "speeds" in plot1_data:
                    try:
                        plot_speeds_per_mine(mine_base, mine_name, plot1_data["speeds"])
                    except Exception as e:
                        print(f"  ✗ FEHLER bei Speed-Plot {mine_base}: {e}")
                        traceback.print_exc()
                
                all_mines_data[mine_base] = plot1_data
                mine_name_map[mine_base]  = mine_name
                print(f"  → Plots saved for {mine_name}")
            else:
                print(f"  → Kein Plot für {mine_name} (keine Daten)")
        
        
        
        except Exception as e:
            print(f"FEHLER bei Mine {scenario_entry.get('mine', '?')}: {e}")
            traceback.print_exc()
            continue

    if all_mines_data:
        for key in ["P_ec", "P_ce", "P_ed", "P_de"]:
            try:
                plot_mine_comparison(all_mines_data, mine_name_map, compare_key=key)
                print(f"  → Comparison plot saved: {key}")
            except Exception as e:
                print(f"  ✗ FEHLER bei Comparison Plot {key}: {e}")
                traceback.print_exc()

        for key in ["E_annual_GWh", "E_specific_kWh_t", "E_specific_kWh_tkm"]:
            try:
                plot_energy_mine_comparison(all_mines_data, mine_name_map, key=key)
                print(f"  → Energy comparison plot saved: {key}")
            except Exception as e:
                print(f"  ✗ FEHLER bei Energy Comparison Plot {key}: {e}")
                traceback.print_exc()  

        for key in ["cost_annual_USD", "cost_specific_USD_t", "cost_specific_USD_tkm"]:
            try:
                plot_cost_mine_comparison(all_mines_data, mine_name_map, key=key)
                print(f"  → Cost comparison plot saved: {key}")
            except Exception as e:
                print(f"  ✗ FEHLER bei Cost Comparison {key}: {e}")
                traceback.print_exc()  

        try:
            plot_h2_breakdown_mine_comparison(all_mines_data, mine_name_map)
            print("  → H2 breakdown comparison plot saved")
        except Exception as e:
            print(f"  ✗ FEHLER bei H2 Breakdown Comparison: {e}")
            traceback.print_exc()  

        for key, subkey in [
            ("cost_specific_USD_tkm", "cost"),
            ("cost_specific_USD_t", "cost"),
            ("E_specific_kWh_tkm",    "energy"),
            ("E_specific_kWh_t", "energy"),
        ]:
            for scenario in ["progressive", "conservative"]:
        

                try:
                    plot_relative_to_diesel(
                        all_mines_data, mine_name_map,
                        key=key, data_subkey=subkey, scenario=scenario,
                        h2_as_electricity=False
                    )
                    print(f"  -> Relative-to-Diesel plot saved: {key} ({scenario})")
                except Exception as e:
                    print(f"  ✗ FEHLER bei Relative-to-Diesel Plot {key} ({scenario}): {e}")
                    traceback.print_exc()
        

                if subkey == "energy":
                    try:
                        plot_relative_to_diesel(
                            all_mines_data, mine_name_map,
                            key=key, data_subkey=subkey, scenario=scenario,
                            h2_as_electricity=True
                        )
                        print(f"  -> Relative-to-Diesel elec_view plot saved: {key} ({scenario})")
                    except Exception as e:
                        print(f"  ✗ FEHLER bei Relative-to-Diesel elec_view Plot {key} ({scenario}): {e}")
                        traceback.print_exc()

        try:
            plot_truck_assumptions(config)
            print("  -> Truck assumptions plots saved.")
        except Exception as e:
            print(f"  ✗ FEHLER bei truck assumptions plot: {e}")
            traceback.print_exc()
            
        plot_base_mine_comparison(config)
        plot_regen_efficiency_by_mine(config)
        plot_payload_gvw(config)
        plot_energy_cost_assumptions(config)
        plot_energy_cost_assumptions_per_mine(config)

if __name__ == "__main__":
    main()
