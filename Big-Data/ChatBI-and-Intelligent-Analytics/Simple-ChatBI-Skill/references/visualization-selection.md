# Visualization Selection

## Auto-Select Chart Type

Choose the best chart based on the data shape returned by the SQL query:

| Data Shape | Chart Type | When to Use |
|------------|------------|-------------|
| Single categorical column | Pie / Donut | Risk level distribution, status counts |
| Categorical + numeric | Bar (vertical) | Revenue by category, count by group |
| Categorical + numeric (long labels) | Bar (horizontal) | Vendor comparison, ranked lists |
| Two numeric columns | Scatter | Correlation between metrics |
| Time series + numeric | Line | Trend over time, monthly evolution |
| Single numeric column | Histogram | Distribution of scores, amounts |
| Categorical + categorical + numeric | Heatmap | Risk by city, sector by region |
| Hierarchical categories | Treemap / Sunburst | Drill-down analysis |

## Implementation Pattern

```python
import plotly.express as px

def auto_visualize(df, user_question=""):
    """Auto-select chart type based on data shape."""
    if df.empty or len(df.columns) < 2:
        return None

    # Identify column types
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    datetime_cols = df.select_dtypes(include=['datetime']).columns.tolist()

    # Time series: datetime + numeric
    if datetime_cols and numeric_cols:
        fig = px.line(df, x=datetime_cols[0], y=numeric_cols[0])
        return fig

    # Single categorical + numeric: pie if few categories, bar if many
    if len(categorical_cols) == 1 and len(numeric_cols) == 1:
        cat = categorical_cols[0]
        num = numeric_cols[0]
        if df[cat].nunique() <= 6:
            fig = px.pie(df, names=cat, values=num)
        else:
            fig = px.bar(df, x=cat, y=num)
        return fig

    # Two categorical + numeric: heatmap or grouped bar
    if len(categorical_cols) == 2 and len(numeric_cols) >= 1:
        pivot = df.pivot_table(index=categorical_cols[0], columns=categorical_cols[1],
                               values=numeric_cols[0], aggfunc='sum')
        fig = px.imshow(pivot, text_auto=True)
        return fig

    # Two numeric: scatter
    if len(numeric_cols) >= 2:
        fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1])
        return fig

    # Fallback: bar chart
    if categorical_cols and numeric_cols:
        fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0])
        return fig

    return None
```

## Chart Selection Rules

1. **Pie charts**: Only when there are 2-6 categories. More than 6 becomes unreadable.
2. **Bar charts**: Default choice for categorical comparisons. Use horizontal when labels are long (>15 chars).
3. **Line charts**: Only for time series. Never for categorical data.
4. **Scatter plots**: Only when both axes are numeric. Add color for a third dimension.
5. **Heatmaps**: Best for two-dimensional categorical comparisons.
6. **Histograms**: Only for single numeric column distribution.

## Formatting Rules

- Currency: `$1,234,567 MXN` format
- Percentages: `45.2%`
- Dates: `2026-05-08`
- Large numbers: Use `K`, `M`, `B` abbreviations for readability
- Risk scores: Keep as-is (0-10 or 0-100 depending on domain)

## Streamlit Integration

```python
import streamlit as st

def display_results(df, user_query):
    """Display results with auto-selected visualization."""
    if df.empty:
        st.info("La consulta no devolvió resultados.")
        return

    # Auto-select chart
    fig = auto_visualize(df, user_query)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    # Always show data table below chart
    st.dataframe(df, use_container_width=True, hide_index=True)
```
