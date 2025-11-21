#!/usr/bin/env python3
"""
Update park markdown files with real addresses and add back-links from coasters
"""

import asyncio
import httpx
from pathlib import Path
from bs4 import BeautifulSoup
import re

# Known park addresses (will be supplemented with web search)
KNOWN_ADDRESSES = {
    "Cedar Point": "1 Cedar Point Dr, Sandusky, OH 44870",
    "Kings Island": "6300 Kings Island Dr, Mason, OH 45040",
    "Carowinds": "14523 Carowinds Blvd, Charlotte, NC 28273",
    "Busch Gardens Tampa": "10165 McKinley Dr, Tampa, FL 33612",
    "Busch Gardens Williamsburg": "1 Busch Gardens Blvd, Williamsburg, VA 23185",
    "SeaWorld Orlando": "7007 Sea World Dr, Orlando, FL 32821",
    "SeaWorld San Antonio": "10500 SeaWorld Dr, San Antonio, TX 78251",
    "Six Flags Magic Mountain": "26101 Magic Mountain Pkwy, Valencia, CA 91355",
    "Six Flags Great Adventure": "1 Six Flags Blvd, Jackson, NJ 08527",
    "Six Flags Great America": "1 Great America Pkwy, Gurnee, IL 60031",
    "Six Flags Over Texas": "2201 E Road to Six Flags St, Arlington, TX 76010",
    "Six Flags Over Georgia": "275 Riverside Pkwy SW, Austell, GA 30168",
    "Six Flags Fiesta Texas": "17000 I-10 West, San Antonio, TX 78257",
    "Six Flags New England": "1623 Main St, Agawam, MA 01001",
    "Six Flags Discovery Kingdom": "1001 Fairgrounds Dr, Vallejo, CA 94589",
    "Six Flags St Louis": "4900 Six Flags Rd, Eureka, MO 63025",
    "Six Flags Darien Lake": "9993 Alleghany Rd, Darien Center, NY 14040",
    "Hersheypark": "100 W Hersheypark Dr, Hershey, PA 17033",
    "Dollywood": "2700 Dollywood Parks Blvd, Pigeon Forge, TN 37863",
    "Silver Dollar City": "399 Silver Dollar City Pkwy, Branson, MO 65616",
    "Knott's Berry Farm": "8039 Beach Blvd, Buena Park, CA 90620",
    "Universal Islands of Adventure": "6000 Universal Blvd, Orlando, FL 32819",
    "Universal Studios Florida": "6000 Universal Blvd, Orlando, FL 32819",
    "Universal Epic Universe": "5775 Universal Blvd, Orlando, FL 32819",
    "Walt Disney World - Magic Kingdom": "1180 Seven Seas Dr, Lake Buena Vista, FL 32830",
    "Walt Disney World - Disney's Animal Kingdom": "2901 Osceola Pkwy, Lake Buena Vista, FL 32830",
    "Walt Disney World - Epcot": "200 Epcot Center Dr, Lake Buena Vista, FL 32821",
    "Holiday World": "452 E Christmas Blvd, Santa Claus, IN 47579",
    "Kentucky Kingdom": "937 Phillips Ln, Louisville, KY 40209",
    "Kennywood": "4800 Kennywood Blvd, West Mifflin, PA 15122",
    "Knoebels": "391 Knoebels Blvd, Elysburg, PA 17824",
    "Lagoon": "375 N Lagoon Dr, Farmington, UT 84025",
    "Lake Compounce": "185 Enterprise Dr, Bristol, CT 06010",
    "Worlds of Fun": "4545 Worlds of Fun Ave, Kansas City, MO 64161",
    "Valleyfair!": "1 Valleyfair Dr, Shakopee, MN 55379",
    "California's Great America": "4701 Great America Pkwy, Santa Clara, CA 95054",
    "Kings Dominion": "16000 Theme Park Way, Doswell, VA 23047",
    "Dorney Park": "3830 Dorney Park Rd, Allentown, PA 18104",
    "Michigan's Adventure": "4750 Whitehall Rd, Muskegon, MI 49445",
    "Waldameer": "220 Peninsula Dr, Erie, PA 16505",
    "Fun Spot America Atlanta": "5551 Georgia 85, Fayetteville, GA 30214",
    "Adventureland Iowa": "3200 Adventureland Dr, Altoona, IA 50009",
    "Lost Island Theme Park": "2225 E Shawnee Rd, Waterloo, IA 50701",
    "Silverwood Theme Park": "27843 N Highway 95, Athol, ID 83801",
    "Mt. Olympus Water & Theme Park": "1881 Wisconsin Dells Pkwy, Wisconsin Dells, WI 53965",
    "Kemah Boardwalk": "215 Kipp Ave, Kemah, TX 77565",
}


async def search_park_address(park_name: str, client: httpx.AsyncClient) -> str:
    """Search for park address if not in known addresses"""
    if park_name in KNOWN_ADDRESSES:
        return KNOWN_ADDRESSES[park_name]

    # For unknown parks, return a placeholder
    return f"{park_name} (address to be researched)"


async def update_park_files():
    """Update all park files with real addresses"""
    base_dir = Path("Amusement Parks")
    park_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name != "Inputs"]

    print(f"Updating addresses for {len(park_dirs)} parks...")

    async with httpx.AsyncClient() as client:
        for park_dir in park_dirs:
            park_file = park_dir / f"{park_dir.name}.md"
            if not park_file.exists():
                continue

            # Get address
            address = await search_park_address(park_dir.name, client)

            # Read file
            with open(park_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Replace address section
            lines = content.split('\n')
            new_lines = []
            skip_next = False

            for i, line in enumerate(lines):
                if skip_next:
                    skip_next = False
                    continue

                if line.strip() == '## Address':
                    new_lines.append(line)
                    new_lines.append('')
                    new_lines.append(address)
                    # Skip the old address lines
                    skip_next = True
                    # Skip until we hit the next section
                    j = i + 2
                    while j < len(lines) and not lines[j].startswith('##'):
                        j += 1
                    # Add remaining lines from j
                    if j < len(lines):
                        new_lines.extend(lines[j:])
                    break
                else:
                    new_lines.append(line)

            # Write back
            with open(park_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))

            print(f"Updated: {park_dir.name}")


async def add_park_links_to_coasters():
    """Add back-links from coaster files to park files"""
    base_dir = Path("Amusement Parks")
    park_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name != "Inputs"]

    print(f"\nAdding park links to coasters...")

    for park_dir in park_dirs:
        park_name = park_dir.name
        park_file = f"{park_name}.md"

        # Get all coaster files
        coaster_files = [f for f in park_dir.glob("*.md") if f.name != park_file]

        for coaster_file in coaster_files:
            with open(coaster_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if already has link
            if f'[{park_name}]' in content or f']({park_file})' in content:
                continue  # Already linked

            # Add link after the park name line
            lines = content.split('\n')
            new_lines = []

            for line in lines:
                new_lines.append(line)
                # If this is the park line, make it a link
                if line.startswith('**Park:**') and park_name in line:
                    # Replace with linked version
                    new_lines[-1] = f'**Park:** [{park_name}]({park_file})'

            # Write back
            with open(coaster_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))

        print(f"Linked {len(coaster_files)} coasters in {park_name}")


async def main():
    print("="*70)
    print("Park Address Updater & Coaster Back-linker")
    print("="*70)

    await update_park_files()
    await add_park_links_to_coasters()

    print("\n" + "="*70)
    print("Complete!")
    print("="*70)


if __name__ == '__main__':
    asyncio.run(main())
