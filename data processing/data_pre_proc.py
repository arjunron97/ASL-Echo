import os
import pandas as pd

# Define paths
base_dir = r"C:\Users\kaush\Music\asl\MS-ASL\asl_landmarks_output"
datasets = ["train", "test", "validate"]

for dataset in datasets:
    # Construct paths
    input_dir = os.path.join(base_dir, f"{dataset}_dataset")
    output_path = os.path.join(base_dir, f"{dataset}.csv")

    print(f"\nProcessing {dataset.upper()} dataset:")
    print(f"Input directory: {input_dir}")

    # Check if directory exists
    if not os.path.exists(input_dir):
        print(f"❌ Directory not found: {input_dir}")
        continue

    # Get CSV files
    csv_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.csv')]

    if not csv_files:
        print(f"❌ No CSV files found in {input_dir}")
        continue

    print(f"Found {len(csv_files)} CSV files")

    # Process files for this dataset
    try:
        merged_df = None
        for i, filename in enumerate(csv_files):
            file_path = os.path.join(input_dir, filename)
            print(f"Reading {filename}...", end=" ")

            # Read with header for first file, skip for others
            # header = 0 if i == 0 else None
            # df = pd.read_csv(file_path, header=header)
            df = pd.read_csv(file_path)


            if i == 0:  # First file
                merged_df = df
                original_columns = df.columns.tolist()
            else:
                # Check column consistency
                if df.columns.tolist() != original_columns:
                    print(f"⚠️ Column mismatch in {filename}. Skipping.")
                    continue

                # Merge data
                merged_df = pd.concat([merged_df, df], ignore_index=True)

            print("✅ Success")

        # Save merged data
        if merged_df is not None:
            merged_df.to_csv(output_path, index=False)
            print(f"\nSaved {len(merged_df)} entries to {output_path}")
        else:
            print(f"❌ No valid data merged for {dataset}")

    except Exception as e:
        print(f"\n⚠️ Error processing {dataset}: {str(e)}")

print("\nMerge process completed!")