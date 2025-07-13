import ifcopenshell

try:
    # Użyj 'ifcopenshell.open' z argumentem 'schema' aby tylko załadować schemat
    schema = ifcopenshell.ifcopenshell_wrapper.schema_by_name("IFC4X3_ADD2")
    if not schema:
        raise ValueError("Nie udało się załadować schematu IFC4X3_ADD2")

    # Pobierz definicję encji
    entity = schema.declaration_by_name("IfcRelAssociates")
    if not entity:
        raise ValueError("Nie znaleziono encji 'IfcRelAssociates' w schemacie")

    print(f"Atrybuty dla encji 'IfcRelAssociates' w schemacie '{schema.name()}':")
    
    # Przejdź przez atrybuty w poprawnej kolejności
    for i in range(entity.attribute_count()):
        attr = entity.attribute_by_index(i)
        print(f" - {attr.name()}")

except Exception as e:
    print(f"Wystąpił błąd: {e}")
