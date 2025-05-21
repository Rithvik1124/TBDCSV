import pandas as pd
import tiktoken
from openai import OpenAI
import numpy as np
import os
import openai
from io import BytesIO
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.optimizers import Adam
import ast

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



#uploaded = files.upload()

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
