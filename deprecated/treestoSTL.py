import geopandas as gpd
import numpy as np
import struct
from shapely.geometry import Point

def create_tree_canopy(point, canopy_radius, trunk_height, canopy_height, trunk_radius,
                      canopy_shape='cylinder', scale_xy=1.0, sides=8):
    x, y = point.x * scale_xy, point.y * scale_xy
    triangles = []
    angles = np.linspace(0, 2*np.pi, sides+1)[:-1]

    # Trunk
    if trunk_height > 0 and trunk_radius > 0:
        trunk_bottom = [[x + trunk_radius*np.cos(a), y + trunk_radius*np.sin(a), 0] for a in angles]
        trunk_top = [[x + trunk_radius*np.cos(a), y + trunk_radius*np.sin(a), trunk_height] for a in angles]
        trunk_center_bottom = [x, y, 0]
        trunk_center_top = [x, y, trunk_height]

        for i in range(sides):
            next_i = (i + 1) % sides
            triangles.append([trunk_center_bottom, trunk_bottom[next_i], trunk_bottom[i]])
            triangles.append([trunk_center_top, trunk_top[i], trunk_top[next_i]])
            triangles.append([trunk_bottom[i], trunk_top[i], trunk_bottom[next_i]])
            triangles.append([trunk_bottom[next_i], trunk_top[i], trunk_top[next_i]])

    # Canopy
    canopy_base_z = trunk_height
    canopy_top_z = trunk_height + canopy_height

    if canopy_shape == 'cylinder':
        canopy_bottom = [[x + canopy_radius*np.cos(a), y + canopy_radius*np.sin(a), canopy_base_z] for a in angles]
        canopy_top = [[x + canopy_radius*np.cos(a), y + canopy_radius*np.sin(a), canopy_top_z] for a in angles]
        canopy_center_bottom = [x, y, canopy_base_z]
        canopy_center_top = [x, y, canopy_top_z]

        for i in range(sides):
            next_i = (i + 1) % sides
            triangles.append([canopy_center_bottom, canopy_bottom[i], canopy_bottom[next_i]])
            triangles.append([canopy_center_top, canopy_top[next_i], canopy_top[i]])
            triangles.append([canopy_bottom[i], canopy_bottom[next_i], canopy_top[i]])
            triangles.append([canopy_bottom[next_i], canopy_top[next_i], canopy_top[i]])

    return triangles

def calculate_normal(triangle):
    p1, p2, p3 = triangle
    v1 = np.array(p2) - np.array(p1)
    v2 = np.array(p3) - np.array(p1)
    normal = np.cross(v1, v2)
    norm = np.linalg.norm(normal)
    return normal / norm if norm > 0 else np.array([0, 0, 1])

def write_stl_binary(filename, triangles):
    with open(filename, 'wb') as f:
        header = b'Binary STL from trees' + b'\0' * (80 - len('Binary STL from trees'))
        f.write(header)
        f.write(struct.pack('<I', len(triangles)))
        for triangle in triangles:
            normal = calculate_normal(triangle)
            f.write(struct.pack('<fff', *normal))
            for vertex in triangle:
                f.write(struct.pack('<fff', *vertex))
            f.write(struct.pack('<H', 0))

def get_coordinate_bounds(gdf):
    bounds = gdf.total_bounds
    return {
        'min_x': bounds[0], 'min_y': bounds[1],
        'max_x': bounds[2], 'max_y': bounds[3]
    }

