# eMMC

**Deps**

https://docs.kernel.org/driver-api/mmc/mmc-tools.html

```
apt install mmc-utils
```

**Analysis of eMMC Health and Information**

1.  **Health Status:**
    *   **Life Time Estimation A [EXT_CSD_DEVICE_LIFE_TIME_EST_TYP_A]: 0x01**: This indicates 0-10% of the device's estimated lifetime has been consumed for Type A memory (typically SLC or pseudo-SLC used for wear-leveling/metadata). This is excellent, essentially like new.
    *   **Life Time Estimation B [EXT_CSD_DEVICE_LIFE_TIME_EST_TYP_B]: 0x00**: This indicates 0% of the device's estimated lifetime has been consumed for Type B memory (typically MLC/TLC used for main storage), *or* this specific estimation type is not reported/used by this particular eMMC. Given Type A is 0x01, it's highly likely this means 0% consumed. This is also excellent.
    *   **Pre EOL information [EXT_CSD_PRE_EOL_INFO]: 0x01**: This means "Normal". The device is not nearing its End Of Life threshold according to the manufacturer's internal metrics. Values `0x02` (Warning) or `0x03` (Urgent) would indicate significant wear.

    **Overall Health Assessment:** The eMMC module is in **excellent health**, showing minimal to no significant wear based on its internal lifetime counters. It is operating normally and far from its predicted end-of-life.

2.  **Device Information:**
    *   **Standard:** `Extended CSD rev 1.8 (MMC 5.1)` - A modern eMMC standard supporting advanced features.
    *   **Capacity:** `Sector Count [SEC_COUNT: 0x07490000]` -> 122,229,760 sectors. Assuming 512-byte sectors (`DATA_SECTOR_SIZE: 0x00`), the capacity is 122,229,760 * 512 = 62,581,637,120 bytes, which is approximately **62.6 GB** (or 58.3 GiB). Often marketed as 64 GB.
    *   **Performance Features:**
        *   `Card Type [CARD_TYPE: 0x57]`: Supports HS400 (up to 400MB/s), HS200, HS DDR, and legacy HS modes. Currently likely operating in a high-speed mode (potentially HS400 if the host supports it).
        *   `Cache Size [CACHE_SIZE]`: 8192 KiB (8 MiB). A reasonable cache size helps buffer writes and reads. `CACHE_CTRL: 0x01` indicates the cache is enabled.
        *   `Command Queue Support [CMDQ_SUPPORT: 0x01]`: Supports command queuing with a depth of 32 (`CMDQ_DEPTH: 32`). This can significantly improve random I/O performance under load, although it's not currently enabled at the eMMC level (`CMDQ_MODE_EN: 0x00`). The OS might enable it dynamically.
        *   `Background operations support [BKOPS_SUPPORT: 0x01]`: The device can perform internal maintenance (like garbage collection) in the background.
    *   **Reliability Features:**
        *   `TRIM Multiplier [TRIM_MULT: 0x05]`: Supports TRIM command, essential for maintaining performance and longevity on flash storage.
        *   `Write reliability setting register [WR_REL_SET: 0x1f]`: Enhanced reliable write features are enabled for all partitions, protecting data against power loss during writes.
        *   `Power off notification [POWER_OFF_NOTIFICATION: 0x01]`: Supports a notification from the host before power off, allowing the eMMC to safely finish operations.
    *   **Other:**
        *   `Boot partition size [BOOT_SIZE_MULTI: 0x20]`: 32 * 128KiB = 4 MiB (likely two boot partitions of this size).
        *   `RPMB Size [RPMB_SIZE_MULT]: 0x80]`: 128 * 128KiB = 16 MiB (Replay Protected Memory Block).
        *   `Partitioning Support [PARTITIONING_SUPPORT: 0x07]`: Supports partitioning and enhanced attributes, but hasn't been configured beyond defaults (`PARTITION_SETTING_COMPLETED: 0x00`).

**Recommendations for Longevity and Performance**

1.  **Maintain Sufficient Free Space:** Avoid filling the eMMC close to its full capacity. Leaving 10-20% free space allows the internal wear-leveling algorithms to work more efficiently, distributing writes evenly and extending the lifespan.
2.  **Ensure TRIM is Active:** This is crucial. Verify that your operating system is periodically issuing TRIM commands (e.g., via `fstrim` in a cron job or using the `discard` mount option in `/etc/fstab` if your filesystem/kernel supports it well). TRIM informs the eMMC which blocks are no longer in use, preventing unnecessary writes and improving performance.
3.  **Minimize Unnecessary Writes:**
    *   Review system logging levels; reduce verbosity if not needed.
    *   Consider mounting temporary directories (`/tmp`) as tmpfs (in RAM) if you have sufficient RAM.
    *   Optimize applications to batch writes instead of performing many small, frequent writes if possible.
4.  **Use Flash-Friendly Filesystems (Optional but Recommended):** Filesystems like F2FS are designed specifically for flash storage and can sometimes offer better performance and longevity compared to traditional filesystems like EXT4. However, EXT4 with TRIM enabled is generally very stable and performs well.
5.  **Ensure Stable Power:** Abrupt power loss can, in rare cases, cause corruption or stress the controller. Use a reliable power supply. The device supports Power Off Notification, which helps mitigate issues if the OS triggers it properly during shutdown.
6.  **Monitor Health Periodically:** Run `sudo mmc extcsd read /dev/mmcblk0 | grep -E "LIFE_TIME|PRE_EOL_INFO"` occasionally (e.g., every few months or annually, depending on usage intensity) to check if the lifetime indicators change significantly.
7.  **Leverage Performance Features (If Needed):**
    *   **HS400:** Ensure your system's host controller is configured to use the highest supported speed (HS400). Check `dmesg | grep mmc` after boot for the negotiated speed.
    *   **Command Queuing (CMDQ):** If you experience bottlenecks with random I/O (e.g., database operations, running many concurrent processes reading/writing small files), investigate enabling CMDQ via sysfs (`/sys/devices/.../mmc_host/mmcX/mmcX:XXXX/cmdq_en`). Benchmark before and after to confirm improvement. This often requires kernel support and specific configuration.
8.  **Keep Kernel/Firmware Updated:** Updates to the Linux kernel or the device's firmware (if available from the board manufacturer) may include improvements to the MMC driver, potentially enhancing performance or reliability.

**How to Use the Script:**

1.  **Save:** Save the code above as a Python file (e.g., `emmc_analyzer.py`).
2.  **Make Executable:** Run `chmod +x emmc_analyzer.py`.
3.  **Install Dependency:** Ensure you have the `mmc-utils` package installed, which provides the `mmc` command. On Debian/Ubuntu: `sudo apt update && sudo apt install mmc-utils`.
4.  **Run:** Execute the script with `sudo` (required for the `mmc` command):
    *   `sudo ./emmc_analyzer.py` (will default to `/dev/mmcblk0`)
    *   `sudo ./emmc_analyzer.py /dev/mmcblk1` (if your eMMC is on a different path)

The script will run the `mmc extcsd read` command, parse its output, and print a formatted report covering the health, key device information, and recommendations.
