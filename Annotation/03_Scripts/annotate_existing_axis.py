# Ten skrypt wczytuje plik IFC z definicją osi drogowej (IfcAlignment),
# a następnie generuje i umieszcza w modelu adnotacje z pikietażem
# w kluczowych punktach geometrii osi (początek, końce segmentów).
#
# Wersja 2.0 - Ukończona i Ulepszona
# ------------------------------------
# - Używa ścieżek względnych dla pełnej przenośności projektu.
# - Wprowadzono solidną obsługę błędów (np. brak osi w pliku).
# - Poprawiono logikę, aby poprawnie obsługiwać osie zaczynające się od łuku.
# - Zrefaktoryzowano kod do funkcji pomocniczych dla większej czytelności i łatwości rozbudowy.
import ifcopenshell
import ifcopenshell.api
import os
import math
import ifcopenshell.guid

# --- Konfiguracja ---
# Używamy ścieżek względnych, zakładając, że skrypt jest uruchamiany z głównego katalogu projektu.
INPUT_IFC_PATH = os.path.join("Road_Axis", "02_Generated_IFCs", "road_axis_with_arc.ifc")
OUTPUT_DIR = os.path.join("Annotation", "02_Generated_IFCs")
OUTPUT_FILENAME = "annotated_road_axis_final.ifc"
OUTPUT_IFC_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

# Upewnij się, że katalog wyjściowy istnieje
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Funkcje Pomocnicze ---

def get_single_element(ifc_file, ifc_class):
    # Bezpiecznie pobiera pojedynczy element danego typu z pliku IFC.
    # Zgłasza błąd, jeśli element nie istnieje.
    # Wyświetla ostrzeżenie, jeśli istnieje więcej niż jeden element.
    elements = ifc_file.by_type(ifc_class)
    if not elements:
        raise ValueError(f"BŁĄD: Nie znaleziono wymaganego elementu typu '{ifc_class}' w pliku.")
    if len(elements) > 1:
        print(f"OSTRZEŻENIE: Znaleziono {len(elements)} elementów typu '{ifc_class}'. Użyto pierwszego z nich.")
    return elements[0]

def get_model_context(project):
    # Znajduje i zwraca kontekst 'Model' potrzebny do geometrii.
    for context in project.RepresentationContexts:
        if context.ContextIdentifier == 'Model':
            return context
    raise ValueError("BŁĄD: Nie znaleziono wymaganego 'IfcGeometricRepresentationContext' ('Model').")

def get_segment_length(parent_curve):
    # Oblicza długość geometryczną dla różnych typów krzywych.
    if parent_curve.is_a("IfcPolyline"):
        length = 0.0
        points = parent_curve.Points
        for i in range(len(points) - 1):
            p1 = points[i].Coordinates
            p2 = points[i+1].Coordinates
            length += math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        return length
    elif parent_curve.is_a("IfcTrimmedCurve"):
        basis_curve = parent_curve.BasisCurve
        if basis_curve.is_a("IfcCircle"):
            # Długość łuku = promień * kąt w radianach
            radius = basis_curve.Radius
            angle1 = parent_curve.Trim1[0][0]
            angle2 = parent_curve.Trim2[0][0]
            return radius * abs(angle2 - angle1)
    # Dodaj obsługę innych typów krzywych (np. IfcLine, IfcClothoid) w przyszłości
    print(f"OSTRZEŻENIE: Pomijam obliczanie długości dla nieobsługiwanego typu krzywej: {parent_curve.is_a()}")
    return 0.0

def get_point_on_curve(curve, position="start"):
    # Ta funkcja pobiera współrzędne punktu 2D na początku lub na końcu krzywej.
    if curve.is_a("IfcPolyline"):
        point_2d = curve.Points[0] if position == "start" else curve.Points[-1]
        return point_2d.Coordinates
        
    elif curve.is_a("IfcTrimmedCurve"):
        basis_curve = curve.BasisCurve
        if basis_curve.is_a("IfcCircle"):
            center = basis_curve.Position.Location.Coordinates
            radius = basis_curve.Radius
            trim_param = curve.Trim1[0][0] if position == "start" else curve.Trim2[0][0]
            
            # Oblicz współrzędne punktu na okręgu
            x = center[0] + radius * math.cos(trim_param)
            y = center[1] + radius * math.sin(trim_param)
            return (x, y)
            
    raise TypeError(f"Nieobsługiwany typ krzywej '{curve.is_a()}' do znalezienia punktu.")


def create_station_annotation(f, context, owner_history, point_coords_3d, text):
    # Tworzy kompletną adnotację (IfcAnnotation) w zadanym punkcie 3D.
    point_3d = f.create_entity("IfcCartesianPoint", point_coords_3d)
    
    text_style_font_model = f.create_entity("IfcTextStyleFontModel", FontFamily=["Arial"], FontSize=f.create_entity("IfcPositiveLengthMeasure", 0.25))
    text_style = f.create_entity("IfcTextStyle", Name="Station Label Style", TextCharacterAppearance=text_style_font_model)
    
    text_placement = f.create_entity("IfcAxis2Placement2D", Location=f.create_entity("IfcCartesianPoint", (0.0, 0.0)))
    planar_extent = f.create_entity("IfcPlanarExtent", SizeInX=5.0, SizeInY=0.5)
    text_literal = f.create_entity("IfcTextLiteralWithExtent", Literal=text, Placement=text_placement, Extent=planar_extent, BoxAlignment="MIDDLE")
    
    styled_item = f.create_entity("IfcStyledItem", Item=text_literal, Styles=[text_style])
    
    annotation_representation = f.create_entity("IfcShapeRepresentation", ContextOfItems=context, RepresentationIdentifier="Annotation", RepresentationType="Annotation2D", Items=[text_literal])
    
    annotation_placement = f.create_entity("IfcLocalPlacement", RelativePlacement=f.create_entity("IfcAxis2Placement3D", Location=point_3d))
    
    annotation = f.create_entity("IfcAnnotation",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner_history,
        Name="Station Label",
        ObjectPlacement=annotation_placement,
        Representation=f.create_entity("IfcProductDefinitionShape", Representations=[annotation_representation])
    )
    return annotation

