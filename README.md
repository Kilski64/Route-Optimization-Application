## FAQ
## General

## What does this project do?

The Route-Optimization-Application is a route optimization system that uses Google OR-Tools to generate the most efficient transportation routes that a vehicle can take based on specified user-defined constraints (e.g. cargo capacity, delivery quantities, etc.). Once the user insert at-least a single vehicle, the user can then run the route optimization which would then generate a dashboard, showing the optimized routes as well as areas where the user can improve in; through KPIs and charts as well as AI generated suggestions from Google AIStudios Gemini API.

## Who is this for?

This application is not production ready and in its current state would not be ideal for anyone; however, once the application is refined, it's ideal for logistics teams, small business owners, students, or anyone interested in exploring vehicle routing problems (VRP).

## What problem does this solve?

Coordinating multiple vehicles and transportation routes is an challenging endeavor in itself, but in addition, ensuring that each vehicle is taking the most optimal route; it's unrealistic and time consuming to rely on traditional or manual methods to achieve such tasks. This application seeks to solve by providing the user an easy, interactable, and painless way to plan most optimized routes without relying on traditional or manual methods; but instead automate the process.   

## How It Works?

RouteForge is a desktop application (built with `tkinter` / `ttkbootstrap`) that turns a list of stops, vehicles, and constraints into an optimized delivery/dispatch plan.

1. **Input** — On the "New Optimization" screen, you define your start location, stops (including optional pickup/delivery pairs), vehicles, and constraints (capacity, time windows, load/unload times, max travel distance, penalties for dropped stops, etc.).

2. **Geocoding** — Addresses are converted to coordinates using `geopy` (Nominatim/ArcGIS), and results are shown live on an interactive map via `tkintermapview`.

3. **Distance & Duration Matrix** — Once all locations are geocoded, the app builds a real-world driving distance/duration matrix by querying the [OSRM](http://project-osrm.org/) routing API.

4. **Optimization Engine** — The matrix and constraints are passed to Google OR-Tools' constraint solver (`ortools.constraint_solver`), which computes vehicle routes that respect time windows, capacity, pickup/delivery pairing, and other constraints, minimizing total cost/distance/time. For details on how the optimization engine itself works, consult the [OR-Tools routing documentation](https://developers.google.com/optimization/routing).

5. **AI Co-Pilot (Gemini)** — After a solution is generated, the app can send the routing results (dropped stops, vehicle loads, time windows, costs) to Google's Gemini API, which analyzes the solution and suggests operational adjustments (re-sequencing, fleet expansion, time-window shifts, etc.) through structured function calls.

6. **Results & Persistence** — Solved routes are displayed with dropped-stop reporting and AI-generated suggestions. Optimizations can be saved as drafts (JSON files) and reloaded later from the "Load Optimizations" screen.

## What optimization engine does this use? 

This project uses Google OR-Tools vehicle routing optimization

## What constraints can I define?

- Vehicle cargo capacity (weight and volume)
- Pickup and delivery quantities and pairings
- Fuel/range limits (max travel distance per vehicle)
- Time windows (per stop, and for the start/end depot)
- Number of vehicles
- Depot/start location(s)
- Load and unload time per stop
- Maximum travel time per vehicle
- Break/wait time allowance
- Fixed and variable cost per vehicle
- Penalty cost for dropped/unassigned stops

## How are AI suggestions generated?

After a route is solved, the results (vehicle count, capacity limits, total distance/time, dropped stops, node sequences, time windows, and cost settings) are sent to the Gemini API. Rather than returning plain text, Gemini is given a structured function (`analyze_and_adjust_route`) to call, so it responds with a defined list of actionable strategies — each tagged with a type (e.g. re-sequencing, fleet expansion, time-window shift, capacity redundancy), an impact level (High/Medium/Low), a description, and an estimated time savings. These are displayed as suggestion cards in the results view. If no adjustments are warranted, Gemini instead returns a plain-language explanation.

## What does the dashboard show?

- Optimized route visualization
- Vehicle-by-vehicle breakdown (route sequence, stops, capacity utilization)
- Total distance, total time, and estimated cost — each compared against a baseline (the route as originally entered, unoptimized)
- Number of stops served vs. dropped (with a list of any dropped addresses)
- An overall route health score
- AI-generated recommendations for further improvements

## Setup & Usage

1. **Add your Gemini API key**
   Open the main script and paste your key into the `API_KEY` variable near the top of the file:
```python
   API_KEY = 'your-api-key-here'
```
   Get a key from [Google AI Studio](https://aistudio.google.com/).

2. **Run the app**
```bash
   python Route_Optimization.py
```

3. **From the home screen**, choose:
   - **New Optimization** — build a route from scratch
   - **Load Optimizations** — reopen a previously saved draft
   - **Settings** — app configuration

4. **Set up a new optimization**
   - Enter your start location and any global settings (date, number of vehicles, etc.)
   - Add stops on the map, including pickup/delivery pairs if needed
   - Configure vehicles (capacity, cost, max travel time/distance)
   - Set optimization constraints (time windows, penalties for dropped stops, etc.)

5. **Run the solver**
   The app geocodes your addresses, builds a driving distance/time matrix via OSRM, and solves the route with OR-Tools.

6. **Review results**
   View the optimized routes, per-vehicle breakdowns, cost/time/distance savings, dropped stops, and AI-generated suggestions from Gemini.

7. **Save or reload**
   Save your optimization as a draft to revisit later from the **Load Optimizations** screen — drafts are stored locally as JSON files in the `drafts/` folder.

## Prerequisites

Python 3.9+
Required libraries: ortools, ttkbootstrap, customtkinter, tkintermapview, tkcalendar, requests, google-genai, geopy, pywinstyles (Windows only)
A Google AI Studio / Gemini API key (see Configuration)

## How do I install this?

bash
git clone https://github.com/[username]/[repo-name].git
cd [repo-name]
pip install -r requirements.txt

## How do I run it?

\`\`\`bash
python Route_Optimization.py
\`\`\`

How do I input my own data? [Explain expected input format — CSV columns, JSON schema, or UI form fields]

Where do I add my API key? [Explain — .env file, config.py, environment variable, etc.]

Data & Privacy

Does this store or share my data? [Explain — e.g., "No. All processing happens locally; data is not stored or transmitted beyond the optimization and AI API calls."]

What format does input data need to be in? [Specify columns/fields required, with an example row or template file link]

Limitations

What are the current limitations?

[e.g., Assumes static traffic conditions / no real-time rerouting]
[e.g., Optimized for single-depot problems]
[e.g., Max number of stops/vehicles supported]

Does this account for real-time traffic or road closures? [Yes/No — explain]

Troubleshooting

I'm getting a solver error / no feasible solution found. What do I do? This usually means constraints are too restrictive (e.g., cargo capacity too low for demand). Try loosening constraints or checking for data entry errors.

The AI suggestions aren't loading. What should I check? Confirm your API key is valid and correctly set in [location]. Check API usage limits if applicable.

Contributing / Contact

Can I contribute to this project? Yes! Feel free to open an issue or submit a pull request. [Add contribution guidelines link if available]

Who do I contact with questions? [Your name / LinkedIn / email]
