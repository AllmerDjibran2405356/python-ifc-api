import ifcopenshell
import ifcopenshell.util.unit
import os
import json
import sys
import math

# --- Konfigurasi ---
FOLDER_OUTPUT = r"C:\Materix_Engine\ai_engine_materix\engine_bim_and_ifc\data\processed"

# Daftar Tipe IFC yang TIDAK perlu diekstrak
SKIP_TYPES = [
    "IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", 
    "IfcSpace", "IfcOpeningElement", "IfcAnnotation", "IfcGrid", 
    "IfcGroup", "IfcZone", "IfcSystem", "IfcPort"
]

# =====================================================================
# HELPER: MENCARI NILAI DARI BERBAGAI KEMUNGKINAN NAMA PROPERTI
# =====================================================================
def get_property_value(element, possible_names):
    """
    Mencari nilai properti berdasarkan daftar kemungkinan nama (possible_names).
    """
    # 1. Cek di Definitions (IsDefinedBy) -> PropertySet / QuantitySet
    for rel in element.IsDefinedBy:
        if rel.is_a("IfcRelDefinesByProperties"):
            pset = rel.RelatingPropertyDefinition
            
            # A. Jika Quantity Set (Angka pasti)
            if pset.is_a("IfcElementQuantity"):
                for q in pset.Quantities:
                    if q.Name in possible_names:
                        if q.is_a("IfcQuantityLength"): return q.LengthValue
                        if q.is_a("IfcQuantityArea"): return q.AreaValue
                        if q.is_a("IfcQuantityVolume"): return q.VolumeValue
                        if q.is_a("IfcQuantityCount"): return q.CountValue
                        # Fallback untuk nilai nominal
                        if hasattr(q, "NominalValue"): return q.NominalValue.wrappedValue
            
            # B. Jika Property Set (Atribut umum)
            elif pset.is_a("IfcPropertySet"):
                for p in pset.HasProperties:
                    if p.Name in possible_names and p.is_a("IfcPropertySingleValue"):
                        if p.NominalValue:
                            return p.NominalValue.wrappedValue

    return None

