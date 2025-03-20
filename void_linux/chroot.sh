#!/bin/bash

##########################################################
# Radxa Rock 5C Lite
# RadxaOS (Debian 12) to Void Linux conversion script
# Author: https:///github.com/c0m4r
# License: Public Domain
##########################################################

set -e

# inside chroot
xbps-install -Suy
xbps-install -Sy base-system bash-completion curl chrony openssh openssl nano vim htop dhclient iproute2 cronie wpa_supplicant
echo "Europe/Warsaw" > /etc/timezone
ln -s /usr/share/zoneinfo/Europe/Warsaw /etc/localtime
echo -e "radxa\nradxa" | passwd
usermod -s /bin/bash root
cp /etc/skel/.* ./
useradd rock
useradd radxa
echo -e "radxa\nradxa" | passwd radxa
echo -e "rock\nrock" | passwd rock
ln -s /etc/sv/chronyd /etc/runit/runsvdir/default/
ln -s /etc/sv/dhcpcd /etc/runit/runsvdir/default/
ln -s /etc/sv/sshd /etc/runit/runsvdir/default/
exit
