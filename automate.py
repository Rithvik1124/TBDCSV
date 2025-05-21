import pandas as pd
import os
import shutil

def merge_and_categorize(file1, file2,output_path="clean_file.csv"):
    
    google_ads_df = pd.read_csv(file1)
    search_console_df = pd.read_csv(file2)
    merged_df = pd.merge(google_ads_df, search_console_df, on='Terms', how='inner')
    
    merged_df['CTR Category'] = merged_df['URL CTR'].apply(lambda x: 'Poor CTR' if x <= 2 else 'Good CTR')
    merged_df['Position Category'] = merged_df['Average Position'].apply(
        lambda x: 'Good Position' if x <= 10 else ('Medium Position' if x <= 26 else 'Poor Position')
    )
    merged_df.drop_duplicates(inplace=True)
    merged_df.to_csv(output_path, index=False)
    print(f"Merge and categorize done. Saved to {output_path}")
    return output_path

def add_normalized_volume_and_potential(input_file, output_file='cleaned_file2.csv', num_clinics=35, conversion_rate=0.1119):
    df = pd.read_csv(input_file)
    df['Norm Volume'] = (df['Search Volume'] / num_clinics) * conversion_rate
    df['Potential Category'] = df['Norm Volume'].apply(
        lambda x: 'Bad Potential' if x < 5 else ('Medium Potential' if x <= 10 else 'Good Potential')
    )
    df.to_csv(output_file, index=False)
    print(f"Normalized volume and potential added. Saved to {output_file}")
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
    print(f"Next steps determined. Saved to {output_file}")
    return output_file

def split_by_clinic_and_zip(input_file, output_dir='separate_csv_files', zip_name='clinic_location_files.zip'):
    df = pd.read_csv(input_file)
    grouped = df.groupby('Clinic Location - Landing pages')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for location, group in grouped:
        safe_location = location.replace(' ', '_').replace('/', '_')
        filepath = os.path.join(output_dir, f"{safe_location}_file.csv")

        # Create a new DataFrame with 'cluster' column set to file name (safe_location)
        cluster_col = [safe_location] * len(group)
        out_df = group[['Terms']].copy()
        out_df['cluster'] = cluster_col  # add the cluster column as requested

        out_df.to_csv(filepath, index=False)

    shutil.make_archive(zip_name.replace('.zip',''), 'zip', output_dir)
    shutil.rmtree(output_dir)
    print(f"CSV files split and zipped as {zip_name}")

# Example usage:
if __name__ == "__main__":
    merged_file = merge_and_categorize('file1.csv', 'file2.csv')  # your input files
    norm_file = add_normalized_volume_and_potential(merged_file)
    next_steps_file = determine_next_steps(norm_file)
    split_by_clinic_and_zip(next_steps_file)
