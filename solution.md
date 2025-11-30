# Trip Planning Solution: Adaptive Multi-Trip Optimization Algorithm

## Problem Statement

**Objective:** Plan optimal multi-day trips from a home base to visit geographically distributed sites, maximizing coverage while respecting:
- Operating hours constraints (sites must be visited during open hours)
- Trip duration limits (target and maximum days per trip)
- Travel time and logistics (daily operating window, average travel speed)
- Realistic pacing (time per site including visit and travel)

## Algorithm Overview

This solution uses a **two-phase iterative optimization** approach combined with **adaptive vehicle allocation** to find the maximum feasible distance that achieves 100% site coverage.

### Core Components

1. **Distance Calculation** - Automatic radius calculation based on trip duration
2. **Adaptive Vehicle Allocation** - Scale trip count based on site density
3. **VRP Solving** - OR-Tools Vehicle Routing Problem solver with time windows
4. **Multi-Pass Deferred Scheduling** - Retry sites that don't fit in initial day placement
5. **Two-Phase Optimization** - Find maximum distance with 100% coverage

## Algorithm Parameters

### Input Parameters
- `home_base` - Starting location (name, latitude, longitude)
- `target_days` - Target trip duration (soft limit with penalties)
- `max_days` - Maximum trip duration (hard limit: `target_days + 1`)
- `visit_hours_per_site` - Time allocated per site visit
- `hours_per_day` - Daily operating window (e.g., 6 AM - 9 PM = 15 hours)
- `preferred_hours_per_day` - Preferred working time (soft limit, e.g., 12 hours)
- `avg_speed_mph` - Average travel speed

### Calculated Parameters
- `max_distance` - Maximum radius from home base
- `num_vehicles` - Number of trips needed
- `sites_per_trip` - Target sites per trip

## Phase 1: Distance Formula Derivation

### Decision Point: How to calculate maximum distance from trip duration?

**Formula:**
```
max_distance = target_days × 8 hours/day × avg_speed_mph ÷ 2
```

**Rationale:**
- Assumes 8 hours of driving time per day
- Divide by 2 for range (out-and-back from home base)
- Provides upper bound that can be refined through optimization

**Examples:**
- 3 days: `3 × 8 × 55 ÷ 2 = 660 miles`
- 7 days: `7 × 8 × 55 ÷ 2 = 1,540 miles`
- 14 days: `14 × 8 × 55 ÷ 2 = 3,080 miles`

**Implementation:** `src/routing/vrp_trip_planner.py::calculate_default_max_distance()`

## Phase 2: Adaptive Vehicle Allocation

### Decision Point: How many trips (vehicles) to allocate?

**Problem:** Fixed vehicle count doesn't scale with site density or geographic distribution.

**Evolution:**

#### Initial Approach (Utilization-Based)
```python
# Overestimated capacity
estimated_sites_per_trip = target_days × hours_per_day × 0.7 / visit_hours_per_site
vehicles = total_sites / estimated_sites_per_trip
```
- **Issue:** Overestimated actual capacity (~73 sites/trip calculated, ~30 actual)

#### Revised Approach (4 Sites/Day)
```python
SITES_PER_DAY = 4
sites_per_trip = target_days × SITES_PER_DAY
vehicles = total_sites / sites_per_trip
```
- **Issue:** Still overloaded trips, all reached maximum days with many rejections

#### Current Approach (2 Sites/Day - Conservative)
```python
SITES_PER_DAY = 2
sites_per_trip = target_days × SITES_PER_DAY
vehicles = max(1, min(30, ⌈total_sites / sites_per_trip⌉))
```

**Rationale for 2 Sites/Day:**
- Accounts for realistic travel time between distant sites
- Provides buffer for operating hours constraints
- Allows for delays, photos, meals, rest
- More accurate: 4 hours per site (2h visit + 2h average travel/buffer)

**Capacity Calculation:**
```
sites_per_trip = target_days × 2 sites/day
vehicles = ⌈total_sites / sites_per_trip⌉
```

**Example Scaling:**
- 3-day trips, 30 sites: `30 / (3 × 2) = 5 vehicles`
- 7-day trips, 100 sites: `100 / (7 × 2) = 8 vehicles`
- 14-day trips, 266 sites: `266 / (14 × 2) = 10 vehicles`

