#!/bin/bash

##########################################################
# Radxa Rock 5C Lite
# RadxaOS (Debian 12) to Void Linux conversion script
# Author: https:///github.com/c0m4r
# License: Public Domain
##########################################################

set -e

if [ ! -e rock-5c_bookworm_cli_b1.output.img.xz ] && [ ! -e rock-5c_bookworm_cli_b1.output.img ]; then
  wget https://github.com/radxa-build/rock-5c/releases/download/rsdk-b1/rock-5c_bookworm_cli_b1.output.img.xz
  xz -T8 -d rock-5c_bookworm_cli_b1.output.img.xz
fi
mkdir -p /tmp/rock
DEVICE=$(losetup --find --partscan --show rock-5c_bookworm_cli_b1.output.img)
mount ${DEVICE}p3 /tmp/rock
cd /tmp/rock
mkdir .modules
mv usr/lib/modules/* .modules/
mkdir .lib
mv usr/lib/linux* .lib/
mv boot .boot
mv etc/fstab .fstab
mv usr/src .src
mv etc/kernel .kernel
rm * -r
wget https://repo-default.voidlinux.org/live/current/void-aarch64-ROOTFS-20250202.tar.xz
tar -xvf void-aarch64-ROOTFS-20250202.tar.xz
rm void-aarch64-ROOTFS-20250202.tar.xz
rm boot/ -r
mv .boot boot
mv .src/* usr/src/
rm .src -r
cat .fstab | grep -v vfat > etc/fstab
rm .fstab
mv .kernel/ etc/kernel
mkdir -p usr/lib/modules
mv .modules/* usr/lib/modules/
rm .modules -r
mv .lib/linux* usr/lib/
rm .lib -r
echo "nameserver 9.9.9.9" > etc/resolv.conf
mount -t proc proc proc
mount -t sysfs sys sys
mount -o bind /dev dev
cd -
cp chroot.sh /tmp/rock/
cd -
chroot . ./chroot.sh
umount proc
umount sys
umount dev
cd -
umount /tmp/rock
umount $DEVICE
mv rock-5c_bookworm_cli_b1.output.img rock-5c_void.img
