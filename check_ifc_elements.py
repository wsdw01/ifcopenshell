import ifcopenshell

file_path = "/Users/wojtek/Blender/BM_Strasse_4x3_upgraded.ifc"

try:
    ifc_file = ifcopenshell.open(file_path)
    products = ifc_file.by_type("IfcProduct")
    print(f"Liczba elementów IfcProduct w pliku {file_path}: {len(products)}")
except Exception as e:
    print(f"Wystąpił błąd podczas otwierania lub przetwarzania pliku {file_path}: {e}")
