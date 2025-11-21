import ifcopenshell
import ifcopenshell.api
import os
import json
import sys

# --- Konfigurasi ---
FOLDER_OUTPUT = r"C:\Users\allme\Documents\python_projects\ai_engine_materix\ai_engine_materix\engine_bim_and_ifc\data\processed"

# =====================================================================
# HELPER FUNCTION (tetap sama)
# =====================================================================
def get_ifc_attribute(element, set_name, attr_name):
    try:
        for rel in element.IsDefinedBy:
            if rel.is_a("IfcRelDefinesByProperties"):
                pset = rel.RelatingPropertyDefinition
                is_pset = pset.is_a("IfcPropertySet")
                is_qset = pset.is_a("IfcElementQuantity")
                if pset.Name == set_name:
                    if is_pset:
                        for prop in pset.HasProperties:
                            if prop.Name == attr_name and prop.is_a("IfcPropertySingleValue"):
                                return prop.NominalValue.wrappedValue
                    elif is_qset:
                        for quantity in pset.Quantities:
                            if quantity.Name == attr_name:
                                if quantity.is_a("IfcQuantityLength"):
                                    return quantity.LengthValue
                                elif quantity.is_a("IfcQuantityArea"):
                                    return quantity.AreaValue
                                elif quantity.is_a("IfcQuantityVolume"):
                                    return quantity.VolumeValue
                                elif hasattr(quantity, 'NominalValue'):
                                    return quantity.NominalValue.wrappedValue
    except Exception as e:
        print(f"[Peringatan] Gagal ambil atribut {attr_name} dari {element.is_a()} ID:{element.id()}: {e}")
    return None

# =====================================================================
# FUNGSI PARSER UTAMA (input: path file IFC)
# =====================================================================
def parse_ifc_file(ifc_path):
    print(f"Membuka file IFC: {ifc_path}")
    try:
        f = ifcopenshell.open(ifc_path)
    except Exception as e:
        print(f"ERROR: Gagal membuka file IFC. {e}")
        return None

    data_terekstrak = []

    # Proses dinding
    for dinding in f.by_type("IfcWall"):
        panjang = get_ifc_attribute(dinding, "BaseQuantities", "Length")
        tinggi = get_ifc_attribute(dinding, "BaseQuantities", "Height")
        tebal = get_ifc_attribute(dinding, "BaseQuantities", "Width")
        area = get_ifc_attribute(dinding, "BaseQuantities", "NetArea")
        volume = get_ifc_attribute(dinding, "BaseQuantities", "NetVolume")

        if area is None:
            area = get_ifc_attribute(dinding, "BaseQuantities", "NetSideArea")
        if area is None and panjang and tinggi:
            area = panjang * tinggi
        if volume is None and area and tebal:
            volume = area * tebal

        objek_dinding = {
            "guid": dinding.GlobalId,
            "tipe_ifc": dinding.is_a(),
            "nama": dinding.Name if dinding.Name else "N/A",
            "label_cad": dinding.Tag,
            "satuan_utama_hitung": "m2",
            "satuan_sumber": "METER",
            "kuantitas": {
                "panjang": round(panjang,3) if panjang else None,
                "tinggi": round(tinggi,3) if tinggi else None,
                "tebal": round(tebal,3) if tebal else None,
                "area_m2": round(area,3) if area else None,
                "volume_m3": round(volume,3) if volume else None
            }
        }
        data_terekstrak.append(objek_dinding)

    # Proses pintu
    for pintu in f.by_type("IfcDoor"):
        lebar = get_ifc_attribute(pintu, "BaseQuantities", "Width") or get_ifc_attribute(pintu, "Pset_DoorCommon", "OverallWidth")
        tinggi = get_ifc_attribute(pintu, "BaseQuantities", "Height") or get_ifc_attribute(pintu, "Pset_DoorCommon", "OverallHeight")
        area = get_ifc_attribute(pintu, "BaseQuantities", "Area") or (lebar * tinggi if lebar and tinggi else None)

        objek_pintu = {
            "guid": pintu.GlobalId,
            "tipe_ifc": pintu.is_a(),
            "nama": pintu.Name if pintu.Name else "N/A",
            "label_cad": pintu.Tag,
            "satuan_utama_hitung": "m²",
            "satuan_sumber": "METER",
            "kuantitas": {
                "lebar": round(lebar,3) if lebar else None,
                "tinggi": round(tinggi,3) if tinggi else None,
                "area_m2": round(area,3) if area else None,
                "jumlah_buah": 1
            }
        }
        data_terekstrak.append(objek_pintu)

    # Simpan hasil JSON
    os.makedirs(FOLDER_OUTPUT, exist_ok=True)
    nama_file = os.path.splitext(os.path.basename(ifc_path))[0] + "_ifc_data.json"
    path_output = os.path.join(FOLDER_OUTPUT, nama_file)
    with open(path_output, 'w') as f:
        json.dump(data_terekstrak, f, indent=2)

    print(f"Parser selesai, {len(data_terekstrak)} objek diekstrak. Output disimpan di: {path_output}")
    return path_output

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("ERROR: Tidak ada path IFC yang diberikan!")
        sys.exit(1)

    ifc_path = sys.argv[1]
    parse_ifc_file(ifc_path)
