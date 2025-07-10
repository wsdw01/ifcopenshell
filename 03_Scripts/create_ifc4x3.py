import ifcopenshell
import ifcopenshell.api.project
import ifcopenshell.api.root
import ifcopenshell.util
import ifcopenshell.util.element

model = ifcopenshell.api.project.create_file(version='IFC4X3')
project = ifcopenshell.api.root.create_entity(model, ifc_class="IfcProject", name="OD Matten")
project.LongName = "Ortsdurchfahrt Matten"
project.Phase="Bauprojekt"

site_586 = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name="Parzelle 586")
site_586.Description = "Kantonsparzelle"
site_587 = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name="Parzelle 587")
site_587.Description = "Gemiendeparzelle"
site_588 = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name="Parzelle 588")
site_588.Description = "Gemiendeparzelle"
site_589 = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name="Parzelle 589")
site_589.Description = "Gemeindeparzelle"
site_590 = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name="Parzelle 589")
site_590.Description = "Gemeindeparzelle"

Kantonstrasse = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoad", name="Kantonstrasse")
Kantonstrasse_carriageway_long = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoadPart", name="Kantonstrasse | ROADSEGMENT")
Kantonstrasse_carriageway_long.UsageType = "LONGITUDINAL"
Kantonstrasse_carriageway_long.PredefinedType = "ROADSEGMENT"
Kantonstrasse_carriageway_lat = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoadPart", name="Kantonstrasse | CARRIAGEWAY")
Kantonstrasse_carriageway_lat.UsageType = "LATERAL"
Kantonstrasse_carriageway_lat.PredefinedType = "CARRIAGEWAY"

Parkstrasse = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoad", name="Parkstrasse")
Parkstrasse_carriageway_long = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoadPart", name="Parkstrasse | ROADSEGMENT")
Parkstrasse_carriageway_long.UsageType = "LONGITUDINAL"
Parkstrasse_carriageway_long.PredefinedType = "ROADSEGMENT"
Parkstrasse_carriageway_lat = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoadPart", name="Parkstrasse | CARRIAGEWAY")
Parkstrasse_carriageway_lat.UsageType = "LATERAL"
Parkstrasse_carriageway_lat.PredefinedType = "CARRIAGEWAY"

Metzgergasse = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoad", name="Metzgergasse")
Metzgergasse_carriageway_long = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoadPart", name="Metzgergasse | ROADSEGMENT")
Metzgergasse_carriageway_long.UsageType = "LONGITUDINAL"
Metzgergasse_carriageway_long.PredefinedType = "ROADSEGMENT"
Metzgergasse_carriageway_lat = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoadPart", name="Metzgergasse | CARRIAGEWAY")
Metzgergasse_carriageway_lat.UsageType = "LATERAL"
Metzgergasse_carriageway_lat.PredefinedType = "CARRIAGEWAY"

Tellweg = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoad", name="Tellweg")
Tellweg_carriageway_long = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoadPart", name="Tellweg | ROADSEGMENT")
Tellweg_carriageway_long.UsageType = "LONGITUDINAL"
Tellweg_carriageway_long.PredefinedType = "ROADSEGMENT"
Tellweg_carriageway_lat = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoadPart", name="Tellweg | CARRIAGEWAY")
Tellweg_carriageway_lat.UsageType = "LATERAL"
Tellweg_carriageway_lat.PredefinedType = "CARRIAGEWAY"

Rugenstrasse = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoad", name="Rugenstrasse")
Rugenstrasse_carriageway_long = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoadPart", name="Rugenstrasse | ROADSEGMENT")
Rugenstrasse_carriageway_long.UsageType = "LONGITUDINAL"
Rugenstrasse_carriageway_long.PredefinedType = "ROADSEGMENT"
Rugenstrasse_carriageway_lat = ifcopenshell.api.root.create_entity(model, ifc_class="IfcRoadPart", name="Rugenstrasse | CARRIAGEWAY")
Rugenstrasse_carriageway_lat.UsageType = "LATERAL"
Rugenstrasse_carriageway_lat.PredefinedType = "CARRIAGEWAY"

best_Terrain = ifcopenshell.api.root.create_entity(model, ifc_class="IfcGeographicElement", name="bestehendes Gelände")

ifcopenshell.api.aggregate.assign_object(model, products=[best_Terrain], relating_object=project)

ifcopenshell.api.aggregate.assign_object(model, products=[site_586,site_587,site_588,site_589,site_590], relating_object=project)

ifcopenshell.api.aggregate.assign_object(model, products=[Kantonstrasse], relating_object=site_586)
ifcopenshell.api.aggregate.assign_object(model, products=[Kantonstrasse_carriageway_long], relating_object=Kantonstrasse)
ifcopenshell.api.aggregate.assign_object(model, products=[Kantonstrasse_carriageway_lat], relating_object=Kantonstrasse_carriageway_long)

ifcopenshell.api.aggregate.assign_object(model, products=[Parkstrasse], relating_object=site_587)
ifcopenshell.api.aggregate.assign_object(model, products=[Parkstrasse_carriageway_long], relating_object=Parkstrasse)
ifcopenshell.api.aggregate.assign_object(model, products=[Parkstrasse_carriageway_lat], relating_object=Parkstrasse_carriageway_long)

ifcopenshell.api.aggregate.assign_object(model, products=[Metzgergasse], relating_object=site_588)
ifcopenshell.api.aggregate.assign_object(model, products=[Metzgergasse_carriageway_long], relating_object=Metzgergasse)
ifcopenshell.api.aggregate.assign_object(model, products=[Metzgergasse_carriageway_lat], relating_object=Metzgergasse_carriageway_long)

ifcopenshell.api.aggregate.assign_object(model, products=[Tellweg], relating_object=site_589)
ifcopenshell.api.aggregate.assign_object(model, products=[Tellweg_carriageway_long], relating_object=Tellweg)
ifcopenshell.api.aggregate.assign_object(model, products=[Tellweg_carriageway_lat], relating_object=Tellweg_carriageway_long)

ifcopenshell.api.aggregate.assign_object(model, products=[Rugenstrasse], relating_object=site_590)
ifcopenshell.api.aggregate.assign_object(model, products=[Rugenstrasse_carriageway_long], relating_object=Rugenstrasse)
ifcopenshell.api.aggregate.assign_object(model, products=[Rugenstrasse_carriageway_lat], relating_object=Rugenstrasse_carriageway_long)



print(best_Terrain.get_info())


model.write("OD_Matten_4x3.ifc")
