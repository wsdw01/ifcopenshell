import ifcopenshell
import ifcopenshell.api
import ifcopenshell.guid
import numpy as np
import os

# --- Configuration ---
# Tolerance for detecting a straight line. Angle in radians.
# A smaller value makes the detection stricter.
ANGLE_TOLERANCE = 0.005  # Approx 0.3 degrees

# Minimum number of points to define a curve or a line
MIN_POINTS_FOR_SEGMENT = 3

def get_polyline_from_proxy(proxy):
    """Extracts an IfcPolyline from an IfcBuildingElementProxy."""
    if proxy.Representation:
        for rep in proxy.Representation.Representations:
            if rep.RepresentationIdentifier == 'GeometricCurveSet':
                for item in rep.Items:
                    if item.is_a("IfcPolyline"):
                        return item
    return None

def calculate_bearing(p1, p2):
    """Calculates the bearing (azimuth) between two points."""
    return np.arctan2(p2[0] - p1[0], p2[1] - p1[1])

def get_circle_from_three_points(p1, p2, p3):
    """Calculates the radius and center of a circle passing through three points."""
    # Using the formula from https://www.ambrsoft.com/trigocalc/circle3d.htm
    p1, p2, p3 = np.array(p1), np.array(p2), np.array(p3)
    v1 = p2 - p1
    v2 = p3 - p1
    
    # Check for colinearity
    if np.linalg.norm(np.cross(v1, v2)) < 1e-9:
        return float('inf'), None # Colinear points, infinite radius

    p1_sq = np.dot(p1, p1)
    p2_sq = np.dot(p2, p2)
    p3_sq = np.dot(p3, p3)

    A = np.array([
        [p1[0], p1[1], 1],
        [p2[0], p2[1], 1],
        [p3[0], p3[1], 1]
    ])
    
    Bx = -np.array([p1_sq, p2_sq, p3_sq])
    By = np.array([p1[0], p2[0], p3[0]])
    
    Dx = np.linalg.det(np.column_stack((Bx, A[:,1], A[:,2])))
    Dy = np.linalg.det(np.column_stack((A[:,0], Bx, A[:,2])))
    
    a = np.linalg.det(A)
    if abs(a) < 1e-9:
        return float('inf'), None # Colinear

    c = -np.linalg.det(np.column_stack((A[:,0], A[:,1], Bx)))

    center_x = -Dx / (2 * a)
    center_y = -Dy / (2 * a)
    
    radius = np.sqrt(center_x**2 + center_y**2 - c/a)
    center = np.array([center_x, center_y])
    
    return radius, center

