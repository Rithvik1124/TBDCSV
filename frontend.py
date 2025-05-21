import streamlit as st
import pandas as pd
import openai
import os
import automate
import clustering
import tempfile
import zipfile

openai.api_key = os.getenv("OPENAI_API_KEY")

st.title("SEO CSV Processor (Streamlit Version)")

# === Step 1 ===
st.header("Step 1: Upload Google Ads + Search Console CSVs")
step1_files = st.file_uploader("Upload exactly 2 CSV files", type="csv", accept_multiple_files=True)

if step1_files and len(step1_files) == 2:
    if st.button("Upload and Merge"):
        # Save files to temp locations
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f1, \
             tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f2:
            f1.write(step1_files[0].read())
            f2.write(step1_files[1].read())
            merged_path = automate.merge_and_categorize(f1.name, f2.name)

        st.session_state["merged_path"] = merged_path
        st.success("Files merged successfully!")

        with open(merged_path, "rb") as f:
            st.download_button("Download Merged File", data=f, file_name="merged_output.csv", mime="text/csv")

# === Step 2 ===
st.header("Step 2: Upload Merged File + Volume CSV")
step2_files = st.file_uploader("Upload merged CSV and volume CSV", type="csv", accept_multiple_files=True, key="step2")

if step2_files and len(step2_files) == 2:
    if st.button("Generate Prompts"):
        # This part is dummy data for now
        data = [
            {"term": "Dental Implants", "prompt": "Create a blog on dental implants benefits."},
            {"term": "Teeth Whitening", "prompt": "Add a meta title focused on results."}
        ]
        df = pd.DataFrame(data)
        st.write("Generated Prompts:")
        st.dataframe(df)

# === Step 3 ===
st.header("Step 3: Cluster, Split, Zip Merged CSV")
if "merged_path" in st.session_state and st.button("Cluster + Split + Zip"):
    automate.split_by_clinic_and_zip(st.session_state["merged_path"])
    zip_path = "clinic_location_files.zip"
    if os.path.exists(zip_path):
        with open(zip_path, "rb") as zf:
            st.download_button("Download Clustered ZIP", data=zf, file_name="clustered_files.zip", mime="application/zip")
        st.success("Clustered and zipped!")

# === Step 4 ===
st.header("Step 4: Select Cluster CSVs and Generate Prompts")
cluster_files = st.file_uploader("Upload Clustered CSVs", type="csv", accept_multiple_files=True, key="cluster")

if cluster_files and st.button("Generate Prompts from Cluster Files"):
    results = []
    for uploaded_file in cluster_files:
        try:
            prompt_text = clustering.process_file(uploaded_file.read())
            results.append({"term": uploaded_file.name, "prompt": prompt_text})
        except Exception as e:
            results.append({"term": uploaded_file.name, "prompt": f"Error: {str(e)}"})

    if results:
        df = pd.DataFrame(results)
        st.write("Generated Prompts:")
        st.dataframe(df)
