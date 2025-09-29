from google.adk.agents import Agent
from google.adk.tools import google_search

import numpy as np
import pandas as pd
from geopy.distance import great_circle
import matplotlib.pyplot as plt
from scipy.optimize import linprog
import json
import os

# --- Helper functions (unchanged) ---

def haversine_km(a, b):
    """Calculates the great-circle distance in kilometers between two (lat, lon) points."""
    return great_circle(a, b).km

def plot_plan(donors_df, receivers_df, solution_matrix, title="Transport plan"):
    """Visualizes the transport plan on a map."""
    # This function remains exactly the same as before.
    plt.figure(figsize=(8, 8))
    plt.scatter(donors_df['lon'], donors_df['lat'], c='green', s=donors_df['supply']*1.5, label='Donors', alpha=0.7)
    plt.scatter(receivers_df['lon'], receivers_df['lat'], c='red', s=receivers_df['demand']*1.5, label='Receivers', alpha=0.7)
    
    for i, row in donors_df.iterrows():
        plt.text(row['lon'] + 0.001, row['lat'] + 0.001, row['name'])
    for i, row in receivers_df.iterrows():
        plt.text(row['lon'] + 0.001, row['lat'] + 0.001, row['name'])

    max_w = solution_matrix.max() if solution_matrix.size > 0 else 1
    if max_w == 0: max_w = 1 # Avoid division by zero
    
    for i in range(len(donors_df)):
        for j in range(len(receivers_df)):
            w = solution_matrix[i, j]
            if w > 1e-6:
                plt.plot([donors_df.loc[i, 'lon'], receivers_df.loc[j, 'lon']],
                         [donors_df.loc[i, 'lat'], receivers_df.loc[j, 'lat']],
                         linewidth=1 + 4 * (w / max_w), alpha=0.6, color='gray')

    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.show()

# --- Core Logic (largely unchanged, but now a sub-function) ---

