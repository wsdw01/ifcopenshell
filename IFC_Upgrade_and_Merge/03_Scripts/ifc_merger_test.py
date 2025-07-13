import ifcopenshell
import ifcopenshell.api
import ifcopenshell.util.element
import uuid
import datetime
import ifcopenshell.util.date

def get_property_value(element, pset_name, prop_name):
    """
    Pobiera wartość konkretnej właściwości z danego zestawu właściwości (PSet) elementu.

    Args:
        element: Element IfcProduct.
        pset_name (str): Nazwa zestawu właściwości (np. "ProVI").
        prop_name (str): Nazwa właściwości (np. "PVI_STATIONSBEZUG").

    Returns:
        Wartość właściwości lub None, jeśli nie zostanie znaleziona.
    """
    psets = ifcopenshell.util.element.get_psets(element)
    if pset_name in psets:
        if prop_name in psets[pset_name]:
            return psets[pset_name][prop_name]
    return None


def clone_element_to_target(source_element, target_file, target_container, owner_history, geometric_context, target_type=None):
    """
    Klonuje element (geometrię i właściwości) z pliku źródłowego do docelowego.
    Tworzy nowy element typu IfcBuildingElementProxy w pliku docelowym,
    kopiuje reprezentację geometryczną i wszystkie Psety.

    Args:
        source_element: Element do sklonowania z pliku źródłowego.
        target_file: Otwarty plik IFC (model docelowy), do którego dodajemy element.
        target_container: Encja w pliku docelowym, do której zostanie przypisany nowy element
                          (np. IfcRoadPart).
        owner_history: Obiekt IfcOwnerHistory do przypisania nowym elementom.
        geometric_context: Obiekt IfcGeometricRepresentationContext do przypisania nowym reprezentacjom.

    Returns:
        Nowo utworzony element w pliku docelowym.
    """
    # Helper function to recursively copy an IFC entity and its attributes
    def copy_ifc_entity(source_entity, target_file, copied_entities):
        if source_entity is None:
            return None
        if source_entity in copied_entities:
            return copied_entities[source_entity]
        if not (hasattr(source_entity, 'is_a') and callable(getattr(source_entity, 'is_a')) and source_entity.is_a()):
            return source_entity

        # Create a placeholder entity to handle circular references in the model
        new_entity = target_file.create_entity(source_entity.is_a())
        copied_entities[source_entity] = new_entity

        # Iterate over attributes by index to ensure correct order and avoid inverse attributes
        for i in range(len(source_entity)):
            attribute = source_entity[i]
            
            # Skip attributes that are handled by the main function or should not be copied directly
            attr_name = source_entity.attribute_name(i)
            if attr_name in ('GlobalId', 'OwnerHistory'):
                continue

            # Recursively copy nested entities or lists of entities
            if isinstance(attribute, ifcopenshell.entity_instance):
                attribute = copy_ifc_entity(attribute, target_file, copied_entities)
            elif isinstance(attribute, (list, tuple)):
                new_list = []
                for item in attribute:
                    if isinstance(item, ifcopenshell.entity_instance):
                        new_list.append(copy_ifc_entity(item, target_file, copied_entities))
                    elif isinstance(item, (list, tuple)):
                        # Handle nested lists of values, e.g. ((1,2,3), (4,5,6)) in IfcTriangulatedFaceSet
                        new_list.append(type(item)(list(sub_item for sub_item in item)))
                    else:
                        new_list.append(item)
                attribute = type(attribute)(new_list)
            
            try:
                # Set the attribute on the new entity by index
                new_entity[i] = attribute
            except Exception:
                # This may fail for derived or read-only attributes, which is expected.
                # We can safely ignore these errors.
                pass

        return new_entity

    # 1. Utworzenie nowego elementu w pliku docelowym
    # Używamy typu docelowego, jeśli został podany, w przeciwnym razie używamy typu źródłowego.
    element_type_to_create = target_type if target_type else source_element.is_a()
    new_element = target_file.create_entity(
        element_type_to_create,
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner_history,
        Name=source_element.Name,
        Description=source_element.Description,
        ObjectType=source_element.ObjectType
    )

    # Słownik do śledzenia już skopiowanych encji, aby uniknąć duplikatów i obsłużyć cykliczne zależności.
    # Klucz: encja w pliku źródłowym, Wartość: encja w pliku docelowym.
    copied_entities = {source_element: new_element}

    # 2. Kopiowanie umiejscowienia (ObjectPlacement)
    if source_element.ObjectPlacement:
        new_element.ObjectPlacement = copy_ifc_entity(source_element.ObjectPlacement, target_file, copied_entities)

    # 3. Kopiowanie reprezentacji geometrycznej (Representation)
    if source_element.Representation:
        new_element.Representation = copy_ifc_entity(source_element.Representation, target_file, copied_entities)

    # 4. Kopiowanie zestawów właściwości (PSet)
    # Iterujemy przez relacje właściwości zdefiniowane dla elementu źródłowego.
    # To jest bardziej niezawodne niż get_psets, ponieważ kopiuje całe encje,
    # zachowując wszystkie typy danych i struktury.
    if source_element.IsDefinedBy:
        for rel in source_element.IsDefinedBy:
            # Kopiujemy tylko relacje typu IfcRelDefinesByProperties
            if rel.is_a("IfcRelDefinesByProperties"):
                # Głębokie kopiowanie definicji właściwości (np. IfcPropertySet)
                new_property_definition = copy_ifc_entity(rel.RelatingPropertyDefinition, target_file, copied_entities)
                
                # Utworzenie nowej relacji w pliku docelowym, łączącej nową definicję właściwości z nowym elementem
                target_file.create_entity(
                    "IfcRelDefinesByProperties",
                    GlobalId=ifcopenshell.guid.new(),
                    OwnerHistory=owner_history,
                    RelatingPropertyDefinition=new_property_definition,
                    RelatedObjects=[new_element]
                )

    # 5. Przypisanie nowego elementu do kontenera (np. IfcRoadPart) w strukturze przestrzennej
    ifcopenshell.api.run("aggregate.assign_object", target_file, products=[new_element], relating_object=target_container)

    return new_element

