import pandas as pd
import numpy as np
import os
from PyADM1_2 import run_simulation
from manure_config import ADM1Simulator

def generate_ml_ready_data():
    sim_manager = ADM1Simulator()
    gubre_tipleri = list(sim_manager.manure_data.keys())
    
    # 1. Load your base files
    try:
        df_influent_base = pd.read_csv("digester_influent.csv")
        df_initial_base = pd.read_csv("digester_initial.csv")
    except FileNotFoundError:
        print("Error: digester_influent.csv or digester_initial.csv not found!")
        return

    master_frames = []

    # 2. Define Loading Scenarios (Multipliers for the influent concentration)
    # 1.0 = Standard, 1.5 = High Load, 2.0 = Overload (Stress Test)
    loading_scenarios = [1.0, 1.5, 2.0]

    print(f"Starting generation for {len(gubre_tipleri)} manure types across {len(loading_scenarios)} scenarios...")

    for key in gubre_tipleri:
        params = sim_manager.manure_data[key]
        
        for load in loading_scenarios:
            print(f"Running: Manure={key} | Load={int(load*100)}% ...")
            
            # Create a modified influent for this specific loading scenario
            # We scale the organic components (Sugars, Proteins, Lipids, Solids)
            df_influent_temp = df_influent_base.copy()
            organic_cols = ['S_su', 'S_aa', 'S_fa', 'X_xc', 'X_ch', 'X_pr', 'X_li']
            df_influent_temp[organic_cols] = df_influent_temp[organic_cols] * load
            
            # --- RUN ADM1 SIMULATION ---
            # This uses your PyADM1_2.py logic
            results = run_simulation(df_influent_temp, df_initial_base, params)
            
            # --- FEATURE ENGINEERING ---
            # Add 'Label' columns so the ML knows the context of the data
            results['manure_type'] = key
            results['load_factor'] = load
            results['k_hyd_ch'] = params['kinetics']['k_hyd_ch']
            results['k_hyd_pr'] = params['kinetics']['k_hyd_pr']
            results['k_hyd_li'] = params['kinetics']['k_hyd_li']
            
            # Calculate TARGET: Total VFA (The sum of all acid states)
            results['target_vfa'] = results['S_ac'] + results['S_pro'] + results['S_bu'] + results['S_va']
            
            # Rename gas methane for clarity
            results['target_methane'] = results['S_gas_ch4']
            
            # --- DOWNSAMPLING (Optional but Recommended) ---
            # Your data has ~27,000 rows. With 18 runs, that's nearly 500,000 rows.
            # We take every 4th row (1-hour intervals) to keep the file size manageable 
            # and reduce redundant data for the LSTM.
            res_downsampled = results.iloc[::4, :].copy()
            
            master_frames.append(res_downsampled)

    # 3. Save the Master File
    final_dataset = pd.concat(master_frames, ignore_index=True)
    
    # Basic Cleaning (Remove any NaN values that might have occurred if a simulation crashed)
    final_dataset = final_dataset.dropna()
    
    final_dataset.to_csv("adm1_master_dataset.csv", index=False)
    print("\n" + "="*30)
    print("SUCCESS: adm1_master_dataset.csv generated!")
    print(f"Total Rows: {len(final_dataset)}")
    print(f"Columns: {list(final_dataset.columns)}")
    print("="*30)

if __name__ == "__main__":
    generate_ml_ready_data()