def _solve_lp_problem(donors_df, receivers_df):
    """Internal function to solve the LP given two dataframes."""
    # This function contains the optimization logic from the previous version.
    
    # 1. Build Cost Matrix
    m, n = len(donors_df), len(receivers_df)
    C = np.zeros((m, n))
    for i in range(m):
        for j in range(n):
            donor_coords = (donors_df.loc[i, 'lat'], donors_df.loc[i, 'lon'])
            receiver_coords = (receivers_df.loc[j, 'lat'], receivers_df.loc[j, 'lon'])
            C[i, j] = haversine_km(donor_coords, receiver_coords)

    # 2. Set up LP
    c = C.flatten()
    A_eq = []
    for i in range(m):
        row = np.zeros(m * n); row[i * n : (i + 1) * n] = 1; A_eq.append(row)
    for j in range(n):
        row = np.zeros(m * n); row[j::n] = 1; A_eq.append(row)
    A_eq = np.vstack(A_eq)
    b_eq = np.concatenate([donors_df['supply'].values, receivers_df['demand'].values])
    bounds = [(0, None)] * (m * n)

    # 3. Solve
    res = linprog(c=c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')

    # 4. Return results
    return res, C


# --- New Agent-Facing Tool Function ---

# --- Corrected Agent-Facing Tool Function ---

def solve_transport_from_excel(excel_file_path: str) -> dict:
    """Solves the optimal transport problem from an Excel file.

    This tool calculates the most cost-effective plan for distributing resources
    from donors to receivers based on geographical distance.

    Args:
        excel_file_path (str): The local path to the input Excel file.
            The file must contain two sheets: 'Donors' and 'Receivers',
            with columns for 'name', 'lat', 'lon', and 'supply'/'demand'.

    Returns:
        dict: A dictionary containing the solution status, plan, and total cost.
    """
    # 1. Input Validation: File existence
    if not os.path.exists(excel_file_path):
        return {'status': 'error', 'message': f"File not found at path: {excel_file_path}"}

    # ... the rest of the function's code remains exactly the same ...
    
    # 2. Data Loading and Validation
    try:
        donors_df = pd.read_excel(excel_file_path, sheet_name='Donors')
        receivers_df = pd.read_excel(excel_file_path, sheet_name='Receivers')
        
        required_donor_cols = {'name', 'lat', 'lon', 'supply'}
        required_receiver_cols = {'name', 'lat', 'lon', 'demand'}
        
        if not required_donor_cols.issubset(donors_df.columns):
            return {'status': 'error', 'message': f"'Donors' sheet is missing required columns. Need: {list(required_donor_cols)}"}
        if not required_receiver_cols.issubset(receivers_df.columns):
            return {'status': 'error', 'message': f"'Receivers' sheet is missing required columns. Need: {list(required_receiver_cols)}"}

    except Exception as e:
        return {'status': 'error', 'message': f"Failed to read or validate Excel file. Error: {e}"}

    # 3. Problem Balance Check
    total_supply = donors_df['supply'].sum()
    total_demand = receivers_df['demand'].sum()
    if not np.isclose(total_supply, total_demand):
        return {
            'status': 'error',
            'message': f"Data is unbalanced. Total supply ({total_supply}) does not equal total demand ({total_demand}).",
        }

    # 4. Call the core solver
    res, C = _solve_lp_problem(donors_df, receivers_df)

    # 5. Process and Format the Results
    if not res.success:
        return {
            'status': 'error',
            'message': f"LP solver failed: {res.message}",
        }
    
    x = res.x.reshape((len(donors_df), len(receivers_df)))
    total_cost = np.sum(x * C)
    
    plan = []
    for i in range(len(donors_df)):
        for j in range(len(receivers_df)):
            amount = x[i, j]
            if amount > 1e-6:
                plan.append({
                    'from_donor': donors_df.loc[i, 'name'],
                    'to_receiver': receivers_df.loc[j, 'name'],
                    'amount_units': round(amount, 2),
                    'distance_km': round(C[i, j], 2)
                })

    return {
        'status': 'success',
        'message': 'Optimal transport plan found and plot has been saved to transport_plan.png.',
        'total_cost_km_units': round(total_cost, 2),
        'transport_plan': plan
    }

# --- Example Usage ---

if __name__ == '__main__':
    # Step A: Create a dummy Excel file for the demonstration
    file_name = "distribution_plan.xlsx"
    donors_data = {
        'name': ['HarrisTeeter_A', 'HarrisTeeter_B', 'TraderJoes_C'],
        'lat': [35.2271, 35.2405, 35.2100],
        'lon': [-80.8431, -80.8200, -80.8600],
        'supply': [120.0, 80.0, 60.0]
    }
    receivers_data = {
        'name': ['FoodBank_X', 'Charity_Y', 'Shelter_Z'],
        'lat': [35.2350, 35.2150, 35.2450],
        'lon': [-80.8350, -80.8550, -80.8400],
        'demand': [100.0, 90.0, 70.0]
    }
    with pd.ExcelWriter(file_name) as writer:
        pd.DataFrame(donors_data).to_excel(writer, sheet_name='Donors', index=False)
        pd.DataFrame(receivers_data).to_excel(writer, sheet_name='Receivers', index=False)
    
    print(f"Created sample input file: '{file_name}'")

    # Step B: Agent calls the tool with the file path
    result = solve_transport_from_excel(file_name)

    # Step C: Agent receives and processes the structured result
    print("\n--- Agent Received Tool Output ---")
    # Pretty print JSON, handling the non-serializable data for printing
    result_for_print = result.copy()
    if 'solution_data' in result_for_print:
        del result_for_print['solution_data']
    print(json.dumps(result_for_print, indent=2))
    
    # Step D: If successful, the agent can decide to visualize
    if result.get('status') == 'success':
        print("\n--- Agent is now generating a visualization ---")
        sol_data = result['solution_data']
        plot_plan(
            sol_data['donors'], 
            sol_data['receivers'], 
            sol_data['matrix'], 
            title="Optimal Plan from Excel Input"
        )

root_agent = Agent(
    name="tool_agent",
    model="gemini-2.0-flash",
    
    description="Tool agent",
    instruction="""
    You are an agent that can resolve optimal transportation problems. First ask the location of the excel data file. Use the excel file as the parameter
    to call solve_transport_from_excel. 
    """,
    tools= [solve_transport_from_excel],
    # tools=[get_current_time],
    # tools=[google_search, get_current_time], # <--- Doesn't work
)