def shapefile_points_to_trees(shapefile_path, output_path, output_format='stl',
                             height_column=None, scale_xy=1.0, scale_z=1.0,
                             extrude_height=3.0, tree_config=None, center_origin=True):
    if tree_config is None:
        tree_config = {
            'canopy_shape': 'cylinder',
            'trunk_height_ratio': 0.25,
            'canopy_radius_ratio': 0.3,
            'trunk_radius': 0.05,
            'detail_level': 8,
            'min_tree_height': 2.0,
            'max_tree_height': 25.0
        }

    print(f"Reading shapefile: {shapefile_path}")
    gdf = gpd.read_file(shapefile_path)

    print(f"Original CRS: {gdf.crs}")
    if gdf.crs.to_epsg() != 32616:
        gdf = gdf.to_crs(epsg=32616)
        print("Reprojected to EPSG:32616 (UTM zone 16N, meters)")

    point_gdf = gdf[gdf.geometry.geom_type == 'Point'].copy()
    print(f"Found {len(point_gdf)} point features")

    if len(point_gdf) == 0:
        raise ValueError("No point geometries found in shapefile")

    bounds = get_coordinate_bounds(point_gdf)
    print(f"Coordinate bounds (meters): {bounds}")

    if center_origin:
        center_x = (bounds['min_x'] + bounds['max_x']) / 2
        center_y = (bounds['min_y'] + bounds['max_y']) / 2
        print(f"Centering coordinates at origin: ({center_x:.2f}, {center_y:.2f})")
    else:
        center_x, center_y = 0, 0

    triangles = []
    trees_created = 0

    for idx, row in point_gdf.iterrows():
        geom = row.geometry
        adjusted_point = Point(geom.x - center_x, geom.y - center_y)

        if height_column and height_column in row and row[height_column] is not None:
            try:
                height = float(row[height_column]) * scale_z
                height = max(tree_config['min_tree_height'],
                             min(tree_config['max_tree_height'], height))
            except Exception:
                height = extrude_height * scale_z
        else:
            height = extrude_height * scale_z

        trunk_height = height * tree_config['trunk_height_ratio']
        canopy_height = height - trunk_height
        trunk_radius = tree_config['trunk_radius'] * scale_xy
        canopy_radius = height * tree_config['canopy_radius_ratio'] * scale_xy

        try:
            tree_triangles = create_tree_canopy(
                point=adjusted_point,
                canopy_radius=canopy_radius,
                trunk_height=trunk_height,
                canopy_height=canopy_height,
                trunk_radius=trunk_radius,
                canopy_shape=tree_config['canopy_shape'],
                scale_xy=scale_xy,
                sides=tree_config['detail_level']
            )
            triangles.extend(tree_triangles)
            trees_created += 1
            if trees_created % 100 == 0:
                print(f"Processed {trees_created} trees...")
        except Exception as e:
            print(f"Error at index {idx}: {e}")

    print(f"Created {trees_created} trees with {len(triangles)} triangles")

    print(f"Writing to {output_format.upper()} at: {output_path}")
    if output_format.lower() == 'stl':
        write_stl_binary(output_path, triangles)
    else:
        raise ValueError("Only STL output supported in this version")

    print("✅ Tree STL model saved successfully")
    return {
        'trees_created': trees_created,
        'triangles_generated': len(triangles),
        'bounds': bounds,
        'coordinate_system': str(point_gdf.crs)
    }

if __name__ == "__main__":
    shapefile_path = "/Users/omokayj/Library/CloudStorage/GoogleDrive-omokayodejohn@gmail.com/My Drive/Research_Gdrive/USGS/lab/treesshapefileKilbourn.shp"
    output_path = "/Users/omokayj/Library/CloudStorage/GoogleDrive-omokayodejohn@gmail.com/My Drive/Research_Gdrive/USGS/lab/treesKilbourn_3D.stl"

    custom_tree_config = {
        'canopy_shape': 'cylinder',
        'trunk_height_ratio': 0.3,
        'canopy_radius_ratio': 0.4,
        'trunk_radius': 0.1,
        'detail_level': 12,
        'min_tree_height': 2.0,
        'max_tree_height': 20.0
    }

    result = shapefile_points_to_trees(
        shapefile_path=shapefile_path,
        output_path=output_path,
        output_format="stl",
        height_column=None,
        scale_xy=1.0,
        scale_z=1.0,
        extrude_height=5.0,
        tree_config=custom_tree_config,
        center_origin=True
    )

    print("\nSummary:")
    for k, v in result.items():
        print(f"{k}: {v}")
