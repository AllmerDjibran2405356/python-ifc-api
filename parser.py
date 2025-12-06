import ifcopenshell
import ifcopenshell.util.unit
import os
import json
import math

# DAFTAR TYPE YANG DI-SKIP
SKIP_TYPES = [
    "IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey",
    "IfcSpace", "IfcOpeningElement", "IfcAnnotation", "IfcGrid",
    "IfcGroup", "IfcZone", "IfcSystem", "IfcPort"
]

def get_property_value(element, possible_names):
    for rel in getattr(element, "IsDefinedBy", []) or []:
        if rel.is_a("IfcRelDefinesByProperties"):
            pset = rel.RelatingPropertyDefinition

            if pset.is_a("IfcElementQuantity"):
                for q in getattr(pset, "Quantities", []) or []:
                    if q.Name in possible_names:
                        # cek type quantity
                        if q.is_a("IfcQuantityLength") and hasattr(q, "LengthValue"): return q.LengthValue
                        if q.is_a("IfcQuantityArea") and hasattr(q, "AreaValue"): return q.AreaValue
                        if q.is_a("IfcQuantityVolume") and hasattr(q, "VolumeValue"): return q.VolumeValue
                        if q.is_a("IfcQuantityCount") and hasattr(q, "CountValue"): return q.CountValue
                        if hasattr(q, "NominalValue"):
                            try:
                                return q.NominalValue.wrappedValue
                            except:
                                return None

            elif pset.is_a("IfcPropertySet"):
                for p in getattr(pset, "HasProperties", []) or []:
                    if p.Name in possible_names and p.is_a("IfcPropertySingleValue"):
                        if getattr(p, "NominalValue", None):
                            try:
                                return p.NominalValue.wrappedValue
                            except:
                                return None
    return None

def parse_all_objects(ifc_path):
    """
    Versi parser: membuka ifc_path, mengekstrak property seperti parser lama,
    lalu mengembalikan list of dict (JSON-serializable).
    """
    # buka model
    f = ifcopenshell.open(ifc_path)

    # unit scale
    try:
        unit_scale = ifcopenshell.util.unit.calculate_unit_scale(f)
    except:
        unit_scale = 1.0

    def to_meter(val, power=1):
        if val is None: return 0.0
        try:
            valf = float(val)
            return round(valf * (unit_scale ** power), 3)
        except:
            return 0.0

    data_output = []
    all_products = f.by_type("IfcProduct")

    for product in all_products:
        ifc_type = product.is_a()
        if ifc_type in SKIP_TYPES:
            continue

        # PANJANG
        list_panjang = ["Length", "NominalLength", "Span", "MajorDimension", "Perimeter", "Girth"]
        val_panjang = get_property_value(product, list_panjang)

        # TINGGI
        list_tinggi = ["Height", "NominalHeight", "OverallHeight", "Rise"]
        val_tinggi = get_property_value(product, list_tinggi)

        # TEBAL
        if ifc_type == "IfcSlab":
            list_tebal = ["Thickness", "ConstructionThickness", "NominalThickness", "Width"]
        else:
            list_tebal = ["Width", "Thickness", "ConstructionThickness", "NominalWidth"]
        val_tebal = get_property_value(product, list_tebal)

        # AREA & VOLUME
        val_area = get_property_value(product, ["NetArea", "GrossArea", "Area", "NetSideArea", "GrossSideArea"])
        val_volume = get_property_value(product, ["NetVolume", "GrossVolume", "Volume"])

        # konversi ke meter
        p_meter = to_meter(val_panjang, 1)
        t_meter = to_meter(val_tinggi, 1)
        l_meter = to_meter(val_tebal, 1)
        area_m2 = to_meter(val_area, 2)
        vol_m3  = to_meter(val_volume, 3)

        # logika perbaikan slab
        if ifc_type == "IfcSlab":
            if l_meter > 2.0 and p_meter < 1.0:
                p_meter = l_meter
                l_meter = 0.15
            if p_meter == 0.0 and area_m2 > 0:
                p_meter = round(math.sqrt(area_m2), 2)

        # fallback volume
        if vol_m3 == 0.0 and p_meter > 0 and t_meter > 0 and l_meter > 0:
            vol_m3 = round(p_meter * t_meter * l_meter, 3)

        # fallback area
        if area_m2 == 0.0:
            if p_meter > 0 and t_meter > 0:
                area_m2 = round(p_meter * t_meter, 3)
            elif p_meter > 0 and l_meter > 0 and ifc_type == "IfcSlab":
                area_m2 = round(p_meter * l_meter, 3)

        satuan_utama = "unit"
        if vol_m3 > 0: satuan_utama = "m3"
        elif area_m2 > 0: satuan_utama = "m2"
        elif p_meter > 0: satuan_utama = "m"

        objek_data = {
            "guid": getattr(product, "GlobalId", None),
            "tipe_ifc": ifc_type,
            "nama": getattr(product, "Name", None) or f"Unnamed {ifc_type}",
            "label_cad": getattr(product, "Tag", None) or "",
            "satuan_utama_hitung": satuan_utama,
            "satuan_sumber": "METER (Converted)",
            "kuantitas": {
                "panjang": p_meter,
                "tinggi": t_meter,
                "tebal": l_meter,
                "area_m2": area_m2,
                "volume_m3": vol_m3
            }
        }

        data_output.append(objek_data)

    return data_output
