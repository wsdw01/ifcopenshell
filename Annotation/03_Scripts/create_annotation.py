import ifcopenshell
import ifcopenshell.api
import uuid
import time
import os

# --- Konfiguracja ---
OUTPUT_DIR = "02_Generated_IFCs"
OUTPUT_FILENAME = "annotation_example.ifc"
# Ścieżka jest teraz budowana względem lokalizacji skryptu w Annotation/03_Scripts/
FULL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "Annotation", OUTPUT_DIR, OUTPUT_FILENAME)

# Upewnij się, że katalog wyjściowy istnieje
os.makedirs(os.path.join(os.path.dirname(__file__), "..", "..", "Annotation", OUTPUT_DIR), exist_ok=True)

import ifcopenshell
import ifcopenshell.api
import time
import os
import ifcopenshell.guid

# --- Konfiguracja ---
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "02_Generated_IFCs")
OUTPUT_FILENAME = "annotation_example.ifc"
FULL_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

# Upewnij się, że katalog wyjściowy istnieje
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 1. Inicjalizacja pliku IFC4x3 ---
f = ifcopenshell.file(schema="IFC4X3")

# --- 2. Tworzenie podstawowej struktury IFC (Project, Site, Context) ---
owner_history = f.create_entity("IfcOwnerHistory")
project = f.create_entity("IfcProject", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, Name="Annotation Project")
context = f.create_entity("IfcGeometricRepresentationContext", ContextType="Model", CoordinateSpaceDimension=3, Precision=1.0e-5, WorldCoordinateSystem=f.create_entity("IfcAxis2Placement3D", Location=f.create_entity("IfcCartesianPoint", (0.0, 0.0, 0.0))))
f.create_entity("IfcUnitAssignment", Units=[
    f.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE"),
    f.create_entity("IfcSIUnit", UnitType="PLANEANGLEUNIT", Name="RADIAN")
])
project.RepresentationContexts = [context]
site = f.create_entity("IfcSite", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, Name="Default Site")
f.create_entity("IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, RelatingObject=project, RelatedObjects=[site])


# --- 3. Definiowanie stylu tekstu ---
# To kontroluje wygląd czcionki, jej rozmiar itp.
font_name = "Arial"
font_size = f.create_entity("IfcPositiveLengthMeasure", 0.25)
text_style_font_model = f.create_entity("IfcTextStyleFontModel",
    FontFamily=[font_name],
    FontSize=font_size
)
text_style = f.create_entity("IfcTextStyle",
    Name=font_name,
    TextCharacterAppearance=text_style_font_model
)
# Definiujemy styl jako "przypisany" do elementu, aby był używany
# Ta część nie jest potrzebna, jeśli styl przypiszemy bezpośrednio do reprezentacji
# styled_item = f.create_entity("IfcStyledItem", ... )

# --- 4. Tworzenie geometrii adnotacji (tekstu) ---
# Używamy IfcTextLiteralWithExtent, który ma zdefiniowane "pudełko"
text_to_display = "Pikieta 0+150.00"
text_placement = f.create_entity("IfcAxis2Placement2D",
    Location=f.create_entity("IfcCartesianPoint", (0.0, 0.0)),
)
# Definiujemy "pudełko" o szerokości 5m i wysokości 0.5m
planar_extent = f.create_entity("IfcPlanarExtent",
    SizeInX=5.0,  # Bezpośrednie podanie wartości float
    SizeInY=0.5   # Bezpośrednie podanie wartości float
)
text_literal = f.create_entity("IfcTextLiteralWithExtent",
    Literal=text_to_display,
    Placement=text_placement,
    Extent=planar_extent,
    BoxAlignment="MIDDLE" # Wyrównanie tekstu w pudełku
)

# --- 5. Tworzenie obiektu IfcAnnotation i jego reprezentacji ---
# Definiujemy, gdzie w przestrzeni 3D ma się znaleźć nasza adnotacja
annotation_placement_3d = f.create_entity("IfcAxis2Placement3D",
    Location=f.create_entity("IfcCartesianPoint", (10.0, 5.0, 2.0))
)
annotation_placement = f.create_entity("IfcLocalPlacement",
    RelativePlacement=annotation_placement_3d
)
# Tworzymy reprezentację adnotacji
annotation_representation = f.create_entity("IfcShapeRepresentation",
    ContextOfItems=context,
    RepresentationIdentifier="Annotation",
    RepresentationType="Annotation2D",
    Items=[text_literal]
)

# Przypisanie stylu do reprezentacji
f.create_entity("IfcStyledItem", Item=text_literal, Styles=[text_style])

# Tworzymy produkt IfcAnnotation
annotation = f.create_entity("IfcAnnotation",
    GlobalId=ifcopenshell.guid.new(),
    OwnerHistory=owner_history,
    Name="Road Stationing Label",
    ObjectPlacement=annotation_placement,
    Representation=f.create_entity("IfcProductDefinitionShape",
        Representations=[annotation_representation]
    )
)

# --- 6. Dodanie adnotacji do struktury przestrzennej (IfcSite) ---
f.create_entity("IfcRelContainedInSpatialStructure",
    GlobalId=ifcopenshell.guid.new(),
    OwnerHistory=owner_history,
    Name="Annotation in Site",
    RelatedElements=[annotation], # Obiekty do umieszczenia
    RelatingStructure=site # Gdzie umieszczamy
)

# --- Zapis pliku ---
f.write(FULL_PATH)
print(f"Utworzono plik IFC z adnotacją: {FULL_PATH}")
