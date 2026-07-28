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
git clone https://github.com/Kilski64/Route-Optimization-Application.git
cd Route-Optimization-Application
pip install -r requirements.txt

## How do I run it?

\`\`\`bash
python Route_Optimization.py
\`\`\`

## How do I input my own data?

Data is entered directly through the app's UI on the **New Optimization** screen — there's no CSV or JSON file to prepare in advance. The form is broken into sections:

- **General** — optimization name, start date, and other high-level settings
- **Locations & Stops** — your start location plus each delivery/pickup stop, entered as an address (autocompleted and geocoded live on the map). Each stop can include:
  - Weight and volume (demand)
  - Load/unload time
  - Time window (HH:MM start/end)
- **Pickups & Deliveries** — pair up stops that must be picked up and dropped off by the same vehicle, in the correct order
- **Vehicles** — for each vehicle: capacity (max weight/volume), fixed cost, variable (per-distance) cost, and max travel time/distance
- **Optimization Settings** — global constraints like penalty weight for dropped stops and overall max travel distance

Once filled in, you can either run the solver directly or **save it as a draft**, which stores everything as a JSON file in the `drafts/` folder (viewable and reloadable later from **Load Optimizations**).

## Where do I add my API key? 

Currently, the API key is set directly in the main script. Open `Route_Optimization.py` and find this line near the top:

\`\`\`python
#INSERT API KEY GEMINI
API_KEY = ''
\`\`\`

Paste your Gemini API key between the quotes:

\`\`\`python
API_KEY = 'your-api-key-here'
\`\`\`

Get a key from [Google AI Studio](https://aistudio.google.com/)

## Data & Privacy

Your addresses and route data are **not stored on any external server** — everything is saved locally on your machine as JSON draft files. However, some data is transmitted to third-party services in order for the app to function:

- **Geocoding** — addresses you enter are sent to OpenStreetMap's Nominatim service (and/or ArcGIS) to convert them into coordinates.
- **Routing (OSRM)** — coordinates are sent to the public OSRM routing server to calculate driving distances and durations.
- **AI Suggestions (Gemini)** — after a route is solved, aggregated route data (vehicle counts, costs, node sequences, time windows, dropped stops) is sent to Google's Gemini API to generate improvement suggestions.

No data is sold, shared for advertising, or retained by this application beyond the local draft files you choose to save. That said, this project relies on public/third-party APIs (Nominatim, OSRM, Gemini), so you should review their respective privacy policies if you're working with sensitive or proprietary location data.

## What format does input data need to be in?

There's no file to prepare — data is entered via form fields in the app. Each field expects the following:

**Start Location**
| Field | Format | Example |
|---|---|---|
| Address | Text (US address) | `100 Main St, Springfield, IL` |
| Load time | Integer (minutes) | `15` |
| Weight / Volume | Decimal | `0` / `0` |
| Time window | HH:MM – HH:MM | `08:00` – `17:00` |

**Each Stop**
| Field | Format | Example |
|---|---|---|
| Address | Text (US address) | `245 Oak Ave, Springfield, IL` |
| Stop type | Dropdown: Pickup / Delivery | `Delivery` |
| Weight / Volume | Decimal (negative if Delivery) | `-25.5` / `-1.2` |
| Load / Unload time | Integer (minutes) | `10` / `10` |
| Time window | HH:MM – HH:MM | `09:00` – `12:00` |

**Vehicle**
| Field | Format | Example |
|---|---|---|
| Max weight / volume | Decimal | `1000` / `50` |
| Fixed cost | Decimal | `50.00` |
| Variable cost | Decimal (per distance unit) | `1.25` |
| Max travel time | Decimal (minutes) | `480` |
| Break/wait allowance | Decimal (minutes) | `30` |

**Global Optimization Settings**
| Field | Format | Example |
|---|---|---|
| Penalty (dropped stop cost) | Decimal | `500` |
| Max travel distance | Decimal (km) | `200` |

Addresses are validated and geocoded automatically as you type — the app will show matching suggestions on the map before you confirm a stop.

## Sample Data (Try It Yourself)

Use the values below to test the app end-to-end with a small, realistic example — 1 start location, 4 stops (including one pickup/delivery pair), and 2 vehicles.

**Start Location**
| Field | Value |
|---|---|
| Address | `100 Main St, Springfield, IL` |
| Load time | `10` min |
| Time window | `08:00` – `18:00` |

**Stops**
| # | Address | Type | Weight | Volume | Load/Unload Time | Time Window |
|---|---|---|---|---|---|---|
| 1 | `245 Oak Ave, Springfield, IL` | Delivery | `-50` | `-2.0` | `5` / `10` min | `09:00` – `11:00` |
| 2 | `88 Maple Dr, Springfield, IL` | Delivery | `-30` | `-1.5` | `5` / `10` min | `10:00` – `13:00` |
| 3 | `312 Birch Ln, Springfield, IL` | Pickup | `40` | `1.8` | `10` / `5` min | `09:30` – `12:00` |
| 4 | `77 Cedar Ct, Springfield, IL` | Delivery | `-40` | `-1.8` | `5` / `10` min | `12:00` – `15:00` |

> Pair stop **3 (Pickup)** with stop **4 (Delivery)** in the Pickups & Deliveries section — the package picked up at Birch Ln gets dropped off at Cedar Ct.

**Vehicles**
| Vehicle | Max Weight | Max Volume | Fixed Cost | Variable Cost | Max Travel Time | Break/Wait Allowance |
|---|---|---|---|---|---|---|
| Vehicle 1 | `500` | `20` | `50.00` | `1.25` | `480` min | `30` min |
| Vehicle 2 | `500` | `20` | `50.00` | `1.25` | `480` min | `30` min |

**Global Optimization Settings**
| Field | Value |
|---|---|
| Penalty (dropped stop cost) | `500` |
| Max travel distance | `200` km |

Once entered, run the solver — you should see both vehicles assigned routes, the pickup/delivery pair kept on the same vehicle and in the correct order, and a results dashboard showing total distance, time, and cost.

## Limitations

## What are the current limitations?

- **Single depot only** — the solver supports one shared start/end depot setup; it's not designed for multi-depot fleets.
- **No real-time traffic or rerouting** — OSRM distances/durations are static, point-in-time estimates and don't account for live traffic, road closures, or conditions changing after the route is solved.
- **US addresses only** — address autocomplete/geocoding is restricted to US locations (`country_codes=['us']`); international addresses are not currently supported.
- **Relies on the public OSRM demo server** — the app calls `router.project-osrm.org` over plain HTTP, which is rate-limited, has no uptime guarantee, and is not intended for production/commercial use. Large stop counts may fail or time out.
- **Geocoding is rate-limited** — Nominatim requests are throttled to one every 3 seconds, so entering many stops can be slow.
- **Solver time limit is fixed at 1 second** — routes are computed with a hardcoded 1-second search window (`time_limit.FromSeconds(1)`), which may return suboptimal solutions for larger or more complex problems rather than the true optimum.
- **Global settings are only read from the first vehicle** — max travel time, break allowance, penalty weight, and max travel distance are pulled from vehicle #1's inputs and applied to all vehicles, rather than being configurable independently per vehicle or truly global.
- **Costs and distances are rounded to integers** — fixed/variable costs and OSRM distance/duration values are rounded, which can introduce small inaccuracies in cost and ETA calculations.
- **No practical cap enforced on stops/vehicles**, but performance will degrade with larger inputs due to the OSRM table size limits, the fixed 1-second solver time limit, and Nominatim's rate limiting — the app has not been tested/tuned for large-scale (e.g. 100+ stop) problems.
- **AI suggestions are advisory only** — Gemini's recommendations are displayed for review; they are not automatically applied to the route.
- **No authentication or multi-user support** — this is a single-user desktop tool; saved drafts are plain local JSON files with no encryption or access control.
- **API key is hardcoded in source** — the Gemini API key currently lives directly in the script rather than an environment variable, which is a security risk if the file is shared or committed with a real key.
- **Windows-only visual styling** — `pywinstyles` (used for title-bar theming) only works on Windows; the app may look different or throw errors for that feature on macOS/Linux.
- **Single-threaded UI** — geocoding, OSRM, and Gemini API calls run on the main thread, so the UI can freeze/appear unresponsive during those requests.

## Does this account for real-time traffic or road closures?

No. Routing distances and travel times come from OSRM, which calculates estimates using the real OpenStreetMap road network (road types, geometry, turn restrictions, one-way streets), but with **static, pre-set speed profiles** — not live data. It does not factor in current traffic congestion, accidents, road closures, construction, or time-of-day variation. A route solved at 2 AM and the same route solved during rush hour will return identical time estimates, even though real-world drive times would differ.

## Troubleshooting

## I'm getting a solver error / no feasible solution found. What do I do?

This usually means the constraints you've entered are too tight for OR-Tools to find a valid route. Common causes to check first:

- **Cargo capacity too low** — total weight/volume demand across your stops exceeds what your configured vehicles can carry. Increase vehicle capacity or add more vehicles.
- **Time windows too narrow or conflicting** — a stop's time window may be too short to reach given travel time, or may not leave room for load/unload time. Widen the window or adjust load/unload durations.
- **Max travel time or max travel distance set too low** — vehicles may not have enough time/range to complete their assigned stops. Increase these limits per vehicle.
- **Pickup/delivery ordering conflicts** — a delivery's time window may occur before its paired pickup can realistically happen. Double-check pickup-before-delivery logic and time windows for paired stops.
- **Data entry errors** — a stop with an incorrect address (e.g. geocoded to the wrong location) can create unrealistic travel times. Confirm each stop pinned correctly on the map before solving.
- **Penalty weight too high or too low** — if "allow dropped stops" is enabled but the penalty is set very high, the solver may still fail rather than dropping a stop; try lowering the penalty so infeasible stops can be dropped instead of blocking the whole solution.

**If you're not sure which constraint is the problem:** try temporarily loosening one constraint at a time (e.g., raise capacity, widen time windows) and re-run the solver to isolate which one is causing the infeasibility.

## The AI suggestions aren't loading. What should I check?

- **Confirm your API key is set correctly.** Open `Route_Optimization_old_2.py` and check that `API_KEY` (near the top of the file) contains a valid key from [Google AI Studio](https://aistudio.google.com/) and hasn't been left blank or with extra spaces/quotes.
- **Check your internet connection** — the AI suggestions require a live call to the Gemini API.
- **Check the console/terminal output.** Errors from the Gemini call are printed to the console (not shown in the UI), so run the app from a terminal and look for a message starting with `❌ Error compiling route updates via Gemini API:` — this will usually show the real cause (invalid key, quota exceeded, network error, etc.).
- **Check API usage limits.** Google AI Studio keys have rate/quota limits on the free tier; if you've made many requests recently, you may be temporarily throttled.
- **Confirm model availability.** This app calls the `gemini-3-flash-preview` model specifically — if that model name changes, is deprecated, or isn't available for your API key/region, the call will fail. Check [Google's model documentation](https://ai.google.dev/gemini-api/docs/models) for the current model name if this happens.
- **No output at all?** If the solver didn't find a solution (see the previous FAQ), the AI suggestion step never runs, since there's no result to analyze yet.

## Contributing / Contact

## Can I contribute to this project? 

Yes! Feel free to open an issue or submit a pull request. 


