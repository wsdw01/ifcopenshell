import ifcopenshell
import ifcopenshell.api

# 1. Utwórz nowy plik IFC ze schematem IFC4x3
file = ifcopenshell.file(schema='IFC4x3')

# 2. Utwórz OwnerHistory (często wymagane, jeśli nie ma go w pliku)
# IfcOpenShell.api często dba o to automatycznie przy tworzeniu nowego projektu,
# ale możesz to zrobić ręcznie:
# owner_history = ifcopenshell.api.run("root.create_entity", file, ifc_class='IfcOwnerHistory')
# W nowszych wersjach IfcOpenShell (np. w użyciu z ifcopenshell.api.project.create_file)
# owner_history jest tworzony automatycznie i domyślnie.
# Dla ifc.create_entity() bezpośrednio, możesz potrzebować go utworzyć, jeśli nie masz.
# Dla uproszczenia, w tym przykładzie zakładamy, że właściciel historii jest już dostępny lub zostanie automatycznie przypisany.

# 3. Utwórz IfcProject
# Zwróć uwagę na kolejność atrybutów. IfcOpenShell oczekuje ich w kolejności schematu.
# Najprościej jest użyć argumentów nazwanych.

# Minimalny IfcProject (Name jest wymagany)
# project = file.create_entity('IfcProject', GlobalId=ifcopenshell.guid.new(), Name='Minimal Project')

# IfcProject z bardziej kompletnymi atrybutami, uwzględniając dziedziczone z IfcContext
# Właściwie, najlepiej jest używać IfcOpenShell API do tworzenia projektu,
# ponieważ dba ono o wszystkie powiązane encje (konteksty, jednostki) automatycznie.

# Zamiast bezpośredniego file.create_entity, zalecam użycie API:
project = ifcopenshell.api.run("project.create_file", file, schema='IFC4x3')

# Teraz możesz ustawić atrybuty na IfcProject utworzonym przez API
# Access the created IfcProject entity
ifc_project = file.by_type("IfcProject")[0] # Będzie tylko jeden IfcProject

# Ustawienie atrybutów dla istniejącego IfcProject (stworzonego przez API)
# API project.create_file już ustawia Name, OwnerHistory, RepresentationContexts i UnitsInContext
# Możemy je zmodyfikować lub dodać inne atrybuty.

ifc_project.Name = "Mój Nowy Projekt IFC4x3"
ifc_project.LongName = "Pełna Nazwa Mojego Projektu Budowlanego"
ifc_project.Phase = "Faza Projektowa"

# Sprawdzenie utworzonych jednostek i kontekstów (automatycznie przez API)
# print("Units in context:", ifc_project.UnitsInContext)
# print("Representation Contexts:", ifc_project.RepresentationContexts)

# Możesz uzyskać dostęp do konkretnych kontekstów, np. kontekstu geometrii 3D
# ifc_project.RepresentationContexts[0] # To będzie IfcGeometricRepresentationContext

# Zapisz plik
file.write("my_ifc4x3_project.ifc")

print(f"Utworzono plik IFC4x3 z projektem: {ifc_project.Name}")
print(f"GUID projektu: {ifc_project.GlobalId}")