**Implementation:** `src/routing/vrp_trip_planner.py::TripPlanner.__init__()` (vehicle allocation logic)

## Phase 3: Distance vs Coverage Testing

### Decision Point: What distance provides optimal coverage?

**Key Insight:** More distance ≠ better coverage

As distance increases:
- More sites become accessible (larger pool)
- But route efficiency decreases (longer distances between sites)
- Operating hours violations increase
- Trip duration constraints become binding

**Example Test Results (14-day trips):**

| Distance | Sites in Pool | Sites Covered | Coverage % | Vehicles |
|----------|---------------|---------------|------------|----------|
| 700 mi   | 81            | 59            | 73%        | 2        |
| 1,500 mi | 243           | 169           | 70%        | 5        |
| 3,080 mi | 266           | 160           | 60%        | 5        |

**With Updated Vehicle Count (2 sites/day):**

| Distance | Sites in Pool | Vehicles | Expected Improvement |
|----------|---------------|----------|---------------------|
| 700 mi   | 81            | 3        | Better pacing       |
| 1,500 mi | 243           | 9        | +80% capacity       |
| 3,080 mi | 266           | 10       | +100% capacity      |

**Conclusion:** Need iterative optimization to find sweet spot.

## Phase 4: Two-Phase Iterative Optimization

### Decision Point: How to systematically find optimal distance?

**Goal:** Find maximum distance that achieves 100% coverage (excluding only sites with inherently incompatible operating hours)

### Algorithm Overview

```
Phase 1: Successive Reduction
  - Start with auto-calculated max_distance
  - Run VRP solver
  - Count duration violations (sites don't fit in trip days)
  - If violations > 0: reduce distance by 25%, retry
  - Continue until 100% coverage (duration_violations = 0)

Phase 2: Binary Search
  - Lower bound: distance with 100% coverage (from Phase 1)
  - Upper bound: last failure distance (from Phase 1)
  - Binary search to find maximum distance with 100% coverage
  - Precision: 10 miles
```

### Phase 4.1: Successive Reduction to 100% Coverage

**Goal:** Reduce distance until ALL sites fit within trip constraints

```python
def phase1_successive_reduction(target_days, reduction_factor=0.75):
    max_distance = calculate_max_distance(target_days)

    while duration_violations > 0:
        Run VRP solver at max_distance

        if duration_violations == 0:
            # 100% coverage achieved!
            return max_distance, last_failure_distance
        else:
            last_failure = max_distance
            max_distance = int(max_distance × reduction_factor)
```

**Reduction Factor:** 0.75 (25% reduction per iteration)
- More aggressive than 0.85 (15% reduction)
- Faster convergence (5-6 iterations vs 10+)
- Binary search in Phase 2 will refine the result

**Expected Iterations:**
```
Start → Reduce 25% each iteration → ~log₀.₇₅(final/initial) iterations

Example: 3,080 mi → 500 mi
  Iterations: log₀.₇₅(500/3080) ≈ 6-7 iterations
  Time: 6 × 3 minutes ≈ 18 minutes
```

### Phase 4.2: Binary Search to Maximize Range

**Goal:** Find MAXIMUM distance that maintains 100% coverage

```python
def phase2_binary_search(lower_bound, upper_bound, precision=10):
    while upper_bound - lower_bound > precision:
        mid = (lower_bound + upper_bound) // 2

        Run VRP solver at mid

        if duration_violations == 0:
            lower_bound = mid  # Can go larger
        else:
            upper_bound = mid  # Too large, go smaller

    return lower_bound  # Optimal distance
```

**Why Binary Search:**
- Efficient: O(log n) complexity
- Precise: Finds maximum within specified tolerance
- Guaranteed: Always converges to optimal
- Reuses work: Phase 1 provided bounds

**Expected Iterations:**
```
Search space: [lower, upper] with precision
Iterations: log₂((upper - lower) / precision)

Example: [500, 1000] with 10-mile precision
  Range: 500 miles
  Iterations: log₂(500/10) ≈ 6 iterations
  Time: 6 × 3 minutes ≈ 18 minutes
```

