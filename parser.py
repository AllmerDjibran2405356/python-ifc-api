import ifcopenshell
import ifcopenshell.util.unit
import math


SKIP_TYPES = [
    "IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey",
    "IfcSpace", "IfcOpeningElement", "IfcAnnotation", "IfcGrid",
    "IfcGroup", "IfcZone", "IfcSystem", "IfcPort"
]

def get_property_value(element, possible_names):
    for rel in element.IsDefinedBy or []:
        if rel.is_a("IfcRelDefinesByProperties"):
            pset = rel.RelatingPropertyDefinition

            # Quantity Set
            if pset.is_a("IfcElementQuantity"):
                for q in pset.Quantities:
                    if q.Name in possible_names:
                        if hasattr(q, "LengthValue"): return q.LengthValue
                        if hasattr(q, "AreaValue"): return q.AreaValue
                        if hasattr(q, "VolumeValue"): return q.VolumeValue

            # Property Set
            elif pset.is_a("IfcPropertySet"):
                for p in pset.HasProperties:
                    if p.Name in possible_names and p.is_a("IfcPropertySingleValue"):
                        if p.NominalValue:
                            return p.NominalValue.wrappedValue

    return None


def parse_all_objects(ifc_path):
    """
    Parse IFC dan mengembalikan format JSON siap dipakai di Laravel
    """
    f = ifcopenshell.open(ifc_path)

    # Unit Scale
    try:
        unit_scale = ifcopenshell.util.unit.calculate_unit_scale(f)
    except:
        unit_scale = 1.0

    def to_meter(val, power=1):
        if val is None:
            return 0
        try:
            return round(float(val) * (unit_scale ** power), 3)
        except:
            return 0

    results = []

    products = f.by_type("IfcProduct")

    for p in products:
        if p.is_a() in SKIP_TYPES:
            continue

        panjang = get_property_value(p, ["Length", "NominalLength", "Span"])
        tinggi  = get_property_value(p, ["Height", "OverallHeight", "NominalHeight"])
        tebal   = get_property_value(p, ["Width", "Thickness", "NominalWidth"])

        area    = get_property_value(p, ["NetArea", "GrossArea", "Area"])
        volume  = get_property_value(p, ["NetVolume", "GrossVolume", "Volume"])

        panjang = to_meter(panjang, 1)
        tinggi  = to_meter(tinggi, 1)
        tebal   = to_meter(tebal, 1)
        area    = to_meter(area, 2)
        volume  = to_meter(volume, 3)

        satuan = "unit"
        if volume > 0: satuan = "m3"
        elif area > 0: satuan = "m2"
        elif panjang > 0: satuan = "m"

        results.append({
            "guid": p.GlobalId,
            "tipe_ifc": p.is_a(),
            "nama": p.Name or f"Unnamed {p.is_a()}",
            "label_cad": p.Tag or "",
            "satuan_utama_hitung": satuan,
            "kuantitas": {
                "panjang": panjang,
                "tinggi": tinggi,
                "tebal": tebal,
                "area_m2": area,
                "volume_m3": volume
            }
        })

    return results
