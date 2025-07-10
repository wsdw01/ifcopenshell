import ifcopenshell

def verify_element_type(ifc_path, element_name):
    """
    Otwiera plik IFC i sprawdza faktyczny typ elementu o podanej nazwie.

    Args:
        ifc_path (str): Ścieżka do pliku IFC do sprawdzenia.
        element_name (str): Nazwa elementu do znalezienia.
    """
    try:
        ifc_file = ifcopenshell.open(ifc_path)
        print(f"Pomyślnie otwarto plik: {ifc_path}")
    except Exception as e:
        print(f"Błąd podczas otwierania pliku {ifc_path}: {e}")
        return

    elements = ifc_file.by_type("IfcProduct")
    found = False
    for element in elements:
        if element.Name == element_name:
            found = True
            print(f"\nZnaleziono element o nazwie: '{element_name}'")
            print(f"  - Jego FAKTYCZNY typ w pliku to: {element.is_a()}")
            break
    
    if not found:
        print(f"\nNie znaleziono elementu o nazwie '{element_name}' w pliku.")

if __name__ == "__main__":
    output_ifc_path = "/Users/wojtek/Blender/BM_Strasse_4x3_upgraded.ifc"
    terrain_element_name = "B_Terrain_ausgeschnitten.GEL"
    
    print(f"--- Weryfikacja pliku: {output_ifc_path} ---")
    verify_element_type(output_ifc_path, terrain_element_name)