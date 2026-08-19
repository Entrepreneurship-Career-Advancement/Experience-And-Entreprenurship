import os
import pandas as pd
import numpy as np
import re
import tldextract
from urllib.parse import urlparse

# Define paths
pb_dir = "/Users/milanmiric/Documents/Research/Active Papers/LinkedIn Entreprenurship & Experience [Paper 2]/Data Extraction and Analysis/C1 - Data Extraction/Extract Pitchbook Data"
c2_dir = "/Users/milanmiric/Documents/Research/Active Papers/LinkedIn Entreprenurship & Experience [Paper 2]/Data Extraction and Analysis/C2 - Dataset Construction"
d2_dir = "/Users/milanmiric/Documents/Research/Active Papers/LinkedIn Entreprenurship & Experience [Paper 2]/Data Extraction and Analysis/D - Data/D2 - Datasets for Matching"

rcid_map_path = os.path.join(pb_dir, "rcid_linkedin_url_map.csv")
pb_names_path = os.path.join(pb_dir, "pb_company_names_websites.csv")
pb_all_firms_path = os.path.join(pb_dir, "PB_Data_All_Firms.csv")
rcid_pb_existing_path = os.path.join(pb_dir, "RCID_PB_Match.csv")

# Outputs
crosswalk_path = os.path.join(c2_dir, "revelio_pb_crosswalk.csv")
matched_dataset_path = os.path.join(c2_dir, "matched_company_level_dataset.csv")

print("Checking input files...")
for p in [rcid_map_path, pb_names_path, pb_all_firms_path, rcid_pb_existing_path]:
    if not os.path.exists(p):
        print(f"Error: Required file {p} does not exist!")
        exit(1)

print("Loading datasets...")
df_rcid_url = pd.read_csv(rcid_map_path)
df_pb = pd.read_csv(pb_names_path)
df_existing = pd.read_csv(rcid_pb_existing_path)
df_pb_covariates = pd.read_csv(pb_all_firms_path)

print(f"Loaded {len(df_rcid_url):,} LinkedIn RCID-URL pairs.")
print(f"Loaded {len(df_pb):,} PitchBook company names & websites.")
print(f"Loaded {len(df_existing):,} existing matches.")
print(f"Loaded {len(df_pb_covariates):,} PitchBook firm covariates records.")

# --- Mitigation 1 & 2: Define generic stop words and suffixes ---
suffixes = [
    r'\binc\b', r'\bllc\b', r'\bcorp\b', r'\bco\b', r'\bltd\b', r'\bgmbh\b',
    r'\bcorporation\b', r'\bincorporated\b', r'\blimited\b', r'\bcompany\b',
    r'\bgroup\b', r'\bholdings\b', r'\bsolutions\b', r'\btechnologies\b',
    r'\bservices\b', r'\bpartner\b', r'\bpartners\b', r'\bllp\b', r'\bplc\b',
    r'\bs\.a\.\b', r'\bsa\b', r'\ba\.g\.\b', r'\bag\b'
]
suffix_re = re.compile('|'.join(suffixes), re.IGNORECASE)

GENERIC_STOP_WORDS = {
    'the', 'and', 'for', 'group', 'partners', 'solutions', 'services', 
    'capital', 'global', 'holding', 'holdings', 'ventures', 'technologies',
    'associates', 'consulting', 'management', 'advisors', 'enterprise',
    'inc', 'llc', 'ltd', 'corp', 'co', 'gmbh', 'sa', 'ag', 'company', 'school',
    'university', 'college', 'institute', 'academy', 'association', 'foundation'
}

MULTITENANT_DOMAINS = {
    'wordpress', 'github', 'githubusercontent', 'shopify', 'squarespace', 
    'wixsite', 'blogspot', 'weebly', 'herokuapp', 'substack', 'medium', 
    'webflow', 'gitbook', 'firebaseapp', 'netlify', 'render', 's3',
    'google', 'amazon', 'facebook', 'instagram', 'twitter', 'linkedin', 
    'youtube', 'apple', 'microsoft', 'wix', 'godaddy', 'bluehost', 'hostgator'
}

# --- Cleaning functions ---
def extract_linkedin_handle(url):
    if pd.isna(url):
        return ""
    url = str(url).lower().strip()
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    url = url.rstrip('/')
    if "linkedin.com/company/" in url:
        parts = url.split("linkedin.com/company/")
        if len(parts) > 1:
            return parts[1].split('/')[0]
    elif "linkedin.com/school/" in url:
        parts = url.split("linkedin.com/school/")
        if len(parts) > 1:
            return parts[1].split('/')[0]
    elif "linkedin.com/edu/" in url:
        parts = url.split("linkedin.com/edu/")
        if len(parts) > 1:
            return parts[1].split('/')[0]
    if '/' in url:
        return url.split('/')[-1]
    return url

def clean_company_name_secure(name):
    if pd.isna(name):
        return ""
    name = str(name).lower().strip()
    # Remove suffixes
    name = suffix_re.sub('', name)
    # Strip non-alphanumeric characters
    name = re.sub(r'[^a-z0-9]', '', name)
    # Strict length constraint
    if len(name) < 3:
        return ""
    # Stop words constraint
    if name in GENERIC_STOP_WORDS:
        return ""
    return name

