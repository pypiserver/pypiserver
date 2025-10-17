#!/usr/bin/env python

'''
Utility script to check for invalid characters in Apache htpasswd files and fix them.

The issue occurs because some special characters in the salt portion of the password hash
cause validation errors in passlib. This script identifies and fixes those problematic entries.

This can be run as: pypi-server-fix-htpasswd /path/to/htpasswd [options]
'''

import argparse
import re
import sys

def is_valid_hash(hash_str):
    """Check if a hash string is valid apr_md5_crypt format."""
    # apr_md5_crypt format: $apr1$salt$hash
    if not hash_str.startswith('$apr1$'):
        return True  # Not an apr1 hash, assume it's valid

    parts = hash_str.split('$')
    if len(parts) != 4:
        return False  # Invalid format

    salt = parts[2]
    # Check for invalid characters in salt
    # Valid chars are alphanumeric, plus . and /
    return all(c.isalnum() or c in './'
               for c in salt)

def fix_hash(hash_str):
    """Replace invalid characters in salt with valid ones."""
    if not hash_str.startswith('$apr1$'):
        return hash_str  # Not an apr1 hash, return unchanged

    parts = hash_str.split('$')
    if len(parts) != 4:
        return hash_str  # Invalid format, return unchanged

    salt = ''
    for c in parts[2]:
        if c.isalnum() or c in './':
            salt += c
        else:
            salt += '.'  # Replace invalid char with a dot

    return f"$apr1${salt}${parts[3]}"

def process_htpasswd_file(file_path, output_path=None, backup=True, check_only=False):
    """Process an htpasswd file and fix invalid hashes."""
    invalid_entries = []
    fixed_entries = []

    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        return False

    for i, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        try:
            username, hash_str = line.split(':', 1)
        except ValueError:
            print(f"Line {i+1}: Invalid format, skipping: {line}", file=sys.stderr)
            continue

        if not is_valid_hash(hash_str):
            invalid_entries.append((i+1, username, hash_str))
            if not check_only:
                fixed_hash = fix_hash(hash_str)
                fixed_entries.append((i+1, username, hash_str, fixed_hash))

    if check_only:
        if invalid_entries:
            print(f"Found {len(invalid_entries)} invalid entries in {file_path}:")
            for line_num, username, hash_str in invalid_entries:
                print(f"Line {line_num}: User '{username}' has invalid hash")
        else:
            print(f"No invalid entries found in {file_path}")
        return True

    if not invalid_entries:
        print(f"No invalid entries found in {file_path}")
        return True

    if backup:
        backup_path = f"{file_path}.bak"
        try:
            with open(backup_path, 'w') as f:
                f.writelines(lines)
            print(f"Created backup at {backup_path}")
        except Exception as e:
            print(f"Error creating backup: {e}", file=sys.stderr)
            return False

    # Fix the entries in the file
    for line_num, username, old_hash, new_hash in fixed_entries:
        line_index = line_num - 1
        lines[line_index] = lines[line_index].replace(old_hash, new_hash)

    out_path = output_path or file_path
    try:
        with open(out_path, 'w') as f:
            f.writelines(lines)
    except Exception as e:
        print(f"Error writing to {out_path}: {e}", file=sys.stderr)
        return False

    print(f"Fixed {len(fixed_entries)} entries in {file_path}:")
    for line_num, username, old_hash, new_hash in fixed_entries:
        print(f"Line {line_num}: Fixed hash for user '{username}'")

    return True

def main():
    parser = argparse.ArgumentParser(
        description="Check and fix invalid characters in htpasswd files"
    )
    parser.add_argument("htpasswd_file", help="Path to the htpasswd file")
    parser.add_argument(
        "--output", "-o", 
        help="Output file path (default: overwrite the input file)"
    )
    parser.add_argument(
        "--no-backup", "-n", action="store_true",
        help="Don't create a backup of the original file"
    )
    parser.add_argument(
        "--check", "-c", action="store_true",
        help="Only check for invalid entries without fixing them"
    )

    args = parser.parse_args()

    process_htpasswd_file(
        args.htpasswd_file, 
        args.output, 
        backup=not args.no_backup,
        check_only=args.check
    )

if __name__ == "__main__":
    main()
