from math import asin, cos, radians, sin, sqrt


def calculate_distance_km(region_i, region_j):
    """
    Calculate great-circle distance between two region bus coordinates.

    Inputs: two region rows with bus_x and bus_y in lon/lat degrees.
    Output: distance in km.
    """
    earth_radius_km = 6371
    lon_i = radians(region_i["bus_x"])
    lat_i = radians(region_i["bus_y"])
    lon_j = radians(region_j["bus_x"])
    lat_j = radians(region_j["bus_y"])

    dlon = lon_j - lon_i
    dlat = lat_j - lat_i
    a = sin(dlat / 2) ** 2 + cos(lat_i) * cos(lat_j) * sin(dlon / 2) ** 2
    return 2 * earth_radius_km * asin(sqrt(a))


def count_transmission_components(region_ids, connections):
    """
    Count connected components(number of independent cycles) in the regional transmission graph.

    Inputs: region IDs and connection tuples (region_i, region_j, distance_km).
    Output: number of graph components.
    """
    regions_to_check = set(region_ids)
    component_count = 0

    while regions_to_check:
        component_count += 1
        connected_regions = {regions_to_check.pop()}    #reinitialize connected regions with the first entry
        found_new_region = True

        while found_new_region:
            found_new_region = False
            # check for all conections if any region is connected to current node 
            for region_i, region_j, _ in connections:
                if region_i in connected_regions and region_j in regions_to_check:
                    connected_regions.add(region_j)
                    regions_to_check.remove(region_j)
                    found_new_region = True

                if region_j in connected_regions and region_i in regions_to_check:
                    connected_regions.add(region_i)
                    regions_to_check.remove(region_i)
                    found_new_region = True

    return component_count


def transmission_is_connected(region_ids, connections):
    """
    Check whether all regions are connected by the transmission graph.

    Inputs: region IDs and connection tuples.
    Output: True if the graph has one component.
    """
    return count_transmission_components(region_ids, connections) == 1


def find_n_minus_1_critical_connections(region_ids, connections):
    """
    Find links whose removal disconnects the graph.

    Inputs: region IDs and connection tuples.
    Output: list of critical (region_i, region_j) pairs.
    """
    if not transmission_is_connected(region_ids, connections):
        return []

    critical_connections = []

    for connection in connections:
        remaining_connections = [other_connection for other_connection in connections if other_connection != connection]

        if not transmission_is_connected(region_ids, remaining_connections):
            region_i, region_j, _ = connection
            critical_connections.append((region_i, region_j))

    return critical_connections


def find_transmission_connections(regions, max_distance_km):
    """
    Build all regional transmission connections below a distance threshold.

    Inputs: regions and maximum distance in km.
    Output: list of connection tuples (region_i, region_j, distance_km).
    """
    connections = []
    region_ids = list(regions["region_id"])
    region_rows = list(regions.iterrows())

    for i in range(len(region_rows)):
        region_i = region_rows[i][1]

        for j in range(i + 1, len(region_rows)):
            region_j = region_rows[j][1]
            distance_km = calculate_distance_km(region_i, region_j)

            if distance_km <= max_distance_km:
                connections.append((region_i["region_id"], region_j["region_id"], distance_km))

    topology = analyse_transmission_topology(regions, connections)
    print_transmission_topology(topology)

    return connections


def analyse_transmission_topology(regions, connections):
    """
    Calculate simple graph metrics for the transmission topology.

    Inputs: regions and connection tuples.
    Output: dict with connectedness, degrees, density and N-1 information.
    """
    region_ids = list(regions["region_id"])
    degrees = {region_id: 0 for region_id in region_ids}

    for region_i, region_j, _ in connections:
        degrees[region_i] += 1
        degrees[region_j] += 1

    possible_links = len(region_ids) * (len(region_ids) - 1) / 2
    component_count = count_transmission_components(region_ids, connections)
    critical_connections = find_n_minus_1_critical_connections(region_ids, connections)
    connected = component_count == 1

    return {
        "number_of_regions": len(region_ids),
        "number_of_links": len(connections),
        "connected": connected,
        "component_count": component_count,
        "min_degree": min(degrees.values()),
        "max_degree": max(degrees.values()),
        "average_degree": sum(degrees.values()) / len(degrees),
        "density": len(connections) / possible_links,
        "cycle_count": len(connections) - len(region_ids) + component_count,
        "n_minus_1": connected and not critical_connections,
        "critical_connections": critical_connections,
    }


def print_transmission_topology(topology):
    """
    Print a compact one-line summary of topology metrics.

    Input: topology dict from analyse_transmission_topology.
    Output: prints to console; returns nothing.
    """
    print(
        "Transmission topology: "
        f"regions={topology['number_of_regions']}, "
        f"links={topology['number_of_links']}, "
        f"connected={topology['connected']}, "
        f"components={topology['component_count']}, "
        f"n_minus_1={topology['n_minus_1']}, "
        f"cycles={topology['cycle_count']}, "
        f"density={topology['density']:.2f}, "
        f"degree_min_avg_max={topology['min_degree']}/"
        f"{topology['average_degree']:.1f}/"
        f"{topology['max_degree']}"
    )
