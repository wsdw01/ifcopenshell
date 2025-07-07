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


def clone_element_to_target(source_element, target_file, target_container, owner_history, geometric_context):
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

        # If already copied, return the copied instance
        if source_entity in copied_entities:
            return copied_entities[source_entity]

        # Handle basic types (int, float, str, bool, tuple) directly
        if not (hasattr(source_entity, 'is_a') and callable(getattr(source_entity, 'is_a')) and source_entity.is_a()):
            return source_entity

        # Collect attributes and their copied values
        copied_attributes = {}
        for attribute_name, source_value in source_entity.get_info().items():
            if attribute_name == "GlobalId":
                copied_attributes[attribute_name] = ifcopenshell.guid.new()
            elif attribute_name == "id": # Skip the 'id' attribute
                continue
            elif source_value is None:
                copied_attributes[attribute_name] = None
            elif hasattr(source_value, 'is_a') and callable(getattr(source_value, 'is_a')) and source_value.is_a():
                # Recursively copy nested IfcEntity
                copied_attributes[attribute_name] = copy_ifc_entity(source_value, target_file, copied_entities)
            elif isinstance(source_value, tuple) and all(hasattr(item, 'is_a') and callable(getattr(item, 'is_a')) and item.is_a() for item in source_value):
                # Handle tuples of IfcEntities (e.g., FbsmFaces)
                copied_attributes[attribute_name] = tuple(copy_ifc_entity(item, target_file, copied_entities) for item in source_value)
            elif isinstance(source_value, list) and all(hasattr(item, 'is_a') and callable(getattr(item, 'is_a')) and item.is_a() for item in source_value):
                # Handle lists of IfcEntities (e.g., CfsFaces)
                copied_attributes[attribute_name] = [copy_ifc_entity(item, target_file, copied_entities) for item in source_value]
            else:
                # Copy basic types (including tuples/lists of basic types) directly
                copied_attributes[attribute_name] = source_value
        
        # Create a new entity in the target file with all copied attributes
        # Remove 'type' from copied_attributes as it's already passed as source_entity.is_a()
        copied_attributes.pop('type', None)
        new_entity = target_file.create_entity(source_entity.is_a())
        for attr_name, attr_value in copied_attributes.items():
            setattr(new_entity, attr_name, attr_value)
        print(f"DEBUG: Created new entity of type {new_entity.is_a()} with ID {new_entity.id()}")
        copied_entities[source_entity] = new_entity # Store immediately to handle circular references

        return new_entity

    # 1. Utworzenie nowego elementu w pliku docelowym
    new_element = target_file.create_entity(
        source_element.is_a(),
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner_history,
        Name=source_element.Name,
        Description=source_element.Description
    )

    copied_entities = {} # Initialize the dictionary once for this element

    # 2. Kopiowanie umiejscowienia (ObjectPlacement)
    if source_element.ObjectPlacement:
        new_element.ObjectPlacement = copy_ifc_entity(source_element.ObjectPlacement, target_file, copied_entities)

    # 3. Kopiowanie reprezentacji geometrycznej (Representation)
    if source_element.Representation:
            new_representations_list = []
            for rep in source_element.Representation.Representations:
                # Use copy_ifc_entity for each item in the representation
                new_items_for_representation = [copy_ifc_entity(item, target_file, copied_entities) for item in rep.Items]

                new_shape_representation = target_file.create_entity(
                    "IfcShapeRepresentation",
                    ContextOfItems=geometric_context,
                    RepresentationIdentifier=rep.RepresentationIdentifier,
                    RepresentationType=rep.RepresentationType,
                    Items=new_items_for_representation
                )
                new_representations_list.append(new_shape_representation)
            new_representation = target_file.create_entity(
                "IfcProductDefinitionShape",
                Representations=new_representations_list
            )
            new_element.Representation = new_representation

    # 4. Kopiowanie zestawów właściwości (PSet)
    for pset_name, pset_properties in ifcopenshell.util.element.get_psets(source_element).items():
        properties_to_add = []
        for prop_name, prop_value in pset_properties.items():
            # ifcopenshell.util.element.get_psets returns raw values, so we need to wrap them
            # in the appropriate IfcValue type. For simplicity, we'll assume IfcText for now.
            # In a real-world scenario, you'd need more robust type handling.
            if isinstance(prop_value, (int, float, str, bool)):
                if isinstance(prop_value, int):
                    nominal_value = target_file.create_entity("IfcInteger", prop_value)
                elif isinstance(prop_value, float):
                    nominal_value = target_file.create_entity("IfcReal", prop_value)
                elif isinstance(prop_value, bool):
                    nominal_value = target_file.create_entity("IfcBoolean", prop_value)
                else:
                    nominal_value = target_file.create_entity("IfcText", prop_value)

                new_prop = target_file.create_entity(
                    "IfcPropertySingleValue",
                    Name=prop_name,
                    NominalValue=nominal_value
                )
                properties_to_add.append(new_prop)
        
        new_pset = target_file.create_entity(
            "IfcPropertySet",
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=owner_history,
            Name=pset_name,
            HasProperties=properties_to_add
        )
        target_file.create_entity(
            "IfcRelDefinesByProperties",
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=owner_history,
            RelatingPropertyDefinition=new_pset,
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

    # --- Logika mapowania (zgodnie z plikiem .md) ---
    # Klucz: Wartość atrybutu PVI_STATIONSBEZUG
    # Wartość: Nazwa docelowego IfcRoadPart
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
    # Reguła specjalna
    terrain_rule_property = "PVI_BAUTEILTYP"
    terrain_rule_value = "Gelände"
    terrain_target_container_name = "Kantonstrasse | CARRIAGEWAY"


    # --- Implementacja ---
    print(f"Wczytywanie pliku źródłowego: {source_ifc_path}")
    source_ifc = ifcopenshell.open(source_ifc_path)

    print(f"Wczytywanie szkieletu docelowego: {target_skeleton_path}")
    target_ifc = ifcopenshell.open(target_skeleton_path)

    # Sprawdzenie i utworzenie IfcOwnerHistory, jeśli nie istnieje
    owner_history = target_ifc.by_type("IfcOwnerHistory")
    if not owner_history:
        print("Brak IfcOwnerHistory w pliku docelowym. Tworzę domyślny.")
        # Utwórz IfcPerson
        person = target_ifc.create_entity("IfcPerson", FamilyName="Unknown", GivenName="User")
        # Utwórz IfcOrganization
        organization = target_ifc.create_entity("IfcOrganization", Name="Unknown Organization")
        # Utwórz IfcApplication
        application = target_ifc.create_entity("IfcApplication",
            ApplicationDeveloper=organization,
            Version="1.0",
            ApplicationFullName="IFC Merger Script",
            ApplicationIdentifier="IFCMerger"
        )
        # Utwórz IfcPersonAndOrganization
        person_and_organization = target_ifc.create_entity("IfcPersonAndOrganization",
            ThePerson=person,
            TheOrganization=organization
        )
        # Utwórz IfcOwnerHistory
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
        # Utwórz IfcAxis2Placement3D dla WorldCoordinateSystem
        world_coords = target_ifc.create_entity("IfcAxis2Placement3D",
            target_ifc.create_entity("IfcCartesianPoint", (0.0, 0.0, 0.0)),
            target_ifc.create_entity("IfcDirection", (0.0, 0.0, 1.0)),
            target_ifc.create_entity("IfcDirection", (1.0, 0.0, 0.0))
        )
        # Utwórz IfcDirection dla TrueNorth
        true_north = target_ifc.create_entity("IfcDirection", (0.0, 1.0, 0.0))
        # Utwórz IfcGeometricRepresentationContext
        geometric_context = target_ifc.create_entity("IfcGeometricRepresentationContext",
            ContextType="Model",
            CoordinateSpaceDimension=3,
            Precision=1.0e-05,
            WorldCoordinateSystem=world_coords,
            TrueNorth=true_north
        )
    else:
        geometric_context = geometric_context[0]

    # Przygotowanie słownika do szybkiego wyszukiwania kontenerów w pliku docelowym
    target_containers = {
        part.Name: part for part in target_ifc.by_type("IfcRoadPart")
    }
    print(f"Znaleziono następujące kontenery w pliku docelowym: {list(target_containers.keys())}")

    # Pobranie wszystkich elementów geometrycznych z pliku źródłowego
    print("\n--- Rozpoczynam przetwarzanie pliku źródłowego ---")
    print("Krok 1: Pobieranie wszystkich elementów IfcProduct. To może zająć chwilę...")
    source_products = ifcopenshell.open(source_ifc_path).by_type("IfcProduct")
    print(f"Krok 1 zakończony. Znaleziono {len(source_products)} elementów w pliku źródłowym.")
    print("\n--- Rozpoczynam pętlę mapowania i klonowania ---")
    print("Krok 2: Iterowanie przez elementy, sprawdzanie reguł i klonowanie. To będzie główna część procesu.")


    cloned_count = 0
    cloned_counts_per_class = {}
    for i, product in enumerate(source_products):
        # Logowanie postępu co 1000 elementów
        if i > 0 and i % 1000 == 0:
            print(f"  ...przetworzono {i} z {len(source_products)} elementów...")

        # Ignorujemy elementy, które nie mają geometrii lub są częścią agregacji
        if not product.Representation:
            continue

        product_type = product.is_a()
        if product_type not in cloned_counts_per_class:
            cloned_counts_per_class[product_type] = 0

        if cloned_counts_per_class[product_type] >= 100:
            continue

        cloned_counts_per_class[product_type] += 1

        target_container_name = None

        # Sprawdzenie reguły dla terenu
        bauteiltyp = get_property_value(product, "ProVI", terrain_rule_property)
        if bauteiltyp == terrain_rule_value:
            target_container_name = terrain_target_container_name
        else:
            # Sprawdzenie głównych reguł mapowania
            stationsbezug = get_property_value(product, "ProVI", "PVI_STATIONSBEZUG")
            if stationsbezug in mapping_rules:
                target_container_name = mapping_rules[stationsbezug]

        # Jeśli znaleziono pasujący kontener, klonujemy element
        if target_container_name and target_container_name in target_containers:
            target_container = target_containers[target_container_name]
            print(f"Mapowanie elementu '{product.Name}' ({product.is_a()}) do '{target_container_name}'")
            clone_element_to_target(product, target_ifc, target_container, owner_history, geometric_context)
            cloned_count += 1
        else:
            print(f"Ostrzeżenie: Nie znaleziono reguły mapowania dla elementu '{product.Name}' ({product.is_a()}). Element zostanie pominięty.")


    total_cloned_elements = sum(cloned_counts_per_class.values())
    print(f"Proces zakończony. Sklonowano {total_cloned_elements} elementów (maks. 100 na klasę) z {len(source_products)} elementów źródłowych.")
    print(f"Zapisywanie zaktualizowanego pliku do: {output_ifc_path}")
    target_ifc.write(output_ifc_path)
    print("Gotowe!")


if __name__ == "__main__":
    main()