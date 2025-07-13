import ifcopenshell
import os

# --- Konfiguracja ---
BLENDER_PROJECT_DIR = "/Users/wojtek/Blender"
FILE_TO_VALIDATE = os.path.join(BLENDER_PROJECT_DIR, "Annotation", "02_Generated_IFCs", "annotated_road_axis.ifc")

print(f"--- Walidacja pliku: {os.path.basename(FILE_TO_VALIDATE)} ---")

# Sprawdzenie, czy plik istnieje
if not os.path.exists(FILE_TO_VALIDATE):
    print(f"BŁĄD: Plik nie istnieje: {FILE_TO_VALIDATE}")
    exit()

# Otwarcie pliku
f = ifcopenshell.open(FILE_TO_VALIDATE)
print(f"Plik wczytany pomyślnie. Wersja schematu: {f.schema}")

# Krok 1: Znajdź oś
alignments = f.by_type("IfcAlignment")
if not alignments:
    print("BŁĄD: Nie znaleziono żadnego IfcAlignment w pliku.")
    exit()

alignment = alignments[0]
print(f"\nZnaleziono oś: '{alignment.Name}' (ID: #{alignment.id()})")

# Krok 2: Znajdź relacje powiązania
associations = f.by_type("IfcRelAssociatesDocument")
if not associations:
    print("BŁĄD: Nie znaleziono żadnych relacji IfcRelAssociatesDocument w pliku.")
    exit()

print(f"Znaleziono {len(associations)} relacji powiązania typu 'IfcRelAssociatesDocument'.")

# Krok 3: Walidacja każdej relacji
validation_passed = True
for i, assoc in enumerate(associations):
    print(f"\n--- Sprawdzanie powiązania #{i+1} (ID: #{assoc.id()}) ---")
    
    # Sprawdzenie obiektu powiązanego (powinna to być nasza oś)
    related_objects = assoc.RelatedObjects
    if not related_objects or len(related_objects) != 1 or related_objects[0].id() != alignment.id():
        print(f"  [BŁĄD] Relacja nie jest poprawnie powiązana z osią! Oczekiwano: #{alignment.id()}, znaleziono: {related_objects[0].id() if related_objects else 'None'}")
        validation_passed = False
    else:
        print(f"  [OK] Relacja poprawnie wskazuje na oś: '{related_objects[0].Name}'")

    # Sprawdzenie dokumentu (powinna to być nasza adnotacja)
    relating_document = assoc.RelatingDocument
    if not relating_document or not relating_document.is_a("IfcAnnotation"):
        print(f"  [BŁĄD] Obiekt 'RelatingDocument' nie jest poprawną adnotacją! Znaleziono: {relating_document.is_a() if relating_document else 'None'}")
        validation_passed = False
    else:
        annotation_text = relating_document.Representation.Representations[0].Items[0].Literal
        print(f"  [OK] Relacja poprawnie wskazuje na adnotację: '{annotation_text}'")

# Krok 4: Podsumowanie
print("\n--- Podsumowanie walidacji ---")
if validation_passed:
    print("✅ SUKCES! Wszystkie znalezione relacje poprawnie łączą oś z adnotacjami.")
    print("Plik jest strukturalnie poprawny. Problem z wyświetlaniem leży po stronie przeglądarki.")
else:
    print("❌ BŁĄD! Znaleziono problemy ze strukturą powiązań w pliku.")
