import pandas as pd
from typing import List


def process_and_save_tsv(input_file_path, output_file_path):
    # Load the TSV file
    df = pd.read_csv(input_file_path, sep="\t")

    # Remove the '__manifest' column if it exists
    if "__manifest" in df.columns:
        df = df.drop(columns=["__manifest"])

    # Limit the size of the 'description' column to 12000 characters
    df["study_description"] = df["study_description"].apply(
        lambda x: x[:12000] if isinstance(x, str) else x
    )

    # Save the processed DataFrame to a new TSV file
    df.to_csv(output_file_path, sep="\t", index=False)


def parse_command_line_arguments(argv: List):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--src", help="path to the input file")
    parser.add_argument("--dst", help="path to the output file")
    args = parser.parse_args(argv)
    input_file_path = args.src
    output_file_path = args.dst

    return input_file_path, output_file_path


if __name__ == "__main__":
    import sys

    input_file_path, output_file_path = parse_command_line_arguments(sys.argv[1:])
    process_and_save_tsv(input_file_path, output_file_path)
