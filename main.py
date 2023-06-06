#!/usr/bin/env python3
import os
from datetime import datetime
from random import randint
from time import sleep

import requests
from bs4 import BeautifulSoup
from sh import sudo, grep, ifconfig, networksetup, pkill, airport


class Hotspot:
    def __init__(self, hotspot_ssid: str):
        self.wifi_enabled = False
        self.connected_to_hotspot = False
        self.hotspot_ssid = hotspot_ssid
        self.tx_rate = 0
        self.remaining_data = 0
        self.mac_address = self.get_mac_address()
        self.task_status = [(self.time_stamp(), "Initialised")]
        self.terminal_height = self.get_terminal_height()

    def __call__(self, refresh_seconds=5, *args, **kwargs):
        # Check/connect to the hotspot
        if self.check_wifi_power() and \
                self.check_connected_to_hotspot() and \
                self.get_tx_rate() > 7:

            # check can connect externally
            test_url = "http://www.google.com/"
            r = self.try_connect_to(test_url)
            if r.request.url == test_url:
                # reached external, so currently logged in to hotspot with data
                self.try_prelogin()
            else:
                # external unreachable, so r.request.url will be a login url
                self.try_login(r.request.url)
            self.update_task_status("Waiting...")
            sleep(refresh_seconds)
        else:
            sleep(5)

    def get_terminal_height(self):
        try:
            size = os.get_terminal_size().lines
        except:
            size = 11
        return size

    def update_task_status(self, status_text):
        max_items = self.terminal_height - 5
        self.task_status.insert(0,(self.time_stamp(), status_text))
        if len(self.task_status) > max_items:
            self.task_status = self.task_status[:max_items]
        self.display()

    def display(self):
        dark_red = '\033[31m'
        dark_green = '\033[32m'
        dark_yellow = '\033[33m'
        grey = '\033[37;2m'
        default = '\033[0m'
        clear = '\033c'

        print(clear, end='')
        print(f'{self.data_bar(self.remaining_data)}')
        print(f'Wi-Fi On: {self.wifi_enabled}', end='    ')
        print(f'Connected to {self.hotspot_ssid}: {self.connected_to_hotspot}', end='    ')
        print(f'Last Tx Rate: {self.tx_rate} Mbps')
        print(f'MAC Address: {self.mac_address}')
        for idx, (time, item) in enumerate(self.task_status):
            if idx == 0:
                print(default, end="")   # Latest message is white text, older messages are grey
            else:
                print(grey, end="")
            print(f'[{time}] {item}')
        print(default, end="")

    def check_wifi_power(self):
        response = networksetup("-getairportpower", "en0").strip()
        if response == "Wi-Fi Power (en0): On":
            self.wifi_enabled = True
        elif response == "Wi-Fi Power (en0): Off":
            self.wifi_enabled = False
            self.connected_to_hotspot = False
            self.update_task_status("Turning on Wi-Fi...")
            networksetup("-setairportpower", "en0", "on")
        self.display()
        return self.wifi_enabled

    def check_connected_to_hotspot(self):
        response = networksetup("-getairportnetwork", "en0").strip()
        if self.hotspot_ssid in response:
            self.connected_to_hotspot = True
        elif "You are not associated with an AirPort network." in response:
            self.connected_to_hotspot = False
            self.connect_wifi(self.hotspot_ssid)
        self.display()
        return self.connected_to_hotspot

    def connect_wifi(self, ssid: str) -> bool:
        self.update_task_status(f"Connecting to {self.hotspot_ssid}")
        networksetup("-setairportnetwork", "en0", ssid)

    def get_tx_rate(self) -> int:
        result = airport("-I")
        results_dict = {"lastTxRate": 0}
        for line in result.strip().split("\n"):
            split = line.strip().split(":")
            try:
                results_dict[split[0].strip()] = split[1].strip()
            except:
                pass  # ignore exceptions
        self.tx_rate = int(results_dict["lastTxRate"])
        self.display()
        return self.tx_rate

    def try_connect_to(self, host: str):
        # Keep trying to connect until host is reached
        zero_if_connected = 1
        while zero_if_connected > 0:
            self.update_task_status(f"Connecting to {host}, attempt {zero_if_connected}")
            self.kill_cna()  # Stop Apple's Captive Network Assistant from interrupting
            try:
                zero_if_connected += 1
                request = requests.get(host)
                if request.status_code == 200:  # Connection successful
                    zero_if_connected = 0
                    self.update_task_status(f"Connected to {host}.")
                    return request
            except:
                pass  # ignore exceptions and try again
            sleep(5)

    def try_prelogin(self):
        r = self.try_connect_to("http://192.168.182.1:3990/prelogin")
        soup = BeautifulSoup(r.content, "html.parser")
        title = soup.findAll("title")[0].text
        if title == "Logged in":
            # already logged in and there must be > 0 data left
            remaining_value, remaining_unit = self.get_remaining(soup)
            self.remaining_data = remaining_value
            if remaining_value < 25:
                # If data is low, spoof the mac to get more data
                self.spoof_mac()

    def try_login(self, actual_url):
        # append the access code to the provided login url then submit
        actual_url += '&passcode=robriv'
        r = self.try_connect_to(actual_url)
        if 'Login failed : Sorry, but you are out of data!' in r.text:
            # get more data by spoofing the mac and re-connecting
            self.spoof_mac()
        else:
            # not previously logged in with this mac address, so log in
            self.update_task_status(f"Logging in...")
            soup = BeautifulSoup(r.content, "html.parser")
            redirect_url = soup.findAll("meta")
            login_url = ""
            # get the server generated login url with challenge code, etc.
            for each in redirect_url:
                login_url = each["content"].split("0;url=")[1]
            self.try_connect_to(login_url)

    def get_mac_address(self) -> str:
        cur = ifconfig("en0")
        # command returns multiple lines, so iterate over to find the mac addr
        for line in str(cur).split("\n"):
            if "ether" in line:
                # remove the text "ether " from the start of the string
                return line.strip().split(" ")[1]

    def generate_mac_address(self) -> str:
        self.update_task_status("Generating a new MAC Address...")
        # probably non-compliant but it works
        mac = [0x60, 0xf8, 0x1d,
               randint(0x00, 0x7f),
               randint(0x00, 0x7f),
               randint(0x00, 0x7f)]
        gen = ':'.join(map(lambda x: "%02x" % x, mac))
        return gen

    def spoof_mac(self):
        self.update_task_status(f"Spoofing the MAC Address...")
        self.display()
        # generate a new random MAC address (note: may not be compliant)
        gen = self.generate_mac_address()

        # disconnect from Wi-Fi network
        # note: for sudo to work without password, add to /etc/sudoers
        # sudo airport -z
        sudo("airport", "-z")

        # spoof the mac address
        # see note re: /etc/sudoers above
        sudo("ifconfig", "en0", "ether", gen)

        self.mac_address = self.get_mac_address()

    def time_stamp(self):
        now = datetime.now()
        result = now.strftime("%H:%M:%S")
        return result

    def get_remaining(self, logged_in_soup) -> (float, str):
        self.update_task_status(f"Checking remaining data...")
        # scrape the hotspot login page for the remaining data text
        results = logged_in_soup.find_all("td", class_="aleft")
        remaining_data_text = results[1].text.strip()
        value = float(remaining_data_text.split(' ')[0])
        unit = remaining_data_text.split(' ')[1]
        return value, unit

    def data_bar(self,
                 remaining_data_value: float,
                 max_data: float = 600.00
                 ):
        # create an ascii progress bar of arbitrary width and segments
        progress_bar_width = 35
        progress_bar_bit_count = max_data / progress_bar_width
        rem_bits = remaining_data_value / progress_bar_bit_count
        bar = int(rem_bits) * "#" + int(progress_bar_width - rem_bits) * "_"
        result = f'Remaining Data: |{bar}| {remaining_data_value:.0f}/{max_data:.0f} MB ({remaining_data_value / max_data * 100:.0f} %)'
        return result

    def kill_cna(self):
        # if the Apple Captive Network Assistant is running, kill it
        try:
            result = pkill("-l", "-f", "Captive Network Assistant")
            sleep(1)
            return 1
        except:
            # do nothing
            # print("CNA not running.")
            return 0


if __name__ == '__main__':
    robriv = Hotspot("NET4")
    while True:
        robriv(60)
