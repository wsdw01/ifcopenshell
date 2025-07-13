import ifcopenshell
import ifcopenshell.api
import ifcopenshell.guid
import numpy as np
import os

# --- Configuration ---
ANGLE_TOLERANCE = 0.005
MIN_POINTS_FOR_SEGMENT = 3

def get_polyline_from_proxy(proxy):
    if proxy.Representation:
        for rep in proxy.Representation.Representations:
            if rep.RepresentationIdentifier == 'GeometricCurveSet':
                for item in rep.Items:
                    if item.is_a("IfcPolyline"):
                        return item
    return None

def calculate_bearing(p1, p2):
    return np.arctan2(p2[0] - p1[0], p2[1] - p1[1])

def get_circle_from_three_points(p1, p2, p3):
    p1, p2, p3 = np.array(p1), np.array(p2), np.array(p3)
    v1 = p2 - p1
    v2 = p3 - p1
    if np.linalg.norm(np.cross(v1, v2)) < 1e-9:
        return float('inf'), None
    p1_sq = np.dot(p1, p1)
    p2_sq = np.dot(p2, p2)
    p3_sq = np.dot(p3, p3)
    A = np.array([[p1[0], p1[1], 1], [p2[0], p2[1], 1], [p3[0], p3[1], 1]])
    Bx = -np.array([p1_sq, p2_sq, p3_sq])
    a = np.linalg.det(A)
    if abs(a) < 1e-9: return float('inf'), None
    Dx = np.linalg.det(np.column_stack((Bx, A[:,1], A[:,2])))
    Dy = np.linalg.det(np.column_stack((A[:,0], Bx, A[:,2])))
    c = -np.linalg.det(np.column_stack((A[:,0], A[:,1], Bx)))
    center_x, center_y = -Dx / (2 * a), -Dy / (2 * a)
    radius = np.sqrt(center_x**2 + center_y**2 - c/a)
    return radius, np.array([center_x, center_y])

