import ifcopenshell

file_path = "/Users/wojtek/Blender/BM_Strasse_4x3_upgraded.ifc"

try:
    ifc_file = ifcopenshell.open(file_path)
    products = ifc_file.by_type("IfcProduct")
    
    elements_with_geometry = 0
    elements_without_geometry = 0

    for product in products:
        if product.Representation:
            elements_with_geometry += 1
        else:
            elements_without_geometry += 1
            # print(f"Element {product.Name} ({product.is_a()}) nie posiada reprezentacji geometrycznej.")

    print(f"W pliku {file_path} znaleziono:")
    print(f"  - Elementy z geometrią: {elements_with_geometry}")
    print(f"  - Elementy bez geometrii: {elements_without_geometry}")
    print(f"  - Łącznie elementów IfcProduct: {len(products)}")

except Exception as e:
    print(f"Wystąpił błąd podczas otwierania lub przetwarzania pliku {file_path}: {e}")
