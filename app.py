import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

#dados
try:
    df_full = pd.read_csv('https://raw.githubusercontent.com/07leonam/plot_vsd/refs/heads/main/Summer_olympic_Medals.csv')
except FileNotFoundError:
    print("Error: 'Summer_olympic_Medals.csv' not found. Make sure the file is in the same directory as the script.")
    exit()
except Exception as e:
    print(f"Error loading CSV: {e}")
    exit()

# Expected columns based on user input
expected_cols_from_user = ['Year', 'Host_country', 'Host_city', 'Country_Name', 'Country_Code', 'Gold', 'Silver', 'Bronze']
missing_cols = [col for col in expected_cols_from_user if col not in df_full.columns]
if missing_cols:
    print(f"Error: The CSV file is missing the following expected columns: {', '.join(missing_cols)}")
    print(f"Available columns are: {', '.join(df_full.columns)}")
    exit()

# Correct country name
df_full['Country_Name'] = df_full['Country_Name'].replace('United States', 'United States of America')

# Filter data for years
df = df_full[(df_full['Year'] >= 1992) & (df_full['Year'] <= 2020)].copy()

# Calculate Total_Medals
df['Total_Medals'] = df['Gold'] + df['Silver'] + df['Bronze']

# Prepare lists for dropdowns
all_countries = sorted(df['Country_Name'].unique())
medal_types = ['Gold', 'Silver', 'Bronze', 'Total_Medals']

# Create year options using the exact column names Host_city and Host_country
year_host_info = df[['Year', 'Host_city', 'Host_country']].drop_duplicates().sort_values('Year')
year_options = [{'label': 'All Years (1992-2020)', 'value': 'All'}] + \
               [{'label': f"{row['Year']} - {row['Host_city']}, {row['Host_country']}", 'value': row['Year']}
                for index, row in year_host_info.iterrows()]


#2 Initialize Dash App
app = dash.Dash(__name__)
server = app.server

# --- 3. Define App Layout ---
app.layout = html.Div([
    html.H1("Olympic Medals Dashboard (1992-2020)", style={'textAlign': 'center', 'marginBottom': '40px'}),

    
    html.Div([
        html.Label("Select Olympic Year (for Bar Chart):"),
        dcc.Dropdown(
            id='year-dropdown',
            options=year_options,
            value='All'
        ),

        html.Br(),

        html.Label("Select Medal Type (for Map, Area, Bar Charts):"),
        dcc.Dropdown(
            id='medal-type-dropdown',
            options=[{'label': medal.replace('_', ' '), 'value': medal} for medal in medal_types],
            value='Total_Medals'
        ),

        html.Br(),

        html.Label("Select Country (for Pie Chart):"),
        dcc.Dropdown(
            id='country-dropdown',
            options=[{'label': country, 'value': country} for country in all_countries],
            value=all_countries[0] if all_countries else None
        ),
    ], style={'width': '80%', 'margin': '0 auto'}),

    html.Br(),
    html.H2("Medal Insights", style={'textAlign': 'center'}),

   
    html.Div([
        dcc.Graph(id='pie-chart'),
        dcc.Graph(id='map-chart')
    ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}),

    html.Br(),
    html.H2("Top Countries Over Time", style={'textAlign': 'center'}),

   
    html.Div([
        dcc.Graph(id='area-chart'),
        dcc.Graph(id='bar-chart')
    ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}),
])


# --- 4. Define Callbacks ---

