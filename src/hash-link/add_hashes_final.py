import os
import hashlib
import re

def process_files_for_site(site_dir_path, site_name):
    main_md_file = os.path.join(site_dir_path, f'{site_name}.md')
    user_data_file = os.path.join(site_dir_path, 'user-data.md')
    key_to_hash = {}

    if not os.path.exists(main_md_file):
        return

    with open(main_md_file, 'r') as f:
        lines = f.readlines()

    new_main_lines = []
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith(('* ', '- ')):
            match = re.search(r'\*\*(.*?)\*\*', stripped_line)
            if match:
                key = match.group(1)
                hash_object = hashlib.sha256(key.encode())
                hex_dig = hash_object.hexdigest()[:6]
                key_to_hash[key] = hex_dig
                
                # Remove all existing hashes from the line
                line_no_hashes = re.sub(r' \[#[0-9a-f]{6}\]', '', line.rstrip('\n'))
                
                new_main_lines.append(f'{line_no_hashes} [{hex_dig}]\n')
            else:
                new_main_lines.append(line)
        else:
            new_main_lines.append(line)
    
    with open(main_md_file, 'w') as f:
        f.writelines(new_main_lines)

    if not (os.path.exists(user_data_file) and key_to_hash):
        return

    with open(user_data_file, 'r') as f:
        lines = f.readlines()
    
    new_user_lines = []
    sorted_keys = sorted(key_to_hash.keys(), key=len, reverse=True)
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith(('- [', '* [')) or stripped_line.startswith(('- ', '* ')):
            found_key = False
            for key in sorted_keys:
                if key in stripped_line:
                    hash_val = key_to_hash[key]
                    
                    # Remove all existing hashes from the line
                    line_no_hashes = re.sub(r' \[#[0-9a-f]{6}\]', '', line.rstrip('\n'))
                    
                    new_user_lines.append(f'{line_no_hashes} [{hash_val}]\n')
                    found_key = True
                    break
            if not found_key:
                new_user_lines.append(line)
        else:
            new_user_lines.append(line)

    with open(user_data_file, 'w') as f:
        f.writelines(new_user_lines)

def main():
    nps_dir = '2-Enhanced Data/NPS/'
    for site_dir in os.listdir(nps_dir):
        site_dir_path = os.path.join(nps_dir, site_dir)
        if os.path.isdir(site_dir_path):
            process_files_for_site(site_dir_path, site_dir)

if __name__ == '__main__':
    main()
