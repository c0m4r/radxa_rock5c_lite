#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyzes eMMC health and information using 'mmc extcsd read'.

Reads the Extended CSD data from an eMMC device, parses key health
and configuration parameters, and provides a summary report with
recommendations for longevity and performance.

Vibe-coded with Gemini 2.5 Pro Experimental 03-25 🙈
I have no fucking idea what it does... YOLO xD
https://github.com/c0m4r
License: Public Domain
"""

import subprocess
import re
import argparse
import sys
import os
import glob
from typing import Dict, List, Optional, Tuple, Any, Union

# --- ANSI Color Codes ---
# (Check if stdout is a TTY to enable colors by default)
_TTY = sys.stdout.isatty()
COLOR_ENABLED = _TTY

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN = "\033[96m"

def _col(text: str, color_code: str) -> str:
    """Applies color codes if enabled."""
    return f"{color_code}{text}{C_RESET}" if COLOR_ENABLED else text

# --- Constants and Mappings ---

# JEDEC Life Time Estimates (Bytes 268, 269)
# Added color hints
LIFE_TIME_MAP: Dict[int, str] = {
    0x00: _col("0% used (or not defined)", C_GREEN),
    0x01: _col("0% - 10% used", C_GREEN),
    0x02: _col("10% - 20% used", C_GREEN),
    0x03: _col("20% - 30% used", C_GREEN),
    0x04: _col("30% - 40% used", C_GREEN),
    0x05: _col("40% - 50% used", C_YELLOW),
    0x06: _col("50% - 60% used", C_YELLOW),
    0x07: _col("60% - 70% used", C_YELLOW),
    0x08: _col("70% - 80% used", C_YELLOW),
    0x09: _col("80% - 90% used", C_RED),
    0x0A: _col("90% - 100% used", C_RED),
    0x0B: _col("Exceeded estimated life", C_BOLD + C_RED),
}

# JEDEC Pre EOL Info (Byte 267)
PRE_EOL_MAP: Dict[int, str] = {
    0x00: "Not defined",
    0x01: _col("Normal", C_GREEN),
    0x02: _col("Warning (80% consumption)", C_YELLOW),
    0x03: _col("Urgent (90% consumption)", C_RED),
}

# Background Operation Status (Byte 246)
BKOPS_STATUS_MAP: Dict[int, str] = {
    0x00: _col("No operation", C_GREEN),
    0x01: _col("Performing background operation", C_YELLOW),
    # 0x02+ are vendor specific, indicate potentially busy
    0x02: _col("Vendor Specific Status 2 (Potentially Busy)", C_YELLOW),
    0x03: _col("Vendor Specific Status 3 (Potentially Busy)", C_YELLOW),
    # Add more vendor specific codes if known, otherwise default
}

# Card Type Bits (Byte 196)
CARD_TYPE_MAP: Dict[int, str] = {
    (1 << 0): "HS eMMC @26MHz - at rated device voltage(s)",
    (1 << 1): "HS eMMC @52MHz - at rated device voltage(s)",
    (1 << 2): "HS DDR eMMC @52MHz 1.8V or 3VI/O",
    (1 << 3): "HS DDR eMMC @52MHz 1.2VI/O",
    (1 << 4): "HS200 SDR eMMC @200MHz 1.8VI/O",
    (1 << 5): "HS200 SDR eMMC @200MHz 1.2VI/O",
    (1 << 6): "HS400 DDR eMMC @200MHz 1.8VI/O",
    (1 << 7): "HS400 DDR eMMC @200MHz 1.2VI/O",
}

# Type alias for parsed data
ExtCsdData = Dict[str, Dict[str, Any]]

# --- Helper Functions ---

def run_mmc_command(device_path: str) -> str:
    """Runs the mmc extcsd read command and returns the output."""
    base_device_path = device_path
    if 'p' in os.path.basename(device_path):
        base_device_path = re.sub(r'p\d+$', '', device_path)
        print(
            f"Warning: Provided path {device_path} looks like a partition. "
            f"Using base device {base_device_path} instead.", file=sys.stderr
        )

    command = ["sudo", "mmc", "extcsd", "read", base_device_path]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, timeout=20,
            encoding='utf-8' # Be explicit
        )
        if not result.stdout.strip():
            print(
                f"Error: 'mmc extcsd read {base_device_path}' produced no output. "
                "Check device and permissions.", file=sys.stderr
            )
            sys.exit(1)
        return result.stdout
    except FileNotFoundError:
        print("Error: 'mmc' command not found. Is 'mmc-utils' installed "
              "and in PATH?", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as error:
        print(f"Error running mmc command (Exit code: {error.returncode}): {error}",
              file=sys.stderr)
        print(f"Command: {' '.join(command)}", file=sys.stderr)
        print(f"Stderr: {error.stderr.strip()}", file=sys.stderr)
        if "Permission denied" in error.stderr or error.returncode == 13:
            print("Hint: Try running the script with 'sudo'.", file=sys.stderr)
        elif "No such file or directory" in error.stderr:
            print(f"Hint: Ensure the device '{base_device_path}' exists.",
                  file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Error: 'mmc' command timed out after 20 seconds.", file=sys.stderr)
        sys.exit(1)
    except PermissionError: # Catch explicit sudo issues if needed
        print("Error: Permission denied. Try running the script with sudo.",
              file=sys.stderr)
        sys.exit(1)
    # Added return type hint and path for non-exception case
    return "" # Should not be reached if successful, satisfies mypy


def parse_extcsd_output(output: str) -> ExtCsdData:
    """Parses the raw text output into a dictionary."""
    data: ExtCsdData = {}

    # Pattern 1: Key [REGISTER]: 0xValue
    pattern1 = re.compile(r"^\s*(.*?)\s+\[(.*?)]:\s*(0x[0-9a-fA-F]+)\s*$",
                          re.MULTILINE)
    # Pattern 2: Key [REGISTER: 0xValue]
    pattern2 = re.compile(r"^\s*(.*?)\s*\[(.*):\s*(0x[0-9a-fA-F]+)\s*\]"
                          r"(?:$|\s*: i\.e\.)", re.MULTILINE)
    # Pattern 3: Key [REGISTER]: DecimalValue
    pattern3 = re.compile(r"^\s*(.*?)\s+\[(.*?)]:\s*(\d+)\s*$", re.MULTILINE)
    # Pattern 4: Cache Size specific format
    pattern4 = re.compile(r"^\s*(Cache Size)\s+\[(CACHE_SIZE)\]\s+is\s+(\d+)"
                          r"\s*(KiB|MiB|GiB)?", re.MULTILINE)
    # Pattern 5: Card Type multi-line block
    pattern5 = re.compile(r"Card Type \[CARD_TYPE: (0x[0-9a-fA-F]+)\]\n"
                          r"((?:\s+.*?\n)+)", re.MULTILINE)

    # Apply patterns sequentially
    patterns = [pattern2, pattern1, pattern3, pattern4]
    for pattern in patterns:
        for match in pattern.finditer(output):
            register: str
            key_desc: str
            value_hex: Optional[str] = None
            value_int: Optional[int] = None
            value_str: Optional[str] = None
            value_num: Optional[int] = None
            value_unit: Optional[str] = None

            if pattern == pattern4: # Cache Size
                key_desc = match.group(1).strip()
                register = match.group(2).strip()
                value_num_str = match.group(3).strip()
                value_unit = match.group(4)
                try:
                    value_num = int(value_num_str)
                    value_str = f"{value_num_str} {value_unit if value_unit else ''}".strip()
                except ValueError:
                    value_num = None
                    value_str = f"{value_num_str} {value_unit if value_unit else ''}".strip()

            elif pattern == pattern3: # Decimal
                key_desc = match.group(1).strip()
                register = match.group(2).strip()
                value_dec_str = match.group(3).strip()
                try:
                    value_int = int(value_dec_str)
                    value_str = value_dec_str # Keep string version too
                except ValueError:
                    value_int = None
                    value_str = value_dec_str

            else: # Hex patterns (pattern1, pattern2)
                key_desc = match.group(1).strip()
                register = match.group(2).strip()
                value_hex = match.group(3).strip()
                try:
                    value_int = int(value_hex, 16)
                except ValueError:
                    value_int = None

            if register not in data:
                data[register] = {'key': key_desc}
                if value_hex is not None: data[register]['hex'] = value_hex
                if value_int is not None: data[register]['int'] = value_int
                if value_str is not None: data[register]['str'] = value_str
                if value_num is not None: data[register]['num'] = value_num
                if value_unit is not None: data[register]['unit'] = value_unit

    # Apply Pattern 5 (Card Type multi-line)
    match5 = pattern5.search(output)
    if match5:
        register_name = 'CARD_TYPE'
        hex_val = match5.group(1)
        supported_types = [line.strip() for line in
                           match5.group(2).strip().split('\n') if line.strip()]
        if register_name in data:
            data[register_name]['supported_types'] = supported_types
        else:
            try: int_val: Optional[int] = int(hex_val, 16)
            except ValueError: int_val = None
            data[register_name] = {
                'key': 'Card Type', 'hex': hex_val, 'int': int_val,
                'supported_types': supported_types
            }

    return data

def calculate_capacity(sec_count: Optional[int]) -> Tuple[str, str]:
    """Calculates capacity in GB and GiB."""
    if sec_count is None or not isinstance(sec_count, int) or sec_count == 0:
        return "Unknown", "Unknown"
    # Assume 512 byte sectors based on DATA_SECTOR_SIZE: 0x00 usually
    total_bytes = sec_count * 512
    gigabytes = total_bytes / (1000**3)
    gibibytes = total_bytes / (1024**3)
    return f"{gigabytes:.2f} GB", f"{gibibytes:.2f} GiB"

def format_bytes(bytes_val: Optional[Union[int, float]]) -> str:
    """Formats bytes into KiB, MiB, GiB."""
    if not isinstance(bytes_val, (int, float)) or bytes_val < 0:
        return "N/A"
    if bytes_val == 0:
        return "0 Bytes"
    if bytes_val < 1024:
        return f"{bytes_val} Bytes"
    if bytes_val < 1024**2:
        return f"{bytes_val / 1024:.1f} KiB"
    if bytes_val < 1024**3:
        return f"{bytes_val / (1024**2):.1f} MiB"
    # else
    return f"{bytes_val / (1024**3):.1f} GiB"

def get_val(data: ExtCsdData, key: str, field: str = 'int',
            default: Any = None) -> Any:
    """Safely get a specific field from the parsed data."""
    return data.get(key, {}).get(field, default)

def get_key(data: ExtCsdData, key: str, default: str = "N/A") -> str:
    """Safely get the descriptive key name associated with a register."""
    return data.get(key, {}).get('key', default)

def _print_aligned(key: str, value: str, width: int) -> None:
    """Prints a key-value pair with alignment."""
    print(f"  {key:<{width}} : {value}")

def _assess_health(data: ExtCsdData) -> Tuple[str, Optional[int], Optional[int], Optional[int]]:
    """Assesses eMMC health and returns summary and raw values."""
    life_a_val = get_val(data, 'EXT_CSD_DEVICE_LIFE_TIME_EST_TYP_A')
    life_b_val = get_val(data, 'EXT_CSD_DEVICE_LIFE_TIME_EST_TYP_B')
    pre_eol_val = get_val(data, 'EXT_CSD_PRE_EOL_INFO')

    health_summary = _col("Excellent", C_GREEN) # Default optimistic
    if pre_eol_val == 0x03:
        health_summary = _col("Urgent (Near/At EOL)", C_RED + C_BOLD)
    elif pre_eol_val == 0x02:
        health_summary = _col("Warning (Approaching EOL)", C_YELLOW)
    elif (life_a_val is not None and life_a_val >= 0x0B) or \
         (life_b_val is not None and life_b_val >= 0x0B):
        health_summary = _col("Critical (Exceeded Lifetime)", C_RED + C_BOLD)
    elif (life_a_val is not None and life_a_val >= 0x09) or \
         (life_b_val is not None and life_b_val >= 0x09):
        health_summary = _col("High Wear (80%+ used)", C_RED)
    elif (life_a_val is not None and life_a_val >= 0x06) or \
         (life_b_val is not None and life_b_val >= 0x06):
        health_summary = _col("Moderate Wear (50%+ used)", C_YELLOW)
    elif life_a_val is None and life_b_val is None and pre_eol_val is None:
        health_summary = _col("Unknown (Health info not available)", C_MAGENTA)

    return health_summary, life_a_val, life_b_val, pre_eol_val

def _print_health_report(data: ExtCsdData, width: int) -> str:
    """Prints the health assessment section."""
    print("\n--- Health Assessment ---")
    health_summary, life_a_val, life_b_val, pre_eol_val = _assess_health(data)

    life_a_desc = LIFE_TIME_MAP.get(life_a_val, _col("Unknown", C_MAGENTA))
    life_b_desc = LIFE_TIME_MAP.get(life_b_val, _col("Unknown", C_MAGENTA))
    pre_eol_desc = PRE_EOL_MAP.get(pre_eol_val, _col("Unknown", C_MAGENTA))

    life_a_hex = f"0x{life_a_val:02X}" if life_a_val is not None else "N/A"
    life_b_hex = f"0x{life_b_val:02X}" if life_b_val is not None else "N/A"
    pre_eol_hex = f"0x{pre_eol_val:02X}" if pre_eol_val is not None else "N/A"

    _print_aligned(get_key(data, 'EXT_CSD_DEVICE_LIFE_TIME_EST_TYP_A', 'Life Time Est. A'),
                   f"{life_a_desc} [{life_a_hex}]", width)
    _print_aligned(get_key(data, 'EXT_CSD_DEVICE_LIFE_TIME_EST_TYP_B', 'Life Time Est. B'),
                   f"{life_b_desc} [{life_b_hex}]", width)
    _print_aligned(get_key(data, 'EXT_CSD_PRE_EOL_INFO', 'Pre EOL Info'),
                   f"{pre_eol_desc} [{pre_eol_hex}]", width)

    print(f"\n  {_col('Overall Health Summary', C_BOLD):<{width+2}} : {health_summary}")
    return health_summary # Return assessed summary for recommendations

def _print_device_info(data: ExtCsdData, raw_output: str, width: int) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[int]]:
    """Prints the device information section and returns key values for recommendations."""
    print("\n--- Device Information ---")
    rev_match = re.search(r"Extended CSD rev (\d\.\d) \(MMC (.*?)\)", raw_output)
    csd_rev = rev_match.group(1) if rev_match else "Unknown"
    mmc_spec = rev_match.group(2) if rev_match else "Unknown"
    _print_aligned("eMMC Standard", f"MMC {mmc_spec} (CSD Rev {csd_rev})", width)

    sec_count = get_val(data, 'SEC_COUNT')
    cap_gb, cap_gib = calculate_capacity(sec_count)
    sec_count_str = str(sec_count) if sec_count is not None else 'N/A'
    _print_aligned("Capacity", f"{cap_gb} / {cap_gib} ({sec_count_str} sectors)", width)

    cache_str = get_val(data, 'CACHE_SIZE', field='str', default="Unknown")
    cache_num = get_val(data, 'CACHE_SIZE', field='num')
    cache_detail = cache_str
    if cache_num is not None:
        cache_detail += f" ({format_bytes(cache_num * 1024)})"
    _print_aligned("Cache Size", cache_detail, width)

    trim_mult_val = get_val(data, 'TRIM_MULT')
    trim_support = _col("Yes", C_GREEN) if trim_mult_val is not None and trim_mult_val > 0 else _col("No / Unknown", C_YELLOW)
    _print_aligned("TRIM Support", trim_support, width)

    bkops_support_val = get_val(data, 'BKOPS_SUPPORT')
    bkops_status_val = get_val(data, 'BKOPS_STATUS')
    bkops_support_str = _col("Supported", C_GREEN) if bkops_support_val == 1 else _col("Not Supported / Unknown", C_YELLOW)
    bkops_status_str = BKOPS_STATUS_MAP.get(bkops_status_val,
                                            _col(f"Vendor Specific Status {bkops_status_val}", C_YELLOW)
                                            if bkops_status_val is not None else _col("Unknown", C_MAGENTA))
    _print_aligned("Background Ops (BKOPS)", bkops_support_str, width)
    if bkops_support_val == 1:
        _print_aligned("  BKOPS Status", bkops_status_str, width - 2) # Indent status

    cmdq_support_val = get_val(data, 'CMDQ_SUPPORT')
    cmdq_support_str = _col("Supported", C_GREEN) if cmdq_support_val == 1 else _col("Not Supported / Unknown", C_YELLOW)
    _print_aligned("Command Queuing (CMDQ)", cmdq_support_str, width)
    cmdq_en_path: Optional[str] = None
    if cmdq_support_val == 1:
        cmdq_depth_val = get_val(data, 'CMDQ_DEPTH')
        cmdq_enabled_val = get_val(data, 'CMDQ_MODE_EN')
        depth_str = str(cmdq_depth_val) if cmdq_depth_val is not None else "Unknown"
        enabled_str = _col("Yes", C_GREEN) if cmdq_enabled_val == 1 else _col("No", C_YELLOW)
        _print_aligned("  CMDQ Depth", depth_str, width - 2)
        _print_aligned("  CMDQ Enabled (FW level)", f"{enabled_str} (Note: OS may override)", width - 2)
        cmdq_en_path = _find_cmdq_sysfs_path(os.path.basename(args.device_path)) # Pass device base name

    wr_rel_param = get_val(data,'WR_REL_PARAM')
    reliable_write = _col("Enhanced", C_GREEN) if wr_rel_param is not None and (wr_rel_param & 0x01) else _col("Basic / Unknown", C_YELLOW)
    _print_aligned("Reliable Write Support", reliable_write, width)

    power_off_notify = get_val(data, 'POWER_OFF_NOTIFICATION')
    power_notify_str = _col("Enabled", C_GREEN) if power_off_notify == 1 else _col("Disabled / Unknown", C_YELLOW)
    _print_aligned("Power Off Notify (Ctrl)", power_notify_str, width)

    boot_mult = get_val(data, 'BOOT_SIZE_MULTI')
    if boot_mult is not None:
        boot_size_kib = boot_mult * 128
        _print_aligned("Boot Partition Size",
                       f"{format_bytes(boot_size_kib * 1024)} (Typically x2)", width)
    rpmb_mult = get_val(data, 'RPMB_SIZE_MULT')
    if rpmb_mult is not None:
        rpmb_size_kib = rpmb_mult * 128
        _print_aligned("RPMB Size", format_bytes(rpmb_size_kib * 1024), width)

    partition_support = get_val(data, 'PARTITIONING_SUPPORT')
    partition_support_str = _col("Yes", C_GREEN) if partition_support is not None and (partition_support & 0x01) else "No"
    _print_aligned("Partitioning Support", partition_support_str, width)
    if partition_support is not None and (partition_support & 0x01):
        partition_completed = get_val(data, 'PARTITION_SETTING_COMPLETED')
        enh_attr = _col("Yes", C_GREEN) if (partition_support & 0x02) else "No"
        completed = _col("Yes", C_GREEN) if partition_completed == 1 else _col("No", C_YELLOW)
        _print_aligned("  Enhanced Attributes", enh_attr, width - 2)
        _print_aligned("  Partitioning Completed", completed, width - 2)

    # Decode Card Type
    card_type_hex = get_val(data, 'CARD_TYPE', 'hex', 'N/A')
    _print_aligned("Supported Interface Modes", f"[{get_key(data, 'CARD_TYPE')}: {card_type_hex}]", width)
    supported_types: Optional[List[str]] = get_val(data, 'CARD_TYPE', 'supported_types')
    card_type_int: Optional[int] = get_val(data, 'CARD_TYPE', 'int')

    if supported_types:
        for type_desc in supported_types:
            if type_desc: print(f"    - {type_desc}")
    elif card_type_int is not None:
        for bit, desc in CARD_TYPE_MAP.items():
            if card_type_int & bit: print(f"    - {desc}")
    else:
        print("    - Could not determine supported modes.")

    return card_type_int, cmdq_support_val, cmdq_en_path, trim_mult_val


def _find_cmdq_sysfs_path(dev_basename: str) -> Optional[str]:
    """Attempts to find the cmdq_en sysfs path for the device."""
    cmdq_en_path: Optional[str] = None
    # Use more specific glob pattern if possible, fallback is wider
    cmdq_path_pattern = f"/sys/class/block/{dev_basename}/device/cmdq_en"
    potential_paths = glob.glob(cmdq_path_pattern)

    if not potential_paths: # Fallback if direct path doesn't exist
         # Try finding via host (less reliable matching)
        cmdq_path_pattern = "/sys/devices/platform/*/mmc_host/mmc?/mmc?:????/cmdq_en"
        potential_paths = glob.glob(cmdq_path_pattern)
        mmc_host_num = None
        try: # Find mmc host number (e.g., mmc0 from mmcblk0)
            link_path = os.readlink(f"/sys/class/block/{dev_basename}")
            # Example link: ../../devices/platform/fe2e0000.mmc/mmc_host/mmc0/mmc0:0001/block/mmcblk0
            mmc_host_num = link_path.split('/')[4] # e.g., mmc0 based on example
        except OSError:
            pass # Ignore if cannot read link or parse

        if mmc_host_num:
            for path in potential_paths:
                # Check if the path contains the likely host identifier
                if f"/{mmc_host_num}/" in path:
                    cmdq_en_path = path
                    break # Take the first match for this host
        elif potential_paths:
            cmdq_en_path = potential_paths[0] # Fallback: take the first found globally

    elif potential_paths: # Direct path found
        cmdq_en_path = potential_paths[0]

    return cmdq_en_path

def _check_cmdq_runtime_status(cmdq_en_path: Optional[str]) -> str:
    """Checks the runtime status of CMDQ via sysfs."""
    if cmdq_en_path and os.path.exists(cmdq_en_path):
        try:
            with open(cmdq_en_path, 'r', encoding='utf-8') as f_handle:
                status = f_handle.read().strip()
                return _col("Enabled", C_GREEN) if status == "1" else _col("Disabled", C_YELLOW)
        except (IOError, OSError) as io_err:
            return _col(f"Error checking sysfs ({type(io_err).__name__})", C_RED)
    else:
        return _col("Unknown (sysfs path not found/verified)", C_MAGENTA)

def _print_recommendations(
    health_summary: str,
    card_type_int: Optional[int],
    cmdq_support_val: Optional[int],
    cmdq_en_path: Optional[str],
    trim_mult_val: Optional[int]
) -> None:
    """Prints recommendations based on analyzed data."""
    print("\n--- Recommendations for Longevity and Performance ---")
    print("  1. Monitor Health: Periodically re-run this script check health status.")
    # Check if health summary contains specific color codes indicating non-optimal
    if C_YELLOW in health_summary or C_RED in health_summary:
        print(_col("     -> Status is non-optimal; monitor more frequently.", C_YELLOW))
    print("  2. Maintain Free Space: Ideally keep 15-20%+ free space for wear "
          "leveling & performance.")

    if trim_mult_val is not None and trim_mult_val > 0:
        print(_col("  3. Ensure TRIM is Active: Verify OS uses TRIM/DISCARD (e.g., "
                   "`sudo fstrim -v /`).", C_GREEN))
    else:
        print(_col("  3. TRIM Not Supported/Enabled: Performance/longevity may degrade "
                   "without TRIM.", C_YELLOW))

    print("  4. Minimize Unnecessary Writes: Review logging levels, use tmpfs for "
          "/tmp if RAM allows.")
    print("  5. Stable Power Supply: Use a quality PSU and ensure clean shutdowns.")

    hs400_support = card_type_int is not None and (card_type_int & (1<<6) or card_type_int & (1<<7))
    hs200_support = card_type_int is not None and (card_type_int & (1<<4) or card_type_int & (1<<5))
    rec6 = "  6. Check Interface Speed: Verify optimal interface speed is used"
    if hs400_support:
        rec6 += _col(" (Ensure host uses HS400 mode).", C_GREEN)
    elif hs200_support:
        rec6 += _col(" (Ensure host uses HS200 mode).", C_GREEN)
    else:
        rec6 += "." # Generic message if specific high speed not detected
    rec6 += " Check with `dmesg | grep -i 'mmc.*timing'`."
    print(rec6)

    if cmdq_support_val == 1:
        cmdq_runtime_status = _check_cmdq_runtime_status(cmdq_en_path)
        print(f"  7. Command Queuing (CMDQ): Supported. Runtime status: {cmdq_runtime_status}.")
        sysfs_path_str = cmdq_en_path if cmdq_en_path else 'N/A'
        print("     -> If random I/O is slow, investigate enabling via OS "
              f"(sysfs path: {sysfs_path_str}).")
        if cmdq_runtime_status != _col("Enabled", C_GREEN) and cmdq_en_path:
            # Provide safe command example
            tee_cmd = f"echo 1 | sudo tee {cmdq_en_path}"
            print(_col("     -> To enable (use with caution, requires root): "
                       f"{tee_cmd}", C_CYAN))

    print("  8. Filesystem: Use flash-aware filesystems (F2FS) or ensure EXT4 uses "
          "TRIM/discard.")
    print("  9. System Updates: Keep kernel/OS updated for potential driver "
          "improvements.")


# --- Main Execution ---

def main(device_path: str) -> None:
    """Main function to analyze eMMC and print report."""
    if os.geteuid() != 0:
        print(_col("Error: This script requires root privileges to run the "
                   "'mmc' command.", C_RED), file=sys.stderr)
        print(_col("Please run using 'sudo'.", C_RED), file=sys.stderr)
        sys.exit(1)

    print(f"--- Analyzing eMMC device: {_col(device_path, C_BLUE)} ---")
    raw_output = run_mmc_command(device_path)
    data = parse_extcsd_output(raw_output)

    # Determine alignment width (optional, can use fixed width)
    # Example: fixed width for better consistency
    key_width = 28

    health_summary = _print_health_report(data, key_width)
    card_type_int, cmdq_support_val, cmdq_en_path, trim_mult_val = \
        _print_device_info(data, raw_output, key_width)
    _print_recommendations(health_summary, card_type_int, cmdq_support_val,
                          cmdq_en_path, trim_mult_val)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"{_col('Analyze eMMC health and information using `mmc extcsd read`.', C_BOLD)}\n"
                    "Requires 'mmc-utils' and root privileges.",
        formatter_class=argparse.RawTextHelpFormatter # Allow newlines in description
    )
    parser.add_argument(
        "device_path",
        nargs="?",
        default="/dev/mmcblk0",
        help="Path to the eMMC block device (default: %(default)s)"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colorized output."
    )

    args = parser.parse_args()

    if args.no_color:
        COLOR_ENABLED = False # Override TTY check

    # --- Device Path Validation ---
    selected_device = args.device_path
    if not os.path.exists(selected_device):
        found_alternative = False
        if selected_device == "/dev/mmcblk0":
            # Check for other mmcblk devices
            for i in range(1, 4): # Check mmcblk1, mmcblk2, mmcblk3
                alt_path = f"/dev/mmcblk{i}"
                if os.path.exists(alt_path):
                    print(f"Info: Default device {selected_device} not found. "
                          f"Using {_col(alt_path, C_YELLOW)} instead.", file=sys.stderr)
                    selected_device = alt_path
                    found_alternative = True
                    break
        if not found_alternative:
            print(f"{_col('Error:', C_RED)} Device path '{selected_device}' does not exist. "
                   "Please specify a valid eMMC device.", file=sys.stderr)
            sys.exit(1)
    # Update args.device_path if an alternative was found and used
    args.device_path = selected_device

    main(args.device_path)
