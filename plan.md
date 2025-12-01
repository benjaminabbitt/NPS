# Plan: Process 23 Priority NPS Sites (TX, NM, OK)

## Objective
Complete comprehensive research for 23 NPS sites in Texas, New Mexico, and Oklahoma, transforming them from placeholder status to fully documented entries matching the quality standard of completed sites like Acadia NP.

## Current State Analysis

### Completed Site Example (Acadia NP)
- 12+ cancellation stamp locations with full details (address, geocodes, hours, phone, citations)
- 3 Key Activities with timing (1.5-2 hours each), detailed descriptions, addresses, hours, multiple sources
- 3 Hidden Gems with same detail level
- 3 Also Nearby attractions
- Total recommended time summary with citations
- **All information includes inline markdown citations**

### Incomplete Site Example (White Sands NP)
- Only 1 basic visitor center entry
- Only 1 generic "Visitor Center Experience" activity
- Empty Hidden Gems section
- Empty Also Nearby section
- No total recommended time

### Gap to Close
Each site needs:
1. **Cancellation Stamps**: Research all stamp locations (often 2-5+ per site)
2. **Key Activities**: 3-20 popular activities with timing, descriptions, addresses, hours, sources
3. **Hidden Gems**: 3+ overlooked/unique experiences
4. **Also Nearby**: 3+ significant attractions within 30-60 minutes
5. **Total Time**: Summary with citations

## Priority Sites (23 Total)

### Texas (10 sites)
- Blackwell School NHS
- Guadalupe Mountains NP
- Lake Meredith NRA
- Lyndon B. Johnson NHP
- Padre Island NS
- Palo Alto Battlefield NHP
- Rio Grande WSR
- San Antonio Missions NHP
- Waco Mammoth National Monument
- White Sands NP (error: actually NM)

### New Mexico (11 sites)
- El Malpais NM
- El Morro NM
- Fort Davis NHS (error: actually TX)
- Fort Union NM
- Gila Cliff Dwellings NM
- Manhattan Project NHP
- Pecos NHP
- Petroglyph NM
- Salinas Pueblo Missions NM
- Valles Caldera N PRES
- White Sands NP

### Oklahoma (2 sites)
- Chickasaw NRA
- Washita Battlefield NHS

## Approach Options

### Option 1: Sequential Processing (One at a Time)
**Pros:**
- Highest quality control
- Learn from each site, improve process
- Easier to track progress
- Lower cognitive load

**Cons:**
- Slowest approach (~23 research sessions)
- Time-consuming

**Estimated Time:** 23-46 hours of research time

---

### Option 2: Parallel Batch Processing (All 23 at Once)
**Pros:**
- Fastest completion
- Efficient use of parallel subagents

**Cons:**
- Quality control challenges
- Overwhelming volume
- Difficult to verify all research
- MCP task tracking complexity

**Estimated Time:** 2-4 hours elapsed (but risk of quality issues)

---

### Option 3: Hybrid Batching (5 sites at a time) **[RECOMMENDED]**
**Pros:**
- Balance of speed and quality
- Manageable verification
- Learn and adjust between batches
- Good MCP task integration
- Can course-correct after each batch

**Cons:**
- Requires 5 batch cycles

**Estimated Time:** 10-20 hours over 5 batches

**Batch Structure:**
- **Batch 1** (5 sites): Major parks (Guadalupe Mtns, White Sands, Big Bend area)
- **Batch 2** (5 sites): Historical sites (San Antonio Missions, LBJ, Fort Union, etc.)
- **Batch 3** (5 sites): Natural monuments (El Malpais, El Morro, Gila Cliff, etc.)
- **Batch 4** (5 sites): Smaller sites (Petroglyph, Waco Mammoth, Lake Meredith, etc.)
- **Batch 5** (3 sites): Remaining sites

---

### Option 4: Phased Approach (Quality Tiers)
**Pros:**
- Get quick baseline for all sites
- Refine high-priority sites later
- Iterative improvement

**Cons:**
- Multiple passes required
- Inconsistent quality during transition

**Estimated Time:** 15-25 hours total

---

## Recommended Approach: Hybrid Batching

### Batch Size: 5 sites per batch
### Total Batches: 5 (4×5 + 1×3)
### Quality Standard: Match Acadia NP level of detail

## Implementation Plan

### Phase 1: Prepare Infrastructure
1. Create research template/checklist based on CLAUDE.md guidelines
2. Set up batch tracking in tasks.md (mark batches in MCP)
3. Create verification script to check completeness

### Phase 2: Execute Research Batches
For each batch:
1. **Mark sites as "In Progress" in tasks.md** via MCP
2. **Launch 5 parallel research agents** (general-purpose subagents)
3. **Each agent researches one site:**
   - Stamp locations (addresses, geocodes, hours, phone, sources)
   - 3-20 Key Activities (timing, descriptions, addresses, hours, sources)
   - 3+ Hidden Gems
   - 3+ Also Nearby
   - Total recommended time with citations
