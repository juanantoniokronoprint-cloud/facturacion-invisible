from app.services.whatsapp_handler import es_nif_cif_valido


def test_validates_spanish_tax_ids():
    assert es_nif_cif_valido("12345678Z")
    assert es_nif_cif_valido("X1234567A")
    assert es_nif_cif_valido("B12345678")


def test_rejects_invalid_tax_ids():
    assert not es_nif_cif_valido("")
    assert not es_nif_cif_valido("123")
    assert not es_nif_cif_valido("CLIENTE")
