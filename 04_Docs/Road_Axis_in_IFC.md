# Reprezentacja Osi Drogowej w Schemacie IFC (IFC4x3)

Oś drogi to fundamentalny element w projektowaniu infrastruktury, a jej prawidłowe odwzorowanie w IFC jest kluczowe dla całego modelu BIM. W schemacie IFC, szczególnie od wersji IFC4x1, a w pełni rozwinięte w **IFC4x3**, reprezentacja liniowych obiektów infrastrukturalnych, takich jak drogi, koleje czy rurociągi, została zrewolucjonizowana.

## Kluczowe Koncepcje i Encje IFC

Podstawą reprezentacji osi drogowej (i każdej innej osi trasowania) w IFC4x3 jest encja **`IfcAlignment`**. To ona jest kontenerem przechowującym pełną definicję geometrii i położenia osi w przestrzeni.

`IfcAlignment` składa się z dwóch głównych komponentów:

1.  **Trasa pozioma (Horizontal Alignment):** Definiuje rzut osi na płaszczyznę XY. Jest to geometria, którą widzisz na mapie.
2.  **Profil pionowy (Vertical Alignment):** Definiuje profil wysokościowy wzdłuż trasy poziomej.

---

### 1. Trasa Pozioma (`IfcAlignment.Axis`)

Atrybut `Axis` w `IfcAlignment` przechowuje geometrię trasy w 2D. Zazwyczaj jest to **`IfcCompositeCurve`**, czyli krzywa złożona z wielu segmentów. To idealnie oddaje naturę osi drogowej, która składa się z odcinków prostych, łuków kołowych i krzywych przejściowych.

-   **`IfcCompositeCurve`**: Działa jak kontener na segmenty.
-   **`IfcCompositeCurveSegment`**: Każdy segment w `IfcCompositeCurve`. Wskazuje na geometrię (np. `IfcLine`) i określa, jak łączy się z poprzednim segmentem (`Transition`).
-   **Geometria segmentów**:
    -   **Odcinki proste**: Reprezentowane przez **`IfcPolyline`** lub **`IfcTrimmedCurve`** z bazową krzywą **`IfcLine`**.
    -   **Łuki kołowe**: Reprezentowane przez **`IfcTrimmedCurve`** z bazową krzywą **`IfcCircle`**.
    -   **Krzywe przejściowe (spirale)**: Reprezentowane przez **`IfcClothoid`**, `IfcSpiral` lub inne typy krzywych przejściowych. Są one kluczowe w projektowaniu dróg dla płynnej zmiany krzywizny.

**Struktura w IFC:**

```
IfcAlignment
└── Axis: IfcCompositeCurve
    ├── Segments[0]: IfcCompositeCurveSegment
    │   └── ParentCurve: IfcLine
    ├── Segments[1]: IfcCompositeCurveSegment
    │   └── ParentCurve: IfcCircularArc
    └── Segments[2]: IfcCompositeCurveSegment
        └── ParentCurve: IfcClothoid
```

---

### 2. Profil Pionowy (`IfcAlignment.Gradient`)

Gdy mamy już zdefiniowaną trasę w 2D, musimy nadać jej wysokości. Robimy to za pomocą atrybutu `Gradient`, który wskazuje na encję **`IfcAlignmentVertical`**.

-   **`IfcAlignmentVertical`**: Jest to kontener na segmenty profilu podłużnego. Co ważne, profil ten jest zdefiniowany w odniesieniu do **długości po trasie poziomej**, a nie prostych współrzędnych X.
-   **`IfcAlignmentVerticalSegment`**: Definiuje pojedynczy segment profilu. Ma kluczowe atrybuty:
    -   `StartDistAlong`: Długość po trasie poziomej (`IfcCompositeCurve`), w której zaczyna się ten segment niwelety.
    -   `HorizontalLength`: Długość rzutu poziomego tego segmentu.
    -   `StartHeight`: Wysokość (współrzędna Z) na początku segmentu.
    -   `StartGradient`: Pochylenie podłużne na początku segmentu (np. 0.02 dla 2%).
    -   `SegmentType`: Określa kształt segmentu (np. `CONSTANTGRADIENT` dla prostej, `PARABOLICARC` dla łuku pionowego).

**Struktura w IFC:**

```
IfcAlignment
└── Gradient: IfcAlignmentVertical
    ├── Segments[0]: IfcAlignmentVerticalSegment
    │   ├── StartDistAlong: 0.0
    │   ├── HorizontalLength: 100.0
    │   ├── StartHeight: 50.0
    │   └── StartGradient: 0.02 (2%)
    └── Segments[1]: IfcAlignmentVerticalSegment
        ├── StartDistAlong: 100.0
        ├── HorizontalLength: 50.0
        ├── StartHeight: 52.0  (50.0 + 100.0 * 0.02)
        └── StartGradient: -0.01 (-1%)
```