# =====================================================================
# FUNGSI UTAMA
# =====================================================================
def parse_all_objects(ifc_path):
    print(f"[*] Membuka file: {ifc_path}")
    
    try:
        f = ifcopenshell.open(ifc_path)
    except Exception as e:
        print(f"[!] Gagal membuka file: {e}")
        return None

    # --- 1. Deteksi Unit Scale ---
    try:
        unit_scale = ifcopenshell.util.unit.calculate_unit_scale(f)
        print(f"[*] Unit Scale: {unit_scale}")
    except:
        unit_scale = 1.0

    def to_meter(val, power=1):
        if val is None: return 0.0
        try:
            val = float(val) # Pastikan float
            res = val * (unit_scale ** power)
            return round(res, 3)
        except:
            return 0.0

    data_output = []

    # --- 2. Ambil SEMUA Produk ---
    all_products = f.by_type("IfcProduct")
    
    print(f"[*] Total objek ditemukan: {len(all_products)}")

    for product in all_products:
        ifc_type = product.is_a()

        if ifc_type in SKIP_TYPES:
            continue

        # --- 3. Logika Ekstraksi Dimensi Universal (DIPERBAIKI) ---
        
        # A. STRATEGI UNTUK PANJANG (Length)
        # Menambahkan "Perimeter" dan "Girth" untuk objek seperti Slab/Floor
        list_panjang = ["Length", "NominalLength", "Span", "MajorDimension", "Perimeter", "Girth"]
        val_panjang = get_property_value(product, list_panjang)

        # B. STRATEGI UNTUK TINGGI (Height)
        # Untuk Slab, kadang Thickness masuk sebagai Height tergantung orientasi
        list_tinggi = ["Height", "NominalHeight", "OverallHeight", "Rise"]
        val_tinggi = get_property_value(product, list_tinggi)

        # C. STRATEGI UNTUK TEBAL (Thickness/Width)
        # Hati-hati: "Width" sering ambigu. 
        # Untuk Slab, kita prioritaskan "Thickness" dulu baru "Width".
        if ifc_type == "IfcSlab":
             list_tebal = ["Thickness", "ConstructionThickness", "NominalThickness", "Width"]
        else:
             list_tebal = ["Width", "Thickness", "ConstructionThickness", "NominalWidth"]
             
        val_tebal = get_property_value(product, list_tebal)

        # D. AREA & VOLUME
        # Menambahkan NetArea dan GrossArea
        val_area = get_property_value(product, ["NetArea", "GrossArea", "Area", "NetSideArea", "GrossSideArea"])
        val_volume = get_property_value(product, ["NetVolume", "GrossVolume", "Volume"])

        # --- 4. Konversi Satuan ---
        p_meter = to_meter(val_panjang, 1)
        t_meter = to_meter(val_tinggi, 1)
        l_meter = to_meter(val_tebal, 1)
        area_m2 = to_meter(val_area, 2)
        vol_m3  = to_meter(val_volume, 3)

        # --- 5. LOGIKA PERBAIKAN KHUSUS (Smart Correction) ---

        # KASUS SLAB/LANTAI:
        # Jika Panjang 0 (karena perimeter tidak ketemu) tapi Area ada,
        # Kita bisa estimasi Panjang = sqrt(Area) agar tidak 0, atau biarkan 0 jika user ingin akurasi.
        # Disini kita coba ambil sisi terpanjang jika Volume dan Tebal diketahui.
        if ifc_type == "IfcSlab":
            # Jika tebal terdeteksi sangat besar (lebih dari 1 meter untuk lantai), 
            # kemungkinan itu tertukar dengan Panjang/Lebar.
            if l_meter > 2.0 and p_meter < 1.0:
                # Tukar nilai: Tebal jadi Panjang, Panjang (yang 0) jadi Tebal (estimasi standar 0.15m)
                # Ini hacky, tapi membantu visualisasi jika data kotor.
                p_meter = l_meter
                l_meter = 0.15 # Default tebal plat beton jika tidak diketahui
            
            # Jika Panjang masih 0, coba hitung dari Area (akar kuadrat sbg pendekatan)
            if p_meter == 0.0 and area_m2 > 0:
                p_meter = round(math.sqrt(area_m2), 2)

        # KASUS UMUM: Kalkulasi Fallback Volume/Area
        if vol_m3 == 0.0 and p_meter > 0 and t_meter > 0 and l_meter > 0:
            vol_m3 = round(p_meter * t_meter * l_meter, 3)
        
        if area_m2 == 0.0:
            if p_meter > 0 and t_meter > 0:
                area_m2 = round(p_meter * t_meter, 3)
            elif p_meter > 0 and l_meter > 0 and ifc_type == "IfcSlab":
                # Untuk slab, kadang area = panjang x lebar
                 area_m2 = round(p_meter * l_meter, 3)

        # --- 6. Satuan Utama ---
        satuan_utama = "unit"
        if vol_m3 > 0: satuan_utama = "m3"
        elif area_m2 > 0: satuan_utama = "m2"
        elif p_meter > 0: satuan_utama = "m"

        # --- 7. Susun JSON ---
        objek_data = {
            "guid": product.GlobalId,
            "tipe_ifc": ifc_type,
            "nama": product.Name if product.Name else f"Unnamed {ifc_type}",
            "label_cad": product.Tag if product.Tag else "",
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

    # --- 8. Simpan File ---
    os.makedirs(FOLDER_OUTPUT, exist_ok=True)
    nama_file_asli = os.path.splitext(os.path.basename(ifc_path))[0]
    nama_file_json = f"{nama_file_asli}_ifc_data.json"
    path_final = os.path.join(FOLDER_OUTPUT, nama_file_json)

    try:
        with open(path_final, 'w') as f_out:
            json.dump(data_output, f_out, indent=2)
        print(f"[*] Sukses! Data tersimpan di: {path_final}")
    except Exception as e:
        print(f"[!] Gagal menulis JSON: {e}")

    return path_final

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parser.py <path_to_ifc>")
        sys.exit(1)
    
    input_ifc = sys.argv[1]
    parse_all_objects(input_ifc)