def extract_website_sld_secure(url):
    if pd.isna(url):
        return ""
    url = str(url).lower().strip()
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    try:
        # Use tldextract to split subdomain and domain accurately
        ext = tldextract.extract(url)
        domain = ext.domain
        
        # Blacklist domain-hosting providers or huge platform subdomains
        if domain in MULTITENANT_DOMAINS:
            return ""
            
        clean_sld = re.sub(r'[^a-z0-9]', '', domain)
        if len(clean_sld) < 3 or clean_sld in GENERIC_STOP_WORDS:
            return ""
        return clean_sld
    except Exception:
        pass
    return ""

print("\nProcessing and cleaning handles and PitchBook names...")
df_rcid_url['handle'] = df_rcid_url['company_linkedin_url'].apply(extract_linkedin_handle)
df_rcid_url['clean_handle'] = df_rcid_url['handle'].str.replace(r'[^a-z0-9]', '', regex=True)

# Keep only handles that meet length and non-generic stop word checks
df_rcid_url['is_valid_handle'] = df_rcid_url['clean_handle'].apply(
    lambda h: len(h) >= 3 and h not in GENERIC_STOP_WORDS
)
df_rcid_url_valid = df_rcid_url[df_rcid_url['is_valid_handle']].copy()
print(f"Valid clean handles after length and stop word filtering: {len(df_rcid_url_valid):,} (out of {len(df_rcid_url):,})")

df_pb['clean_name'] = df_pb['COMPANYNAME'].apply(clean_company_name_secure)
df_pb['clean_sld'] = df_pb['WEBSITE'].apply(extract_website_sld_secure)

# Lookups
print("Building lookup dictionaries...")
pb_name_map = df_pb[df_pb['clean_name'] != ""].drop_duplicates(subset=['clean_name'])
pb_name_dict = dict(zip(pb_name_map['clean_name'], pb_name_map['COMPANYID']))

pb_sld_map = df_pb[df_pb['clean_sld'] != ""].drop_duplicates(subset=['clean_sld'])
pb_sld_dict = dict(zip(pb_sld_map['clean_sld'], pb_sld_map['COMPANYID']))

# Run match pipeline
print("Matching clean handles against PitchBook names and domains...")
results = []
for h in df_rcid_url_valid['clean_handle']:
    name_pbid = pb_name_dict.get(h)
    sld_pbid = pb_sld_dict.get(h)
    
    if name_pbid and sld_pbid and (name_pbid == sld_pbid):
        results.append((name_pbid, "Double Match (Name + Domain)"))
    elif name_pbid:
        results.append((name_pbid, "Name Match"))
    elif sld_pbid:
        results.append((sld_pbid, "Domain Match"))
    else:
        results.append((None, None))

df_rcid_url_valid['new_PBID'] = [r[0] for r in results]
df_rcid_url_valid['match_method'] = [r[1] for r in results]

matched_df = df_rcid_url_valid.dropna(subset=['new_PBID']).copy()
print(f"Total newly matched companies: {len(matched_df):,}")
print(f"Matches via Double Match: {sum(matched_df['match_method'] == 'Double Match (Name + Domain)'):,}")
print(f"Matches via Name Match: {sum(matched_df['match_method'] == 'Name Match'):,}")
print(f"Matches via Domain Match: {sum(matched_df['match_method'] == 'Domain Match'):,}")

# --- Combine with Existing Matches ---
print("\nCombining with existing matches...")
# Prepare existing matches
df_existing_clean = df_existing.dropna(subset=['PBID'])[['rcid', 'company', 'PBID']].copy()
df_existing_clean['match_method'] = 'Existing_Match'
df_existing_clean['source'] = 'Existing'

# Prepare new matches
df_new_map = matched_df[['rcid', 'handle', 'new_PBID', 'match_method']].rename(
    columns={'handle': 'company', 'new_PBID': 'PBID'}
)
df_new_map['source'] = 'New_Algorithm'

# Combine by prioritizing existing matches if there's any conflict, keeping unique rcid
df_combined = pd.concat([df_existing_clean, df_new_map])
df_combined = df_combined.drop_duplicates(subset=['rcid'], keep='first')

print(f"Combined crosswalk dataset rows: {len(df_combined):,}")
print("Combined matches by method:")
print(df_combined['match_method'].value_counts())

# Save crosswalk
os.makedirs(c2_dir, exist_ok=True)
df_combined.to_csv(crosswalk_path, index=False)
print(f"Saved crosswalk file to: {crosswalk_path}")

# --- Build Matched Company-Level Dataset ---
print("\nBuilding matched company-level dataset...")
# Clean covariates database
df_pb_covariates = df_pb_covariates.dropna(subset=['COMPANYID'])
df_pb_covariates['COMPANYID'] = df_pb_covariates['COMPANYID'].astype(str)
df_combined['PBID'] = df_combined['PBID'].astype(str)

df_matched_covariates = pd.merge(
    df_combined[['rcid', 'PBID', 'match_method', 'source']], 
    df_pb_covariates, 
    left_on='PBID', 
    right_on='COMPANYID', 
    how='inner'
)
# Collapse or drop duplicated company ID columns if any
df_matched_covariates = df_matched_covariates.drop(columns=['COMPANYID'])

df_matched_covariates.to_csv(matched_dataset_path, index=False)
print(f"Saved matched company level dataset to: {matched_dataset_path}")
print(f"Matched company level dataset contains {len(df_matched_covariates):,} records with covariates.")
print("Process Complete.")
