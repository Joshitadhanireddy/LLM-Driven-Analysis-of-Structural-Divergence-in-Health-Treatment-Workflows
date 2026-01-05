import os
import glob
import re
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

WF_FOLDERS = ["mayowf", "clevelandwf", "merckwf", "webmdwf", "wikiwf"]

def load_workflows(root):
    data = {}
    for folder in WF_FOLDERS:
        path = os.path.join(root, folder)
        if not os.path.isdir(path):
            continue
        
        for f in glob.glob(os.path.join(path, "*.txt")):
            text = open(f, encoding="utf-8").read()
            # disease name is between wf_ and _mayo.txt
            disease = re.findall(r"wf_(.*?)_", os.path.basename(f))[0]
            if disease not in data:
                data[disease] = {}
            data[disease][folder] = text
    return data

def preprocess(text):
    # remove numbering like 1. , 2.3 etc
    text = re.sub(r"\d+[\.\)]", " ", text)
    text = text.lower()
    return text

def compute_similarity(workflows):
    sites = list(workflows.keys())
    texts = [preprocess(workflows[s]) for s in sites]

    vect = TfidfVectorizer(stop_words="english")
    tfidf = vect.fit_transform(texts)

    sim = cosine_similarity(tfidf)
    return sites, sim

def find_unique_terms(workflows):
    out = {}
    all_text = {site: preprocess(workflows[site]) for site in workflows}
    vect = TfidfVectorizer(stop_words="english", max_features=40)
    tfidf = vect.fit_transform(all_text.values())
    terms = vect.get_feature_names_out()

    for i, site in enumerate(all_text):
        row = tfidf[i].toarray()[0]
        top_idxs = row.argsort()[-10:][::-1]  # top 10 unique terms
        out[site] = [terms[j] for j in top_idxs]
    return out

def analyze(root):
    wf_data = load_workflows(root)
    report = {}

    for disease, workflows in wf_data.items():
        if len(workflows) < 2:
            continue
        
        sites, sim = compute_similarity(workflows)
        uniq = find_unique_terms(workflows)

        report[disease] = {
            "sites": sites,
            "similarity_matrix": sim.tolist(),
            "unique_terms": uniq
        }
    
    return report

def save_report(report, outpath):
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    REPORT = analyze("./")  
    save_report(REPORT, "workflow_analysis.json")
    print("Saved workflow_analysis.json")
