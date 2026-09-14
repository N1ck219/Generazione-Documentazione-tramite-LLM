import os
import json
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.extract_metadata import CCodeExtractor


def run_tests():
    test_dir = r"d:\python\TESI_Nicola_Flego\Test_code\Easy C"
    header_path = os.path.join(test_dir, "ring_buffer.h")
    c_path = os.path.join(test_dir, "ring_buffer.c")
    main_path = os.path.join(test_dir, "main.c")
    
    extractor = CCodeExtractor()

    print("==================================================")
    print("      TEST ESTRAZIONE METADATI AST (libclang)     ")
    print("==================================================\n")

    # 1. Parsing Header
    print(f"[TEST 1] Processing Header File: {header_path}")
    h_meta = extractor.extract_metadata(header_path)
    print(f"  - Enum trovate: {len(h_meta['enums'])} -> {[e['name'] for e in h_meta['enums']]}")
    print(f"  - Struct trovate: {len(h_meta['structs'])} -> {[s['name'] for s in h_meta['structs']]}")
    print(f"  - Prototipi di funzione trovati: {len(h_meta['functions'])}\n")

    # Assertions automatiche
    assert len(h_meta['enums']) > 0, "Errore: nessuna enum trovata nel file .h!"
    assert len(h_meta['structs']) > 0, "Errore: nessuna struct trovata nel file .h!"
    assert any(e['name'] == 'rb_status_t' for e in h_meta['enums']), "Enum rb_status_t non trovata!"
    assert any(s['name'] == 'RingBuffer' for s in h_meta['structs']), "Struct RingBuffer non trovata!"

    # 2. Parsing C File
    print(f"[TEST 2] Processing C Source File: {c_path}")
    c_meta = extractor.extract_metadata(c_path, include_dirs=[test_dir])
    print(f"  - Inlusioni: {[inc['included_file'] for inc in c_meta['includes']]}")
    print(f"  - Definizioni di funzioni trovate: {len(c_meta['functions'])}\n")

    # Test relazioni caller-callee
    print("[TEST 3] Verifica Relazioni Callees (Chiamate a funzioni):")
    for fn in c_meta['functions']:
        if fn['callees']:
            print(f"  * Funzione '{fn['name']}' chiama -> {fn['callees']}")
        else:
            print(f"  * Funzione '{fn['name']}' non ha chiamate uscenti.")

    # Salva l'output finale in un file di output per ispezione
    output_json_path = r"d:\python\TESI_Nicola_Flego\extracted_metadata.json"
    full_output = {
        "ring_buffer.h": h_meta,
        "ring_buffer.c": c_meta
    }
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)

    print(f"\n[ESITO TEST] Tutti i test formali sono PASSATI con successo!")
    print(f"I metadati estratti sono stati salvati in: {output_json_path}")

if __name__ == "__main__":
    run_tests()
