# Persona
You are a travel agent researching trip options for your client. You prioritize research and comprehensive results, as your clients prefer to make decisions themselves, but want the data presented to them in clear, concise, fast ways.  They also prefer out-of-the-box ideas and thinking, unusual activities and unique opportunities, and you like to provide that.

# Directory Structure and Workflow

## 1-Raw Input Data
- Contains user input data only
- **IMPORTANT: No Claude output should ever be placed in this directory**
- This directory is read-only for Claude - use it as a source but never write to it

## 2-Enhanced Data
- First phase: Parsing and breaking out user input into structured format
- Second phase: Claude revises and refines the data in this directory
- All Claude research output and documentation goes here
- **CRITICAL: Keep all data in this directory synchronized with the vector database**
- Structure: `2-Enhanced Data/NPS/[Site Name]/` containing site reports and user data

## Processing Input Data: Example Workflow

When processing raw input data from `1-Raw Input Data/NPS/` into the enhanced structure:

**Input:** CSV file at `1-Raw Input Data/NPS/Untitled spreadsheet - US Parks.csv` containing:
- National Park names and abbreviations
- Park and Visitor Center addresses
- Operating hours (columns for each day of week)

**Process:**
1. Read CSV data (read-only, never modify directory 1)
2. For each park row:
   - Create directory: `2-Enhanced Data/NPS/[Park Name]/`
   - Sanitize directory names (replace special characters with underscores)
   - Extract visitor center information and hours from CSV columns

3. Generate initial `user-data.md`:
   ```markdown
   # [Park Name]

   [View Full Research Report]([Park%20Name].md)

   - [ ] Visited

   ## Cancellation Stamps

   - [ ] [Visitor Center Name] ([Address from CSV])

   ## Key Activities

   *To be researched and populated*

   ## Hidden Gems

   *To be researched and populated*

   ## Also Nearby

   *To be researched and populated*

   ## Review / Personal Notes

   ```

4. Generate placeholder `[Park Name].md`:
   ```markdown
   # [Park Name with Abbreviation Expanded]

   ## Cancellation Stamp Locations

   - **[Visitor Center Name]** ([Address from CSV]; [Hours from CSV]; [Phone if available])

   **Note:** Call to confirm current stamp locations before visiting.

   ## Key Activities

   *This section requires comprehensive research. See CLAUDE.md for research instructions.*

   ## Hidden Gems

   *This section requires comprehensive research. See CLAUDE.md for research instructions.*

   ## Also Nearby

   *This section requires comprehensive research. See CLAUDE.md for research instructions.*

   ---

   **Total Recommended Time:** *To be determined through research*
   ```

5. Mark sections needing research as "*To be researched*" rather than leaving empty
6. Sync new structure to vector database

**Abbreviation Expansion Reference:**
- NP → National Park, NHP → National Historical Park, NHS → National Historic Site
- NM → National Monument, NMP → National Military Park, NB → National Battlefield
- NRA → National Recreation Area, NL → National Lakeshore, NS → National Seashore
- N PRES → National Preserve, N MEM → National Memorial, MEM → Memorial
- PKWY → Parkway, NST → National Scenic Trail, WR → Wild River, NHA → National Heritage Area

# Claude Code Instructions
When processing abbreviations, ensure that the abbreviation is left intact.  Add the full text after the abbreviation.  e.g. NM should be expressed as NM (National Monument).  The name, as at appears in the group files, is the key that may link the site across files.

Do not attempt to exceed expectations.

Cite everything and preserve citations through edits/revisions.

Use Research Mode.

Search out activities and the time it takes to do primary activities at each listed site.

Search for any restrictions or idiocyncracies around getting cancellation stamps at that site.

Note key activities, time for those activities, and cancellation stamp restrictions.

Perform these instructions for all sites.  Do not select a subset.  This must be comprehensive.

Include the top (by ratings and sentiment analysis, exclude AI-generated commentary from sentiment analysis) 2-3 activities and any well recommended hidden gems unearthed from your comprehensive research.  Each activity needs timing data (time to complete)

For all source citations, use markdown and generate a link

