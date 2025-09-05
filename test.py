import unicodedata

def normalize_str(s):
    if s is None:
        return ""
    s = str(s)

    # Unifier tirets et espaces
    s = s.replace('\u00A0', ' ')   # espace insécable -> espace normal
    s = s.replace('–', '-')        # EN DASH -> tiret normal
    s = s.replace('—', '-')        # EM DASH -> tiret normal

    # Supprimer espaces multiples
    s = " ".join(s.split())

    # Dé-accentuation
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))

    return s.lower().strip()


def get_payment_summary_travaux(nom_classe, type_travail):
    worksheet = get_or_create_travaux_sheet()  # à adapter à ton code gspread
    records = worksheet.get_all_records()

    nom_classe_norm = normalize_str(nom_classe)
    type_travail_norm = normalize_str(type_travail)

    print(f"[Travaux] Classe demandée : {nom_classe} -> {nom_classe_norm}")
    print(f"[Travaux] Travail demandé : {type_travail} -> {type_travail_norm}")
    print(f"[Travaux] Nb lignes lues depuis Google Sheet : {len(records)}")

    payes, non_payes, total_recettes = 0, 0, 0.0
    detail = {}

    for i, row in enumerate(records, 1):
        classe_raw = row.get("NomClasse", "")
        travail_raw = row.get("TypeTravail", "")
        etudiant_raw = row.get("Etudiant", "")
        statut_raw = row.get("StatutPaiement", "")
        montant_raw = row.get("Montant", 0)

        # Normalisation
        classe = normalize_str(classe_raw)
        travail = normalize_str(travail_raw)
        etudiant = str(etudiant_raw).strip()
        statut = str(statut_raw).strip()
        montant_str = str(montant_raw).strip()

        if classe != nom_classe_norm or travail != type_travail_norm:
            # Ligne ignorée (ne correspond pas aux filtres)
            if i <= 10:  # éviter trop de logs
                print(f"[Travaux][Row {i}] Ignorée: Classe='{classe_raw}' ({classe}) | "
                      f"Travail='{travail_raw}' ({travail})")
            continue

        try:
            montant = float(montant_str.replace(",", "."))
        except ValueError:
            montant = 0.0

        detail[etudiant] = {
            "type_travail": travail_raw,
            "statut": statut,
            "montant": montant,
        }

        if normalize_str(statut) == "paye":  # "Payé" normalisé -> "paye"
            payes += 1
            total_recettes += montant
        else:
            non_payes += 1

    summary = {
        "payes": payes,
        "non_payes": non_payes,
        "total_recettes": round(total_recettes, 2),
        "detail": detail,
    }

    print(f"[Travaux] Résumé final: {summary}")
    return summary
