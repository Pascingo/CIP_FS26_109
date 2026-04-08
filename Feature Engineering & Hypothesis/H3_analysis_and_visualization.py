"""
CIP Project - Data Analysis & Visualization
Research Question: Does geographic proximity to the host country reveal a statistically
significant positive spillover effect on Olympic medal share?
"""

import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pathlib import Path




def prepare_analysis_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates Medal Share and Historical Baseline for the regression analysis.
    """
    print("Calculating Medal Share and Historical Baseline...")

    # 1. Calculate the total medals awarded per year to compute the "Medal Share"
    yearly_totals = df.groupby('Year')['Total'].sum().reset_index(name='Yearly_Total_Medals')
    df = pd.merge(df, yearly_totals, on='Year')

    # Calculate the share (0.0 to 1.0)
    df['Medal_Share'] = df['Total'] / df['Yearly_Total_Medals']

    # 2. Calculate the "Historical Baseline"
    # We sort by Country and Year to ensure chronological order.
    # Then we shift the Medal Share by 1 period (the previous Olympics) for each country.
    df = df.sort_values(by=['Country_ISO3', 'Year'])

    def rolling_prev3(series):
        return series.shift(1).rolling(window=3, min_periods=3).mean()

    df['Historical_Baseline'] = df.groupby('Country_ISO3')['Medal_Share'].transform(rolling_prev3)

    # 3. Format boolean columns for statsmodels (True/False -> 1/0)
    df['Is_Host'] = df['Is_Host'].astype(int)
    df['Is_Host_Neighbour'] = df['Is_Host_Neighbour'].astype(int)

    return df


def run_regression(df: pd.DataFrame):
    """
    Runs an Ordinary Least Squares (OLS) regression to test for statistical significance.
    """
    print("\n" + "=" * 50)
    print("--- STATISTICAL ANALYSIS (OLS REGRESSION) ---")
    print("=" * 50)

    # Drop rows missing the Historical Baseline (e.g., a country's very first appearance)
    # Regression cannot handle NaN values.
    df_reg = df.dropna(subset=['Historical_Baseline', 'Is_Host_Neighbour', 'Is_Host'])

    # Model Formula: Medal_Share is explained by Neighbour-Status, Host-Status, and Past Performance
    # We MUST control for 'Is_Host' because the host itself usually has a massive bump.
    formula = "Medal_Share ~ Is_Host_Neighbour + Is_Host + Historical_Baseline"

    # Fit the model
    model = smf.ols(formula, data=df_reg).fit()

    # Print the summary
    print(model.summary())
    return model


def create_visualizations(df: pd.DataFrame, output_path: Path):
    """
    Generates plots using seaborn and matplotlib and saves them to output_path.
    """
    print("\nGenerating visualizations...")

    # Set the aesthetic style of the plots
    sns.set_theme(style="whitegrid")

    # Filter out the Host countries to isolate the "Neighbour" effect
    df_plot = df[df['Is_Host'] == 0]

    # Create a figure with two subplots
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Spillover Effect: Geographic Proximity on Olympic Medal Share', fontsize=16)

    # Plot 1: Boxplot
    sns.boxplot(
        ax=axes[0],
        x='Is_Host_Neighbour',
        y='Medal_Share',
        data=df_plot,
        hue='Is_Host_Neighbour',
        palette="Set2",
        legend=False
    )
    axes[0].set_title('Medal Share Distribution (Neighbour vs. Non-Neighbour)')

    # Plot 2: Scatterplot
    sns.scatterplot(
        ax=axes[1],
        x='Historical_Baseline',
        y='Medal_Share',
        hue='Is_Host_Neighbour',
        data=df_plot,
        alpha=0.7,
        palette="Set1"
    )

    # 45-degree reference line
    max_val = max(df_plot['Medal_Share'].max(), df_plot['Historical_Baseline'].max())
    axes[1].plot([0, max_val], [0, max_val], color='black', linestyle='--', linewidth=1)

    axes[1].set_title('Current Performance vs. Historical Baseline')

    plt.tight_layout()

    # Check path logic
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_path, dpi=300)
    print(f"Plot saved successfully at: {output_path}")
    plt.show()


if __name__ == "__main__":
    # Konsistente Pfadbehandlung mit Pathlib
    current_script_dir = Path(__file__).resolve().parent
    base_project_dir = current_script_dir.parent

    input_file = base_project_dir / "Data_clean" / "clean_wikipedia_medals_features.csv"
    if not input_file.exists():
        raise FileNotFoundError(f"Required file not found: {input_file}")

    output_image = base_project_dir / "Visualisations" / "H3_spillover_effect_analysis.png"

    try:
        # Laden der Daten
        df_master = pd.read_csv(input_file)
        print(f"File found: {input_file.name}")

        # Pipeline
        df_prepared = prepare_analysis_metrics(df_master)
        regression_model = run_regression(df_prepared)
        create_visualizations(df_prepared, output_image)

    except FileNotFoundError:
        print(f"Error: Could not find the file at {input_file}")
        print("Check if the integration script successfully created the CSV in 'Data_clean'.")