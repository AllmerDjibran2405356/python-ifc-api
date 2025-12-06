import ifcopenshell
import ifcopenshell.util.unit


def process_ifc(path: str):
    model = ifcopenshell.open(path)

    project = model.by_type("IfcProject")[0]
    unit_scale = ifcopenshell.util.unit.calculate_unit_scale(project)

    output = []

    for element in model.by_type("IfcBuildingElement"):

        try:
            guid = element.GlobalId
            name = element.Name or ""
            label = str(element.id())
            type_ifc = element.is_a()

            qto = model.get_qto(element)

            panjang = getattr(qto, "Length", 0) * unit_scale if qto else 0
            tinggi  = getattr(qto, "Height", 0) * unit_scale if qto else 0
            tebal   = getattr(qto, "Width", 0)  * unit_scale if qto else 0
            area    = getattr(qto, "Area", 0)   * (unit_scale ** 2) if qto else 0
            volume  = getattr(qto, "Volume", 0) * (unit_scale ** 3) if qto else 0

            satuan = "m3" if volume > 0 else "m2"

            output.append({
                "guid": guid,
                "tipe_ifc": type_ifc,
                "nama": name,
                "label_cad": label,
                "satuan_utama_hitung": satuan,
                "satuan_sumber": "METER (Converted)",
                "kuantitas": {
                    "panjang": round(panjang, 3),
                    "tinggi": round(tinggi, 3),
                    "tebal": round(tebal, 3),
                    "area_m2": round(area, 3),
                    "volume_m3": round(volume, 3)
                }
            })

        except:
            continue

    return output
