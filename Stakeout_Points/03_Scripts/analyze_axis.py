import ifcopenshell
import numpy as np
import os

def analyze_ifc_axis(ifc_path):
    """
    Analyzes an IFC file to extract information about a road axis
    represented as IfcPolylines.

    :param ifc_path: Path to the IFC file.
    """
    try:
        ifc_file = ifcopenshell.open(ifc_path)
    except Exception as e:
        print(f"Error opening IFC file: {e}")
        return

    print(f"Analyzing axis from: {os.path.basename(ifc_path)}\n")

    polylines = ifc_file.by_type("IfcPolyline")
    if not polylines:
        print("No IfcPolyline entities found in the file.")
        return

    for polyline in polylines:
        # Find the proxy this polyline belongs to
        refs = ifc_file.get_inverse(polyline)
        proxy = None
        parent_name = "Unknown"

        # A bit of a complex inverse search to find the parent proxy and its context
        for ref in refs:
            if ref.is_a("IfcShapeRepresentation"):
                if hasattr(ref, 'OfProductRepresentation') and ref.OfProductRepresentation:
                    prod_def_shape = ref.OfProductRepresentation[0]
                    if hasattr(prod_def_shape, 'ShapeOfProduct') and prod_def_shape.ShapeOfProduct:
                        product = prod_def_shape.ShapeOfProduct[0]
                        if product.is_a("IfcBuildingElementProxy"):
                            proxy = product
                            if hasattr(proxy, 'ContainedInStructure') and proxy.ContainedInStructure:
                                parent_name = proxy.ContainedInStructure[0].RelatingStructure.Name
                            break
        
        if not proxy:
            continue

        is_3d = "Raumkurve" in parent_name
        header = f"--- Analysis of {'3D Axis (Raumkurve)' if is_3d else '2D Axis (2D-Linie)'} ---"
        print(header)

        # --- 1. Geometric Analysis ---
        points = np.array([p.Coordinates for p in polyline.Points])
        start_coord = points[0]
        end_coord = points[-1]

        print("  Geometric Data:")
        print(f"    Start Coords: ({', '.join(f'{c:.3f}' for c in start_coord)})")
        print(f"    End Coords:   ({', '.join(f'{c:.3f}' for c in end_coord)})")

        segment_vectors = np.diff(points, axis=0)
        segment_lengths = np.linalg.norm(segment_vectors, axis=1)
        total_length = np.sum(segment_lengths)
        print(f"    Calculated Length: {total_length:.3f} m")
        print(f"    Number of Vertices: {len(points)}")

        # --- 2. Properties Analysis ---
        print("\n  Properties (from Pset):")
        properties_found = False
        if hasattr(proxy, 'IsDefinedBy') and proxy.IsDefinedBy:
            for rel in proxy.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a("IfcPropertySet") and 'ProVI' in prop_set.Name:
                        properties_found = True
                        for prop in prop_set.HasProperties:
                            if prop.is_a("IfcPropertySingleValue"):
                                prop_name = prop.Name
                                prop_value = prop.NominalValue.wrappedValue if prop.NominalValue else 'N/A'
                                unit = f" {prop.Unit.Name}" if hasattr(prop, 'Unit') and prop.Unit and hasattr(prop.Unit, 'Name') else ""
                                print(f"    - {prop_name}: {prop_value}{unit}")
        
        if not properties_found:
            print("    No 'ProVI' property sets found for this axis.")
        
        print("-" * len(header) + "\n")

if __name__ == "__main__":
    # Use an absolute path to be safe
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_ifc = os.path.join(script_dir, "..", "01_Source_IFCs", "Achse.IFC")
    if os.path.exists(source_ifc):
        analyze_ifc_axis(source_ifc)
    else:
        print(f"Error: Could not find the IFC file at {source_ifc}")