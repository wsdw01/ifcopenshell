import ifcopenshell
import ifcopenshell.api
import ifcopenshell.template
import numpy as np
import os

# --- Ustawienia --- #
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
GENERATED_IFC_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "02_Generated_IFCs"))
OUTPUT_FILENAME = "road_axis_example.ifc"
OUTPUT_FILE_PATH = os.path.join(GENERATED_IFC_DIR, OUTPUT_FILENAME)

# Upewnij się, że katalog docelowy istnieje
if not os.path.exists(GENERATED_IFC_DIR):
    os.makedirs(GENERATED_IFC_DIR)

# 1. Inicjalizacja pliku IFC4x3
f = ifcopenshell.template.create(schema_identifier="IFC4X3_ADD2")
owner_history = f.by_type("IfcOwnerHistory")[0]
project = f.by_type("IfcProject")[0]
context = f.by_type("IfcGeometricRepresentationContext")[0]

# Helper do tworzenia IfcCartesianPoint w kontekście 2D dla osi
def create_point_2d(point_tuple):
    return f.create_entity("IfcCartesianPoint", Coordinates=point_tuple)

# --- 2. Definicja Trasy Poziomej (Horizontal Alignment) ---

# Punkty definiujące geometrię 2D
p1 = create_point_2d((0.0, 0.0))
p2 = create_point_2d((100.0, 0.0))
center_arc = create_point_2d((100.0, -50.0)) # Środek łuku
p4 = create_point_2d((150.0, -50.0))

# Segment 1: Odcinek prosty
line_segment = f.create_entity("IfcPolyline", Points=[p1, p2])

# Segment 2: Łuk kołowy (90 stopni w prawo)
circle = f.create_entity("IfcCircle", Position=center_arc, Radius=50.0)
arc_segment = f.create_entity("IfcTrimmedCurve",
    BasisCurve=circle,
    Trim1=[p2],
    Trim2=[p4],
    SenseAgreement=True
)

# Łączenie segmentów w jedną krzywą złożoną
composite_curve_segment1 = f.create_entity("IfcCompositeCurveSegment", Transition="CONTINUOUS", SameSense=True, ParentCurve=line_segment)
composite_curve_segment2 = f.create_entity("IfcCompositeCurveSegment", Transition="CONTINUOUS", SameSense=True, ParentCurve=arc_segment)

horizontal_alignment_curve = f.create_entity("IfcCompositeCurve", Segments=[composite_curve_segment1, composite_curve_segment2], SelfIntersect=False)

# --- 3. Definicja Profilu Pionowego (Vertical Alignment) ---

# Długość łuku = 2 * pi * R * (kąt / 360) = 78.54m
arc_horizontal_length = 0.5 * np.pi * 50.0

# Krok 1: Stwórz wszystkie segmenty niezależnie
# Segment 1: Wzniesienie 2% na odcinku prostym
vertical_segment1 = f.create_entity("IfcAlignmentVerticalSegment",
    StartDistAlong=0.0,
    HorizontalLength=100.0,
    StartHeight=10.0,
    StartGradient=0.02,
    EndGradient=0.02,
    RadiusOfCurvature=0.0
)

# Obliczenie wysokości na końcu pierwszego segmentu
end_height_segment1 = 10.0 + 100.0 * 0.02

# Segment 2: Spadek -1% na łuku
vertical_segment2 = f.create_entity("IfcAlignmentVerticalSegment",
    StartDistAlong=100.0,
    HorizontalLength=round(arc_horizontal_length, 5),
    StartHeight=end_height_segment1,
    StartGradient=-0.01,
    EndGradient=-0.01,
    RadiusOfCurvature=0.0
)

# Krok 2: Stwórz kontener na profil pionowy
vertical_alignment = f.create_entity("IfcAlignmentVertical")

# Krok 3: Zagnieźdź segmenty w profilu za pomocą IfcRelNests
f.create_entity("IfcRelNests",
    RelatingObject=vertical_alignment,
    RelatedObjects=[vertical_segment1, vertical_segment2]
)

# --- 4. Tworzenie Głównej Encji IfcAlignment i jej komponentów ---

# Krok 4a: Stwórz kontener na trasę poziomą (IfcAlignmentHorizontal)
# Geometria (horizontal_alignment_curve) jest przypisywana jako reprezentacja
horizontal_alignment = f.create_entity("IfcAlignmentHorizontal")
product_shape = f.create_entity("IfcProductDefinitionShape",
    Representations=[
        f.create_entity("IfcShapeRepresentation",
            ContextOfItems=context,
            RepresentationIdentifier='Axis',
            RepresentationType='Curve2D',
            Items=[horizontal_alignment_curve]
        )
    ]
)
horizontal_alignment.Representation = product_shape

# Krok 4b: Stwórz główny kontener IfcAlignment
alignment = f.create_entity("IfcAlignment",
    OwnerHistory=owner_history,
    Name="Oś Drogi Głównej",
    Description="Przykład osi drogowej z odcinkiem prostym i łukiem"
)

