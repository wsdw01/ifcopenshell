import ifcopenshell
import ifcopenshell.util
import ifcopenshell.util.element
model = ifcopenshell.open('IFCs/BM_Strasse_Erg_1.IFC')
# par=model.by_guid('2MB1XmTfD32wxE3SuUNT4H')
# par2=model.by_type('ifcbuildingstorey')[1]
# # print(len(par))
# # print(len(par2))
# # print(dir(par))
# print(par.get_info())
# par_type = ifcopenshell.util.element.get_type(par)
# print(par_type)
# psets = ifcopenshell.util.element.get_psets(par)
# print(psets)

ifc = ifcopenshell.file(schema='IFC4x3_ADD2')

ifc.create_entity('IfcProject', GlobalId=ifcopenshell.guid.new(), Name='OD Matten')


ifc.write('4x3.ifc')