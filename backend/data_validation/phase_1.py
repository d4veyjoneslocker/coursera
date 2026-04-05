

def flag_dupes(df):
    dupes = df[df.duplicated("helper", keep=False)].sort_values("helper")

    if not dupes.empty:
        dupes.to_csv("duplicate_rows.csv", index=False)

        choice = input("Duplicates found. Continue anyway? (y/n): ")

        if choice.lower() != "y":
            raise ValueError("Pipeline stopped due to duplicates.")
        
# ADD FUNCTION TO CONFIRM THAT ALL EXPECTED MONTHS OF DATA ARE THERE FROM ALL SOURCES

def validate_first_pod_flag(df, export_path="duplicate_pods.csv"):
    """
    Ensures each pod_helper has exactly one first_pod_flag == True.
    If duplicates exist, exports them for debugging.
    """

    flagged = df[df["first_pod_flag"]]

    counts = flagged.groupby("pod_helper").size()

    duplicate_pods = counts[counts > 1]

    if not duplicate_pods.empty:

        problem_rows = df[df["pod_helper"].isin(duplicate_pods.index)]

        problem_rows.to_csv(export_path, index=False)

        raise ValueError(
            f"Duplicate POD flags detected for {len(duplicate_pods)} pods. "
            f"Problem rows exported to {export_path}."
        )