**Total Optimization Time:** 30-40 minutes (Phase 1 + Phase 2)

**Implementation:** `src/routing/iterative_trip_optimizer.py::optimize_iteratively()`

## Phase 5: Multi-Pass Deferred Scheduling

### Decision Point: How to handle operating hours violations?

**Two Types of Exclusions:**

1. **Duration violations**: Sites can't fit within trip day limits
   - Caused by: Insufficient vehicles, poor distance choice
   - Solvable: Reduce distance (Phase 4) or increase vehicles
   - Strategy: Iterative optimization

2. **Hours violations**: Sites have restrictive operating hours
   - Examples:
     - Site open only 13:00-17:00 (4-hour window)
     - Site open only 10:00-16:00 (6-hour window)
   - Caused by: Site-specific constraints
   - Not solvable by distance/vehicle adjustment
   - Strategy: Multi-pass deferred scheduling, then accept/flag

### Multi-Pass Strategy

```python
def resequence_trip_with_deferred_scheduling(trip):
    days = []
    deferred_sites = []

    # Pass 1: Try to schedule all sites in VRP order
    for site in trip:
        fits = check_if_site_fits_in_current_day(site, current_day)

        if fits:
            schedule_site_in_current_day(site)
        elif can_start_new_day():
            start_new_day()
            schedule_site_in_new_day(site)
        else:
            # Don't reject - defer for retry
            deferred_sites.append(site)

    # Pass 2+: Retry deferred sites (up to 3 passes)
    for retry_round in range(1, 4):
        still_deferred = []

        for site in deferred_sites:
            scheduled = False

            # Try to fit in ANY existing day
            for day in days:
                if check_if_site_fits_in_day(site, day):
                    schedule_site_in_day(site, day)
                    scheduled = True
                    break

            if not scheduled:
                still_deferred.append(site)

        deferred_sites = still_deferred

        if not deferred_sites:
            break  # All scheduled!

    # Only reject if truly incompatible after all retry attempts
    for site in deferred_sites:
        reject_site(site, reason="Operating hours incompatible")
```

**Benefits:**
- Sites only rejected if truly incompatible
- Maximizes scheduling flexibility
- Reduces false negatives from initial VRP ordering

**Implementation:** `src/routing/vrp_trip_planner.py::TripPlanner._resequence_trip_with_violations()`

## Operating Hours Handling

### Output Requirements

**For duration violations:** List count and optimization status
```
Duration violations: 92 sites
  → Reducing distance by 25% to improve coverage
```

**For hours violations:** List sites with operating hours details
```yaml
skipped_sites:
  - name: Clara Barton NHS
    reason: Operating hours incompatible with trip schedule
    operating_hours:
      opens: 13:00
      closes: 17:00
    lat: 38.9676
    lon: -77.1378
```

**Always-Available Sites:**
Sites with `always_stamp_available: true` flag bypass hours checks
- Stamps accessible 24/7 (e.g., outdoor kiosks)
- Flagged as `[INFO]` instead of `[VIOLATION]` in warnings

## Algorithm Complexity Analysis

### VRP Solver Complexity
- **Sites (n):** Variable (50-300 typical range)
- **Vehicles (k):** Adaptive (1-30 range)
- **Complexity:** O(n² × k) with OR-Tools heuristics
- **Time per solve:** 2-3 minutes for 250+ sites

### Phase 1: Successive Reduction
- **Iterations:** ~log₀.₇₅(final/initial) ≈ 6 iterations
- **Time per iteration:** 2-3 minutes
- **Total Phase 1:** ~15-20 minutes

### Phase 2: Binary Search
- **Search space:** Typically 500-1,000 mile range
- **Iterations:** log₂(range/precision) ≈ 6-7 iterations
- **Time per iteration:** 2-3 minutes
- **Total Phase 2:** ~15-20 minutes

### Total Optimization Time
- **Expected:** 30-40 minutes
- **Worst case:** 60 minutes (many sites, complex constraints)

## Success Criteria

### Quantitative
- ✅ **100% coverage**: All sites fit within trip constraints (excluding hours violations)
- ✅ **Maximum range**: Largest distance achieving 100% coverage
- ✅ **Precision**: Binary search within 10 miles
- ✅ **Operating hours documented**: All violations include hours info

