import ifcopenshell

def print_all_attributes(entity, indent=""):
    """Rekursywnie drukuje wszystkie atrybuty, włączając te z klas nadrzędnych."""
    if not entity:
        return
        
    # Drukuj atrybuty z klasy nadrzędnej (jeśli istnieje)
    # Używamy 'supertype()' aby przejść w górę drzewa dziedziczenia
    if hasattr(entity, 'supertype') and entity.supertype():
        print_all_attributes(entity.supertype(), indent)

    # Drukuj atrybuty z bieżącej klasy
    print(f"{indent}Atrybuty z {entity.name()}:")
    for i in range(entity.attribute_count()):
        attr = entity.attribute_by_index(i)
        # Sprawdzamy czy atrybut jest zadeklarowany w tej klasie, czy odziedziczony
        # To pomaga uniknąć duplikatów
        if attr.declaring_entity().name() == entity.name():
            print(f"{indent} - {attr.name()}")


try:
    schema = ifcopenshell.ifcopenshell_wrapper.schema_by_name("IFC4X3_ADD2")
    if not schema:
        raise ValueError("Nie udało się załadować schematu IFC4X3_ADD2")

    entity_name = "IfcRelAssociates"
    entity = schema.declaration_by_name(entity_name)
    if not entity:
        raise ValueError(f"Nie znaleziono encji '{entity_name}' w schemacie")

    print(f"Pełna lista atrybutów (wraz z dziedziczonymi) dla '{entity_name}':")
    print_all_attributes(entity)

except Exception as e:
    print(f"Wystąpił błąd: {e}")
