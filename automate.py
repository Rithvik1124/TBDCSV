import pandas as pd
import os
import shutil
import tiktoken
from openai import OpenAI
import numpy as np
import openai
from io import BytesIO
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.optimizers import Adam
import ast

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#_________DATA NORMALIZATION AND MERGING STUFF__________
def merge_and_apply_weights(file_root, file_hist, file_month, historical_weight=0.6, monthly_weight=0.4, output='merged_output_without_search_volume.csv'):
    # Read input files
    df_root = pd.read_csv(file_root)
    df_hist = pd.read_csv(file_hist)
    df_month = pd.read_csv(file_month)

    # Merge files
    merged = pd.merge(pd.merge(df_root, df_hist, on='Terms', how='inner'), df_month, on='Terms', how='inner')
    
    # Weighted CTR
    merged['Historical_Weighted CTR'] = merged['URL CTR_x'] * historical_weight
    merged['Monthly_Weighted CTR'] = merged['URL CTR_y'] * monthly_weight
    merged['Weighted_CTR'] = (merged['Historical_Weighted CTR'] + merged['Monthly_Weighted CTR']) / 2

    # Weighted Position
    merged['Historical_Weighted Position'] = merged['Average Position_x'] * historical_weight
    merged['Monthly_Weighted Position'] = merged['Average Position_y'] * monthly_weight
    merged['Weighted_Position'] = (merged['Historical_Weighted Position'] + merged['Monthly_Weighted Position']) / 2

    # Categorization
    merged['CTR Category'] = merged['Weighted_CTR'].apply(lambda x: 'Poor CTR' if x <= 2 else 'Good CTR')
    merged['Position Category'] = merged['Weighted_Position'].apply(
        lambda x: 'Good Position' if x <= 10 else ('Medium Position' if x <= 26 else 'Poor Position')
    )

    # Drop duplicates
    merged = merged.drop_duplicates()
    merged.to_csv(output, index=False)
    print(f"Weighted merge saved to {output}")
    return output


def add_weighted_volume(input_file, output_file='cleaned_file2.csv', hist_weight=0.6, monthly_weight=0.4, clinics=35, hist_conversion_rate=0.1119, month_conversion_rate=0):
    df = pd.read_csv(input_file)

    df['Historical_Weighted SV'] = df['Search Volume_x'] * hist_weight
    df['Monthly_Weighted SV'] = df['Search Volume_y'] * monthly_weight
    df['Weighted_SV'] = (df['Historical_Weighted SV'] + df['Monthly_Weighted SV']) / 2

    combined_conversion = hist_conversion_rate * hist_weight  + month_conversion_rate*monthly_weight
    df['Norm Volume'] = (df['Weighted_SV'] / clinics) * combined_conversion

    df['Potential Category'] = df['Norm Volume'].apply(
        lambda x: 'Bad Potential' if x < 5 else ('Medium Potential' if x <= 10 else 'Good Potential')
    )

    df.to_csv(output_file, index=False)
    print(f"Normalized volume and potential saved to {output_file}")
    return output_file


def determine_next_steps(input_file, output_file='cleaned_file3.csv'):
    df = pd.read_csv(input_file)

    def next_step(row):
        if row['CTR Category'] == 'Poor CTR' and row['Position Category'] == 'Medium Position' and row['Potential Category'] == 'Good Potential':
            return "Keyword Insertion on main page to improve Position"
        elif row['CTR Category'] == 'Good CTR' and row['Position Category'] == 'Medium Position' and row['Potential Category'] == 'Good Potential':
            return "Keyword Insertion if no"
        elif row['CTR Category'] == 'Poor CTR' and row['Position Category'] == 'Poor Position' and row['Potential Category'] == 'Good Potential':
            return "Keyword Insertion if possible"
        elif row['CTR Category'] == 'Good CTR' and row['Position Category'] == 'Poor Position' and row['Potential Category'] == 'Good Potential':
            return "Create New Pages"
        elif row['CTR Category'] == 'Good CTR' and row['Position Category'] == 'Good Position' and row['Potential Category'] == 'Good Potential':
            return "Create New Blogs"
        elif row['CTR Category'] == 'Poor CTR' and row['Position Category'] == 'Good Position' and row['Potential Category'] == 'Good Potential':
            return "Add Meta Title"
        elif row['CTR Category'] == 'Good CTR' and row['Position Category'] == 'Good Position' and row['Potential Category'] == 'Medium Potential':
            return "No Next Steps"
        elif row['CTR Category'] == 'Poor CTR' and row['Position Category'] == 'Good Position' and row['Potential Category'] == 'Medium Potential':
            return "Create new pages"
        elif row['CTR Category'] == 'Good CTR' and row['Position Category'] == 'Medium Position' and row['Potential Category'] == 'Medium Potential':
            return "Create new pages"
        elif row['CTR Category'] == 'Poor CTR' and row['Position Category'] == 'Medium Position' and row['Potential Category'] == 'Medium Potential':
            return "Add in Meta description"
        elif row['CTR Category'] == 'Good CTR' and row['Position Category'] == 'Poor Position' and row['Potential Category'] == 'Medium Potential':
            return "Add New Pages"
        elif row['CTR Category'] == 'Poor CTR' and row['Position Category'] == 'Poor Position' and row['Potential Category'] == 'Medium Potential':
            return "Create new pages"
        return "No Action Required"

    df['Next Steps'] = df.apply(next_step, axis=1)
    df.to_csv(output_file, index=False)
    print(f"Next steps saved to {output_file}")
    return output_file