# Krok 4c: Zagnieźdź komponenty (poziomy i pionowy) w głównym kontenerze
f.create_entity("IfcRelNests",
    RelatingObject=alignment,
    RelatedObjects=[horizontal_alignment, vertical_alignment]
)


# --- 5. Generate 3D Representation for Visualization ---

# Krok 5a: Przygotuj dane wejściowe
# Poprawny sposób na dostęp do zagnieżdżonych segmentów przez relację odwrotną
vertical_segments = sorted(vertical_alignment.HasSegments, key=lambda s: s.StartDistAlong)

points_3d = []

# Krok 5b: Ręczne próbkowanie geometrii 2D i obliczanie Z

# Próbkowanie segmentu 1: IfcPolyline
line_start_point = horizontal_alignment_curve.Segments[0].ParentCurve.Points[0]
line_end_point = horizontal_alignment_curve.Segments[0].ParentCurve.Points[1]
line_length = np.linalg.norm(np.array(line_end_point.Coordinates) - np.array(line_start_point.Coordinates))
num_samples_line = int(line_length / 1.0) # Próbkowanie co ~1m

for i in range(num_samples_line + 1):
    alpha = i / num_samples_line
    # Interpolacja punktu 2D
    x = (1 - alpha) * line_start_point.Coordinates[0] + alpha * line_end_point.Coordinates[0]
    y = (1 - alpha) * line_start_point.Coordinates[1] + alpha * line_end_point.Coordinates[1]
    
    # Obliczanie wysokości Z
    current_distance = line_length * alpha
    dist_in_segment = current_distance - vertical_segments[0].StartDistAlong
    height_z = vertical_segments[0].StartHeight + dist_in_segment * vertical_segments[0].StartGradient
    
    points_3d.append(f.create_entity("IfcCartesianPoint", Coordinates=(x, y, height_z)))

# Próbkowanie segmentu 2: IfcTrimmedCurve (Łuk)
arc_curve = horizontal_alignment_curve.Segments[1].ParentCurve
circle_center = np.array(arc_curve.BasisCurve.Position.Coordinates)
radius = arc_curve.BasisCurve.Radius
# Kąty są w radianach. Start: 90° (pi/2), Koniec: 0°
start_angle = np.pi / 2
end_angle = 0
arc_length = radius * abs(start_angle - end_angle)
num_samples_arc = int(arc_length / 1.0)

for i in range(1, num_samples_arc + 1): # Zaczynamy od 1, bo punkt 0 już jest
    alpha = i / num_samples_arc
    current_angle = start_angle + alpha * (end_angle - start_angle)
    # Obliczanie punktu 2D na łuku
    x = circle_center[0] + radius * np.cos(current_angle)
    y = circle_center[1] + radius * np.sin(current_angle)

    # Obliczanie wysokości Z
    current_distance = line_length + arc_length * alpha
    dist_in_segment = current_distance - vertical_segments[1].StartDistAlong
    height_z = vertical_segments[1].StartHeight + dist_in_segment * vertical_segments[1].StartGradient

    points_3d.append(f.create_entity("IfcCartesianPoint", Coordinates=(x, y, height_z)))


# Krok 5c: Stwórz krzywą 3D (jako IfcPolyline)
polyline_3d = f.create_entity("IfcPolyline", Points=points_3d)

# Krok 5d: Stwórz i przypisz reprezentację 'Body' do głównego IfcAlignment
body_representation = f.create_entity("IfcShapeRepresentation",
    ContextOfItems=context,
    RepresentationIdentifier='Body',
    RepresentationType='Curve3D',
    Items=[polyline_3d]
)

# Jeśli IfcAlignment nie ma jeszcze definicji kształtu, stwórz ją
if not alignment.Representation:
    alignment.Representation = f.create_entity("IfcProductDefinitionShape")

# Dodaj nową reprezentację 'Body'
alignment.Representation.Representations.append(body_representation)


# --- 6. Umieszczenie w strukturze przestrzennej (jako część drogi) ---

# Tworzymy IfcRoad jako kontener dla naszej osi
road = f.create_entity("IfcRoad", Name="Droga Krajowa S1")

# Agregacja - droga składa się z osi
f.create_entity("IfcRelAggregates",
    RelatingObject=road,
    RelatedObjects=[alignment]
)

# Umieszczamy drogę w projekcie
# Sprawdzamy czy IfcSite istnieje, jeśli nie, tworzymy go
ifc_project = f.by_type("IfcProject")[0]
ifc_site_list = f.by_type("IfcSite")
if not ifc_site_list:
    ifc_site = f.create_entity("IfcSite", OwnerHistory=owner_history, Name="Default Site")
    f.create_entity("IfcRelAggregates", RelatingObject=ifc_project, RelatedObjects=[ifc_site])
else:
    ifc_site = ifc_site_list[0]

f.create_entity("IfcRelContainedInSpatialStructure",
    RelatingStructure=ifc_site,
    RelatedElements=[road]
)

# --- 7. Zapis pliku ---
f.write(OUTPUT_FILE_PATH)
print(f"Plik {OUTPUT_FILENAME} został pomyślnie zaktualizowany o geometrię 3D.")