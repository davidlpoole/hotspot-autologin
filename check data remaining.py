#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 20 18:42 2023
@author: David Poole
"""
from sh import networksetup
import requests
from bs4 import BeautifulSoup

wifi = networksetup("-getairportnetwork", "en0")

if "NET4" in wifi:
    print("Connected to NET4.")
    url = 'http://192.168.182.1:3990/prelogin'
    try:
        r = requests.get(url)
        soup = BeautifulSoup(r.content, "html.parser")
        try:
            title = soup.findAll("title")[0].text
            if title == "Logged in":
                # headings = soup.find_all("td", class_="aright")
                values = soup.find_all("td", class_="aleft")

                value = values[1].text.strip()
                mb = value.split(' ')[0]
                print("There's {remaining} left.".format(remaining=value))
        except:
            print("No title tag found.")

    except requests.exceptions.Timeout:
        print("Error: Connection Timeout.")
    except requests.exceptions.TooManyRedirects:
        print("Error: Too Many Redirects.")
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

else:
    print("Not connected to NET4.")
