import ifcopenshell
import ifcopenshell.util.element

def inspect_elements(ifc_path, search_keyword):
    """
    Przeszukuje plik IFC w poszukiwaniu elementów zawierających w nazwie
    dane słowo kluczowe i wypisuje ich wszystkie właściwości.

    Args:
        ifc_path (str): Ścieżka do pliku IFC.
        search_keyword (str): Słowo kluczowe do wyszukania w nazwie elementu (ignoruje wielkość liter).
    """
    try:
        ifc_file = ifcopenshell.open(ifc_path)
        print(f"Pomyślnie otwarto plik: {ifc_path}")
    except Exception as e:
        print(f"Błąd podczas otwierania pliku {ifc_path}: {e}")
        return

    products = ifc_file.by_type("IfcProduct")
    print(f"\nZnaleziono {len(products)} elementów IfcProduct. Przeszukiwanie w poszukiwaniu słowa kluczowego: '{search_keyword}'...")

    found_elements = 0
    for product in products:
        # Sprawdzamy nazwę elementu, jeśli istnieje
        if product.Name and search_keyword.lower() in product.Name.lower():
            found_elements += 1
            print(f"\n--- Element #{found_elements} ---")
            print(f"ID: {product.id()}")
            print(f"Typ: {product.is_a()}")
            print(f"GlobalId: {product.GlobalId}")
            print(f"Nazwa: {product.Name}")
            
            # Pobieranie i wypisywanie wszystkich Psetów
            psets = ifcopenshell.util.element.get_psets(product)
            if psets:
                print("  Zestawy właściwości (Psets):")
                for pset_name, properties in psets.items():
                    print(f"    - {pset_name}:")
                    for prop_name, prop_value in properties.items():
                        print(f"        - {prop_name}: {prop_value}")
            else:
                print("  Brak zestawów właściwości (Psetów).")
    
    if found_elements == 0:
        print(f"\nNie znaleziono żadnych elementów z nazwą zawierającą '{search_keyword}'.")
    else:
        print(f"\nPrzeszukiwanie zakończone. Znaleziono {found_elements} pasujących elementów.")

if __name__ == "__main__":
    source_ifc_path = "/Users/wojtek/Blender/IFCs/BM_Strasse.IFC"
    keyword = "Gelände" 
    inspect_elements(source_ifc_path, keyword)