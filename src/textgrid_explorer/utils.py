#!/usr/bin/env python
#   textgrid_explorer - A TextGrid editing tool with a spreadsheet interface
#   Copyright (C) 2025 Rolando Muñoz <rolando.muar@gmail.com>
#
#   This program is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License version 3, as published
#   by the Free Software Foundation.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranties of
#   MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
#   PURPOSE.  See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program.  If not, see <https://www.gnu.org/licenses/>.
from pathlib import Path
from pprint import pprint

import mytextgrid

def read_textgrid(path):
    try:
        encoding = detect_praat_encoding(path)
        if encoding == '':
            encoding = None

        tg = mytextgrid.read_from_file(path, encoding=encoding)
        tg.file_path = path
        for index, tier in enumerate(tg):
            tg.file_path = path
            tg.parent = tg
            tier.index = index
            for item in tier:
                item.file_path =path
                item.tier = tier
                item.textgrid = tg
                item.modified = False
        return tg
    except Exception as e:
        return None

def get_tier_names(source_dir):
    source_dir = Path(source_dir)

    names = []
    for path in source_dir.rglob('*.TextGrid'):
        try:
            tg = read_textgrid(path)
        except Exception as e:
            print(f'Could not read {path}: {e}')
            continue

        for tier in tg:
            name = tier.name
            if name in names:
                continue
            names.append(name)
    return names

def create_aligned_tier_table(source_dir, primary_tier_name, secondary_tier_names):
    """
    Reads TextGrid files from a source directory, aligns them based on a
    primary tier's intervals, and organizes the data into a table.

    Parameters
    ----------
    source_dir: str
        The path to the directory containing TextGrid files.
    primary_tier_name:  str
        The name of the tier to use as the key for alignment.
    secondary_tier_names: list of str
        A list of names of the secondary tiers to align with the primary tier.

    Returns
    -------
    tuple
        A tuple containing a list of headers and a list of lists representing
        the aligned table data.
    """
    # Ensure the source directory path is a Path object
    source_dir = Path(source_dir)
    if not source_dir.is_dir() or not source_dir.is_absolute():
        return [], []

    # Initialize data structures
    aligned_data = {}
    headers = ['filename', primary_tier_name] + secondary_tier_names

    # Process each TextGrid file in the source directory
    for path in source_dir.rglob('*.TextGrid'):
        try:
            tg = read_textgrid(path)
        except Exception as e:
            print(f'Could not read {path}: {e}')
            continue

        # Get the primary tier
        for tier in tg:
            primary_tiers = [tier for tier in tg if tier.name == primary_tier_name]
            if not primary_tiers:
                print(f'Primary tier "{primary_tier_name}" not found in {path}. Skipping.')
                continue

            primary_tier = primary_tiers[0]

            for primary_interval in primary_tier:
                if not primary_interval.text.strip():
                    continue

                interval_times = (primary_interval.xmin, primary_interval.xmax)

                row = [None]*len(headers)
                row[0] = path
                row[1] = primary_interval

                aligned_data[interval_times] = row

            for tier in tg:
                if tier == primary_tier:
                    continue
                if tier.name in secondary_tier_names:
                    for secondary_interval in tier:
                        interval_times = (secondary_interval.xmin, secondary_interval.xmax)

                        if interval_times in aligned_data:
                            try:
                                tier_index = headers.index(tier.name)
                                aligned_data[interval_times][tier_index] = secondary_interval
                            except:
                                continue
    # Convert the dictionary of aligned data into a list of lists for the table model
#    pprint(aligned_data)
    table_rows = list(aligned_data.values())
    return headers, table_rows

def detect_praat_encoding(path):
    """
    Detect the likely character encoding of a TextGrid file.

    The function first checks for a Byte Order Mark (BOM) to identify
    UTF-16 encodings. If no BOM is found, it attempts to validate the
    byte sequence as UTF-8. If UTF-8 validation fails, it defaults to
    'latin_1' (an assumption based on typical legacy TextGrid formats).

    Parameters
    ----------
    path : str or os.PathLike
        The path to the TextGrid file.

    Returns
    -------
    str
        The detected encoding as a string suitable for use with
        Python's `open()` function. Possible values are:
        - 'utf-16le'
        - 'utf-16be'
        - 'utf-8'
        - 'latin_1' (legacy)
        - 'MacRoman' (legacy, for the future)

    Notes
    -----
    Windows -> \r\n
    Linux and modern Mac -> \n
    old Mac -> \r
    """
    with open(path, 'rb') as f:
        header = f.readline()

        if header.startswith(b'\xff\xfe'):
            return 'utf-16le'
        elif header.startswith(b'\xfe\xff'):
            return 'utf-16be'
        else:
            byte_sequence = f.read()
            if _is_valid_utf8(byte_sequence):
                return 'utf-8'
            else:
                return 'latin_1'
    return ''

def _is_valid_utf8(byte_sequence):
    try:
        byte_sequence.decode('utf-8')
        return True
    except UnicodeError:
        return False
