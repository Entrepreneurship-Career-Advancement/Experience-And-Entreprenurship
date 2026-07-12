#############################################################
## Extract Founder IDs and Founder Career Histories 
## [August 2025 REDUX - Cleaned and Optimized June 2026]
#############################################################

import os 
import pandas as pd 
from tqdm import tqdm
import time

# --- PREAMBLE: DEFINE CONSTANTS ---

# Input directory containing position parquet files
INPUT_PATH = "/Volumes/GT[Revelio]/revelio_individual_position/"

# Target output folder for refined data
OUTPUT_PATH = "/Users/milanmiric/Documents/Research/Active Papers/LinkedIn Entreprenurship & Experience [Paper 2]/Data Extraction and Analysis/D - Data/D1 - Extracted Datasets"

# Define output filenames in refined folder
FOUNDER_POS_FILE = os.path.join(OUTPUT_PATH, "Founder_Position_List_[US-2000-2023].csv")
LOG_DIR = os.path.join(OUTPUT_PATH, "log files")
PROGRESS_LOG = os.path.join(LOG_DIR, "E1a_progress.log")

# Define the list of columns to keep
RELEVANT_COLS = [
    'user_id', 'position_id', 'company_linkedin_url', 'startdate', 'enddate', 
    'metro_area','msa', 'country', 'title_raw', 
    'job_category_v2', 'role_k50_v3', 'role_k150_v3', 
    'role_k500_v3', 'role_k1000_v3', 'role_k1500_v3',
    'role_k5000_v3','role_k10000_v3','role_k15000_v3', 
    'start_salary', 'end_salary', 'salary', 'total_compensation', 'additional_compensation', 
    'seniority', 'position_number', 
    'rcid', 'rics_k50', 'rics_k200', 'rics_k400',
    'onet_code', 'onet_title', 'ticker', 
    'naics_code', 'naics_description', 'ultimate_parent_factset_id'
]

# Ensure the output directory and log directory exist before writing files
os.makedirs(OUTPUT_PATH, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


###########################################################
## Helper Functions
###########################################################

def read_parquet_with_retries(file_path, columns=None, max_retries=3, delay=5):
    """
    Reads a parquet file with automatic retry logic upon disconnections or OSError.
    """
    # Check if the input directory exists (disk dismount check)
    if not os.path.exists(os.path.dirname(file_path)):
        print(f"\nError: The input directory {os.path.dirname(file_path)} does not exist. The disk may have dismounted.")
        print("Please check the drive connection, remount it, and run the script again to resume.")
        os._exit(1)

    for attempt in range(max_retries):
        try:
            return pd.read_parquet(file_path, columns=columns)
        except OSError as e:
            print(f"\nWarning: OSError reading {os.path.basename(file_path)} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                # Log error to file
                log_file = os.path.join(LOG_DIR, "data_extraction_errors.log")
                with open(log_file, "a") as f:
                    f.write(f"Failed to read {file_path} after {max_retries} attempts. Error: {e}\n")
                print(f"Skipping {os.path.basename(file_path)} due to persistent read error.")
                return None
        except Exception as e:
            print(f"\nError reading {os.path.basename(file_path)}: {e}")
            log_file = os.path.join(LOG_DIR, "data_extraction_errors.log")
            with open(log_file, "a") as f:
                f.write(f"Failed to read {file_path}. Error: {e}\n")
            return None


###########################################################
## Part 1: Construct Sample of Founders
###########################################################

files = sorted([f for f in os.listdir(INPUT_PATH) if f.endswith(".parquet")])

# Resume checkpointing check
processed_files = set()
if os.path.exists(PROGRESS_LOG) and os.path.exists(FOUNDER_POS_FILE):
    with open(PROGRESS_LOG, "r") as log:
        processed_files = set(line.strip() for line in log if line.strip())
    print(f"Resuming run. Found {len(processed_files)} already processed files in progress log.")
    files = [f for f in files if f not in processed_files]
    is_first_file = False
else:
    # Clear any stale progress log
    if os.path.exists(PROGRESS_LOG):
        os.remove(PROGRESS_LOG)
    is_first_file = True

for file in tqdm(files, desc="Extract Profiles of Founders"):
    file_path = os.path.join(INPUT_PATH, file)
    
    # Resilient read
    data = read_parquet_with_retries(file_path, columns=RELEVANT_COLS)
    if data is None:
        continue
    
    # Optimization 1: Pre-filter country and title first to avoid expensive date parsing on millions of rows
    is_candidate = (
        (data['country'] == 'United States') &
        (data['title_raw'].str.contains("founder|founding|entrepreneur", case=False, na=False))
    )
    candidates = data.loc[is_candidate].copy()

    if not candidates.empty:
        # Optimization 2: Parse dates only for candidates and specify explicit date format for speed
        candidates['startyear'] = pd.to_datetime(candidates['startdate'], format='%Y-%m-%d', errors='coerce').dt.year
        candidates['endyear'] = pd.to_datetime(candidates['enddate'], format='%Y-%m-%d', errors='coerce').dt.year
        
        # Apply year filters
        is_founder = (
            (candidates['startyear'] >= 2000) & 
            (candidates['endyear'] <= 2023)
        )
        Founders = candidates.loc[is_founder].copy()

        # If founders are found, save them
        if not Founders.empty:
            Founders['Found_Pos'] = 1
            output_chunk = Founders[['user_id', 'position_id', 'Found_Pos']]
            
            # Append to CSV, handling the header on the first write
            if is_first_file:
                output_chunk.to_csv(FOUNDER_POS_FILE, header=True, mode='w', index=False)
                is_first_file = False
            else: 
                output_chunk.to_csv(FOUNDER_POS_FILE, header=False, mode='a', index=False)

    # Log successful file completion
    with open(PROGRESS_LOG, "a") as log:
        log.write(file + "\n")

# Complete successfully - clean progress log
if os.path.exists(PROGRESS_LOG):
    os.remove(PROGRESS_LOG)
print("\nProcess Complete successfully.")