def analyze_horizontal_geometry(points):
    if len(points) < MIN_POINTS_FOR_SEGMENT: return []
    segments = []
    current_segment_points = [points[0]]
    is_line = True
    for i in range(1, len(points) - 1):
        p_prev, p_curr, p_next = points[i-1], points[i], points[i+1]
        angle_diff = abs(calculate_bearing(p_prev, p_curr) - calculate_bearing(p_curr, p_next))
        if is_line:
            if angle_diff < ANGLE_TOLERANCE:
                current_segment_points.append(p_curr)
            else:
                if len(current_segment_points) >= 2: segments.append({'type': 'line', 'points': current_segment_points})
                current_segment_points = [p_curr]
                is_line = False
        else:
            if angle_diff >= ANGLE_TOLERANCE:
                current_segment_points.append(p_curr)
            else:
                if len(current_segment_points) >= 3: segments.append({'type': 'arc', 'points': current_segment_points})
                current_segment_points = [p_curr]
                is_line = True
    current_segment_points.append(points[-1])
    if len(current_segment_points) >= 2:
        segment_type = 'line' if is_line else 'arc'
        if segment_type == 'arc' and len(current_segment_points) < 3: segment_type = 'line'
        segments.append({'type': segment_type, 'points': current_segment_points})
    
    processed_segments = []
    for seg in segments:
        start_point, end_point = seg['points'][0], seg['points'][-1]
        if seg['type'] == 'line':
            length = np.linalg.norm(end_point - start_point)
            processed_segments.append({'type': 'line', 'start': start_point, 'end': end_point, 'length': length})
        elif seg['type'] == 'arc':
            mid_point = seg['points'][len(seg['points']) // 2]
            radius, _ = get_circle_from_three_points(start_point, mid_point, end_point)
            if radius == float('inf'):
                length = np.linalg.norm(end_point - start_point)
                processed_segments.append({'type': 'line', 'start': start_point, 'end': end_point, 'length': length})
                continue
            v1, v2 = end_point - start_point, mid_point - start_point
            is_left = (v1[0] * v2[1] - v1[1] * v2[0]) > 0
            chord_length = np.linalg.norm(end_point - start_point)
            arc_length = 2 * radius * np.arcsin(chord_length / (2 * radius)) if (2*radius) > chord_length else chord_length
            processed_segments.append({
                'type': 'arc', 'points': seg['points'], 'start': start_point, 'end': end_point, 
                'mid': mid_point, 'radius': radius, 'is_left': is_left, 'length': arc_length
            })
    return processed_segments

def get_z_from_3d_polyline(xy_point, polyline_3d_points):
    point_2d = np.array([xy_point[0], xy_point[1]])
    points_3d_2d = polyline_3d_points[:, :2]
    distances = np.linalg.norm(points_3d_2d - point_2d, axis=1)
    closest_idx = np.argmin(distances)
    return polyline_3d_points[closest_idx][2]

def create_stakeout_point(ifc_file, site, owner_history, name, coords, properties):
    point_geom = ifc_file.create_entity("IfcCartesianPoint", Coordinates=coords)
    placement = ifc_file.create_entity("IfcLocalPlacement", RelativePlacement=ifc_file.create_entity("IfcAxis2Placement3D", Location=point_geom))
    stakeout_point = ifc_file.create_entity("IfcReferent", ifcopenshell.guid.new(), owner_history, Name=name, ObjectPlacement=placement, PredefinedType='POSITION')
    prop_values = [ifc_file.create_entity("IfcPropertySingleValue", k, None, ifc_file.create_entity("IfcLabel", str(v))) for k, v in properties.items()]
    prop_set = ifc_file.create_entity("IfcPropertySet", ifcopenshell.guid.new(), owner_history, "Pset_StakeoutPoint", None, prop_values)
    ifc_file.create_entity("IfcRelDefinesByProperties", ifcopenshell.guid.new(), owner_history, Name=None, Description=None, RelatingPropertyDefinition=prop_set, RelatedObjects=[stakeout_point])
    return stakeout_point

def create_coordinate_annotation(ifc_file, owner_history, context, name, coords, text_height=150.0):
    """Creates a visible text annotation in the IFC file."""
    
    text_to_display = f"X: {coords[0]:.3f}\nY: {coords[1]:.3f}\nZ: {coords[2]:.3f}"

    annotation_placement_3d = ifc_file.create_entity(
        "IfcAxis2Placement3D",
        Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=tuple(coords))
    )

    annotation = ifc_file.create_entity(
        "IfcAnnotation",
        ifcopenshell.guid.new(),
        owner_history,
        Name=name,
        ObjectType="COORDINATE_LABEL",
        ObjectPlacement=ifc_file.create_entity("IfcLocalPlacement", RelativePlacement=annotation_placement_3d)
    )

    text_literal = ifc_file.create_entity(
        "IfcTextLiteralWithExtent",
        Literal=text_to_display,
        Placement=ifc_file.create_entity(
            "IfcAxis2Placement2D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
        ),
        Path='RIGHT',
        Extent=ifc_file.create_entity(
            "IfcPlanarExtent", 
            SizeInX=text_height * 12,
            SizeInY=text_height * 4
        ),
        BoxAlignment='top-left'
    )

    text_style_font = ifc_file.create_entity(
        "IfcTextStyleFontModel",
        FontSize=ifc_file.create_entity("IfcPositiveLengthMeasure", text_height)
    )
    text_style = ifc_file.create_entity(
        "IfcTextStyle", 
        TextCharacterAppearance=text_style_font
    )
    
    styled_item = ifc_file.create_entity(
        "IfcStyledItem", 
        Item=text_literal, 
        Styles=[text_style]
    )

    annotation_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier='Annotation',
        RepresentationType='Annotation2D',
        Items=[styled_item]
    )

    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[annotation_representation]
    )
    annotation.Representation = product_shape

    return annotation

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_ifc_path = os.path.join(script_dir, "..", "01_Source_IFCs", "Achse.IFC")
    output_ifc_path = os.path.join(script_dir, "..", "02_Generated_IFCs", "Achse_with_Stakeout_Points.ifc")

    ifc_file = ifcopenshell.open(source_ifc_path)
    
    polyline_2d, polyline_3d = None, None
    for polyline in ifc_file.by_type("IfcPolyline"):
        refs = ifc_file.get_inverse(polyline)
        for ref in refs:
            if ref.is_a("IfcShapeRepresentation"):
                if hasattr(ref, 'OfProductRepresentation') and ref.OfProductRepresentation:
                    prod_def_shape = ref.OfProductRepresentation[0]
                    if hasattr(prod_def_shape, 'ShapeOfProduct') and prod_def_shape.ShapeOfProduct:
                        product = prod_def_shape.ShapeOfProduct[0]
                        if product.is_a("IfcBuildingElementProxy"):
                            if hasattr(product, 'ContainedInStructure') and product.ContainedInStructure:
                                parent_name = product.ContainedInStructure[0].RelatingStructure.Name
                                if "2D-Linie" in parent_name: polyline_2d = polyline
                                elif "Raumkurve" in parent_name: polyline_3d = polyline
    
    if not polyline_2d or not polyline_3d:
        print("Could not find both 2D and 3D polylines. Aborting.")
        return

    points_2d = np.array([p.Coordinates for p in polyline_2d.Points])
    points_3d = np.array([p.Coordinates for p in polyline_3d.Points])
    
    print("--- Analyzing Horizontal Geometry ---")
    horizontal_segments = analyze_horizontal_geometry(points_2d)
    
    site = ifc_file.by_type("IfcSite")[0]
    owner_history = ifc_file.by_type("IfcOwnerHistory")[0]
    context = ifc_file.by_type("IfcGeometricRepresentationContext")[0]
    stakeout_points = []
    coordinate_annotations = []
    chainage = 0.0
    
    print("\n--- Creating Stakeout Points and Annotations for Arcs ---")
    for i, seg in enumerate(horizontal_segments):
        if seg['type'] == 'arc':
            print(f"Processing Arc #{i+1} (Radius: {seg['radius']:.2f}m)")
            
            # Start of Arc
            z_start = get_z_from_3d_polyline(seg['start'], points_3d)
            coords_start = [float(seg['start'][0]), float(seg['start'][1]), float(z_start)]
            stakeout_points.append(create_stakeout_point(ifc_file, site, owner_history, f"Arc {i+1} - Start", coords_start, {'PointType': 'Arc Start', 'Segment': i+1, 'Radius': f"{seg['radius']:.2f}", 'Chainage': f"{chainage:.3f}"}))
            coordinate_annotations.append(create_coordinate_annotation(ifc_file, owner_history, context, f"Coords Arc {i+1} - Start", coords_start))

            # Mid of Arc
            z_mid = get_z_from_3d_polyline(seg['mid'], points_3d)
            coords_mid = [float(seg['mid'][0]), float(seg['mid'][1]), float(z_mid)]
            stakeout_points.append(create_stakeout_point(ifc_file, site, owner_history, f"Arc {i+1} - Mid", coords_mid, {'PointType': 'Arc Mid', 'Segment': i+1, 'Radius': f"{seg['radius']:.2f}", 'Chainage': f"{chainage + seg['length']/2:.3f}"}))
            coordinate_annotations.append(create_coordinate_annotation(ifc_file, owner_history, context, f"Coords Arc {i+1} - Mid", coords_mid))

            # End of Arc
            z_end = get_z_from_3d_polyline(seg['end'], points_3d)
            coords_end = [float(seg['end'][0]), float(seg['end'][1]), float(z_end)]
            stakeout_points.append(create_stakeout_point(ifc_file, site, owner_history, f"Arc {i+1} - End", coords_end, {'PointType': 'Arc End', 'Segment': i+1, 'Radius': f"{seg['radius']:.2f}", 'Chainage': f"{chainage + seg['length']:.3f}"}))
            coordinate_annotations.append(create_coordinate_annotation(ifc_file, owner_history, context, f"Coords Arc {i+1} - End", coords_end))
        
        chainage += seg['length']

    if stakeout_points:
        stakeout_group = ifc_file.create_entity("IfcGroup", ifcopenshell.guid.new(), owner_history, Name="Stakeout Points (Arcs)", ObjectType="Survey points")
        ifc_file.create_entity("IfcRelAssignsToGroup", ifcopenshell.guid.new(), owner_history, RelatedObjects=stakeout_points, RelatingGroup=stakeout_group)
        print(f"\nAdded {len(stakeout_points)} stakeout points to a new group.")

    if coordinate_annotations:
        annotation_group = ifc_file.create_entity("IfcGroup", ifcopenshell.guid.new(), owner_history, Name="Coordinate Annotations", ObjectType="Annotations")
        ifc_file.create_entity("IfcRelAssignsToGroup", ifcopenshell.guid.new(), owner_history, RelatedObjects=coordinate_annotations, RelatingGroup=annotation_group)
        print(f"Added {len(coordinate_annotations)} coordinate annotations to a new group.")

    ifc_file.write(output_ifc_path)
    print(f"\nSuccessfully created new IFC file at:\n{output_ifc_path}")

if __name__ == "__main__":
    main()
