# Route Mind
RouteMind computes how much food each donor should send to each recipient. It reads supply, demand, and coordinates from an Excel workbook and uses linear programming to minimize the total distance weighted by the amount shipped. A Gemini agent built with Google’s Agent Development Kit (ADK) lets you request an allocation through chat.
Quick start
From the repository root, create a Python virtual environment and install the dependencies:
python3 -m venv .venv
source .venv/bin/activate
python -m pip install google-adk numpy pandas scipy geopy matplotlib openpyxl
Create Agent-OptimalTransport/.env locally:
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_key_here
Keep .env out of Git. The agent in Agent-OptimalTransport/agent.py is configured with gemini-2.0-flash. If the API reports that this model is unavailable, change the model setting to a Gemini model available to your account.

From the repository root, start the ADK development UI:
adk web
Open the local URL printed by ADK, select the RouteMind agent package, and give it the absolute path to your workbook:
Find the optimal allocation using /absolute/path/to/Optimal_Transport_Data.xlsx.

Workbook format
Worksheet	Required columns
Donors	name, lat, lon, supply
Receivers	name, lat, lon, demand


Use decimal degrees for coordinates and a consistent unit for supply and demand, such as boxes. Total supply must equal total demand. The repository includes Optimal_Transport_Data.xlsx as a starting point.
Optimization model
For each donor and recipient pair, RouteMind computes the great-circle distance using geopy. SciPy’s linprog with the HiGHS solver finds the nonnegative shipment quantities that meet all supply and demand constraints while minimizing the sum of quantity times distance.

The result lists each nonzero shipment, its donor and recipient, the quantity, and the distance in kilometers. The objective value is reported in quantity-kilometers. The workbook solver can also be called directly from Python as solve_transport_from_excel(path).

The allocation uses geographic distances between coordinates. It does not calculate road mileage, driving time, or stop sequences.
