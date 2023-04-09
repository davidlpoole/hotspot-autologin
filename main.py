import requests
from bs4 import BeautifulSoup
from time import sleep
from datetime import datetime
from sh import sudo, grep, ifconfig, networksetup
from random import randint

debug_level = False


def print_time_stamp():
    now = datetime.now()
    return now.strftime("%H:%M:%S")


def get_mac_address() -> str:
    cur = grep(ifconfig("en0"), "ether").strip()
    return cur


def generate_mac_address() -> str:

    mac = [0x60, 0xf8, 0x1d,
           randint(0x00, 0x7f),
           randint(0x00, 0x7f),
           randint(0x00, 0x7f)]
    gen = ':'.join(map(lambda x: "%02x" % x, mac))
    return gen


def check_wifi(ssid: str) -> bool:
    wifi_response = networksetup("-getairportnetwork", "en0")
    if ssid in wifi_response:
        min_rate = 7
        while not get_tx_rate() > min_rate:
            print(print_time_stamp(), "[check_wifi] lastTxRate <= {int}. Check again in 5s...".format(int=min_rate))
            sleep(5)
        return True
    else:
        return False


def connect_wifi(ssid: str) -> bool:
    for attempt in range(1, 99):
        print(print_time_stamp(), "[connect_wifi] Attempt {number} to connect to {ssid}".format(
            number=attempt,
            ssid=ssid))
        networksetup("-setairportnetwork", "en0", ssid)
        if check_wifi(ssid):
            print(print_time_stamp(), "[connect_wifi] Connected to", ssid)
            sleep(5)
            return True
        sleep(10)
    return False


def spoof_mac():

    # get current MAC address
    # ifconfig en0 | grep ether
    cur = get_mac_address()
    print(print_time_stamp(), "[spoof_mac] Current MAC Address: ", cur)

    # generate a new random MAC address (note: may not be compliant)
    gen = generate_mac_address()

    # disconnect from Wi-Fi network
    # note: for sudo to work without password, add to /etc/sudoers
    # sudo airport -z
    sudo("airport", "-z")

    # spoof the mac address
    # see note re: /etc/sudoers above
    sudo("ifconfig", "en0", "ether", gen)

    # check it updated
    check = get_mac_address()
    print(print_time_stamp(), "[spoof_mac] New MAC Address:     ", check)


def get_remaining(logged_in_soup) -> (float, str):
    results = logged_in_soup.find_all("td", class_="aleft")
    remaining_data_text = results[1].text.strip()
    value = float(remaining_data_text.split(' ')[0])
    unit = remaining_data_text.split(' ')[1]
    return value, unit


def kill_cna():
    # if the Apple Captive Network Assistant is running, kill it
    from sh import pkill
    try:
        result = pkill("-l", "-f", "Captive Network Assistant")
        print(print_time_stamp(), "[kill_cna] Killed CNA.", result)
        sleep(1)
    except:
        # do nothing
        # print("CNA not running.")
        return 0


def try_connect_to(host):
    # Keep trying until Google is reached or redirected to hotspot
    # could use ping instead?
    zero_if_connected = 1
    while zero_if_connected > 0:
        if debug_level: print(print_time_stamp(), "[try_connect_to] trying", host, "attempt:", zero_if_connected)
        kill_cna()
        try:
            request = requests.get(host)
            if request.status_code == 200:
                if debug_level: print(print_time_stamp(), "[try_connect_to]", request.status_code, request.reason, request.request.url)
                zero_if_connected = 0
                return request
        except:
            print(print_time_stamp(), "[try_connect_to] connection to", host, "failed.")
        sleep(5)


def get_tx_rate() -> int:
    # Check what rate the Wi-Fi is connected at, <=7 seems to cause issues.
    # alternatively use ping latency?
    from sh import airport
    result = airport("-I")
    results_dict = {}
    for line in result:
        split = line.strip().split(":")
        results_dict[split[0].strip()] = split[1].strip()
    last_tx_rate = int(results_dict["lastTxRate"])
    if debug_level: print(print_time_stamp(), "[get_tx_rate] lastTxRate: ", last_tx_rate)
    return last_tx_rate


for i in range(1, 1440):
    # ensure connection to the wifi hotspot
    hotspot_name = "NET4"
    while not check_wifi(hotspot_name):
        connect_wifi(hotspot_name)

    # try to connect to google.com
    test_url = "http://www.google.com/"

    r = try_connect_to(test_url)

    # compare the test_url against where it actually went
    actual_url = r.request.url
    if actual_url == test_url:
        # connection to google.com was successful
        # so try the hotspot url to login/check remaining data
        u = try_connect_to("http://192.168.182.1:3990/prelogin")

        u_soup = BeautifulSoup(u.content, "html.parser")
        title = u_soup.findAll("title")[0].text

        if title == "Logged in":
            # already logged in and there must be > 0 data left
            remaining_value, remaining_unit = get_remaining(u_soup)
            if remaining_value < 25:
                # not much though, so spoof a new mac and reconnect
                print(print_time_stamp(), "[Logged in] There's only {value} {units} left.".format(
                    value=remaining_value,
                    units=remaining_unit))
                spoof_mac()
                sleep(5)
            else:
                # enough data left, so just sleep for 60 seconds
                print(print_time_stamp(), "[Logged in] There's {value} {units} left.".format(
                    value=remaining_value,
                    units=remaining_unit))
                sleep(60)
    else:
        # not logged in yet, or maybe ran out of data
        # so try logging in
        actual_url = actual_url + '&passcode=robriv'
        # print(actual_url)
        s = try_connect_to(actual_url)

        if 'Login failed : Sorry, but you are out of data!' in s.text:
            print(print_time_stamp(), "[Logged in] Out of data, spoof the mac...")
            spoof_mac()
        else:
            # must be a new mac, so complete the login process
            s_soup = BeautifulSoup(s.content, "html.parser")
            redirect_url = s_soup.findAll("meta")

            for each in redirect_url:
                login_url = each["content"].split("0;url=")[1]
            t = try_connect_to(login_url)
