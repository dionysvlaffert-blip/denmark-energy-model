import os

network_dir = "results/networks"

rename_map = {
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_nuclear_2500_eur_per_kw_zero_co2_nuclear_2500eurkw.nc":
        "57_zero_co2_nuclear_2500eurkw.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_nuclear_5000_eur_per_kw_zero_co2_nuclear_5000eurkw.nc":
        "58_zero_co2_nuclear_5000eurkw.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_nuclear_7500_eur_per_kw_zero_co2_nuclear_7500eurkw.nc":
        "59_zero_co2_nuclear_7500eurkw.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_nuclear_10000_eur_per_kw_zero_co2_nuclear_10000eurkw.nc":
        "60_zero_co2_nuclear_10000eurkw.nc",
}
# Umbenennen
renamed = 0
skipped = 0
for old_name, new_name in rename_map.items():
    old_path = os.path.join(network_dir, old_name)
    new_path = os.path.join(network_dir, new_name)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        print(f"✓ {old_name[:50]}... → {new_name}")
        renamed += 1
    else:
        print(f"✗ nicht gefunden: {old_name[:50]}...")
        skipped += 1

print(f"\nFertig: {renamed} umbenannt, {skipped} nicht gefunden")

