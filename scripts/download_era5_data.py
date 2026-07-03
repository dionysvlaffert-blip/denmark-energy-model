from pathlib import Path

import requests
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

original_request = requests.sessions.Session.request


def request_without_ssl_verification(self, method, url, **kwargs):
    """
    Forward requests with SSL verification disabled for ERA5 download issues.

    Inputs: requests Session arguments.
    Output: response from the original requests method.
    """
    kwargs["verify"] = False
    return original_request(self, method, url, **kwargs)


requests.sessions.Session.request = request_without_ssl_verification

import atlite


YEAR = 2024

# Atlite uses longitude as x and latitude as y.
# Bounds for Denmark excluding Greenland and Faroe Islands, including Bornholm,
# with the required 0.25 degree buffer.
X_MIN = 7.75
X_MAX = 15.55
Y_MIN = 54.15
Y_MAX = 58.15

CUTOUT_FILE = Path(f"data/raw/weather/{YEAR}/denmark_era5_{YEAR}.nc")


CUTOUT_FILE.parent.mkdir(parents=True, exist_ok=True)

cutout = atlite.Cutout(
    path=str(CUTOUT_FILE),
    module="era5",
    x=slice(X_MIN, X_MAX),
    y=slice(Y_MIN, Y_MAX),
    time=slice(f"{YEAR}-01-01", f"{YEAR}-12-31"),
)

cutout.prepare(
    features=["influx", "temperature", "wind", "height"],
    show_progress=True,
)

print(f"Atlite cutout written to: {CUTOUT_FILE}")