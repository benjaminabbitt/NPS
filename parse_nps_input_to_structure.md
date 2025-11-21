# Parse NPS Input Data to Enhanced Data Structure

## Objective
Process NPS data from `1-Raw Input Data/NPS/` and create the initial directory structure and files in `2-Enhanced Data/NPS/` based on the format defined in CLAUDE.md.

## Input Source
Read from: `C:\Users\Ben\workspace\NPS\1-Raw Input Data\NPS\Untitled spreadsheet - US Parks.csv`

CSV Structure:
- Columns: State, In the Book, Completed, Est. Hours, National Park, Address, City, State, Zip, Sunday-Saturday (park hours), Visitor Center Location, Visitor Center Address, Visitor Center City, Visitor Center State, Visitor Center Zip, Sunday-Saturday (visitor center hours)

## Output Destination
Create in: `C:\Users\Ben\workspace\NPS\2-Enhanced Data\NPS\[Site Name]/`

For each NPS site in the CSV:

### Step 1: Create Directory Structure
- Create directory: `2-Enhanced Data/NPS/[National Park Name]/`
- Replace special characters in directory names with underscores for filesystem compatibility
- Example: "Denali NP & PRES" → "Denali NP _ PRES"

### Step 2: Create Initial user-data.md
Create `user-data.md` file with structure populated from CSV data:

```markdown
# [National Park Name]

[View Full Research Report]([National%20Park%20Name].md)

- [ ] Visited

## Cancellation Stamps

- [ ] [Visitor Center Location] ([Visitor Center Address, City, State Zip])

## Key Activities

*To be researched and populated*

## Hidden Gems

*To be researched and populated*

## Also Nearby

*To be researched and populated*

## Review / Personal Notes

```

**Visitor Center Hours Handling:**
- Convert the CSV hours columns (Sunday-Saturday) into a readable format
- Example: If hours are "9:00 AM–5:00 PM" for all days, note "Daily 9:00 AM - 5:00 PM"
- If "Closed" on some days, list the days when open
- Add this information as a comment in the user-data.md for reference

### Step 3: Create Placeholder Main Report
Create `[National Park Name].md` file with placeholder structure:

```markdown
# [National Park Name with Abbreviation Expanded]

## Cancellation Stamp Locations

- **[Visitor Center Location]** ([Visitor Center Address, City, State Zip]; [Hours from CSV]; [Phone if available])

**Note:** Call to confirm current stamp locations and seasonal hours before visiting.

## Key Activities

*This section requires comprehensive research. See CLAUDE.md for research instructions.*

## Hidden Gems

*This section requires comprehensive research. See CLAUDE.md for research instructions.*

## Also Nearby

*This section requires comprehensive research. See CLAUDE.md for research instructions.*

---

**Total Recommended Time:** *To be determined through research*
```

**CSV Data to Extract:**
- National Park name (column: "National Park")
- Expand abbreviation in title (NM → National Monument, NHP → National Historical Park, etc.)
- Park address from: Address, City, State, Zip columns
- Park hours from: Sunday-Saturday columns (columns 9-15)
- Visitor Center name from: "Visitor Center Location" column
- Visitor Center address from: Visitor Center Address, City, State, Zip columns
- Visitor Center hours from: Sunday-Saturday columns (columns 23-29)

### Step 4: Handle Special Cases

**Missing Data:**
- If visitor center location is empty, note "Contact park for stamp locations"
- If hours show "Open" for all days, note "Open daily, contact for specific hours"
- If park has "No Stamp" in any field, add note in cancellation section

**Abbreviation Expansion Map:**
```
NP → National Park
NHP → National Historical Park
NHS → National Historic Site
NM → National Monument
NMP → National Military Park
NB → National Battlefield
NRA → National Recreation Area
NL → National Lakeshore
NS → National Seashore
N PRES → National Preserve
N MEM → National Memorial
PKWY → Parkway
NST → National Scenic Trail
WR → Wild River
NHA → National Heritage Area
MEM → Memorial
```

### Step 5: Validation
After creating files:
- Verify directory exists for each CSV row
- Verify both files (user-data.md and [Site Name].md) exist in each directory
- Ensure markdown syntax is valid
- Confirm visitor center address and hours are properly extracted

## Processing Instructions

1. Read the entire CSV file
2. For each row (skip header and empty rows):
   - Extract National Park name and create sanitized directory name
   - Create directory if it doesn't exist
   - Generate user-data.md with CSV data
   - Generate placeholder main report with CSV data
3. Log any errors or missing data
4. Provide summary of:
   - Total sites processed
   - Sites with missing visitor center data
   - Sites with missing hours data
   - Any special cases encountered

## Important Notes

- **Do NOT write to `1-Raw Input Data` directory** - it is read-only
- **All output goes to `2-Enhanced Data/NPS/`**
- This creates the initial structure; comprehensive research will be added later per CLAUDE.md instructions
- Preserve the exact park names as they appear in the CSV for consistency
- Mark sections as "To be researched" rather than leaving them empty or making assumptions