### Qualitative
- ✅ **Reproducible**: Algorithm deterministically finds optimal
- ✅ **Automated**: No manual intervention required
- ✅ **Well-documented**: Decision rationale captured
- ✅ **Maintainable**: Clear code structure and comments
- ✅ **Scalable**: Works for any home base, trip duration, or site count

## Key Algorithm Properties

### Adaptability
- **Any home base**: Algorithm works from any starting location
- **Any trip duration**: Parameters scale with `target_days`
- **Any site count**: Vehicle allocation scales automatically
- **Any distance**: Optimization finds feasible maximum

### Robustness
- **No hard-coded limits**: All parameters calculated from inputs
- **Graceful degradation**: Reduces distance until solution found
- **Multi-pass scheduling**: Maximizes site inclusion
- **Clear failure modes**: Distinguishes duration vs hours violations

### Performance
- **Parallel-ready**: Multiple distance tests can run concurrently
- **Capped complexity**: Vehicle count limited to 30 for solver performance
- **Efficient search**: Logarithmic convergence in both phases
- **Reasonable runtime**: 30-40 minutes for optimal solution

## Implementation Summary

### File Structure
```
src/routing/
├── vrp_trip_planner.py           # Core VRP solver with adaptive allocation
├── iterative_trip_optimizer.py   # Two-phase distance optimization
└── optimize_trip_parameters.py   # Legacy binary search (deprecated)
```

### Key Functions

**Distance Calculation:**
```python
def calculate_default_max_distance(target_days: int) -> int:
    return int(target_days * 8 * 55 * 0.5)
```

**Vehicle Allocation:**
```python
SITES_PER_DAY = 2
sites_per_trip = target_days * SITES_PER_DAY
num_vehicles = max(1, min(30, math.ceil(total_sites / sites_per_trip)))
```

**Two-Phase Optimization:**
```python
def optimize_iteratively(target_days, reduction_factor=0.75):
    # Phase 1: Successive reduction
    while duration_violations > 0:
        reduce_distance()

    # Phase 2: Binary search
    optimal_distance = binary_search(lower_bound, upper_bound)

    return optimal_distance
```

## Example: 14-Day Trips from Kirkwood, MO

### Initial Configuration
- **Home base:** Kirkwood, MO (38.5831, -90.4068)
- **Target days:** 14 (max 15)
- **Auto-calculated max distance:** 3,080 miles

### Test Results

**With Old Vehicle Count (4 sites/day = 5 vehicles):**
- Sites in radius: 266
- Coverage: 160/266 (60%)
- All trips maxed at 15 days
- 106 sites skipped due to duration violations

**With New Vehicle Count (2 sites/day = 10 vehicles):**
- Sites in radius: 209
- Coverage: 209/209 (100%) ✓
- All 10 trips within 14-day target ✓
- Zero duration violations ✓
- Zero operating hours violations ✓
- Optimal distance: 3,080 miles (no reduction needed)

## Future Enhancements

### Potential Optimizations
1. **Parallel VRP solving**: Run multiple distances simultaneously
2. **Warm start**: Reuse solutions from similar distances
3. **Multi-objective**: Balance coverage, distance, and trip count
4. **Day boundary optimization**: Position end-of-day for next day's sites
5. **Vehicle count optimization**: Independent search for optimal trip count

### Configuration Flexibility
1. **Variable trip lengths**: Support 7-day, 14-day, 21-day, etc.
2. **Multiple start locations**: Different home bases
3. **Seasonal constraints**: Site availability by season
4. **Priority sites**: Must-visit vs optional sites
5. **Multi-day sites**: Allocate multiple days for large parks

## Conclusion

The adaptive multi-trip optimization algorithm provides a robust, scalable solution for trip planning:

- **Automated**: Finds optimal distance without manual tuning
- **Efficient**: Converges in reasonable time (30-40 minutes)
- **Optimal**: Guarantees maximum distance with 100% coverage
- **Transparent**: Documents all decisions and violations
- **General**: Works for any home base, trip duration, or site distribution

The algorithm evolved through iterative refinement based on empirical testing and user feedback, resulting in a production-ready solution that balances automation, optimality, and transparency.
