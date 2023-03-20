#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 20 14:42:18 2023
@author: David Poole
"""
from sh import grep, ifconfig, sudo, networksetup
from random import randint

# get current MAC address
# ifconfig en0 | grep ether
cur = grep(ifconfig("en0"), "ether").strip()
print("Current MAC Address: ", cur)

# generate a new random MAC address (note: may not be compliant)
mac = [0x60, 0xf8, 0x1d,
       randint(0x00, 0x7f),
       randint(0x00, 0x7f),
       randint(0x00, 0x7f)]
gen = ':'.join(map(lambda x: "%02x" % x, mac))

# disconnect from Wi-Fi network
# note: for sudo to work without password, add to /etc/sudoers
# sudo airport -z
sudo("airport", "-z")

# spoof the mac address
# see note re: /etc/sudoers above
# sh.sudo("ifconfig", "en0", "ether", gen)

# check it updated
check = grep(ifconfig("en0"), "ether").strip()
print("New MAC Address:     ", check)

# check if connected to a Wi-Fi network
# TODO: maybe change it so it's not an infinite loop XD
wifi = str(networksetup("-getairportnetwork", "en0"))
while "NET4" not in wifi:
    print("Trying to connect to NET4...")
    networksetup("-setairportnetwork", "en0", "NET4")
    wifi = str(networksetup("-getairportnetwork", "en0"))

# final check and confirmation message to console
if "NET4" in wifi:
    print("Connected to NET4.")
else:
    print("Error, didn't connect to NET4.")
