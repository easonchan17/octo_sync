import pandas as pd
from pathlib import Path

def save_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    if df is None:
        raise ValueError("DataFrame is required and cannot be empty")

    if output_path.suffix == ".csv":
        df.to_csv(output_path, index=False)
    elif output_path.suffix == ".json":
        df.to_json(output_path, orient="records", indent=2)
    elif output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    else:
        raise ValueError(f"Unsupported output format: {output_path.suffix}")

def load_dataframe(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    if input_path.suffix == ".csv":
        return pd.read_csv(input_path)
    elif input_path.suffix == ".json":
        return pd.read_json(input_path, orient="records")
    elif input_path.suffix == ".parquet":
        return pd.read_parquet(input_path)
    else:
        raise ValueError(f"Unsupported input format: {input_path.suffix}")
