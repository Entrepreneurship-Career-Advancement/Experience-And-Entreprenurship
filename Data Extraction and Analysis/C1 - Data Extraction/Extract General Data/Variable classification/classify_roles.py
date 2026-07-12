import os
import pandas as pd
import json
import time

# ==========================================
# CONFIGURATION
# ==========================================
# Choose your platform: "gemini" or "openai"
PLATFORM = "openai" 

# Choose model:
# - For Gemini: "gemini-1.5-flash" (recommended, highly cost-effective) or "gemini-2.0-flash"
# - For OpenAI: "gpt-4o-mini" (highly cost-effective) or "gpt-4o"
MODEL_NAME = "gpt-4o-mini"

# How many of the top roles to classify
LIMIT_ROLES = 600

# Input/Output paths
INPUT_FILE = "role_k500_frequencies.csv"
OUTPUT_FILE = "classified_roles.csv"

# API Keys: Recommend setting these as environment variables, or paste them below
# os.environ["GEMINI_API_KEY"] = "YOUR_API_KEY_HERE"
# os.environ["OPENAI_API_KEY"] = "YOUR_API_KEY_HERE"
# ==========================================

CATEGORIES = ["Academic", "Business", "Creative", "Entrepreneur", "Other", "Technical"]

PROMPT_TEMPLATE = """
You are an expert research assistant classifying job roles from a professional dataset for a paper.
Classify each job role in the list below into exactly one of these 6 categories:
- Academic: roles associated with universities, research institutes, teaching, or academic research (e.g., University Professor, Researcher, Art Educator).
- Business: roles associated with corporate management, marketing, sales, accounting, finance, strategy, consulting, corporate legal, etc. (e.g., Marketing Coordinator, Business Development, Strategy Consultant, Account Executive). Note: You MUST classify accountants as Business roles.
- Creative: roles associated with design, writing, arts, media production, entertainment (e.g., Visual Designer, Media Producer, Content Writer, UX Designer, Sports Coach).
- Entrepreneur: roles associated with starting companies or founding ventures (e.g., Entrepreneur, Co-Founder, Startup Founder).
- Technical: roles associated with engineering, computer science, software development, programmers, those involved in developing applications, hard sciences (like biology and chemistry), tech architecture (e.g., Software Engineer, Solutions Architect, Design Engineer, Embedded Systems Engineer, Biologist, Chemist). Note: You MUST classify software engineers, programmers, application developers, and biology/chemistry roles as Technical.
- Other: roles that do not fit into the above categories (e.g., Food Service Staff, Administrative Coordinator, Real Estate Agent, Doctor). Note: You MUST classify doctors as Other.

For each role, you must output:
1. The role name (matching the input exactly)
2. The category (must be exactly one of: Academic, Business, Creative, Entrepreneur, Other, Technical)
3. A short description (1-2 sentences) explaining why it fits this category.

Respond ONLY with a JSON object containing a single key "classifications" whose value is a JSON array of objects, where each object has keys "role", "category", and "description".

Roles to classify:
{roles_list}
"""

def classify_with_gemini(roles_to_classify):
    try:
        import google.generativeai as genai
    except ImportError:
        print("google-generativeai is not installed. Run: pip install google-generativeai")
        return []
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please set it or define it in code.")
        
    genai.configure(api_key=api_key)
    
    # Use Structured Output JSON mode if supported
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config={"response_mime_type": "application/json"}
    )
    
    roles_str = "\n".join([f"- {r}" for r in roles_to_classify])
    prompt = PROMPT_TEMPLATE.format(roles_list=roles_str)
    
    print("Calling Gemini API...")
    response = model.generate_content(prompt)
    
    try:
        results = json.loads(response.text)
        return results
    except Exception as e:
        print(f"Error parsing JSON from Gemini: {e}")
        print("Raw response text:")
        print(response.text)
        return []

def classify_with_openai(roles_to_classify):
    try:
        from openai import OpenAI
    except ImportError:
        print("openai is not installed. Run: pip install openai", flush=True)
        return []
        
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it or define it in code.")
        
    client = OpenAI(api_key=api_key, timeout=20.0)
    
    roles_str = "\n".join([f"- {r}" for r in roles_to_classify])
    prompt = PROMPT_TEMPLATE.format(roles_list=roles_str)
    
    print("Calling OpenAI API...", flush=True)
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful research assistant."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
    except Exception as api_err:
        print(f"OpenAI API request error: {api_err}", flush=True)
        return []
    
    try:
        raw_json = json.loads(response.choices[0].message.content)
        if isinstance(raw_json, list):
            return raw_json
        elif isinstance(raw_json, dict):
            # If wrapped in a dict, check keys for list
            for v in raw_json.values():
                if isinstance(v, list):
                    return v
        return []
    except Exception as e:
        print(f"Error parsing JSON from OpenAI: {e}", flush=True)
        print("Raw response text:", flush=True)
        print(response.choices[0].message.content, flush=True)
        return []

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Input file {INPUT_FILE} not found. Please run extract_roles.py first to generate it.", flush=True)
        return
        
    df = pd.read_csv(INPUT_FILE)
    # Get top roles
    roles_to_classify = df['role_k500_v3'].dropna().head(LIMIT_ROLES).tolist()
    print(f"Loaded {len(roles_to_classify)} roles to classify.", flush=True)
    
    # Process in batches of 25 to ensure LLM prompt window and responses are manageable
    batch_size = 25
    classified_results = []
    
    for i in range(0, len(roles_to_classify), batch_size):
        batch = roles_to_classify[i:i+batch_size]
        print(f"Classifying batch {i//batch_size + 1} ({len(batch)} roles)...", flush=True)
        
        if PLATFORM.lower() == "gemini":
            batch_results = classify_with_gemini(batch)
        elif PLATFORM.lower() == "openai":
            batch_results = classify_with_openai(batch)
        else:
            print(f"Unknown platform: {PLATFORM}", flush=True)
            return
            
        classified_results.extend(batch_results)
        
        # Polite rate-limiting wait between calls
        time.sleep(1)
        
    if classified_results:
        df_out = pd.DataFrame(classified_results)
        # Ensure correct column ordering
        cols = [c for c in ['role', 'category', 'description'] if c in df_out.columns]
        df_out = df_out[cols]
        df_out.to_csv(OUTPUT_FILE, index=False)
        print(f"Successfully saved classified roles to {OUTPUT_FILE}!", flush=True)
        print(df_out.head(10), flush=True)
    else:
        print("No classification results were returned or parsed.", flush=True)

if __name__ == "__main__":
    main()
