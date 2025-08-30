import app.models.storage_gsheets as storage

df = storage.lire_classes()
print(df[df["NomClasse"].str.strip() == "M1 GEI 2024-2025"])
