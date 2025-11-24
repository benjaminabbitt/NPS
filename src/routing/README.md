# NPS Trip Routing Tools

Advanced routing solutions for planning National Park Service trips with time constraints and optimization.

## Overview

This package provides three routing approaches:

1. **Enhanced OR-Tools Router** (`enhanced_ortools_router.py`) - Industry-standard optimization with time windows
2. **Reinforcement Learning Router** (`rl_router.py`) - Q-Learning based adaptive routing
3. **Hybrid Approach** (coming soon) - Combines OR-Tools with RL fine-tuning

## Features

### Enhanced OR-Tools Router

- ✅ **Visit Duration per Site** - Uses actual recommended times from research
- ✅ **Maximum Daily Drive Time** - Constraints on hours driven per day
- ✅ **Trip Duration Constraints** - Maximum total trip length
- ✅ **Time Windows** - Optional earliest/latest arrival times for sites
- ✅ **Geocoded Coordinates** - Extracted from Chroma vector database
- ✅ **Soft Constraints** - Penalizes violations rather than hard failures

**Usage:**
```python
from enhanced_ortools_router import EnhancedRouter, load_sites_from_chroma

# Load sites from database
sites = load_sites_from_chroma(limit=20)

# Create router with constraints
router = EnhancedRouter(
    sites=sites,
    avg_speed_mph=55.0,
    max_daily_drive_hours=8.0,  # Don't drive more than 8 hours/day
    max_total_trip_days=14      # Trip must fit in 14 days
)

# Solve
result = router.solve(
    start_index=0,
    time_limit_seconds=60,
    use_time_windows=False
)

# Results include:
# - Optimized route order
# - Total distance and time
# - Arrival times and days for each site
# - Constraint violations (if any)
```

### Reinforcement Learning Router

Uses Q-Learning to learn optimal routing policies through trial and error.

**Key Concepts:**
- **State**: Current location + visited sites + time/distance accumulation
- **Action**: Choose next site to visit
- **Reward**: Negative distance + penalties for constraint violations + bonuses for efficiency

**Advantages:**
- Can learn complex patterns and preferences
- Adapts to specific constraints through training
- Can be fine-tuned with custom reward functions
- Scales well with problem size

**Usage:**
```python
from rl_router import RoutingEnvironment, QLearningRouter, load_sites_from_json

# Create environment
env = RoutingEnvironment(
    sites=sites,
    max_daily_hours=12.0,
    max_trip_days=14,
    avg_speed_mph=55.0
)

# Create and train agent
agent = QLearningRouter(env=env)
results = agent.train(episodes=1000)

# Get best route
best_route = agent.get_best_route()
```

## Installation

```bash
# Install dependencies
pip install ortools numpy chromadb

# OR-Tools is the main dependency
# Chromadb is needed for loading site data
```

## Comparison: OR-Tools vs RL

| Feature | OR-Tools | Q-Learning RL |
|---------|----------|---------------|
| **Optimality** | Near-optimal (proven algorithms) | Converges to good solutions |
| **Speed** | Fast (seconds to minutes) | Slower (requires training) |
| **Flexibility** | Limited to defined constraints | Highly customizable rewards |
| **Interpretability** | Clear constraint violations | Black box decision making |
| **Scalability** | Excellent (100s of sites) | Good (limited by state space) |
| **Custom Preferences** | Hard to encode | Easy via reward shaping |

## Recommendation

**For most use cases**: Use the **Enhanced OR-Tools Router**
- Proven algorithms
- Fast and reliable
- Handles all common constraints
- Predictable behavior

**For custom preferences**: Use the **RL Router**
- When you want to learn from historical trip data
- When you have complex, hard-to-formalize preferences
- When you want adaptive routing that improves over time

## Advanced: Hybrid Approach (Future)

Combine both approaches:
1. Use OR-Tools to get a good initial solution
2. Fine-tune with RL to adapt to specific preferences
3. Learn from actual trip experiences to improve future routes

## Time Constraint Examples

### Example 1: Multi-Day Road Trip
```python
router = EnhancedRouter(
    sites=sites,
    avg_speed_mph=55.0,
    max_daily_drive_hours=6.0,     # Only drive 6 hours per day
    max_total_trip_days=10         # 10-day vacation
)
```

### Example 2: Weekend Trip
```python
router = EnhancedRouter(
    sites=sites,
    avg_speed_mph=60.0,
    max_daily_drive_hours=8.0,     # Can drive more on weekends
    max_total_trip_days=3          # 3-day weekend
)
```

### Example 3: With Time Windows
```python
# Create sites with specific time windows
sites = [
    SiteVisit(
        name="Site A",
        lat=40.0,
        lon=-100.0,
        visit_duration_minutes=120,
        earliest_arrival=0,        # Can visit anytime
        latest_arrival=1440        # But must visit within first day
    ),
    # ... more sites
]

router.solve(use_time_windows=True)
```

## Output Format

Both routers produce JSON output with:
```json
{
  "algorithm": "or-tools" | "q_learning",
  "stats": {
    "total_sites": 20,
    "total_distance_miles": 2543.1,
    "total_time_hours": 156.2,
    "total_days": 7,
    "avg_distance_per_day": 363.3
  },
  "route_details": [
    {
      "order": 1,
      "site": "Acadia NP",
      "lat": 44.3386,
      "lon": -68.2733,
      "visit_duration_hours": 8.0,
      "arrival_time_hours": 0.0,
      "arrival_day": 1
    },
    // ... more stops
  ]
}
```

## Future Enhancements

- [ ] Deep Q-Network (DQN) for larger state spaces
- [ ] Multi-objective optimization (distance + time + preferences)
- [ ] Integration with real-time traffic data
- [ ] Weather-aware routing
- [ ] Accommodation booking integration
- [ ] Interactive route visualization
- [ ] Mobile app integration

## Contributing

To add new routing algorithms:
1. Implement the router class with a `solve()` method
2. Return results in the standard format
3. Add documentation and examples
4. Include unit tests

## License

MIT License - See LICENSE file for details
