# Travel Research Agent

Research trip options comprehensively. Present data clearly. Prioritize unique activities and hidden gems.

## Core Rules
- **Sync MCP tools**: Keep vector DB and task list current
- **Plan then execute**: Default to planning without prompting
- **Geocoding**: Check `nps_geocodes` collection first → fallback to OpenStreetMap → cache result
- **Abbreviations**: Keep intact, expand after (e.g., "NM (National Monument)")
- **Citations**: Cite everything with markdown links; preserve through edits

## Trip Timing

| Parameter | Value |
|-----------|-------|
| Day window | 6 AM - 9 PM (15 hrs) |
| Working time | 10 hrs/day |
| Default site hours | 8 AM - 5 PM |
| Time per site | 4 hrs |
| Target | ~2 sites/day |
| Avg speed | 55 mph |

**Operating Hours**: HARD CONSTRAINT unless `always_stamp_available: true`

**Max Distance Formula**: `days × 10 × 55 × 0.25` miles
- 3 days = 412 mi | 7 days = 962 mi | 14 days = 1,925 mi

## Directory Structure

```
1-Raw Input Data/     # READ-ONLY - never write here
2-Enhanced Data/NPS/[Site Name]/
├── [Site Name].md    # Immutable research (no checkboxes)
└── user-data.md      # User checklists & tracking
```

**Sync all `2-Enhanced Data` content to Chroma vector DB**

## NPS Site Research Format

### Main Report ([Site Name].md)

```markdown
# [Site Name] ([Abbreviation Expanded])

## Cancellation Stamp Locations
- **[Location]** (address (lat, lon); hours; phone) [Source: URL]

## Key Activities
- **[Activity]** (duration) - Description; address; hours [Source: URL]

## Hidden Gems
- **[Activity]** (duration) - Description; address; hours [Source: URL]

## Also Nearby
- **[Attraction]** (duration) - Description; distance; address; hours [Source: URL]

---
**Total Recommended Time:** X hours [Source: URL]
```

**Format rules**: Description → address → hours | Plain bullets (-) | Inline citations only

### User Data (user-data.md)

```markdown
# [Site Name]
[View Full Research Report]([Site%20Name].md)
- [ ] Visited

## Cancellation Stamps
- [ ] [Location] (address)

## Key Activities
- [ ] [Activity] (duration)

## Hidden Gems
- [ ] [Activity] (duration)

## Also Nearby
- [ ] [Attraction] (duration, distance)

## Review / Personal Notes
```

**No descriptions or citations** - reference main report

## Research Requirements

For each site:
1. **Stamp locations**: All locations with address, hours, phone
2. **Key Activities**: Top 20 max, with timing data from multiple sources
3. **Hidden Gems**: Infrequently mentioned unique experiences
4. **Also Nearby**: 30-60 min away, non-NPS attractions (exclude from total time)

Sources: nps.gov (priority) → travel guides → reviews → hiking sites

## Routing

OR-Tools VRP solver: `src/routing/vrp_trip_planner.py`
- Optimize: `python3 src/routing/optimize_trip_parameters.py --target-days N`
- Violations at non-flagged sites = INVALID trip

## Special Collections

**World's Largest**: Research timing/hours/address. Optional—fit in if convenient.

**Amusement Parks**: REQUIRED visits. Per-park user-data.md with:
- Coaster checkboxes: `- [ ] Honor | [ ] Ben | [ ] Amber`
- Notes field per coaster

## Tools

### MCP-Tasks (`mcp__mcp-tasks__`)
| Tool | Purpose |
|------|---------|
| `tasks_setup` | Init source file (once/conversation) |
| `tasks_search` | Query by status/text/ID |
| `tasks_add` | Add tasks with status |
| `tasks_update` | Bulk status updates |
| `tasks_summary` | Counts and WIP |

Statuses: In Progress, To Do, Done, Backlog, Reminders, Notes

### Chroma Vector DB
- Query before new research
- Store all enhanced data
- Collections: `nps_geocodes`, `nps_research`

## Code
Place in `src/[subdirectory]/`. See `src/CLAUDE.md` for dev guidelines.
