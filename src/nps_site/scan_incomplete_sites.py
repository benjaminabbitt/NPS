#!/usr/bin/env python3
"""
Scan NPS main report files to identify sites with incomplete research.

A site is considered incomplete if:
1. Hidden Gems section is empty or only has the header
2. Also Nearby section is empty or only has the header
3. Key Activities section has fewer than 2 activities
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


def extract_section_content(content: str, section_header: str) -> List[str]:
    """
    Extract bullet points from a section.

    Args:
        content: Full markdown file content
        section_header: Section header to search for (e.g., "## Hidden Gems")

    Returns:
        List of bullet point content (lines starting with -)
    """
    # Find the section
    section_pattern = rf'^{re.escape(section_header)}.*?$'
    section_match = re.search(section_pattern, content, re.MULTILINE | re.IGNORECASE)

    if not section_match:
        return []

    # Get content after this section header until next ## header or end of file
    start_pos = section_match.end()
    next_section = re.search(r'^##\s', content[start_pos:], re.MULTILINE)

    if next_section:
        section_content = content[start_pos:start_pos + next_section.start()]
    else:
        section_content = content[start_pos:]

    # Extract bullet points (lines starting with -)
    bullet_points = []
    for line in section_content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('- ') and not stripped.startswith('- [ ]'):
            # Exclude lines that are just placeholders
            if not any(placeholder in stripped.lower() for placeholder in [
                'to be researched',
                'to be determined',
                '*to be',
                'requires research',
                'requires comprehensive research'
            ]):
                bullet_points.append(stripped)

    return bullet_points


def analyze_site_file(file_path: Path) -> Dict[str, any]:
    """
    Analyze a single NPS main report file for completeness.

    Returns:
        Dictionary with analysis results
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {
            'error': str(e),
            'site_name': file_path.stem,
            'file_path': str(file_path)
        }

    # Extract site name from first line (# Site Name)
    site_name_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    site_name = site_name_match.group(1) if site_name_match else file_path.stem

    # Extract sections
    key_activities = extract_section_content(content, '## Key Activities')
    hidden_gems = extract_section_content(content, '## Hidden Gems')
    also_nearby = extract_section_content(content, '## Also Nearby')

    return {
        'site_name': site_name,
        'file_path': str(file_path),
        'key_activities_count': len(key_activities),
        'hidden_gems_count': len(hidden_gems),
        'also_nearby_count': len(also_nearby),
        'has_hidden_gems': len(hidden_gems) > 0,
        'has_also_nearby': len(also_nearby) > 0,
        'has_sufficient_activities': len(key_activities) >= 2,
        'is_complete': len(hidden_gems) > 0 and len(also_nearby) > 0 and len(key_activities) >= 2
    }


def scan_all_sites(base_path: str = "/workspace/2-Enhanced Data/NPS/") -> List[Dict]:
    """
    Scan all NPS site directories for main report files.

    Returns:
        List of analysis results for each site
    """
    base_dir = Path(base_path)
    results = []

    # Find all subdirectories
    for site_dir in sorted(base_dir.iterdir()):
        if not site_dir.is_dir():
            continue

        # Look for main report file (not user-data.md)
        main_reports = [
            f for f in site_dir.glob('*.md')
            if f.name != 'user-data.md' and f.name != 'CLAUDE.md'
        ]

        if not main_reports:
            # No main report found
            results.append({
                'site_name': site_dir.name,
                'file_path': str(site_dir),
                'error': 'No main report file found',
                'is_complete': False
            })
            continue

        # Analyze the first main report (should only be one)
        analysis = analyze_site_file(main_reports[0])
        results.append(analysis)

    return results


