#!/usr/bin/env python3
"""
Integrate Amber's data into NPS user-data.md files and clean up.

For all 402 NPS sites with ambers-data.md files:
1. Read both ambers-data.md and user-data.md
2. Verify that user-data.md contains the critical information from ambers-data.md
3. Remove any "Amber's Data" section from user-data.md files
4. Delete ambers-data.md files after verification
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class AmberDataIntegrator:
    def __init__(self, nps_base_dir: str):
        self.nps_base_dir = Path(nps_base_dir)
        self.stats = {
            'total_sites_processed': 0,
            'data_already_integrated': 0,
            'ambers_section_removed': 0,
            'ambers_data_files_deleted': 0,
            'issues': []
        }

    def parse_ambers_data(self, ambers_file: Path) -> Optional[Dict[str, str]]:
        """Parse ambers-data.md file and extract visitor center info."""
        try:
            content = ambers_file.read_text(encoding='utf-8')

            # Extract visitor center name
            vc_match = re.search(r'\*\*Visitor Center:\*\*\s*(.+)', content)
            visitor_center = vc_match.group(1).strip() if vc_match else None

            # Extract address with coordinates
            addr_match = re.search(r'\*\*Address:\*\*\s*(.+)', content)
            address = addr_match.group(1).strip() if addr_match else None

            # Extract hours
            hours_match = re.search(r'\*\*Hours:\*\*\s*(.+)', content)
            hours = hours_match.group(1).strip() if hours_match else None

            return {
                'visitor_center': visitor_center,
                'address': address,
                'hours': hours
            }
        except Exception as e:
            self.stats['issues'].append(f"Error parsing {ambers_file}: {e}")
            return None

    def check_data_in_user_file(self, user_file: Path, ambers_data: Dict[str, str]) -> bool:
        """Check if user-data.md contains the critical information from ambers-data.md."""
        try:
            content = user_file.read_text(encoding='utf-8')

            # Check for address with coordinates in Cancellation Stamps section
            if ambers_data.get('address'):
                # Extract just the address part (without coordinates) for flexible matching
                addr_without_coords = re.sub(r'\s*\([0-9.-]+,\s*[0-9.-]+\)\s*$', '', ambers_data['address'])

                # Check if address appears in the file (with or without coordinates)
                if addr_without_coords in content:
                    return True

                # Also check for visitor center name
                if ambers_data.get('visitor_center') and ambers_data['visitor_center'] in content:
                    return True

            return False
        except Exception as e:
            self.stats['issues'].append(f"Error checking {user_file}: {e}")
            return False

    def remove_ambers_section(self, user_file: Path) -> bool:
        """Remove ## Amber's Data section from user-data.md if present."""
        try:
            content = user_file.read_text(encoding='utf-8')

            # Check if Amber's Data section exists
            if "## Amber's Data" not in content:
                return False

            # Remove the Amber's Data section (everything from ## Amber's Data to the end or next ##)
            # Pattern: ## Amber's Data followed by everything until end of file or next ## heading
            pattern = r'\n## Amber\'s Data.*?(?=\n##|\Z)'
            new_content = re.sub(pattern, '', content, flags=re.DOTALL)

            # Also remove if it's at the very end with extra formatting
            pattern2 = r'\n## Amber\'s Data \(from spreadsheet\).*?\Z'
            new_content = re.sub(pattern2, '', new_content, flags=re.DOTALL)

            # Clean up any trailing whitespace
            new_content = new_content.rstrip() + '\n'

            if new_content != content:
                user_file.write_text(new_content, encoding='utf-8')
                return True

            return False
        except Exception as e:
            self.stats['issues'].append(f"Error removing Amber's section from {user_file}: {e}")
            return False

    def process_site(self, site_dir: Path) -> None:
        """Process a single NPS site directory."""
        ambers_file = site_dir / 'ambers-data.md'
        user_file = site_dir / 'user-data.md'

        # Skip if no ambers-data.md file
        if not ambers_file.exists():
            return

        self.stats['total_sites_processed'] += 1

        # Parse ambers-data.md
        ambers_data = self.parse_ambers_data(ambers_file)
        if not ambers_data:
            self.stats['issues'].append(f"Could not parse {ambers_file}")
            return

        # Check if user-data.md exists
        if not user_file.exists():
            self.stats['issues'].append(f"Missing user-data.md for {site_dir.name}")
            return

        # Verify data is in user-data.md
        data_present = self.check_data_in_user_file(user_file, ambers_data)
        if data_present:
            self.stats['data_already_integrated'] += 1
        else:
            self.stats['issues'].append(
                f"Data not found in user-data.md for {site_dir.name}: "
                f"VC={ambers_data.get('visitor_center')}, "
                f"Addr={ambers_data.get('address')}"
            )

        # Remove Amber's Data section from user-data.md
        section_removed = self.remove_ambers_section(user_file)
        if section_removed:
            self.stats['ambers_section_removed'] += 1

        # Delete ambers-data.md file
        try:
            ambers_file.unlink()
            self.stats['ambers_data_files_deleted'] += 1
        except Exception as e:
            self.stats['issues'].append(f"Error deleting {ambers_file}: {e}")

    def process_all_sites(self) -> None:
        """Process all NPS site directories."""
        # Get all subdirectories in NPS base directory
        site_dirs = [d for d in self.nps_base_dir.iterdir() if d.is_dir()]

        for site_dir in sorted(site_dirs):
            self.process_site(site_dir)

    def print_summary(self) -> None:
        """Print summary of processing results."""
        print("\n" + "="*80)
        print("AMBER'S DATA INTEGRATION SUMMARY")
        print("="*80)
        print(f"\nTotal sites processed: {self.stats['total_sites_processed']}")
        print(f"Sites where data was already integrated: {self.stats['data_already_integrated']}")
        print(f"Sites where Amber's Data section was removed from user-data.md: {self.stats['ambers_section_removed']}")
        print(f"Number of ambers-data.md files deleted: {self.stats['ambers_data_files_deleted']}")

        if self.stats['issues']:
            print(f"\n⚠️  Issues encountered: {len(self.stats['issues'])}")
            print("\nFirst 20 issues:")
            for issue in self.stats['issues'][:20]:
                print(f"  - {issue}")
            if len(self.stats['issues']) > 20:
                print(f"\n  ... and {len(self.stats['issues']) - 20} more issues")
        else:
            print("\n✓ No issues encountered")

        print("\n" + "="*80)


def main():
    nps_base_dir = "/workspace/2-Enhanced Data/NPS"

    integrator = AmberDataIntegrator(nps_base_dir)
    integrator.process_all_sites()
    integrator.print_summary()


if __name__ == '__main__':
    main()
