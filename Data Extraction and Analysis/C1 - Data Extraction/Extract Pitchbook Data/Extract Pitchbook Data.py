#############################################################
## Extract Pitchbook Data for Founders
## [Adapted for Paper 2 - LinkedIn Entrepreneurship & Experience]
#############################################################

import os
import pandas as pd
import numpy as np
import shutil

# --- PREAMBLE: DEFINE CONSTANTS ---

# Input directories
INPUT_DIR = "/Users/milanmiric/Documents/Research/Active Papers/LinkedIn Gender [Paper 3][ReEntry]/Data"
PB_COMPANY_FILE = os.path.join(INPUT_DIR, "Pitchbook-202402/PB_COMPANY_202402122037.csv")
PB_DEAL_FILE = os.path.join(INPUT_DIR, "Pitchbook-202402/PB_DEAL_202402131235.csv")

# Local directories
CURRENT_DIR = "/Users/milanmiric/Documents/Research/Active Papers/LinkedIn Entreprenurship & Experience [Paper 2]/Data Extraction and Analysis/C1 - Data Extraction/Extract Pitchbook Data"
MATCHING_FILE_SOURCE = os.path.join(CURRENT_DIR, "RCID_PB_Match.csv")

# Output files
PB_ALL_FIRMS_OUTPUT = os.path.join(CURRENT_DIR, "PB_Data_All_Firms.csv")
PB_MATCHED_OUTPUT = os.path.join(CURRENT_DIR, "Matched_PB_Founded_Venture_Data.csv")

# Also save to Paper 2's Datasets for Matching for integration
D2_DIR = "/Users/milanmiric/Documents/Research/Active Papers/LinkedIn Entreprenurship & Experience [Paper 2]/Data Extraction and Analysis/D - Data/D2 - Datasets for Matching"
D2_PB_MATCHED_OUTPUT = os.path.join(D2_DIR, "Matched_PB_Founded_Venture_Data.csv")

# Create output folders if they don't exist
os.makedirs(CURRENT_DIR, exist_ok=True)
os.makedirs(D2_DIR, exist_ok=True)


###########################################################
## Part 1: Process PB Company Data
###########################################################

print("\nProcessing PB Company data...")
# Optimization: Loading only the required columns reduces memory usage by ~90% on this 10GB file
cols_company = ['COMPANYID', 'TOTALRAISED', 'YEARFOUNDED', 'EMPLOYEES', 'REVENUE', 'BUSINESSSTATUS', 'OWNERSHIPSTATUS']

try:
    pb_company = pd.read_csv(PB_COMPANY_FILE, usecols=cols_company, low_memory=False)
except FileNotFoundError:
    print(f"Error: Company file not found at {PB_COMPANY_FILE}")
    exit(1)

# Define outcome flags
pb_company['Bankrupt'] = np.where(
    (pb_company['BUSINESSSTATUS'] == 'Out of Business') |
    (pb_company['BUSINESSSTATUS'] == 'Bankruptcy: Liquidation') |
    (pb_company['BUSINESSSTATUS'] == 'Bankruptcy: Admin/Reorg'), 1, 0
)

pb_company['Acquired_IPO'] = np.where(
    (pb_company['OWNERSHIPSTATUS'] == 'Acquired/Merged (Operating Subsidiary)') |
    (pb_company['OWNERSHIPSTATUS'] == 'Acquired/Merged') |
    (pb_company['OWNERSHIPSTATUS'] == 'Publicly Held') |
    (pb_company['OWNERSHIPSTATUS'] == 'In IPO Registration'), 1, 0
)

# Collapse by COMPANYID (taking the max of the characteristics)
print("Collapsing company variables by COMPANYID...")
pb_company_collapsed = pb_company.groupby('COMPANYID').agg({
    'TOTALRAISED': 'max',
    'YEARFOUNDED': 'max',
    'EMPLOYEES': 'max',
    'REVENUE': 'max',
    'Bankrupt': 'max',
    'Acquired_IPO': 'max'
}).reset_index()


###########################################################
## Part 2: Process PB Deal Data
###########################################################

print("\nProcessing PB Deal data...")
# Optimization: Loading only the required columns from the 4.8GB deal file
cols_deal = ['COMPANYID', 'DEALSIZE', 'DEALTYPE2']

try:
    pb_deal = pd.read_csv(PB_DEAL_FILE, usecols=cols_deal, encoding='latin-1', low_memory=False)
except FileNotFoundError:
    print(f"Error: Deal file not found at {PB_DEAL_FILE}")
    exit(1)

# Create Series A Flag
pb_deal['SeriesA'] = np.where((pb_deal['DEALTYPE2'] == 'Series A'), 1, 0)

# Collapse by COMPANYID (taking the max of the characteristics)
print("Collapsing deal variables by COMPANYID...")
pb_deal_collapsed = pb_deal.groupby('COMPANYID').agg({
    'DEALSIZE': 'max',
    'SeriesA': 'max'
}).reset_index()


###########################################################
## Part 3: Combine all PB Data and Save
###########################################################

print("\nMerging company and deal data for all PB firms...")
pb_all_firms = pd.merge(pb_company_collapsed, pb_deal_collapsed, on='COMPANYID', how='outer')

print(f"Saving Pitchbook Data for all firms to: {PB_ALL_FIRMS_OUTPUT}")
pb_all_firms.to_csv(PB_ALL_FIRMS_OUTPUT, index=False)


###########################################################
## Part 4: Filter and Collapse to Matched Ventures (rcid level)
###########################################################

print("\nLoading and cleaning matching data...")
if os.path.exists(MATCHING_FILE_SOURCE):
    matching = pd.read_csv(MATCHING_FILE_SOURCE)
    
    # Filter rows that have both RCID and PBID
    matching = matching.dropna(subset=['rcid', 'PBID'])
    matching['PBID'] = matching['PBID'].astype(str)
    matching = matching[['rcid', 'PBID']].drop_duplicates()
    
    # Merge PB Data with matching on PBID
    print("Merging Pitchbook data with matching links...")
    pb_matched = pd.merge(pb_all_firms, matching, left_on='COMPANYID', right_on='PBID', how='inner')
    
    # Collapse variables at the LinkedIn rcid level
    print("Collapsing variables to rcid level...")
    pb_matched_collapsed = pb_matched.groupby('rcid').agg({
        'TOTALRAISED': 'max',
        'YEARFOUNDED': 'max',
        'EMPLOYEES': 'max',
        'REVENUE': 'max',
        'Bankrupt': 'max',
        'Acquired_IPO': 'max',
        'DEALSIZE': 'max',
        'SeriesA': 'max'
    }).reset_index()
    
    print(f"Saving Matched Founded Venture Data to: {PB_MATCHED_OUTPUT}")
    pb_matched_collapsed.to_csv(PB_MATCHED_OUTPUT, index=False)
    
    print(f"Saving copy of Matched Founded Venture Data to: {D2_PB_MATCHED_OUTPUT}")
    pb_matched_collapsed.to_csv(D2_PB_MATCHED_OUTPUT, index=False)
else:
    print(f"Error: Matching file not found at {MATCHING_FILE_SOURCE}")

print("\nProcess Complete.")