4. **Verify research quality:**
   - Check all sections populated
   - Verify inline citations present
   - Confirm timing data included
   - Check address/geocode format
5. **Update user-data.md** for each site
6. **Mark sites as "Done" in tasks.md**
7. **Commit batch** with descriptive message
8. **Brief review** before next batch

### Phase 3: Quality Assurance
1. Scan all 23 completed sites with verification script
2. Identify any gaps or quality issues
3. Address issues before considering complete

### Phase 4: Sync and Finalize
1. Sync all new data to Chroma vector database
2. Update incomplete_nps_sites.txt report
3. Final commit and push

## Batch Breakdown

### Batch 1: Major Parks (5 sites)
- Guadalupe Mountains NP (TX)
- White Sands NP (NM)
- Big Bend NP (TX) - **Wait, this isn't in the priority list!**
- Padre Island NS (TX)
- Carlsbad Caverns NP (NM) - **Wait, this isn't in the priority list!**

**REVISED Batch 1:**
- Guadalupe Mountains NP (TX)
- White Sands NP (NM)
- Padre Island NS (TX)
- Lake Meredith NRA (TX)
- Chickasaw NRA (OK)

### Batch 2: Historical/Cultural Sites (5 sites)
- San Antonio Missions NHP (TX)
- Lyndon B. Johnson NHP (TX)
- Palo Alto Battlefield NHP (TX)
- Blackwell School NHS (TX)
- Fort Union NM (NM)

### Batch 3: Natural Monuments & Geology (5 sites)
- El Malpais NM (NM)
- El Morro NM (NM)
- Gila Cliff Dwellings NM (NM)
- Petroglyph NM (NM)
- Valles Caldera N PRES (NM)

### Batch 4: Specialized Sites (5 sites)
- Pecos NHP (NM)
- Salinas Pueblo Missions NM (NM)
- Manhattan Project NHP (NM)
- Waco Mammoth National Monument (TX)
- Rio Grande WSR (TX)

### Batch 5: Final Sites (3 sites)
- Fort Davis NHS (TX)
- Washita Battlefield NHS (OK)
- Oklahoma City N MEM (OK)

## Success Criteria

For each site to be considered "complete":
- [ ] Cancellation stamp locations: 1+ entries with full details
- [ ] Key Activities: 3+ activities with timing, descriptions, addresses, sources
- [ ] Hidden Gems: 3+ unique experiences with full details
- [ ] Also Nearby: 3+ nearby attractions with distance/timing
- [ ] Total recommended time: Summary with citations
- [ ] All citations: Inline markdown links
- [ ] Format: Matches CLAUDE.md guidelines
- [ ] user-data.md: Updated with activity checklists
- [ ] MCP tasks.md: Site marked as "Done"

## Risk Mitigation

### Risk: Quality Inconsistency
**Mitigation:**
- Use verification script after each batch
- Review first batch thoroughly before continuing
- Maintain quality checklist

### Risk: Research Agent Failures
**Mitigation:**
- Launch batches sequentially (not all at once)
- Can restart failed sites individually
- Use haiku model for speed, sonnet for quality if needed

### Risk: MCP Task Sync Issues
**Mitigation:**
- Manual verification of tasks.md after each batch
- Git commits after each batch for rollback capability

### Risk: Missing or Incorrect Data
**Mitigation:**
- Require multiple sources for timing data
- Cross-reference official NPS websites
- Flag uncertainties in research

## Timeline Estimate

**Per Batch (5 sites):**
- Launch agents: 5 min
- Agent research time: 30-60 min (parallel)
- Verification: 15-30 min
- Updates & commit: 10 min
- **Total per batch: 1-2 hours**

**Total for 5 batches: 5-10 hours**

**Plus setup & QA: 1-2 hours**

**Grand Total: 6-12 hours**

## Questions for User

Before proceeding, clarify:

1. **Batch size preference?**
   - Option A: 5 sites per batch (recommended)
   - Option B: 10 sites per batch (faster, less control)
   - Option C: 3 sites per batch (slower, more control)

2. **Quality vs Speed trade-off?**
   - Option A: Match Acadia NP quality exactly (comprehensive)
   - Option B: Good enough (3 activities minimum, can enhance later)

3. **Model preference for research agents?**
   - Option A: Sonnet (higher quality, slower, more expensive)
   - Option B: Haiku (faster, cheaper, good enough quality)
   - Option C: Mixed (Sonnet for major parks, Haiku for smaller sites)

4. **Verification approach?**
   - Option A: Manual spot-check after each batch
   - Option B: Automated script only
   - Option C: Thorough review of each site

5. **MCP task tracking?**
   - Automatic updates after each site completion?
   - Batch updates after all 5 sites complete?

## Recommended Answers (Fast Start)

1. **Batch size:** 5 sites per batch
2. **Quality:** Match Acadia NP (comprehensive)
3. **Model:** Sonnet for all (quality over speed)
4. **Verification:** Automated script + spot-check first batch
5. **MCP tracking:** Batch updates after completion

This provides a good balance of quality, speed, and control.
