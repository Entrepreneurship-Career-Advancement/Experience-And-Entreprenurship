#############################################################
## Extract Founder Educational Histories
## [Cleaned and Optimized June 2026]
#############################################################

import os 
import pandas as pd 
from tqdm import tqdm
import time

# --- PREAMBLE: DEFINE CONSTANTS ---

# Input directory containing education parquet files
INPUT_PATH = "/Volumes/GT[Revelio]/revelio_individual_user_education/"

# Target output folder for refined data
OUTPUT_PATH = "/Users/milanmiric/Documents/Research/Active Papers/LinkedIn Entreprenurship & Experience [Paper 2]/Data Extraction and Analysis/D - Data/D1 - Extracted Datasets"

# Define output and input filenames
FOUNDER_POS_FILE = os.path.join(OUTPUT_PATH, "Founder_Position_List_[US-2000-2023].csv")
FOUNDER_EDU_FILE = os.path.join(OUTPUT_PATH, "Founder_Education_List_[US-2000-2023].csv")
LOG_DIR = os.path.join(OUTPUT_PATH, "log files")
PROGRESS_LOG = os.path.join(LOG_DIR, "E3_progress.log")

# Define the list of columns to keep from education parquet files
RELEVANT_COLS = [
    'user_id', 'university_raw', 'university_name', 'rsid', 
    'education_number', 'startdate', 'enddate', 'degree', 
    'field', 'degree_raw', 'field_raw', 'university_country', 
    'university_location', 'ultimate_parent_school_name', 
    'ultimate_parent_rsid', 'description'
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
            # If file not found (errno 2), the disk has dismounted or path is gone. Exit immediately.
            if e.errno == 2 or "No such file or directory" in str(e):
                print(f"\nError: File not found. The disk has likely dismounted.")
                print("Please remount the drive and run the script again to resume from the last logged file.")
                os._exit(1)
            
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                # Log error to file
                log_file = os.path.join(LOG_DIR, "education_extraction_errors.log")
                with open(log_file, "a") as f:
                    f.write(f"Failed to read {file_path} after {max_retries} attempts. Error: {e}\n")
                print(f"Skipping {os.path.basename(file_path)} due to persistent read error.")
                return None
        except Exception as e:
            print(f"\nError reading {os.path.basename(file_path)}: {e}")
            log_file = os.path.join(LOG_DIR, "education_extraction_errors.log")
            with open(log_file, "a") as f:
                f.write(f"Failed to read {file_path}. Error: {e}\n")
            return None


###########################################################
## Part 3: Construct Educational Histories of Founders 
###########################################################

files = sorted([f for f in os.listdir(INPUT_PATH) if f.endswith(".parquet")])

# Load founder user IDs from E1a output list
try:
    Founders = pd.read_csv(FOUNDER_POS_FILE)
    founder_user_ids = Founders['user_id'].drop_duplicates()
    print(f"Loaded {len(founder_user_ids)} unique founder user IDs from {FOUNDER_POS_FILE}")
except FileNotFoundError:
    print(f"Error: Founder position list file not found at {FOUNDER_POS_FILE}. Please run E1a first.")
    exit(1)

# Check if progress log exists to resume checkpoint
processed_files = set()
if os.path.exists(PROGRESS_LOG) and os.path.exists(FOUNDER_EDU_FILE):
    with open(PROGRESS_LOG, "r") as log:
        processed_files = set(line.strip() for line in log if line.strip())
    print(f"Resuming run. Found {len(processed_files)} already processed files in progress log.")
    print(f"To start a fresh run, delete the progress log at: {PROGRESS_LOG}")
    files = [f for f in files if f not in processed_files]
    is_first_file = False
else:
    # Fresh run: delete log if it exists and set is_first_file = True
    if os.path.exists(PROGRESS_LOG):
        os.remove(PROGRESS_LOG)
        print(f"Deleted old progress log to start fresh: {PROGRESS_LOG}")
    is_first_file = True

# --- COOL DOWN SETTINGS ---
# To prevent external drive overheating and dismounting, sleep periodically
SLEEP_INTERVAL_FILES = 50  # Sleep after this many files
SLEEP_DURATION_SECONDS = 15  # Sleep duration in seconds
files_processed_this_run = 0

for file in tqdm(files, desc="Extract Educational Histories of Founder Sample"):
    # Cool down period to prevent drive overheating
    if files_processed_this_run > 0 and files_processed_this_run % SLEEP_INTERVAL_FILES == 0:
        print(f"\nCooling down external drive for {SLEEP_DURATION_SECONDS} seconds...")
        time.sleep(SLEEP_DURATION_SECONDS)

    file_path = os.path.join(INPUT_PATH, file)
    
    # Resilient read
    data = read_parquet_with_retries(file_path, columns=RELEVANT_COLS)
    if data is None:
        continue
    
    # Filter to only keep education records of founders in our sample
    founder_edu_chunk = data[data['user_id'].isin(founder_user_ids)].copy()
    
    # If matching records found, save them
    if not founder_edu_chunk.empty:
        if is_first_file:
            founder_edu_chunk.to_csv(FOUNDER_EDU_FILE, header=True, mode='w', index=False)
            is_first_file = False
        else: 
            founder_edu_chunk.to_csv(FOUNDER_EDU_FILE, header=False, mode='a', index=False)

    # Log successful file completion
    with open(PROGRESS_LOG, "a") as log:
        log.write(file + "\n")
    
    files_processed_this_run += 1

# Clean progress log upon successful completion
if os.path.exists(PROGRESS_LOG):
    os.remove(PROGRESS_LOG)
print("\nProcess Complete successfully.")