# Callback for Pie Chart
@app.callback(
    Output('pie-chart', 'figure'),
    [Input('country-dropdown', 'value')]
)
def update_pie_chart(selected_country):
    if not selected_country:
        # Return an empty figure or a message
        fig = px.pie(title="Please select a country")
        fig.update_layout(annotations=[dict(text='No country selected', showarrow=False)])
        return fig


    country_data = df[df['Country_Name'] == selected_country]
    if country_data.empty:
        fig = px.pie(title=f"No data for {selected_country} (1992-2020)")
        fig.update_layout(annotations=[dict(text='No data available', showarrow=False)])
        return fig


    medal_sum = country_data[['Gold', 'Silver', 'Bronze']].sum()
    medal_counts_df = pd.DataFrame({
        'Medal_Type': ['Gold', 'Silver', 'Bronze'],
        'Count': [medal_sum.get('Gold', 0), medal_sum.get('Silver', 0), medal_sum.get('Bronze', 0)]
    })
    

    fig_pie = px.pie(medal_counts_df,
                     names='Medal_Type',
                     values='Count',
                     title=f'Medal Distribution for {selected_country} (1992-2020)',
                     color='Medal_Type',
                     color_discrete_map={'Gold': 'gold', 'Silver': 'silver', 'Bronze': '#cd7f32'})
    fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
    return fig_pie

# Callback for Map Chart
@app.callback(
    Output('map-chart', 'figure'),
    [Input('medal-type-dropdown', 'value')]
)
def update_map_chart(selected_medal_type):
    medal_col = selected_medal_type
    map_data = df.groupby('Country_Name', as_index=False)[medal_col].sum()

    fig_map = px.choropleth(map_data,
                            locations='Country_Name',
                            locationmode='country names',
                            color=medal_col,
                            hover_name='Country_Name',
                            color_continuous_scale=px.colors.sequential.YlOrRd, # Example color scale
                            title=f'Total {selected_medal_type.replace("_", " ")} by Country (1992-2020)')
    return fig_map

# Callback for Area Chart
@app.callback(
    Output('area-chart', 'figure'),
    [Input('medal-type-dropdown', 'value')]
)
def update_area_chart(selected_medal_type):
    medal_col = selected_medal_type

    df_country_year_medals = df.groupby(['Country_Name', 'Year'], as_index=False)[medal_col].sum()
    top_10_countries_overall = df.groupby('Country_Name')[medal_col].sum().nlargest(10).index
    df_top_10 = df_country_year_medals[df_country_year_medals['Country_Name'].isin(top_10_countries_overall)]

    fig_area = px.area(df_top_10,
                       x="Year",
                       y=medal_col,
                       color="Country_Name",
                       title=f'Top 10 Countries by {selected_medal_type.replace("_", " ")} (1992-2020)',
                       labels={medal_col: selected_medal_type.replace("_", " ") + ' Won'})
    fig_area.update_xaxes(type='category') # Treat years as discrete categories for area chart
    return fig_area

# Callback for Bar Chart
@app.callback(
    Output('bar-chart', 'figure'),
    [Input('medal-type-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_bar_chart(selected_medal_type, selected_year_value):
    medal_col = selected_medal_type
    current_df_bar = df.copy()
    
    year_title_segment = "All Years (1992-2020)"
    if selected_year_value != 'All':
        current_df_bar = current_df_bar[current_df_bar['Year'] == selected_year_value]
        year_label_info_obj = next((item for item in year_options if item['value'] == selected_year_value), None)
        if year_label_info_obj:
            year_title_segment = year_label_info_obj['label']
        else:
            year_title_segment = str(selected_year_value) # Fallback if label not found

    df_grouped_bar = current_df_bar.groupby('Country_Name', as_index=False)[medal_col].sum()
    df_grouped_bar = df_grouped_bar.nlargest(10, medal_col) # Get top 10 based on the selected medal column

    bar_color_val = None # Default color
    if medal_col == 'Gold': bar_color_val = 'gold'
    elif medal_col == 'Silver': bar_color_val = 'silver'
    elif medal_col == 'Bronze': bar_color_val = '#cd7f32'
    # For 'Total_Medals', Plotly Express will use its default color sequence

    fig_bar = px.bar(df_grouped_bar,
                     x='Country_Name',
                     y=medal_col,
                     title=f'Top 10 Countries by {selected_medal_type.replace("_", " ")} in {year_title_segment}',
                     labels={'Country_Name': 'Country', medal_col: selected_medal_type.replace("_", " ")})
    if bar_color_val:
        fig_bar.update_traces(marker_color=bar_color_val)
    return fig_bar

# Executar o aplicativo
if __name__ == '__main__':
    app.run_server(debug=True)
