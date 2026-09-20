from pathlib import Path
import pandas as pd


from pathlib import Path
import pandas as pd


def combine_kehe_fill_rate(folder_path: str, output_path: str):
    folder = Path(folder_path)

    frames = []

    for file_path in sorted(folder.glob("*.csv")):
        # Example:
        # "KeHE Fill Rate - August 2026.csv"
        # -> "August 2026"
        month_text = file_path.stem.split(" - ")[-1]

        month_year = pd.Period(
            pd.to_datetime(month_text, format="%B %Y"),
            freq="M",
        )

        print(f"Processing {file_path.name} -> {month_year}")

        # Read everything as strings so formatting differences
        # between monthly KeHE exports don't create mixed types
        df = pd.read_csv(file_path, dtype=str)

        # Add monthly period
        df["month_year"] = month_year

        frames.append(df)

    if not frames:
        raise ValueError(f"No CSV files found in: {folder}")

    combined = pd.concat(frames, ignore_index=True)

    combined = (
        combined
        .sort_values("month_year")
        .reset_index(drop=True)
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    combined.to_parquet(output, index=False)

    print()
    print("Done!")
    print(f"Files combined: {len(frames)}")
    print(f"Rows: {len(combined):,}")
    print(
        f"Months: {combined['month_year'].min()} "
        f"-> {combined['month_year'].max()}"
    )
    print(f"Saved to: {output}")


if __name__ == "__main__":
    # CHANGE THESE TWO PATHS
    INPUT_FOLDER = "backend/data/default_org/raw/fill_rate/kehe"
    OUTPUT_FILE = "backend/data/default_org/processed/fill_rate"

    combine_kehe_fill_rate(
        folder_path=INPUT_FOLDER,
        output_path=OUTPUT_FILE,
    )