# Podsumowanie: `IfcAlignment` w IFC 4x3

`IfcAlignment` to "inteligentna oś" lub "kręgosłup" projektu liniowego (drogi, kolei, rurociągu). To nie jest zwykła linia 3D. To obiekt, który definiuje geometrię trasy oraz tworzy wzdłuż niej system współrzędnych (pikietaż/kilometraż), umożliwiając precyzyjne lokalizowanie innych obiektów względem osi.

---

### 1. Kluczowe Koncepcje

*   **Oś 3D definiowana przez 2D + 1D**: `IfcAlignment` nie jest definiowany bezpośrednio jako krzywa w 3D. Zamiast tego, jest kompozycją dwóch oddzielnych definicji, co odzwierciedla praktykę projektową:
    1.  **Trasa w planie (`IfcAlignmentHorizontal`)**: Definiuje przebieg osi w rzucie z góry (XY).
    2.  **Profil podłużny (`IfcAlignmentVertical`)**: Definiuje wysokość (Z) w funkcji odległości wzdłuż trasy poziomej (pikietażu).

*   **Pikietaż (Stationing/Chainage)**: To najważniejsza cecha `IfcAlignment`. Tworzy on jednowymiarowy układ współrzędnych wzdłuż osi. Dzięki temu można powiedzieć, że "studzienka znajduje się w pikietażu 123.45 m, 5 metrów na prawo od osi i 0.5 m poniżej niwelety".

---

### 2. Struktura i Hierarchia w Modelu IFC

`IfcAlignment` nigdy nie występuje w próżni. Jest częścią logicznej struktury przestrzennej (SPS - Spatial Project Structure) i ma swoją własną, wewnętrzną strukturę.

#### a) Struktura Wewnętrzna (`IfcRelNests`)

`IfcAlignment` jest "rodzicem" dla swoich definicji poziomej i pionowej. Relacja ta jest tworzona za pomocą `IfcRelNests`.

```
IfcAlignment
  └─ IfcRelNests
      ├─ IfcAlignmentHorizontal  (definicja w planie)
      └─ IfcAlignmentVertical    (definicja profilu)
```

#### b) Struktura Przestrzenna w Projekcie (`IfcRelAggregates`)

Zgodnie z najlepszymi praktykami dla infrastruktury (SPS002), `IfcAlignment` powinien być zagregowany wewnątrz `IfcRoadPart` (lub `IfcRailwayPart`, etc.), który z kolei jest częścią `IfcRoad`.

```
IfcProject
  └─ IfcSite
      └─ IfcRoad
          └─ IfcRoadPart ("Pas drogowy", "Jezdnia")
              └─ IfcAlignment ("Oś główna", "Oś krawędzi")
```

---

### 3. Definicja Geometrii

#### a) Trasa Pozioma (`IfcAlignmentHorizontal`)

*   Jej geometria jest najczęściej definiowana przez `IfcCompositeCurve` – krzywą złożoną z segmentów.
*   Każdy segment (`IfcCompositeCurveSegment`) to osobny element:
    *   `IfcPolyline`: Odcinek prosty.
    *   `IfcTrimmedCurve` (bazujący na `IfcCircle`): Łuk kołowy.
    *   `IfcClothoid` / `IfcSpiral`: Krzywa przejściowa (klotoida).
*   W Twoim skrypcie `create_road_axis_with_arc.py` właśnie taką strukturę stworzyliśmy.

#### b) Profil Podłużny (`IfcAlignmentVertical`)

*   Jest to zagnieżdżona lista segmentów profilu (`IfcAlignmentVerticalSegment`).
*   Każdy segment opisuje niweletę na danym odcinku pikietażu i ma określony typ, np.:
    *   `.CONSTANTGRADIENT.`: Odcinek o stałym pochyleniu.
    *   `.PARABOLICARC.`: Łuk pionowy (parabola).

---

### 4. Reprezentacja w `ifcopenshell` (Praktyczny Przykład)

Oto skondensowany przepływ pracy w Pythonie, bazujący na Twoim kodzie:

```python
# 1. Stwórz geometrię 2D dla trasy poziomej (np. IfcCompositeCurve)
horizontal_curve = f.create_entity("IfcCompositeCurve", ...)

# 2. Stwórz IfcAlignmentHorizontal i przypisz mu geometrię
horizontal_alignment = f.create_entity("IfcAlignmentHorizontal", ...)
horizontal_alignment.Representation = f.create_entity("IfcProductDefinitionShape",
    Representations=[f.create_entity("IfcShapeRepresentation",
        ContextOfItems=axis_sub_context, # Ważny sub-kontekst 'Axis'
        RepresentationIdentifier='Axis',
        RepresentationType='Curve2D',
        Items=[horizontal_curve]
    )]
)

# 3. Stwórz segmenty profilu podłużnego
vert_seg_1_geom = f.create_entity("IfcAlignmentVerticalSegment", StartDistAlong=0.0, ...)
vert_seg_1 = f.create_entity("IfcAlignmentSegment", DesignParameters=vert_seg_1_geom)
# ... kolejne segmenty

# 4. Stwórz IfcAlignmentVertical i zagnieść w nim segmenty
vertical_alignment = f.create_entity("IfcAlignmentVertical", ...)
f.create_entity("IfcRelNests", RelatingObject=vertical_alignment, RelatedObjects=[vert_seg_1, ...])

# 5. Stwórz główny IfcAlignment
alignment = f.create_entity("IfcAlignment", Name="Oś Drogi Głównej", ...)

# 6. Zagnieść w nim oś poziomą i pionową
f.create_entity("IfcRelNests", RelatingObject=alignment, RelatedObjects=[horizontal_alignment, vertical_alignment])

# 7. Umieść IfcAlignment w strukturze przestrzennej (np. w IfcRoadPart)
road_part = f.create_entity("IfcRoadPart", ...)
f.create_entity("IfcRelAggregates", RelatingObject=road_part, RelatedObjects=[alignment])
```

---

### 5. Najważniejsze Dobre Praktyki i Pułapki

1.  **MVD (Model View Definition)**: Aby przeglądarki IFC poprawnie zinterpretowały `IfcAlignment`, nagłówek pliku **musi** zawierać `ViewDefinition [Alignment-basedView]`. To kluczowe, jak już odkryliśmy.
2.  **Struktura Przestrzenna (SPS)**: Zawsze umieszczaj `IfcAlignment` w odpowiednim kontenerze (`IfcRoadPart`, `IfcBridgePart` etc.). Nie agreguj go bezpośrednio do `IfcSite`.
3.  **Kompletność**: Użyteczny `IfcAlignment` musi mieć zdefiniowane **oba** komponenty: `IfcAlignmentHorizontal` i `IfcAlignmentVertical`.
4.  **Sub-kontekst Reprezentacji**: Geometria osi (`Curve2D`) musi być zdefiniowana w odpowiednim `IfcGeometricRepresentationSubContext` z `ContextIdentifier='Axis'`.
5.  **Jednostki**: Upewnij się, że `IfcUnitAssignment` w projekcie jest poprawnie zdefiniowany (metry, radiany).