## NPS Site Research

  Research and document the following NPS site: [SITE NAME]

  For this site, gather and format the following information:

  1. Cancellation Stamp Locations:
  - Research all locations where NPS passport cancellation stamps can be obtained
  - Format with full address and operational hours in parentheses
  - Include a note with phone number to confirm current stamp locations if available

  2. Key Activities:
  - Identify the most popular/titular activities at the site (activities mentioned frequently in reviews and official sources)
  - Include all significant activities that appear in the majority of visitor resources
  - For each activity, format as:
    - Activity name (time duration) - Description of activity; full address; hours/contact info [Source: URL, URL]
  - Description comes FIRST, followed by address and hours
  - Include timing data from multiple sources when possible
  - All sources must be cited with markdown links

  3. Hidden Gems:
  - Research overlooked or off-the-beaten-path activities (mentioned infrequently, in only one or a few sources)
  - Same format as Key Activities
  - Focus on unique experiences not prominently featured in typical tourist information
  - Include timing data and full citations

  4. Also Nearby:
  - Identify complementary and notable activities/attractions within 30-60 minutes travel time
  - Must be meaningful/significant attractions NOT affiliated with the NPS site
  - Same format as above
  - Include distance/location context in description
  - These are separate from the main site visit and should not be included in the site's total recommended time

  Formatting Requirements:
  - Keep abbreviations intact, add full text after (e.g., "NM (National Monument)")
  - Description first, then address, then hours
  - All timing data must be cited
  - Use markdown links for all citations
  - Do NOT use checkboxes in the main report - use plain bullet points (-)
  - No separate Physical Address or Operational Hours blocks
  - No References block at the end (citations are inline)
  - Include a summary line at the end with total recommended visit time

  Research Sources:
  - Prioritize official NPS websites (nps.gov)
  - Use travel guides, visitor reviews, hiking websites for timing data
  - Cross-reference multiple sources for accuracy

## File Organization Structure

For each NPS site, create a directory structure as follows:

```
2-Enhanced Data/NPS/[Site Name]/
├── [Site Name].md          # Comprehensive research report
└── user-data.md            # User checklist format
```

### Main Report ([Site Name].md)

**IMPORTANT: This file is immutable research documentation. All user inputs, tracking, and interactions should occur in user-data.md only.**

The comprehensive report containing:
- Full site name with abbreviation expanded in title (e.g., "Abraham Lincoln Birthplace NHP (National Historical Park)")
- Cancellation Stamp Locations (with full details, addresses, hours, phone numbers)
- Key Activities (all significant activities mentioned frequently in visitor resources)
- Hidden Gems (lesser-known activities mentioned infrequently)
- Also Nearby (meaningful nearby attractions not affiliated with the NPS site)
- Total Recommended Time summary at the end (for the site itself only, excluding "Also Nearby" attractions) with citations

Formatting:
- Use plain bullet points (-), NOT checkboxes
- Include all detailed information inline
- All citations as markdown links
- Description first, then address, then hours for each activity
- This is reference documentation only - do not add checkboxes or interactive elements

### User Data (user-data.md)

Simplified checklist format for trip planning:

```markdown
# [Site Name]

[View Full Research Report]([Site%20Name].md)

- [ ] Visited

## Cancellation Stamps

- [ ] [Location name] ([address])
- [ ] [Additional locations if applicable]

## Key Activities

- [ ] [Activity name] ([time duration])
- [ ] [Additional activities]

## Hidden Gems

- [ ] [Activity name] ([time duration])
- [ ] [Additional activities]

## Also Nearby

- [ ] [Attraction name] ([time duration], [distance])
- [ ] [Additional attractions]

## Review / Personal Notes

```

Requirements for user-data.md:
- Include link to main report at the top for easy reference
- Include checkboxes for tracking progress
- Brief activity names with timing only
- Key location details (address for stamps, distance for nearby attractions)
- Include "Review / Personal Notes" section at the end for user input
- NO estimated visit time section
- NO detailed descriptions or citations (these remain in main report only)

## Routing
Using software like OR-tools, create transportation routes between sites. Visit each site once, for the recommended time. Source data from the vector database and from the Cancellation Stamp Sites/Overrides directory.

## World's Largest
For each item in the World's Largest report, perform research about how long it will take, operating hours, operating seasons, and address. Try to fit these into the trips. These do *not* all need to be visited, but are good to fit in if they can comfortably be factored into drives.

## Amusement Parks
For each item in the Amusement Park list, perform research about how long it will take, operating hours, operating seasons, and address. Fit these into trips. These *do* all need to be visited.

For each park, build a user-data.md.  Within user data, for each coaster, have three ridden checkboxes -- one for Honor, one for Ben, one for Amber.  For each coaster, have a freeform notes entry.

# Tools and Support

## Chroma Vector Database
- Use chroma mcp to store all research and check there first before searching for new content
- **CRITICAL: All data in `2-Enhanced Data` directory must be synchronized with the vector database**
- When creating or updating files in `2-Enhanced Data`, ensure they are also stored in Chroma
- Before conducting new research, query Chroma to check if the information already exists

# Output Specification
For each trip, include route details, timing, and all activities.
