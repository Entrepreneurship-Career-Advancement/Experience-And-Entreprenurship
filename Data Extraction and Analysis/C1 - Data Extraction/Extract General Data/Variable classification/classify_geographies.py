import os
import pandas as pd

# File path
merged_path = "/Users/milanmiric/Documents/Research/Active Papers/LinkedIn Entreprenurship & Experience [Paper 2]/Data Extraction and Analysis/D - Data/D3 - Refined Datasets for Analysis/Founder_Level_Merged_Dataset.csv"

if os.path.exists(merged_path):
    print("Loading merged dataset...")
    df = pd.read_csv(merged_path)
    print(f"Loaded {len(df):,} rows.")
    
    # 1. Identify Silicon Valley (SF or SJ metros) for venture
    df['is_sv'] = df['venture_metro_area'].str.contains('san francisco|san jose', case=False, na=False)
    
    # 2. Identify Silicon Valley for prior position
    df['prior_is_sv'] = df['prior_metro_area'].str.contains('san francisco|san jose', case=False, na=False)
    
    # Save the updated dataset
    print("Saving updated dataset back to file...")
    df.to_csv(merged_path, index=False)
    print("Silicon Valley classifications successfully merged into the dataset.")
else:
    print(f"Merged dataset not found at {merged_path}.")