def main():
    """
    Główna funkcja skryptu.
    """
    # --- Konfiguracja ---
    source_ifc_path = "/Users/wojtek/Blender/IFCs/BM_Strasse.IFC"
    target_skeleton_path = "/Users/wojtek/Blender/OD_Matten_4x3.ifc"
    output_ifc_path = "/Users/wojtek/Blender/BM_Strasse_4x3_upgraded.ifc"

    # --- Logika mapowania ---
    mapping_rules = {
        "Achse 006B (B_Achse_Parkstrasse)": "Parkstrasse | CARRIAGEWAY",
        "Achse 001B (B_Achse_Hauptachse)": "Kantonstrasse | CARRIAGEWAY",
        "Achse 018B (B_Insel_1_aussen)": "Kantonstrasse | CARRIAGEWAY",
        "Achse 019B (B_Insel_2_aussen)": "Kantonstrasse | CARRIAGEWAY",
        "Achse 020B (B_Achse_Metzgerstrasse)": "Metzgergasse | CARRIAGEWAY",
        "Achse 029B (B_Achse_Tellweg)": "Tellweg | ROADSEGMENT",
        "Achse 038B (B_Insel_3_aussen)": "Kantonstrasse | CARRIAGEWAY",
        "Achse 040B (B_Achse_Rugenstrasse)": "Rugenstrasse | CARRIAGEWAY",
        "Achse 039B (B_Insel_4_aussen)": "Rugenstrasse | CARRIAGEWAY",
    }
    terrain_target_container_name = "Kantonstrasse | CARRIAGEWAY"

    # --- Implementacja ---
    source_ifc = ifcopenshell.open(source_ifc_path)
    target_ifc = ifcopenshell.open(target_skeleton_path)

    # Przygotowanie słownika do szybkiego wyszukiwania kontenerów w pliku docelowym
    target_containers = {
        part.Name: part for part in target_ifc.by_type("IfcRoadPart")
    }
    if not target_containers:
        print("Krytyczny błąd: Nie znaleziono żadnych elementów IfcRoadPart w pliku docelowym. Nie można kontynuować.")
        return
    print(f"Znaleziono następujące kontenery w pliku docelowym: {list(target_containers.keys())}")

    # Sprawdzenie i utworzenie IfcOwnerHistory, jeśli nie istnieje
    owner_history = target_ifc.by_type("IfcOwnerHistory")
    if not owner_history:
        print("Brak IfcOwnerHistory w pliku docelowym. Tworzę domyślny.")
        person = target_ifc.create_entity("IfcPerson", FamilyName="Unknown", GivenName="User")
        organization = target_ifc.create_entity("IfcOrganization", Name="Unknown Organization")
        application = target_ifc.create_entity("IfcApplication",
            ApplicationDeveloper=organization,
            Version="1.0",
            ApplicationFullName="IFC Merger Script",
            ApplicationIdentifier="IFCMerger"
        )
        person_and_organization = target_ifc.create_entity("IfcPersonAndOrganization",
            ThePerson=person,
            TheOrganization=organization
        )
        owner_history = target_ifc.create_entity("IfcOwnerHistory",
            OwningUser=person_and_organization,
            OwningApplication=application,
            ChangeAction="ADDED",
            CreationDate=int(datetime.datetime.now().timestamp())
        )
    else:
        owner_history = owner_history[0]

    # Sprawdzenie i utworzenie IfcGeometricRepresentationContext, jeśli nie istnieje
    geometric_context = target_ifc.by_type("IfcGeometricRepresentationContext")
    if not geometric_context:
        print("Brak IfcGeometricRepresentationContext w pliku docelowym. Tworzę domyślny.")
        world_coords = target_ifc.create_entity("IfcAxis2Placement3D",
            target_ifc.create_entity("IfcCartesianPoint", (0.0, 0.0, 0.0)),
            target_ifc.create_entity("IfcDirection", (0.0, 0.0, 1.0)),
            target_ifc.create_entity("IfcDirection", (1.0, 0.0, 0.0))
        )
        true_north = target_ifc.create_entity("IfcDirection", (0.0, 1.0, 0.0))
        geometric_context = target_ifc.create_entity("IfcGeometricRepresentationContext",
            ContextType="Model",
            CoordinateSpaceDimension=3,
            Precision=1.0e-05,
            WorldCoordinateSystem=world_coords,
            TrueNorth=true_north
        )
    else:
        geometric_context = geometric_context[0]

    # --- Logika dla terenu ---
    print("\n--- Przetwarzanie terenu ---")
    cloned_terrain_elements = set()
    terrain_storey = None
    for storey in source_ifc.by_type("IfcBuildingStorey"):
        if storey.Name == "Gelände":
            terrain_storey = storey
            print(f"Znaleziono kontener terenu (IfcBuildingStorey): '{terrain_storey.Name}'")
            break

    if terrain_storey:
        terrain_target_container = target_containers.get(terrain_target_container_name)
        if terrain_target_container:
            print(f"Elementy terenu będą klonowane do: '{terrain_target_container.Name}'")
            if hasattr(terrain_storey, 'ContainsElements') and terrain_storey.ContainsElements:
                for rel in terrain_storey.ContainsElements:
                    for element in rel.RelatedElements:
                        if element.is_a("IfcProduct") and element.Representation:
                            print(f"Mapowanie elementu terenu '{element.Name}' ({element.is_a()}) do '{terrain_target_container_name}' jako IfcGeographicElement")
                            clone_element_to_target(element, target_ifc, terrain_target_container, owner_history, geometric_context, target_type="IfcGeographicElement")
                            cloned_terrain_elements.add(element.id())
            else:
                print("Ostrzeżenie: Kontener terenu nie zawiera żadnych elementów (atrybut ContainsElements jest pusty).")
        else:
            print(f"Ostrzeżenie: Nie znaleziono docelowego kontenera dla terenu '{terrain_target_container_name}' w pliku docelowym.")
    else:
        print("Ostrzeżenie: Nie znaleziono kontenera terenu (IfcBuildingStorey o nazwie 'Gelände') w pliku źródłowym.")

    # --- Główna pętla przetwarzania ---
    print("\n--- Rozpoczynam pętlę mapowania i klonowania pozostałych elementów ---")
    source_products = source_ifc.by_type("IfcProduct")
    print(f"Znaleziono {len(source_products)} elementów w pliku źródłowym. Rozpoczynam pętlę...")

    cloned_count = 0
    cloned_counts_per_class = {}
    for i, product in enumerate(source_products):
        if i > 0 and i % 1000 == 0:
            print(f"  ...przetworzono {i} z {len(source_products)} elementów...")

        if not product.Representation or product.id() in cloned_terrain_elements:
            continue

        product_type = product.is_a()
        if product_type not in cloned_counts_per_class:
            cloned_counts_per_class[product_type] = 0

        if cloned_counts_per_class[product_type] >= 100:
            continue

        cloned_counts_per_class[product_type] += 1

        target_container_name_main = None
        stationsbezug = get_property_value(product, "ProVI", "PVI_STATIONSBEZUG")
        if stationsbezug in mapping_rules:
            target_container_name_main = mapping_rules[stationsbezug]

        if target_container_name_main and target_container_name_main in target_containers:
            target_container = target_containers[target_container_name_main]
            print(f"Mapowanie elementu '{product.Name}' ({product.is_a()}) do '{target_container_name_main}'")
            clone_element_to_target(product, target_ifc, target_container, owner_history, geometric_context)
            cloned_count += 1

    total_cloned_elements = len(cloned_terrain_elements) + sum(cloned_counts_per_class.values())
    print(f"\nProces zakończony. Sklonowano łącznie {total_cloned_elements} elementów.")
    print(f"Zapisywanie zaktualizowanego pliku do: {output_ifc_path}")
    target_ifc.write(output_ifc_path)
    print("Gotowe!")

if __name__ == "__main__":
    main()
