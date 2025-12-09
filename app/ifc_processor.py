# ifc_processor.py
import ifcopenshell
import ifcopenshell.util.unit
import math

SKIP_TYPES = [
    "IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey",
    "IfcSpace", "IfcOpeningElement", "IfcAnnotation", "IfcGrid",
    "IfcGroup", "IfcZone", "IfcSystem", "IfcPort"
]

def get_property_value(element, possible_names):
    for rel in getattr(element, "IsDefinedBy", []):
        if rel.is_a("IfcRelDefinesByProperties"):
            pset = rel.RelatingPropertyDefinition

            # Quantities
            if pset.is_a("IfcElementQuantity"):
                for q in pset.Quantities:
                    if q.Name in possible_names:
                        if q.is_a("IfcQuantityLength"): return q.LengthValue
                        if q.is_a("IfcQuantityArea"):   return q.AreaValue
                        if q.is_a("IfcQuantityVolume"): return q.VolumeValue
                        if hasattr(q, "NominalValue"):
                            return q.NominalValue.wrappedValue

            # Properties
            elif pset.is_a("IfcPropertySet"):
                for p in pset.HasProperties:
                    if p.Name in possible_names:
                        if p.is_a("IfcPropertySingleValue") and p.NominalValue:
                            return p.NominalValue.wrappedValue
    return None


def parse_all_objects(ifc_path):
    try:
        f = ifcopenshell.open(ifc_path)
    except:
        return []

    try:
        unit_scale = ifcopenshell.util.unit.calculate_unit_scale(f)
    except:
        unit_scale = 1.0

    def to_meter(val, power=1):
        if val is None:
            return 0.0
        try:
            return round(float(val) * (unit_scale ** power), 3)
        except:
            return 0.0

    results = []

    for product in f.by_type("IfcProduct"):
        if product.is_a() in SKIP_TYPES:
            continue

        # Ambil quantities
        val_panjang = get_property_value(product, ["Length", "NominalLength", "Span", "MajorDimension", "Perimeter"])
        val_tinggi  = get_property_value(product, ["Height", "NominalHeight", "OverallHeight", "Rise"])
        val_tebal   = get_property_value(product, ["Thickness", "ConstructionThickness", "NominalThickness", "Width"])
        val_area    = get_property_value(product, ["NetArea", "GrossArea", "Area"])
        val_volume  = get_property_value(product, ["NetVolume", "GrossVolume", "Volume"])

        p = to_meter(val_panjang, 1)
        t = to_meter(val_tinggi, 1)
        l = to_meter(val_tebal, 1)
        a = to_meter(val_area, 2)
        v = to_meter(val_volume, 3)

        # Slab fix
        if product.is_a() == "IfcSlab":
            if l > 2.0 and p < 1.0:
                p, l = l, 0.15
            if p == 0.0 and a > 0:
                p = round(math.sqrt(a), 2)

        # Volume/area fallback
        if v == 0 and p > 0 and t > 0 and l > 0:
            v = round(p * t * l, 3)
        if a == 0 and p > 0 and t > 0:
            a = round(p * t, 3)

        # Satuan utama
        satuan = "unit"
        if v > 0: satuan = "m3"
        elif a > 0: satuan = "m2"
        elif p > 0: satuan = "m"

        obj = {
            "guid": product.GlobalId,
            "tipe_ifc": product.is_a(),
            "nama": product.Name if product.Name else f"Unnamed {product.is_a()}",
            "label_cad": product.Tag if product.Tag else "",
            "satuan_utama_hitung": satuan,
            "satuan_sumber": "METER (Converted)",
            "kuantitas": {
                "panjang": p,
                "tinggi": t,
                "tebal": l,
                "area_m2": a,
                "volume_m3": v
            }
        }

        results.append(obj)

    return results
