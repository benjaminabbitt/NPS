import csv
import sys

sites = set()

# Read US Parks CSV
with open('Cancellation Stamp Sites with Timing/Inputs/Untitled spreadsheet - US Parks.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        site_name = row.get('National Park', '').strip()
        if site_name and site_name != 'National Park':
            sites.add(site_name)

# Read Trails CSV
with open('Cancellation Stamp Sites with Timing/Inputs/Untitled spreadsheet - Trails.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        site_name = row.get('National Park', '').strip()
        if site_name and site_name != 'National Park':
            sites.add(site_name)

# Sort and print
for site in sorted(sites):
    print(site)

print(f"\n\nTotal unique sites: {len(sites)}", file=sys.stderr)
