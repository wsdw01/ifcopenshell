import ifcopenshell
import ifcopenshell.api
import os
import time
import ifcopenshell.guid

# --- Ustawienia --- #
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
GENERATED_IFC_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "02_Generated_IFCs"))
OUTPUT_FILENAME = "road_axis_with_arc.ifc" # Nowa nazwa pliku
OUTPUT_FILE_PATH = os.path.join(GENERATED_IFC_DIR, OUTPUT_FILENAME)

os.makedirs(GENERATED_IFC_DIR, exist_ok=True)

# --- 1. Inicjalizacja pliku IFC4x3 ---
f = ifcopenshell.file(schema="IFC4X3")

# Dodanie Model View Definition (MVD) do nagłówka
# Zgodnie z dokumentacją buildingSMART, dla IFC4x3 używamy "Reference View" z dodatkiem "IFC4x3_ADD2"
f.header.file_description.description = ("ViewDefinition [Alignment-basedView]",)

# --- Podstawowe encje (sprawdzone, działające) ---
owner_history = f.create_entity("IfcOwnerHistory",
    OwningUser=f.create_entity("IfcPersonAndOrganization",
        ThePerson=f.create_entity("IfcPerson", GivenName="Wojtek"),
        TheOrganization=f.create_entity("IfcOrganization", Name="Civil Engineer")),
    OwningApplication=f.create_entity("IfcApplication",
        ApplicationDeveloper=f.create_entity("IfcOrganization", Name="ifcopenshell"),
        Version="0.8.0", ApplicationFullName="IfcOpenShell", ApplicationIdentifier="IfcOpenShell"),
    ChangeAction="NOCHANGE", CreationDate=int(time.time()))

unit_assignment = f.create_entity("IfcUnitAssignment", Units=[
    f.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE"),
    f.create_entity("IfcSIUnit", UnitType="PLANEANGLEUNIT", Name="RADIAN")])

world_coordinate_system = f.create_entity("IfcAxis2Placement3D", Location=f.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)))
context = f.create_entity("IfcGeometricRepresentationContext", ContextIdentifier="Model", ContextType="Model", CoordinateSpaceDimension=3, Precision=1e-5, WorldCoordinateSystem=world_coordinate_system)
plan_context = f.create_entity("IfcGeometricRepresentationContext", ContextIdentifier="Plan", ContextType="Plan", CoordinateSpaceDimension=2, Precision=1e-5, WorldCoordinateSystem=world_coordinate_system)
axis_sub_context = f.create_entity("IfcGeometricRepresentationSubContext", ContextIdentifier='Axis', ContextType='Plan', ParentContext=plan_context, TargetView='PLAN_VIEW')

project = f.create_entity("IfcProject", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, Name="Projekt z Łukiem", RepresentationContexts=[context, plan_context], UnitsInContext=unit_assignment)
site = f.create_entity("IfcSite", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, Name="Teren Projektu", CompositionType="ELEMENT")
f.create_entity("IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, RelatingObject=project, RelatedObjects=[site])

# --- Definicja geometrii (z dodanym łukiem) ---

# Punkty
p1 = f.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
p2 = f.create_entity("IfcCartesianPoint", Coordinates=(100.0, 0.0))
center_arc_point = f.create_entity("IfcCartesianPoint", Coordinates=(100.0, -50.0))
p4 = f.create_entity("IfcCartesianPoint", Coordinates=(150.0, -50.0))

# Segment 1: Prosta
line_segment = f.create_entity("IfcPolyline", Points=[p1, p2])

import math

# ... (reszta kodu bez zmian do tego miejsca)

# Segment 2: Łuk kołowy - ZMIENIONA METODA PRZYCINANIA
center_arc_placement = f.create_entity("IfcAxis2Placement2D", Location=center_arc_point)
circle = f.create_entity("IfcCircle", Position=center_arc_placement, Radius=50.0)

# POPRAWKA: Zamiast przycinać punktami, przycinamy za pomocą parametrów (kątów)
# Jest to bardziej niezawodna metoda, lepiej wspierana przez oprogramowanie.
import math
trim1_param = f.create_entity("IfcParameterValue", math.pi / 2) # Kąt dla punktu p2
trim2_param = f.create_entity("IfcParameterValue", 0.0)         # Kąt dla punktu p4

arc_segment = f.create_entity("IfcTrimmedCurve",
    BasisCurve=circle,
    Trim1=[trim1_param],
    Trim2=[trim2_param],
    SenseAgreement=False,
    MasterRepresentation="PARAMETER" # Zmiana na PARAMETER
)

# Segment 3: Koniec
zero_length_segment = f.create_entity("IfcPolyline", Points=[p4, p4])

# ... (reszta kodu bez zmian)


# Krzywa złożona
segment1 = f.create_entity("IfcCompositeCurveSegment", Transition="CONTINUOUS", SameSense=True, ParentCurve=line_segment)
segment2 = f.create_entity("IfcCompositeCurveSegment", Transition="CONTINUOUS", SameSense=True, ParentCurve=arc_segment)
segment3 = f.create_entity("IfcCompositeCurveSegment", Transition="DISCONTINUOUS", SameSense=True, ParentCurve=zero_length_segment)
horizontal_alignment_curve = f.create_entity("IfcCompositeCurve", Segments=[segment1, segment2, segment3], SelfIntersect=False)

# --- Struktura osi (bez zmian) ---
placement = f.create_entity("IfcLocalPlacement", RelativePlacement=f.create_entity("IfcAxis2Placement3D", Location=f.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))))