def generate_report(results: List[Dict]) -> Tuple[str, Dict[str, int]]:
    """
    Generate a comprehensive report from analysis results.

    Returns:
        Tuple of (report text, summary statistics)
    """
    # Categorize sites
    missing_hidden_gems = []
    missing_also_nearby = []
    insufficient_activities = []
    complete_sites = []
    error_sites = []

    for result in results:
        if 'error' in result:
            error_sites.append(result)
            continue

        if result['is_complete']:
            complete_sites.append(result)
        else:
            if not result['has_hidden_gems']:
                missing_hidden_gems.append(result)
            if not result['has_also_nearby']:
                missing_also_nearby.append(result)
            if not result['has_sufficient_activities']:
                insufficient_activities.append(result)

    # Generate report text
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("NPS SITE RESEARCH COMPLETENESS REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Summary statistics
    total_sites = len(results)
    incomplete_sites = total_sites - len(complete_sites)

    report_lines.append("SUMMARY STATISTICS")
    report_lines.append("-" * 80)
    report_lines.append(f"Total sites scanned: {total_sites}")
    report_lines.append(f"Complete sites: {len(complete_sites)}")
    report_lines.append(f"Incomplete sites: {incomplete_sites}")
    report_lines.append(f"Sites with missing Hidden Gems: {len(missing_hidden_gems)}")
    report_lines.append(f"Sites with missing Also Nearby: {len(missing_also_nearby)}")
    report_lines.append(f"Sites with insufficient Key Activities (0-1): {len(insufficient_activities)}")
    report_lines.append(f"Sites with errors: {len(error_sites)}")
    report_lines.append("")

    # Detailed listings
    if missing_hidden_gems:
        report_lines.append("=" * 80)
        report_lines.append(f"SITES MISSING HIDDEN GEMS ({len(missing_hidden_gems)} sites)")
        report_lines.append("=" * 80)
        for site in missing_hidden_gems:
            report_lines.append(f"- {site['site_name']}")
            report_lines.append(f"  File: {site['file_path']}")
            report_lines.append(f"  Key Activities: {site['key_activities_count']}, Also Nearby: {site['also_nearby_count']}")
            report_lines.append("")

    if missing_also_nearby:
        report_lines.append("=" * 80)
        report_lines.append(f"SITES MISSING ALSO NEARBY ({len(missing_also_nearby)} sites)")
        report_lines.append("=" * 80)
        for site in missing_also_nearby:
            report_lines.append(f"- {site['site_name']}")
            report_lines.append(f"  File: {site['file_path']}")
            report_lines.append(f"  Key Activities: {site['key_activities_count']}, Hidden Gems: {site['hidden_gems_count']}")
            report_lines.append("")

    if insufficient_activities:
        report_lines.append("=" * 80)
        report_lines.append(f"SITES WITH INSUFFICIENT KEY ACTIVITIES ({len(insufficient_activities)} sites)")
        report_lines.append("=" * 80)
        for site in insufficient_activities:
            report_lines.append(f"- {site['site_name']}")
            report_lines.append(f"  File: {site['file_path']}")
            report_lines.append(f"  Key Activities: {site['key_activities_count']}")
            report_lines.append("")

    if error_sites:
        report_lines.append("=" * 80)
        report_lines.append(f"SITES WITH ERRORS ({len(error_sites)} sites)")
        report_lines.append("=" * 80)
        for site in error_sites:
            report_lines.append(f"- {site['site_name']}")
            report_lines.append(f"  Error: {site.get('error', 'Unknown error')}")
            report_lines.append(f"  Path: {site['file_path']}")
            report_lines.append("")

    # All incomplete sites list
    all_incomplete = [r for r in results if not r.get('is_complete', False)]
    if all_incomplete:
        report_lines.append("=" * 80)
        report_lines.append(f"ALL INCOMPLETE SITES ({len(all_incomplete)} sites)")
        report_lines.append("=" * 80)
        for site in all_incomplete:
            status = []
            if 'error' in site:
                status.append(f"ERROR: {site['error']}")
            else:
                if not site['has_hidden_gems']:
                    status.append("No Hidden Gems")
                if not site['has_also_nearby']:
                    status.append("No Also Nearby")
                if not site['has_sufficient_activities']:
                    status.append(f"Only {site['key_activities_count']} Key Activities")

            report_lines.append(f"- {site['site_name']}")
            report_lines.append(f"  Issues: {', '.join(status)}")
            report_lines.append("")

    stats = {
        'total_sites': total_sites,
        'complete_sites': len(complete_sites),
        'incomplete_sites': incomplete_sites,
        'missing_hidden_gems': len(missing_hidden_gems),
        'missing_also_nearby': len(missing_also_nearby),
        'insufficient_activities': len(insufficient_activities),
        'error_sites': len(error_sites)
    }

    return '\n'.join(report_lines), stats


def main():
    """Main execution function."""
    print("Scanning NPS main report files...")
    results = scan_all_sites()

    print(f"Found {len(results)} sites\n")

    report_text, stats = generate_report(results)

    # Save report to file
    output_file = "/workspace/incomplete_nps_sites.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(report_text)
    print("\n" + "=" * 80)
    print(f"Report saved to: {output_file}")

    return stats


if __name__ == "__main__":
    main()