def analyze_horizontal_geometry(points):
    """
    Analyzes a 2D polyline and segments it into lines and circular arcs.
    Returns a list of segment dictionaries.
    """
    if len(points) < MIN_POINTS_FOR_SEGMENT:
        return []

    segments = []
    current_segment_points = [points[0]]
    is_line = True

    for i in range(1, len(points) - 1):
        p_prev = points[i-1]
        p_curr = points[i]
        p_next = points[i+1]

        bearing1 = calculate_bearing(p_prev, p_curr)
        bearing2 = calculate_bearing(p_curr, p_next)
        angle_diff = abs(bearing1 - bearing2)

        if is_line:
            if angle_diff < ANGLE_TOLERANCE:
                # Still a line
                current_segment_points.append(p_curr)
            else:
                # Line ends, curve begins
                current_segment_points.append(p_curr)
                if len(current_segment_points) >= 2:
                    segments.append({'type': 'line', 'points': current_segment_points})
                current_segment_points = [p_curr]
                is_line = False
        else: # is_curve
            if angle_diff >= ANGLE_TOLERANCE:
                 # Still a curve
                current_segment_points.append(p_curr)
            else:
                # Curve ends, line begins
                current_segment_points.append(p_curr)
                if len(current_segment_points) >= 3:
                    segments.append({'type': 'arc', 'points': current_segment_points})
                current_segment_points = [p_curr]
                is_line = True

    # Add the last point and finalize the last segment
    current_segment_points.append(points[-1])
    if len(current_segment_points) >= 2:
        segment_type = 'line' if is_line else 'arc'
        if segment_type == 'arc' and len(current_segment_points) < 3:
            segment_type = 'line' # Not enough points for an arc
        segments.append({'type': segment_type, 'points': current_segment_points})

    # --- Post-process segments to calculate parameters ---
    processed_segments = []
    for seg in segments:
        start_point = seg['points'][0]
        end_point = seg['points'][-1]
        
        if seg['type'] == 'line':
            length = np.linalg.norm(end_point - start_point)
            processed_segments.append({
                'type': 'line',
                'start': start_point,
                'end': end_point,
                'length': length
            })
            print(f"Detected Line: Length={length:.3f}m")
        elif seg['type'] == 'arc':
            mid_point = seg['points'][len(seg['points']) // 2]
            radius, center = get_circle_from_three_points(start_point, mid_point, end_point)
            
            if radius == float('inf'): # Colinear points detected
                 length = np.linalg.norm(end_point - start_point)
                 processed_segments.append({'type': 'line', 'start': start_point, 'end': end_point, 'length': length})
                 print(f"Detected Line (from degenerated arc): Length={length:.3f}m")
                 continue

            # Determine if the arc is left or right turning
            # Formula for 2D cross product: (x1*y2 - y1*x2)
            v1 = end_point - start_point
            v2 = mid_point - start_point
            cross_product_z = v1[0] * v2[1] - v1[1] * v2[0]
            is_left = cross_product_z > 0

            length = np.linalg.norm(end_point - start_point) # Chord length
            arc_length = 2 * radius * np.arcsin(length / (2 * radius))

            processed_segments.append({
                'type': 'arc',
                'start': start_point,
                'end': end_point,
                'radius': radius,
                'is_left': is_left,
                'length': arc_length
            })
            print(f"Detected Arc: Radius={radius:.3f}m, Length={arc_length:.3f}m, Turn={'Left' if is_left else 'Right'}")

    return processed_segments


def create_ifc_alignment_file(output_path, horizontal_segments):
    """Creates a new IFC file with an IfcAlignment entity."""
    
    # --- Boilerplate IFC Creation ---
    f = ifcopenshell.file(schema="IFC4X3")
    owner = f.createIfcOwnerHistory(
        f.createIfcPersonAndOrganization(
            f.createIfcPerson(Identification="WJ", GivenName="Wojciech"),
            f.createIfcOrganization(Name="Bonsai-BIM"), None),
        f.createIfcApplication(
            f.createIfcOrganization(Name="IfcOpenShell"),
            ifcopenshell.version, "Ios-python", "reconstruct_alignment.py"
        )
    )
    project = f.createIfcProject(ifcopenshell.guid.new(), owner, Name="Reconstructed Road Axis")
    ctx = f.createIfcGeometricRepresentationContext(
        ContextIdentifier='Model', ContextType='Model', CoordinateSpaceDimension=3, Precision=1e-6,
        WorldCoordinateSystem=f.createIfcAxis2Placement3D(f.createIfcCartesianPoint([0.0, 0.0, 0.0])),
        TrueNorth=f.createIfcDirection([0.0, 1.0])
    )
    f.createIfcRelAggregates(ifcopenshell.guid.new(), owner, RelatingObject=project, RelatedObjects=[
        f.createIfcSite(ifcopenshell.guid.new(), owner, Name="Project Site")
    ])

    # --- Create IfcAlignment ---
    alignment = f.createIfcAlignment(ifcopenshell.guid.new(), owner, Name="Reconstructed Alignment")
    
    # --- Create Horizontal Alignment ---
    horizontal_curve_segments = []
    start_dist = 0.0
    
    for i, seg in enumerate(horizontal_segments):
        start_point_2d = f.createIfcCartesianPoint([float(seg['start'][0]), float(seg['start'][1])])
        
        if seg['type'] == 'line':
            segment = f.createIfcSegment(
                ParentCurve=None,
                SegmentLength=f.createIfcPositiveLengthMeasure(seg['length']),
                StartPoint=start_point_2d,
                StartDirection=f.createIfcDirection([
                    float((seg['end'][0] - seg['start'][0]) / seg['length']),
                    float((seg['end'][1] - seg['start'][1]) / seg['length'])
                ]),
                SegmentType='LINE'
            )
        elif seg['type'] == 'arc':
            segment = f.createIfcSegment(
                ParentCurve=None,
                SegmentLength=f.createIfcPositiveLengthMeasure(seg['length']),
                StartPoint=start_point_2d,
                StartDirection=f.createIfcDirection([
                    float((horizontal_segments[i+1]['start'][0] - seg['start'][0]) / np.linalg.norm(horizontal_segments[i+1]['start'] - seg['start']) if i+1 < len(horizontal_segments) else (seg['end'][0] - seg['start'][0]) / seg['length']),
                    float((horizontal_segments[i+1]['start'][1] - seg['start'][1]) / np.linalg.norm(horizontal_segments[i+1]['start'] - seg['start']) if i+1 < len(horizontal_segments) else (seg['end'][1] - seg['start'][1]) / seg['length'])
                ]),
                SegmentType='CIRCULARARC',
                Radius=f.createIfcPositiveLengthMeasure(seg['radius']),
                IsCCW=seg['is_left']
            )
            
        horizontal_curve_segments.append(
            f.createIfcAlignmentHorizontalSegment(
                StartDistAlong=f.createIfcLengthMeasure(start_dist),
                HorizontalLength=f.createIfcPositiveLengthMeasure(seg['length']),
                CurveGeometry=segment,
                PredefinedType='LINE' if seg['type'] == 'line' else 'CIRCULARARC'
            )
        )
        start_dist += seg['length']

    horizontal = f.createIfcAlignmentHorizontal(
        ifcopenshell.guid.new(), owner,
        CurveGeometry=f.createIfcCurveSegment(
            Placement=f.createIfcAxis2Placement2D(f.createIfcCartesianPoint([0.0, 0.0])),
            ParentCurve=None,
            SegmentType='POLYLINE',
            Segments=horizontal_curve_segments
        )
    )
    
    f.createIfcRelNests(ifcopenshell.guid.new(), owner, RelatingObject=alignment, RelatedObjects=[horizontal])
    
    # --- Write to file ---
    f.write(output_path)
    print(f"\nSuccessfully created new IFC file with IfcAlignment at:\n{output_path}")


def main():
    """Main execution function."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_ifc_path = os.path.join(script_dir, "..", "01_Source_IFCs", "Achse.IFC")
    output_ifc_path = os.path.join(script_dir, "..", "02_Generated_IFCs", "Achse_as_IfcAlignment.ifc")

    if not os.path.exists(source_ifc_path):
        print(f"Error: Source IFC file not found at {source_ifc_path}")
        return

    ifc_file = ifcopenshell.open(source_ifc_path)
    
    polyline_2d = None
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
                                if "2D-Linie" in parent_name:
                                    polyline_2d = polyline
                                    break
        if polyline_2d:
            break
            
    if not polyline_2d:
        print("Could not find the 2D axis polyline. Cannot proceed.")
        return

    points_2d = np.array([p.Coordinates for p in polyline_2d.Points])
    
    print("--- Starting Horizontal Geometry Analysis ---")
    horizontal_segments = analyze_horizontal_geometry(points_2d)
    print("--- Analysis Complete ---")

    if not horizontal_segments:
        print("No segments were detected. Aborting IFC file creation.")
        return

    create_ifc_alignment_file(output_ifc_path, horizontal_segments)


if __name__ == "__main__":
    main()
