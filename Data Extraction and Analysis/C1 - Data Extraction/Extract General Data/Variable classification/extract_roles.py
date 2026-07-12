import os
import pandas as pd
import time

def main():
    start_time = time.time()
    base_dir = "/Users/milanmiric/Documents/Research/Active Papers/LinkedIn Entreprenurship & Experience [Paper 2]/Data Extraction and Analysis"
    positions_path = os.path.join(base_dir, "D - Data/D1 - Extracted Datasets/Founder_Full_Position_List_[US-2000-2023].csv")
    out_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(out_dir, "role_k500_frequencies.csv")
    
    print(f"Reading raw positions from {positions_path} to count unique role_k500_v3 values...")
    
    role_counts = pd.Series(dtype=int)
    chunk_idx = 0
    for chunk in pd.read_csv(positions_path, usecols=['role_k500_v3'], chunksize=500000, low_memory=False):
        chunk_idx += 1
        print(f"Processing chunk {chunk_idx}...")
        counts = chunk['role_k500_v3'].value_counts()
        role_counts = role_counts.add(counts, fill_value=0)
        
    # Sort and save
    df_counts = role_counts.reset_index()
    df_counts.columns = ['role_k500_v3', 'count']
    df_counts = df_counts.sort_values(by='count', ascending=False)
    
    df_counts.to_csv(output_path, index=False)
    print(f"Successfully extracted {len(df_counts):,} unique role_k500_v3 values and saved to {output_path}")
    print(f"Extraction completed in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    main()