horizontal_alignment = f.create_entity("IfcAlignmentHorizontal", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, Name="Oś pozioma z łukiem", ObjectPlacement=placement)
horizontal_alignment.Representation = f.create_entity("IfcProductDefinitionShape", Representations=[f.create_entity("IfcShapeRepresentation", ContextOfItems=axis_sub_context, RepresentationIdentifier='Axis', RepresentationType='Curve2D', Items=[horizontal_alignment_curve])])

arc_horizontal_length = 0.5 * 3.1415926535 * 50.0
vertical_segment1_geom = f.create_entity("IfcAlignmentVerticalSegment", StartDistAlong=0.0, HorizontalLength=100.0, StartHeight=10.0, StartGradient=0.02, EndGradient=0.02, RadiusOfCurvature=None, PredefinedType="CONSTANTGRADIENT")
vertical_segment1 = f.create_entity("IfcAlignmentSegment", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, DesignParameters=vertical_segment1_geom)
vertical_segment2_geom = f.create_entity("IfcAlignmentVerticalSegment", StartDistAlong=100.0, HorizontalLength=arc_horizontal_length, StartHeight=12.0, StartGradient=-0.01, EndGradient=-0.01, RadiusOfCurvature=None, PredefinedType="CONSTANTGRADIENT")
vertical_segment2 = f.create_entity("IfcAlignmentSegment", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, DesignParameters=vertical_segment2_geom)
vertical_segment3_geom = f.create_entity("IfcAlignmentVerticalSegment", StartDistAlong=100.0 + arc_horizontal_length, HorizontalLength=0.0, StartHeight=12.0 - arc_horizontal_length * 0.01, StartGradient=-0.01, EndGradient=-0.01, RadiusOfCurvature=None, PredefinedType="CONSTANTGRADIENT")
vertical_segment3 = f.create_entity("IfcAlignmentSegment", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, DesignParameters=vertical_segment3_geom)

vertical_alignment = f.create_entity("IfcAlignmentVertical", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history)
f.create_entity("IfcRelNests", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, RelatingObject=vertical_alignment, RelatedObjects=[vertical_segment1, vertical_segment2, vertical_segment3])

alignment = f.create_entity("IfcAlignment", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, Name="Oś Drogi Głównej", ObjectPlacement=placement)
alignment.Representation = f.create_entity("IfcProductDefinitionShape", Representations=[f.create_entity("IfcShapeRepresentation", ContextOfItems=axis_sub_context, RepresentationIdentifier='Axis', RepresentationType='Curve2D', Items=[horizontal_alignment_curve])])

# --- Poprawka struktury przestrzennej (SPS002) ---
# Tworzymy IfcRoad, który będzie kontenerem dla części drogi
road = f.create_entity("IfcRoad", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, Name="Główna Droga")

# Tworzymy IfcRoadPart, który będzie właściwym kontenerem dla IfcAlignment
road_part = f.create_entity("IfcRoadPart", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, Name="Pas drogowy", UsageType="LONGITUDINAL", PredefinedType="ROADSEGMENT")

# Agregujemy IfcRoad do IfcSite
f.create_entity("IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, RelatingObject=site, RelatedObjects=[road])

# Agregujemy IfcRoadPart do IfcRoad
f.create_entity("IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, RelatingObject=road, RelatedObjects=[road_part])

# Agregujemy IfcAlignment do IfcRoadPart
f.create_entity("IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, RelatingObject=road_part, RelatedObjects=[alignment])

f.create_entity("IfcRelNests", GlobalId=ifcopenshell.guid.new(), OwnerHistory=owner_history, RelatingObject=alignment, RelatedObjects=[horizontal_alignment, vertical_alignment])

# --- Zapis pliku ---
f.write(OUTPUT_FILE_PATH)
print(f"Plik {OUTPUT_FILENAME} został pomyślnie wygenerowany w {GENERATED_IFC_DIR}")
