import os
import re
import pandas as pd
from collections import defaultdict

# --- Configuration ---

# The 5 workflow folders
WF_FOLDERS = ["mayowf", "clevelandwf", "merckwf", "webmdwf", "wikiwf"]

# The 20 disease names as they appear in the filenames (lowercase, no spaces)
DISEASE_LIST = [
    "atopicdermatitis", "commoncold", "type2diabetes", "multiplesclerosis",
    "gerd", "cataracts", "pcos", "marfansyndrome", "asthma", "hemophilia",
    "hearingloss", "narcolepsy", "bph", "bellspalsy", "chronickidneydisease",
    "carpaltunnelsyndrome", "chlamydia", "tetanus", "acromegaly", "progeria"
]

# Mapping between the folder name and the filename suffix
SUFFIX_MAP = {
    "mayowf": "mayo",
    "clevelandwf": "cleveland",
    "merckwf": "merck",
    "webmdwf": "webmd",
    "wikiwf": "wiki"
}

# Keywords that signify a definitive, aggressive, or late-stage intervention.
# This list is used to determine the "Aggressiveness" ranking.
DEFINITIVE_INTERVENTION_KEYWORDS = [
    "surgery", "surgical", "transplant", "radiation", "dialysis",
    "fundoplication", "replacement", "ablation", "resection", "cut",
    "operative", "implant", "neuro", "graft", "laser", "artery", "steroids" # Added 'steroids' as early aggressive med
]

# --- Helper Functions ---

def analyze_workflow(text):
    """
    Counts steps and finds the position of the first definitive intervention.
    A Major Step is a line starting with a number followed by a period/paren (e.g., '1.', '2)').
    A Sub-Step is a line starting with a bullet point (e.g., '-', '*').
    """
    lines = text.strip().split('\n')
    major_steps = 0
    sub_steps = 0
    intervention_step_position = None
    current_major_step = 0
    
    # Pre-compile regex for efficiency
    major_step_re = re.compile(r"^\s*(\d+)\s*[\.\)]\s*") # Matches 1. or 1)
    sub_step_re = re.compile(r"^\s*[-*•]\s*")           # Matches -, *, or •

    for line in lines:
        # 1. Major Step Count and Position Tracking
        match_major = major_step_re.match(line)
        if match_major:
            major_steps += 1
            # Record the step number (e.g., '1' from '1.')
            current_major_step = int(match_major.group(1))

        # 2. Sub-Step Count
        if sub_step_re.match(line):
            sub_steps += 1

        # 3. Find Intervention Position
        if intervention_step_position is None:
            lower_line = line.lower()
            if any(keyword in lower_line for keyword in DEFINITIVE_INTERVENTION_KEYWORDS):
                # The intervention appeared. Record the current major step number.
                if current_major_step > 0:
                    intervention_step_position = current_major_step
                elif major_steps > 0:
                    # If found in the text immediately before the first major step (e.g., in an introductory heading)
                    # we still register it as position 1.
                    intervention_step_position = 1

    return major_steps, sub_steps, intervention_step_position

# --- Main Analysis Function ---

def structural_analysis(root_dir="./"):
    """Performs the full step count and aggression analysis across all files."""
    
    # Dictionary to store accumulated counts for averaging
    results = defaultdict(lambda: {'major': 0, 'sub': 0, 'aggression_pos_sum': 0, 'aggression_count': 0, 'count': 0})
    processed_files = 0
    
    for disease in DISEASE_LIST:
        for folder in WF_FOLDERS:
            # Construct filename based on the specified convention: wf_<disease>_<suffix>.txt
            site_suffix = SUFFIX_MAP[folder]
            filename = f"wf_{disease}_{site_suffix}.txt"
            
            file_path = os.path.join(root_dir, folder, filename)

            if not os.path.exists(file_path):
                # print(f"File not found: {file_path}")
                continue # Skip if file doesn't exist
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                major_steps, sub_steps, intervention_pos = analyze_workflow(text)
                site_key = folder
                
                results[site_key]['major'] += major_steps
                results[site_key]['sub'] += sub_steps
                results[site_key]['count'] += 1
                processed_files += 1

                # Only count intervention positions for ranking if a position was found
                if intervention_pos is not None:
                    results[site_key]['aggression_pos_sum'] += intervention_pos
                    results[site_key]['aggression_count'] += 1
                    
            except Exception:
                # print(f"Error processing {file_path}: {e}")
                continue

    # --- Generate Final Tables ---
    
    # 1. Step Count Comparison Table
    step_data = []
    for site, data in results.items():
        if data['count'] > 0:
            avg_major = data['major'] / data['count']
            avg_sub = data['sub'] / data['count']
            step_data.append({
                'Source': site.replace('wf', '').title(),
                'Avg Major Steps': f"{avg_major:.2f}",
                'Avg Sub-Steps': f"{avg_sub:.2f}",
                'Total WFs Processed': data['count']
            })
    df_steps = pd.DataFrame(step_data).sort_values(by='Avg Major Steps', ascending=False)
    
    # 2. Aggressiveness Ranking Table
    aggression_data = []
    for site, data in results.items():
        if data['aggression_count'] > 0:
            avg_aggression_pos = data['aggression_pos_sum'] / data['aggression_count']
            aggression_data.append({
                'Source': site.replace('wf', '').title(),
                'Avg Intervention Step Position': f"{avg_aggression_pos:.2f}",
                'Applicable WFs Count': data['aggression_count']
            })
    # Lower average position means *more* aggressive (intervention appears earlier)
    df_aggression = pd.DataFrame(aggression_data).sort_values(by='Avg Intervention Step Position', ascending=True)

    print("\n# 1. Workflow Step Count Comparison (Density)")
    print("This table shows the average number of steps per workflow across all 20 diseases.")
    print("A higher step count suggests greater fragmentation or detail.")
    print(df_steps.to_markdown(index=False))
    
    print("\n# 2. Most Aggressive Workflow Ranking (Sequencing Bias)")
    print("This table ranks sites by the average position (step number) of the first definitive intervention (Surgery, Radiation, Transplant, etc.).")
    print("A *lower* position value indicates a *more aggressive* workflow, as intervention is prioritized earlier.")
    print(df_aggression.to_markdown(index=False))
    
    print(f"\nTotal unique workflow files processed for analysis: {processed_files}")

if __name__ == "__main__":
    # NOTE: Ensure you run this script from the directory containing your five workflow folders.
    structural_analysis("./")