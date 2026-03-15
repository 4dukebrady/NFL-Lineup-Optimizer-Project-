import streamlit as st
import pandas as pd

# Import the linear programs and cleaned data function
from linear_program import optimize_projected_lineup, optimize_actual_lineup 
from data_collect_clean import get_cleaned_data

# ==========================================
# 1. PAGE SETUP & HELPER FUNCTIONS
# ==========================================
st.set_page_config(page_title="NFL DFS Optimizer", layout="wide")
st.title("🏈 NFL Daily Fantasy Sports Lineup Optimizer")

@st.cache_data
def load_and_cache_data():
    print("Executing data pipeline...")
    df = get_cleaned_data() 
    return df

df_merged = load_and_cache_data()

# Helper function to generate the headshot gallery cleanly
def display_headshots(team_df):
    cols = st.columns(len(team_df))
    for idx, (index, player) in enumerate(team_df.iterrows()):
        with cols[idx]:
            raw_url = player.get('headshot_url')
            if isinstance(raw_url, str) and raw_url.startswith("http"):
                url = raw_url
            else:
                player_name_url = player['Name'].replace(" ", "+")
                url = f"https://ui-avatars.com/api/?name={player_name_url}&background=random&size=150"
                
            st.image(url, use_container_width=True)
            st.caption(f"**{player['Name']}** \n{player['position']} - {player['team']}")

# ==========================================
# 2. THE CONTROL PANEL (SIDEBAR)
# ==========================================
st.sidebar.header("Control Panel")

available_years = sorted(df_merged['Year'].unique(), reverse=True)
available_weeks = sorted(df_merged['Week'].unique())

selected_year = st.sidebar.selectbox("Select Year", available_years)
selected_week = st.sidebar.selectbox("Select Week", available_weeks)

st.sidebar.markdown("---")
# A single button to rule them all
run_optimizer = st.sidebar.button("Run Optimizer", type="primary")

# ==========================================
# 3. MAIN DISPLAY LOGIC
# ==========================================
# ==========================================
# 3. MAIN DISPLAY LOGIC
# ==========================================
if run_optimizer:
    
    # --- THE SAFETY VALVE ---
    # Filter for the selected week to inspect the data before running the solvers
    df_week = df_merged[(df_merged['Year'] == selected_year) & (df_merged['Week'] == selected_week)]
    
    # Check if the 'fantasy_points' column exists AND has actual scores recorded
    has_actuals = (
        'fantasy_points' in df_week.columns and 
        df_week['fantasy_points'].fillna(0).sum() > 0
    )

    with st.spinner('Solving linear programs...'):
        
        # 1. ALWAYS RUN THE PROJECTED SOLVER
        projected_team = optimize_projected_lineup(df_merged, target_year=selected_year, target_week=selected_week)
        
        if projected_team is None:
            st.error("No valid lineup could be found for this week. Check your data constraints.")
        else:
            # ==========================================
            # SECTION 1: THE PROJECTED LINEUP
            # ==========================================
            st.header("📊 The Optimized Projected Lineup")
            st.markdown("This is the roster our model generated *before* the games were played.")
            
            # Projected KPIs
            proj_salary = projected_team['FD salary'].sum()
            proj_points = projected_team['proj_points'].sum()
            
            p_col1, p_col2, p_col3 = st.columns(3)
            p_col1.metric("Total Budget Used", f"${proj_salary:,.0f} / $60,000")
            p_col2.metric("Total Projected Points", f"{proj_points:.2f}")
            
            # Dynamic Grade Reveal
            if has_actuals:
                proj_actual_score = projected_team['fantasy_points'].sum()
                delta = proj_actual_score - proj_points
                p_col3.metric(
                    label="Actual Points Scored", 
                    value=f"{proj_actual_score:.2f}", 
                    delta=f"{delta:+.2f} vs Proj"
                )
                display_cols = ['Name', 'position', 'team', 'FD salary', 'proj_points', 'fantasy_points']
            else:
                p_col3.metric("Actual Points Scored", "Pending...")
                display_cols = ['Name', 'position', 'team', 'FD salary', 'proj_points']
            
            # Display Projected Headshots and Table
            display_headshots(projected_team)
            st.dataframe(
                projected_team[display_cols],
                use_container_width=True, hide_index=True
            )
            
# ... [Your existing Projected Lineup dataframe code is right above here] ...
            
            # --- THE BOOM/BUST ANALYZER ---
            if has_actuals:
                st.write("") # Adds a tiny bit of vertical spacing
                st.subheader("📈 Post-Game Lineup Analysis")
                
                # 1. Calculate the math
                analysis_df = projected_team.copy()
                analysis_df['point_diff'] = analysis_df['fantasy_points'] - analysis_df['proj_points']
                analysis_df['value'] = analysis_df['fantasy_points'] / (analysis_df['FD salary'] / 1000)
                
                # 2. Find the extremes
                mvp_row = analysis_df.loc[analysis_df['point_diff'].idxmax()]
                bust_row = analysis_df.loc[analysis_df['point_diff'].idxmin()]
                bargain_row = analysis_df.loc[analysis_df['value'].idxmax()]
                
                # 3. Display the insights using Streamlit alert boxes
                b_col1, b_col2, b_col3 = st.columns(3)
                
                with b_col1:
                    st.success(f"**🌟 The MVP (Biggest Boom)**\n\n{mvp_row['Name']}\n\n**+{mvp_row['point_diff']:.2f}** pts over projection")
                    
                with b_col2:
                    st.error(f"**🧊 The Bust (Biggest Miss)**\n\n{bust_row['Name']}\n\n**{bust_row['point_diff']:.2f}** pts under projection")
                    
                with b_col3:
                    st.info(f"**💰 Best Bargain**\n\n{bargain_row['Name']}\n\n**{bargain_row['value']:.2f}** pts per $1K salary")

            st.divider() # Adds a clean visual break before Section 2
            
            # ... [Section 2: The Perfect Hindsight Lineup is right below here] ...

            st.divider()
            
            # ==========================================
            # SECTION 2: THE PERFECT HINDSIGHT LINEUP
            # ==========================================
            if has_actuals:
                # Only run the second solver if we have real data to maximize!
                actual_team = optimize_actual_lineup(df_merged, target_year=selected_year, target_week=selected_week)
                
                st.header("🏆 The Perfect Hindsight Lineup")
                st.markdown("If we had a crystal ball, this is the mathematically perfect roster based on actual points scored.")
                
                # Hindsight KPIs
                act_salary = actual_team['FD salary'].sum()
                act_score = actual_team['fantasy_points'].sum()
                
                a_col1, a_col2 = st.columns(2)
                a_col1.metric("Total Budget Used", f"${act_salary:,.0f} / $60,000")
                a_col2.metric("Total Actual Points", f"{act_score:.2f}")
                
                # Display Hindsight Headshots and Table
                display_headshots(actual_team)
                st.dataframe(
                    actual_team[['Name', 'position', 'team', 'FD salary', 'fantasy_points', 'proj_points']],
                    use_container_width=True, hide_index=True
                )
            else:
                # The safety message triggers instead of the second solver
                st.info("🕒 **No hindsight lineup until after the game.** Actual fantasy points have not been recorded for this week yet.")
else:
    st.info("👈 Select a Year and Week from the Control Panel and click 'Run Optimizer'.")
