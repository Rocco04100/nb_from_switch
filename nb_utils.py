import logging

"""
FOR GLOBAL LOOKUP UTILS
"""

site_table = {
    "192.168": "Bob Test site",
    "10.2": "Building 2",
    "10.3": "Building 3",
    "10.4": "Building 4",
    "10.5": "Buidling 5",
    "10.6": "Building 6",
    "10.7": "Building 7",
    "10.8": "Building 8",
    "10.10": "Building 10",
    "10.11": "Building 11",
    # "10.53": "Building 16", -> Weird ip ask question
    "10.18": "Building 18",
    "10.19": "Building 19",
    # 20-24 are term c
    "10.20": "Building 20",  # some dpips are on 10.21 in building 20 its weird probably need another octect to specify
    "10.21": "Building 21",  # im guessing those dpips in bdlg 20 with 10.21 are in the wrong site
    "10.22": "Building 22",
    "10.23": "Building 23",
    "10.24": "Building 24",  # theres a vps switch on 10.31 wierd
    "10.25": "Building 25",
    # "10.26": "Building 26", -> No building 26 maybe under alias?
    # 27-29 are term b
    "10.27": "Building 27",
    "10.28": "Building 28",  # no objects yet
    "10.29": "Building 29",
    #        "10.30": "Building 30", -> No building 30 maybe under alias?
    # 31-32 are term a
    "10.31": "Building 31",
    "10.32": "Building 32",
    "10.44": "Building 44",
    "10.45": "Building 45",
    "10.51": "Building 51",
    "10.52": "Building 52",
    "10.53": "Building 53",
    "10.55": "Building 55",
    "10.58": "Building 58",
    "10.60": "Building 60",
    "10.61": "Building 61",
    "10.66": "Building 66",
    "10.72": "Builidng 72",
    "10.75": "Building 75",
    "10.76": "Building 76",
    "10.78": "Building 78",
    "10.79": "Building 79",
    "10.81": "Builidng 81",
    "10.91": "Building 91",
    "10.96": "Building 96",
    "10.100": "Building 100",
    "10.129": "Conley Shipyard",
    # "10.128": "FP East", I got no idea if there are different subnets will have to check if we have switch location maybe
    # "10.128": "FP West"
    # "10.135": "Framingham Garage", shares with braintree lex
    "10.132": "BFCT",
    "10.135": "Braintree_Lex",
    "10.65": "Logan Office Center",
    "10.131":"Worcester Terminal",
}
def get_site(ip_address):
    if ip_address:
        return site_table[f"{".".join(ip_address.split(".")[:2])}"]
    else:
        logging.error("Site not found in site table unable to add device")
    return None
