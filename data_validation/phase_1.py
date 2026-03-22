

def flag_dupes(df):
    dupes = df[df.duplicated("helper", keep=False)].sort_values("helper")

    if not dupes.empty:
        dupes.to_csv("duplicate_rows.csv", index=False)

        choice = input("Duplicates found. Continue anyway? (y/n): ")

        if choice.lower() != "y":
            raise ValueError("Pipeline stopped due to duplicates.")
        
# ADD FUNCTION TO CONFIRM THAT ALL EXPECTED MONTHS OF DATA ARE THERE FROM ALL SOURCES