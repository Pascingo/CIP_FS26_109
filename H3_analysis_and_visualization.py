"""
CIP Project - Data Analysis & Visualization
Research Question: Does geographic proximity to the host country reveal a statistically
significant positive spillover effect on Olympic medal share?
"""

import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import seaborn as sns


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
    df['Historical_Baseline'] = df.groupby('Country_ISO3')['Medal_Share'].shift(1)

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
    df_reg = df.dropna(subset=['Medal_Share', 'Historical_Baseline', 'Is_Host_Neighbour', 'Is_Host'])

    # Model Formula: Medal_Share is explained by Neighbour-Status, Host-Status, and Past Performance
    # We MUST control for 'Is_Host' because the host itself usually has a massive bump.
    formula = "Medal_Share ~ Is_Host_Neighbour + Is_Host + Historical_Baseline"

    # Fit the model
    model = smf.ols(formula, data=df_reg).fit()

    # Print the summary
    print(model.summary())
    return model


def create_visualizations(df: pd.DataFrame):
    """
    Generates plots using seaborn and matplotlib to visualize the spillover effect.
    """
    print("\nGenerating visualizations...")

    # Set the aesthetic style of the plots
    sns.set_theme(style="whitegrid")

    # Filter out the Host countries for the plot to isolate the "Neighbour" effect clearly
    # We want to compare strictly: Neighbours vs. Non-Neighbours (who are not the host)
    df_plot = df[df['Is_Host'] == 0]

    # Create a figure with two subplots
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Spillover Effect: Geographic Proximity on Olympic Medal Share', fontsize=16)

    # Plot 1: Boxplot comparing Medal Share distribution
    sns.boxplot(
        ax=axes[0],
        x='Is_Host_Neighbour',
        y='Medal_Share',
        data=df_plot,
        palette="Set2"
    )
    axes[0].set_title('Medal Share Distribution (Neighbour vs. Non-Neighbour)')
    axes[0].set_xlabel('Is Neighbour to Host (0 = No, 1 = Yes)')
    axes[0].set_ylabel('Medal Share')

    # Plot 2: Scatterplot showing Baseline vs. Actual Share, colored by Neighbour status
    sns.scatterplot(
        ax=axes[1],
        x='Historical_Baseline',
        y='Medal_Share',
        hue='Is_Host_Neighbour',
        data=df_plot,
        alpha=0.7,
        palette="Set1"
    )

    # Add a 45-degree reference line (where current share equals past share)
    max_val = max(df_plot['Medal_Share'].max(), df_plot['Historical_Baseline'].max())
    axes[1].plot([0, max_val], [0, max_val], color='black', linestyle='--', linewidth=1)

    axes[1].set_title('Current Performance vs. Historical Baseline')
    axes[1].set_xlabel('Historical Baseline (Medal Share at Previous Games)')
    axes[1].set_ylabel('Current Medal Share')

    plt.tight_layout()
    plt.savefig("spillover_effect_analysis.png", dpi=300)
    print("Plot saved successfully as 'spillover_effect_analysis.png'.")
    plt.show()


if __name__ == "__main__":
    # Load the integrated dataset
    input_file = "winter_olympics_analysis_ready.csv"
    try:
        df_master = pd.read_csv(input_file)

        # Execute the pipeline
        df_prepared = prepare_analysis_metrics(df_master)
        regression_model = run_regression(df_prepared)
        create_visualizations(df_prepared)

    except FileNotFoundError:
        print(f"Error: Could not find '{input_file}'. Please run the integration script first.")