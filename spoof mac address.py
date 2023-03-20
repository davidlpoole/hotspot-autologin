#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 20 14:42:18 2023
@author: user
"""

# import subprocess

# result = subprocess.call(["sudo","/usr/local/bin/airport", "-z"])
# result = subprocess.check_output(['sudo', '/sbin/ifconfig', "en0"])
# print(result)

from sh import ifconfig

print(ifconfig("en0"))


## get current MAC address
## generate a new random MAC address
## disconnect from Wifi network
## change to the new random MAC address
## verify it changed
## Connect to Wifi network


"""
#!/bin/sh

##  
echo Updating MAC address...

## do until macaddr actually updates
while [[ $new = $cur ]]
   do
      ## disconnect from current network
      sudo airport -z

      ## get the current mac address
      cur=$(ifconfig en0 | grep ether)
      
      ## generate a new random mac address
      gen=$(openssl rand -hex 6 | sed 's/\(..\)/\1:/g; s/.$//')
      
      ## spoof the macaddr with the generated one
      sudo ifconfig en0 ether $gen

      ## check the macaddr updated
      new=$(ifconfig en0 | grep ether)
   done

echo Waiting...
sleep 1

## attempt to connect to hotspot
echo Trying to connect to NET4...
networksetup -setairportnetwork en0 NET4
echo Done.
"""