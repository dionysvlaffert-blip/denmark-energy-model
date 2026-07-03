from pathlib import Path
import sys
import matplotlib.pyplot as plt
import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.fixxed_values import COUNTRY


GADM_FILE = Path("data/raw/gadm41_DNK_2.json")
OUTPUT_DIR = Path("data/processed/regions")

REGION_NAME_COLUMN = "NAME_2"
SEPARATION_LEVEL = "level_2"



def load_regions():
    """
    Load raw GADM regions and assign simple numeric region IDs.

    Input: GADM_FILE and fixed country/region settings.
    Output: GeoDataFrame with region_name, region_id and geometry.
    """
    if not GADM_FILE.exists():
        raise FileNotFoundError(f"GADM file not found: {GADM_FILE}")

    regions = gpd.read_file(GADM_FILE)

    if regions.crs is None:
        regions = regions.set_crs("EPSG:4326")

    if "COUNTRY" in regions.columns:
        regions = regions[regions["COUNTRY"] == COUNTRY]

    regions = regions[[REGION_NAME_COLUMN, "geometry"]].copy()
    #set column to region
    regions = regions.rename(columns={REGION_NAME_COLUMN: "region_name"})
    #set index as region name to imporve accasablitalty ( normal names have spezial characters..)
    regions["region_id"] = range(1, len(regions) + 1)
    return regions


def add_bus_coordinates(regions):
    """
    Calculate region area and representative bus coordinates.

    Input: regions GeoDataFrame.
    Output: GeoDataFrame with area_km2, bus_x and bus_y.
    """
    regions_projected = regions.to_crs("EPSG:3035")
    representative_points = regions_projected.representative_point().to_crs("EPSG:4326")

    regions = regions.to_crs("EPSG:4326").copy()
    regions["area_km2"] = regions_projected.area / 1_000_000
    regions["bus_x"] = representative_points.x
    regions["bus_y"] = representative_points.y
    return regions


def save_regions(regions, suffix=""):
    """
    Save processed region geometries and coordinate table.

    Inputs: regions GeoDataFrame and filename suffix.
    Output: writes GeoJSON and CSV files.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    regions.to_file(OUTPUT_DIR / f"denmark_regions{suffix}.geojson", driver="GeoJSON")

    regions[["region_id", "region_name", "area_km2", "bus_x", "bus_y"]].to_csv(
        OUTPUT_DIR / f"denmark_region_coordinates_{suffix}.csv",
        index=False,
    )

regions = load_regions()
regions.plot(column="NAME_2", legend=True, figsize=(10, 10))
plt.show()
regions = add_bus_coordinates(regions)
save_regions(regions, suffix=SEPARATION_LEVEL)

print(regions[["region_id", "region_name", "bus_x", "bus_y"]])
print(f"Saved {len(regions)} regions to {OUTPUT_DIR}")