def split_by_clinic_and_zip(input_file, output_dir='separate_csv_files', zip_name='clinic_location_files.zip'):
    df = pd.read_csv(input_file)

    group_col = 'Clinic Location - Landing pages'
    if group_col not in df.columns:
        group_col = 'Clinic Location - Landing pages_x'  # fallback from Colab//dont know what it mean

    grouped = df.groupby(group_col)

    os.makedirs(output_dir, exist_ok=True)

    for location, group in grouped:
        safe_location = location.replace(' ', '_').replace('/', '_')
        filepath = os.path.join(output_dir, f"{safe_location}_file.csv")
        out_df = group[['Terms']].copy()
        out_df['cluster'] = [safe_location] * len(out_df)
        out_df.to_csv(filepath, index=False)

    shutil.make_archive(zip_name.replace('.zip',''), 'zip', output_dir)
    shutil.rmtree(output_dir)
    print(f"Split and zipped to {zip_name}")

#_____________API SUMMARY STUFF_____________

def process_file(file_bytes):
    df = pd.read_csv(BytesIO(file_bytes))
    df.columns = df.columns.str.lower().str.strip()

    required_cols = {'terms', 'cluster'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Missing required columns: {required_cols}")

    top_clusters = df['cluster'].value_counts().head(2).index.tolist()

    def generate_content_structure(primary_kw, secondary_kws):
        prompt = f"""
        Create a high-converting SEO content outline for a webpage targeting the keyword: "{primary_kw}".
        Include the following:
        - SEO Optimized Title (max 60 characters)
        - Meta Description (max 155 characters)
        - URL Slug
        - H1 Heading
        - 4–6 H2 sections using keywords like: {secondary_kws}
        - 3 FAQs relevant to the topic (include answers)
        """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert SEO content strategist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

    results = []
    for cluster in top_clusters:
        cluster_df = df[df['cluster'] == cluster]
        if cluster_df.empty:
            continue
        primary_keyword = cluster_df.iloc[0]['terms']
        secondary_keywords = cluster_df['terms'].iloc[1:6].tolist()
        print(f"Generating prompt for cluster {cluster} with primary keyword: {primary_keyword}")
        try:
            structure = generate_content_structure(primary_keyword, secondary_keywords)
            results.append(f"Cluster {cluster}:\n{structure}")
        except Exception as e:
            results.append(f"Cluster {cluster} generation error: {e}")

    if not results:
        return "No clusters found or no prompts generated."

    return "\n\n".join(results)


if __name__ == "__main__":
    file1 = "F1_1.csv"
    file2 = "F2_1.csv"
    file3 = "F3_1.csv"
    merged = merge_and_apply_weights(file1, file2, file3)
    normed = add_weighted_volume(merged,hist_weight=float(input("Enter the Historical Weight:")), monthly_weight=float(input("Enter the Monthly Weight:")), clinics=float(input("Enter number of Clinics(default:35):")), hist_conversion_rate=float(input("Enter the Historical Conversion Rate(default:0.1119):")), month_conversion_rate=float(input("Enter the Monthly Conversion Rate(default:0):")) )
    final = determine_next_steps(normed)
    split_by_clinic_and_zip(final)
