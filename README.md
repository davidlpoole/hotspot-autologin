# hotspot-autologin
In brief: Spoof the device mac address and auto login to wifi hotspot until allowance runs out then repeat.

I wrote this while staying at a holiday park that provided a free wifi hotspot but which was was limited to 600 MB per device per day.

Given that the hotspot passcode was the same for every user, I discovered that the hotspot was using the MAC address to differentiate between devices, I also knew that it's possible to spoof the mac address (i.e. generate a new address). This meant that if I spoofed the MAC address and re-connected, the hotspot thinks it's a new device, and issues a new IP and 600 MB allowance.

This script connects to the hotspot, logs in to the captive portal with the passcode all users share, then scrapes the status page for the remaining data allowance. If the allowance is too low or run out, the script spoofs the device mac address and loops back to logging in and scraping the hotspot page etc. ensuring almost uninterrupted internet usage without any interference from the user.
