#!/usr/bin/env python3
"""
Mark cancellation stamp locations for ALL sites with loose address matching
"""
import re
from pathlib import Path

def normalize_for_matching(text):
    """Normalize text for fuzzy matching"""
    if not text:
        return ""
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    text = ' '.join(text.split())
    return text

def extract_address_parts(address):
    """Extract key parts from an address for matching"""
    if not address:
        return []
    
    # Extract street number
    street_num = re.search(r'\b\d+\b', address)
    
    # Extract street name (words before city/state)
    parts = []
    if street_num:
        parts.append(street_num.group(0))
    
    # Get normalized address
    normalized = normalize_for_matching(address)
    words = normalized.split()
    
    # Common location words to keep
    for word in words:
        if len(word) > 3 and word not in ['street', 'avenue', 'road', 'drive', 'lane', 'boulevard']:
            parts.append(word)
    
    return parts

def addresses_match(addr1, addr2, loose=True):
    """Check if two addresses match (loosely)"""
    if not addr1 or not addr2:
        return False
    
    parts1 = extract_address_parts(addr1)
    parts2 = extract_address_parts(addr2)
    
    if not parts1 or not parts2:
        return False
    
    # Check if they share significant parts
    common = set(parts1) & set(parts2)
    
    if loose:
        # Loose matching: just need 1-2 common parts
        return len(common) >= 1
    else:
        # Strict matching: need majority of parts
        return len(common) >= min(len(parts1), len(parts2)) / 2

def extract_visitor_center_from_ambers_data(main_md_content):
    """Extract visitor center info from Amber's Data section"""
    amber_match = re.search(r"## Amber's Data\n\n.*?(?=\n## |$)", main_md_content, re.DOTALL)
    if not amber_match:
        return None, None
    
    amber_section = amber_match.group(0)
    
    vc_name_match = re.search(r'\*\*Name:\*\*\s+(.+)', amber_section)
    vc_name = vc_name_match.group(1).strip() if vc_name_match else None
    
    vc_addr_match = re.search(r'\*\*Address:\*\*\s+(.+)', amber_section)
    vc_addr = vc_addr_match.group(1).strip() if vc_addr_match else None
    
    return vc_name, vc_addr

def find_matching_stamp_location(main_md_content, vc_name, vc_addr):
    """Find cancellation stamp location that matches the visitor center"""
    stamp_match = re.search(r'## Cancellation Stamp Locations\n\n(.*?)(?=\n## )', main_md_content, re.DOTALL)
    if not stamp_match:
        return None
    
    stamp_section = stamp_match.group(1)
    
    # Find all stamp locations with their full details
    stamp_pattern = r'- \*\*(.+?)\*\* \((.+?)\)'
    stamps = re.findall(stamp_pattern, stamp_section)
    
    # Try to match by name first (strict)
    if vc_name:
        vc_normalized = normalize_for_matching(vc_name)
        for stamp_name, stamp_details in stamps:
            stamp_normalized = normalize_for_matching(stamp_name)
            # Exact or substring match
            if vc_normalized == stamp_normalized or vc_normalized in stamp_normalized or stamp_normalized in vc_normalized:
                return stamp_name
    
    # Try to match by address (loose)
    if vc_addr:
        for stamp_name, stamp_details in stamps:
            if addresses_match(vc_addr, stamp_details, loose=True):
                return stamp_name
    
    # Very loose: check if visitor center name appears anywhere in stamp details
    if vc_name:
        vc_words = set(normalize_for_matching(vc_name).split())
        # Remove very common words
        vc_words = {w for w in vc_words if len(w) > 3 and w not in ['visitor', 'center', 'national', 'park']}
        
        for stamp_name, stamp_details in stamps:
            stamp_text = normalize_for_matching(stamp_name + ' ' + stamp_details)
            stamp_words = set(stamp_text.split())
            
            # If significant words match
            common = vc_words & stamp_words
            if len(common) >= min(2, len(vc_words)):
                return stamp_name
    
    return None

def mark_stamp_in_user_data(site_name, stamp_name):
    """Mark the matching stamp location in user-data.md"""
    user_data_file = Path(f'2-Enhanced Data/NPS/{site_name}/user-data.md')
    
    if not user_data_file.exists():
        return False
    
    content = user_data_file.read_text()
    
    stamps_match = re.search(r'## Cancellation Stamps\n\n(.*?)(?=\n## )', content, re.DOTALL)
    if not stamps_match:
        return False
    
    stamp_normalized = normalize_for_matching(stamp_name)
    
    # Find all unchecked stamp lines
    stamp_lines = re.findall(r'- \[ \] (.+)', content)
    
    for line in stamp_lines:
        line_normalized = normalize_for_matching(line)
        # Loose matching
        if stamp_normalized in line_normalized or line_normalized in stamp_normalized:
            old_line = f'- [ ] {line}'
            new_line = f'- [x] {line}'
            content = content.replace(old_line, new_line, 1)
            user_data_file.write_text(content)
            return True
    
    return False

def main():
    print("="*70)
    print("Marking Visitor Center Stamps for ALL Sites")
    print("="*70)
    
    # Get all sites
    base_path = Path('2-Enhanced Data/NPS')
    all_sites = [d.name for d in base_path.iterdir() if d.is_dir()]
    
    print(f"\nFound {len(all_sites)} sites")
    print("\nProcessing...")
    
    marked_count = 0
    no_ambers_data = 0
    no_match = 0
    
    for i, site in enumerate(sorted(all_sites), 1):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(all_sites)}")
        
        main_md_file = Path(f'2-Enhanced Data/NPS/{site}/{site}.md')
        if not main_md_file.exists():
            continue
        
        main_content = main_md_file.read_text()
        
        vc_name, vc_addr = extract_visitor_center_from_ambers_data(main_content)
        
        if not vc_name and not vc_addr:
            no_ambers_data += 1
            continue
        
        matching_stamp = find_matching_stamp_location(main_content, vc_name, vc_addr)
        
        if not matching_stamp:
            no_match += 1
            continue
        
        if mark_stamp_in_user_data(site, matching_stamp):
            marked_count += 1
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total sites: {len(all_sites)}")
    print(f"Stamps marked: {marked_count}")
    print(f"Sites without Amber's Data: {no_ambers_data}")
    print(f"Sites with no matching stamp: {no_match}")
    print(f"\n✓ Complete!")

if __name__ == '__main__':
    main()
