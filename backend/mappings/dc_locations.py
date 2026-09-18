DC_LOCATIONS = {
    # =========================================================
    # KEHE
    # =========================================================

    ("KEHE", "AUR"): {
        "name": "Aurora",
        "address": "2200 N Himalaya Rd",
        "city": "Aurora",
        "state": "CO",
        "zip": "80011",
        "latitude": 39.7496,
        "longitude": -104.7539,
        "location_precision": "exact_address",
    },

    ("KEHE", "BLO"): {
        "name": "Ellettsville",
        "address": "8101 W State Rd 46",
        "city": "Ellettsville",
        "state": "IN",
        "zip": "47429",
        "latitude": 39.2284,
        "longitude": -86.6250,
        "location_precision": "exact_address",
    },

    ("KEHE", "CHN"): {
        "name": "Chino",
        "address": "16081 Fern Ave",
        "city": "Chino",
        "state": "CA",
        "zip": "91708",
        "latitude": 33.9537,
        "longitude": -117.6420,
        "location_precision": "exact_address",
    },

    ("KEHE", "DFW"): {
        "name": "Dallas",
        "address": "4450 Logistics Dr",
        "city": "Dallas",
        "state": "TX",
        "zip": "75241",
        "latitude": 32.6719,
        "longitude": -96.7436,
        "location_precision": "exact_address",
    },

    ("KEHE", "DGV"): {
        "name": "Douglasville",
        "address": "1851 Riverside Pkwy",
        "city": "Douglasville",
        "state": "GA",
        "zip": "30135",
        "latitude": 33.7135,
        "longitude": -84.6075,
        "location_precision": "exact_address",
    },

    ("KEHE", "EMD"): {
        "name": "North East",
        "address": "585 Principio Pkwy W",
        "city": "North East",
        "state": "MD",
        "zip": "21901",
        "latitude": 39.5898,
        "longitude": -76.0015,
        "location_precision": "exact_address",
    },

    ("KEHE", "LHV"): {
        "name": "Lehigh Valley",
        "address": "860 Nestle Way, Suite 250",
        "city": "Breinigsville",
        "state": "PA",
        "zip": "18031",
        "latitude": 40.570181,
        "longitude": -75.648356,
        "location_precision": "exact_address",
    },

    ("KEHE", "MIA"): {
        "name": "Miami",
        "address": "4020 W 104th St",
        "city": "Hialeah",
        "state": "FL",
        "zip": "33018",
        "latitude": 25.8697,
        "longitude": -80.3554,
        "location_precision": "exact_address",
    },

    ("KEHE", "NCA"): {
        "name": "Stockton",
        "address": "4650 Newcastle Rd",
        "city": "Stockton",
        "state": "CA",
        "zip": "95215",
        "latitude": 37.9528,
        "longitude": -121.2384,
        "location_precision": "exact_address",
    },

    ("KEHE", "PHX"): {
        "name": "Phoenix",
        "address": "17510 W Thomas Rd",
        "city": "Goodyear",
        "state": "AZ",
        "zip": "85395",
        "latitude": 33.4795,
        "longitude": -112.4306,
        "location_precision": "exact_address",
    },

    ("KEHE", "POR"): {
        "name": "Portland",
        "address": "9555 NE Alderwood Rd",
        "city": "Portland",
        "state": "OR",
        "zip": "97220",
        "latitude": 45.5735,
        "longitude": -122.5637,
        "location_precision": "exact_address",
    },

    # =========================================================
    # UNFI
    # =========================================================

    ("UNFI", "GRW"): {
        "name": "Greenwood",
        "address": "655 Commerce Parkway East Dr",
        "city": "Greenwood",
        "state": "IN",
        "zip": "46143",
        "latitude": 39.610565,
        "longitude": -86.057557,
        "location_precision": "exact_address",
    },

    ("UNFI", "HOW"): {
        "name": "Howell",
        "address": "433 Oak Glen Rd",
        "city": "Howell",
        "state": "NJ",
        "zip": "07731",
        "latitude": 40.139971,
        "longitude": -74.188791,
        "location_precision": "exact_address",
    },

    ("UNFI", "HVA"): {
        "name": "Hudson Valley",
        "address": "525 Neelytown Rd",
        "city": "Montgomery",
        "state": "NY",
        "zip": "12549",
        "latitude": 41.5039,
        "longitude": -74.2189,
        "location_precision": "exact_address",
    },

    ("UNFI", "MAN"): {
        "name": "Manchester",
        "address": "1025 Locust Point Rd",
        "city": "Manchester",
        "state": "PA",
        "zip": "17345",
        "latitude": 40.0706,
        "longitude": -76.7198,
        "location_precision": "exact_address",
    },

    # Client PO data identifies POR as Ridgefield.
    # We do not yet have a verified street address for this exact DC.
    ("UNFI", "POR"): {
        "name": "Ridgefield",
        "address": None,
        "city": "Ridgefield",
        "state": "WA",
        "zip": None,
        "latitude": 45.8151,
        "longitude": -122.7426,
        "location_precision": "city",
    },

    ("UNFI", "RCH"): {
        "name": "Richburg",
        "address": "578B L&C Distribution Center",
        "city": "Richburg",
        "state": "SC",
        "zip": "29729",
        "latitude": 34.7047,
        "longitude": -81.0209,
        "location_precision": "exact_address",
    },

    # Client PO data identifies SCAL specifically as Moreno Valley.
    # Use city-level coordinates until we verify its exact street address.
    ("UNFI", "SCAL"): {
        "name": "Moreno Valley",
        "address": None,
        "city": "Moreno Valley",
        "state": "CA",
        "zip": None,
        "latitude": 33.9425,
        "longitude": -117.2297,
        "location_precision": "city",
    },

    ("UNFI", "SRQ"): {
        "name": "Sarasota North",
        "address": "8380 21st St E",
        "city": "Sarasota",
        "state": "FL",
        "zip": "34243",
        "latitude": 27.4057,
        "longitude": -82.4498,
        "location_precision": "exact_address",
    },
}