# --- Główny Skrypt ---
def main():
    print(f"Wczytywanie pliku IFC: {INPUT_IFC_PATH}")
    if not os.path.exists(INPUT_IFC_PATH):
        print(f"BŁĄD KRYTYCZNY: Plik wejściowy nie istnieje: {INPUT_IFC_PATH}")
        return
    f = ifcopenshell.open(INPUT_IFC_PATH)

    print("Krok 1: Weryfikacja i pobieranie kluczowych elementów z modelu...")
    try:
        owner_history = get_single_element(f, "IfcOwnerHistory")
        project = get_single_element(f, "IfcProject")
        site = get_single_element(f, "IfcSite")
        alignment = get_single_element(f, "IfcAlignment")
        context = get_model_context(project)
    except ValueError as e:
        print(f"BŁĄD KRYTYCZNY: {e}")
        return

    horizontal_alignment_curve = alignment.Representation.Representations[0].Items[0]
    if not horizontal_alignment_curve.is_a("IfcCompositeCurve"):
        raise TypeError("Oczekiwano, że geometria osi będzie typu IfcCompositeCurve.")
    print(f"Znaleziono oś do przetworzenia: {alignment.Name or 'Bez nazwy'}")

    print("\nKrok 2: Analiza segmentów osi i obliczanie pikietażu...")
    key_points = []
    current_station = 0.0

    # Pierwszy punkt osi (pikieta 0.0)
    first_segment_curve = horizontal_alignment_curve.Segments[0].ParentCurve
    start_point_coords = get_point_on_curve(first_segment_curve, "start")
    key_points.append({"coords": start_point_coords, "station": current_station})

    # Przetwarzanie kolejnych segmentów
    for segment in horizontal_alignment_curve.Segments:
        parent_curve = segment.ParentCurve
        
        segment_length = get_segment_length(parent_curve)
        current_station += segment_length
        
        end_point_coords = get_point_on_curve(parent_curve, "end")
        key_points.append({"coords": end_point_coords, "station": current_station})

    print("Zidentyfikowano punkty kluczowe i obliczono pikietaż:")
    for kp in key_points:
        print(f" - Pikieta: {kp['station']:.3f} m, Współrzędne: ({kp['coords'][0]:.2f}, {kp['coords'][1]:.2f})")

    print("\nKrok 3: Tworzenie adnotacji dla każdego punktu kluczowego...")
    all_new_annotations = []
    # Zmieniono pętlę, aby unikać duplikowania adnotacji na tych samych współrzędnych
    processed_coords = set()
    for kp in key_points:
        coord_tuple = (round(kp['coords'][0], 4), round(kp['coords'][1], 4))
        if coord_tuple in processed_coords:
            continue
        processed_coords.add(coord_tuple)

        station_text = f"km {int(kp['station'] // 1000)}+{kp['station'] % 1000:07.3f}"
        point_3d_coords = (kp['coords'][0], kp['coords'][1], 1.5)
        
        annotation = create_station_annotation(f, context, owner_history, point_3d_coords, station_text)
        all_new_annotations.append(annotation)
    print(f"Utworzono {len(all_new_annotations)} unikalnych adnotacji.")


    print("\nKrok 4: Dodawanie adnotacji do struktury przestrzennej i powiązanie z osią...")
    # Krok 4: Dodawanie adnotacji do struktury i powiązanie z osią
    if all_new_annotations:
        # Dodanie adnotacji do kontenera przestrzennego (IfcSite)
        f.create_entity("IfcRelContainedInSpatialStructure",
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=owner_history,
            Name="Contains Station Annotations",
            RelatedElements=all_new_annotations,
            RelatingStructure=site
        )

        # Powiązanie każdej adnotacji z osią za pomocą IfcRelAssociatesDocument.
        # To prosta i niezawodna metoda.
        for annotation in all_new_annotations:
            f.create_entity("IfcRelAssociatesDocument",
                GlobalId=ifcopenshell.guid.new(),
                OwnerHistory=owner_history,
                Name="Annotation Association",
                RelatedObjects=[alignment],
                RelatingDocument=annotation
            )
        print("Powiązano adnotacje z osią i dodano do struktury przestrzennej.")
    else:
        print("Nie utworzono żadnych adnotacji, pomijam ten krok.")


    print("\nKrok 5: Zapisywanie wyniku do nowego pliku IFC...")
    try:
        f.write(OUTPUT_IFC_PATH)
        print(f"\nSUKCES! Wygenerowano nowy, kompletny plik z adnotacjami:\n{os.path.abspath(OUTPUT_IFC_PATH)}")
    except Exception as e:
        print(f"BŁĄD KRYTYCZNY podczas zapisywania pliku: {e}")

if __name__ == "__main__":
    main()