import pandas as pd
from pyomo.environ import *

def optimize_projected_lineup(df_merged, target_year, target_week, salary_cap=60000):
    """
    Filters df_merged for the specified year and week, 
    then runs the Pyomo linear program to find the optimal 8-player offensive lineup.
    """
    print(f"Filtering df_merged for Year: {target_year}, Week: {target_week}...")
    
    # 1. FILTER FOR THE SPECIFIC WEEK & YEAR
    df_week = df_merged[(df_merged['Year'] == target_year) & (df_merged['Week'] == target_week)].copy()
    
    if df_week.empty:
        print("Error: No data found for this Year and Week in df_merged.")
        return None
        
    # Reset index so Pyomo can iterate cleanly from 0 to N
    df_week = df_week.reset_index(drop=True)
    
    # 2. INITIALIZE MODEL
    model = ConcreteModel()
    model.PLAYERS = Set(initialize=df_week.index)
    
    # DECISION VARIABLE: 1 if selected, 0 if not
    model.x = Var(model.PLAYERS, domain=Binary)
    
    # 3. OBJECTIVE: Maximize 'proj_points'
    def obj_rule(model):
        return sum(df_week.loc[i, 'proj_points'] * model.x[i] for i in model.PLAYERS)
    model.obj = Objective(rule=obj_rule, sense=maximize)
    
    # 4. SALARY CONSTRAINT: Use 'FD salary'
    def salary_rule(model):
        return sum(df_week.loc[i, 'FD salary'] * model.x[i] for i in model.PLAYERS) <= salary_cap
    model.salary_con = Constraint(rule=salary_rule)
    
    # 5. ROSTER SIZE CONSTRAINT: Exactly 8 players (since we dropped Defense)
    def total_players_rule(model):
        return sum(model.x[i] for i in model.PLAYERS) == 8
    model.total_players_con = Constraint(rule=total_players_rule)
    
    # 6. POSITIONAL CONSTRAINTS
    qb_idx = df_week[df_week['position'] == 'QB'].index
    rb_idx = df_week[df_week['position'] == 'RB'].index
    wr_idx = df_week[df_week['position'] == 'WR'].index
    te_idx = df_week[df_week['position'] == 'TE'].index
    
    # Exactly 1 QB
    model.qb_con = Constraint(expr=sum(model.x[i] for i in qb_idx) == 1)
    
    # FLEX Logic: RB (2-3), WR (3-4), TE (1-2)
    model.rb_min_con = Constraint(expr=sum(model.x[i] for i in rb_idx) >= 2)
    model.rb_max_con = Constraint(expr=sum(model.x[i] for i in rb_idx) <= 3)
    
    model.wr_min_con = Constraint(expr=sum(model.x[i] for i in wr_idx) >= 3)
    model.wr_max_con = Constraint(expr=sum(model.x[i] for i in wr_idx) <= 4)
    
    model.te_min_con = Constraint(expr=sum(model.x[i] for i in te_idx) >= 1)
    model.te_max_con = Constraint(expr=sum(model.x[i] for i in te_idx) <= 2)
    
    # 7. RUN THE SOLVER
    print("Solving...")
    solver = SolverFactory('cbc') 
    results = solver.solve(model, tee=False)
    
    if results.solver.termination_condition != TerminationCondition.optimal:
        print("Solver failed to find an optimal lineup.")
        return None
        
    # 8. EXTRACT RESULTS
    selected_indices = [i for i in model.PLAYERS if value(model.x[i]) > 0.5]
    projected_winning_lineup = df_week.loc[selected_indices].copy()
    
    # Sort the dataframe so it looks nice on the dashboard
    pos_order = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 4}
    projected_winning_lineup['sort_order'] = projected_winning_lineup['position'].map(pos_order)
    projected_winning_lineup = projected_winning_lineup.sort_values('sort_order').drop('sort_order', axis=1)
    
    return projected_winning_lineup

def optimize_actual_lineup(df_merged, target_year, target_week, salary_cap=60000):

    print(f"Filtering df_merged for ACTUALS - Year: {target_year}, Week: {target_week}...")
    
    # 1. FILTER FOR THE SPECIFIC WEEK & YEAR
    df_week = df_merged[(df_merged['Year'] == target_year) & (df_merged['Week'] == target_week)].copy()
    
    if df_week.empty:
        print("Error: No data found for this Year and Week in df_merged.")
        return None
        
    # Reset index so Pyomo can iterate cleanly
    df_week = df_week.reset_index(drop=True)
    
    # 2. INITIALIZE MODEL
    model = ConcreteModel()
    model.PLAYERS = Set(initialize=df_week.index)
    
    # DECISION VARIABLE: 1 if selected, 0 if not
    model.x = Var(model.PLAYERS, domain=Binary)
    
    # 3. OBJECTIVE: Maximize 'fantasy_points' (THIS IS THE ONLY CHANGE)
    def obj_rule(model):
        return sum(df_week.loc[i, 'fantasy_points'] * model.x[i] for i in model.PLAYERS)
    model.obj = Objective(rule=obj_rule, sense=maximize)
    
    # 4. SALARY CONSTRAINT: Use 'FD salary'
    def salary_rule(model):
        return sum(df_week.loc[i, 'FD salary'] * model.x[i] for i in model.PLAYERS) <= salary_cap
    model.salary_con = Constraint(rule=salary_rule)
    
    # 5. ROSTER SIZE CONSTRAINT: Exactly 8 players
    def total_players_rule(model):
        return sum(model.x[i] for i in model.PLAYERS) == 8
    model.total_players_con = Constraint(rule=total_players_rule)
    
    # 6. POSITIONAL CONSTRAINTS
    qb_idx = df_week[df_week['position'] == 'QB'].index
    rb_idx = df_week[df_week['position'] == 'RB'].index
    wr_idx = df_week[df_week['position'] == 'WR'].index
    te_idx = df_week[df_week['position'] == 'TE'].index
    
    # Exactly 1 QB
    model.qb_con = Constraint(expr=sum(model.x[i] for i in qb_idx) == 1)
    
    # FLEX Logic: RB (2-3), WR (3-4), TE (1-2)
    model.rb_min_con = Constraint(expr=sum(model.x[i] for i in rb_idx) >= 2)
    model.rb_max_con = Constraint(expr=sum(model.x[i] for i in rb_idx) <= 3)
    
    model.wr_min_con = Constraint(expr=sum(model.x[i] for i in wr_idx) >= 3)
    model.wr_max_con = Constraint(expr=sum(model.x[i] for i in wr_idx) <= 4)
    
    model.te_min_con = Constraint(expr=sum(model.x[i] for i in te_idx) >= 1)
    model.te_max_con = Constraint(expr=sum(model.x[i] for i in te_idx) <= 2)
    
    # 7. RUN THE SOLVER
    print("Solving for Hindsight Optimal...")
    solver = SolverFactory('cbc') 
    results = solver.solve(model, tee=False)
    
    if results.solver.termination_condition != TerminationCondition.optimal:
        print("Solver failed to find an optimal lineup.")
        return None
        
    # 8. EXTRACT RESULTS
    selected_indices = [i for i in model.PLAYERS if value(model.x[i]) > 0.5]
    actual_winning_lineup = df_week.loc[selected_indices].copy()
    
    # Sort the dataframe 
    pos_order = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 4}
    actual_winning_lineup['sort_order'] = actual_winning_lineup['position'].map(pos_order)
    actual_winning_lineup = actual_winning_lineup.sort_values('sort_order').drop('sort_order', axis=1)
    
    return actual_winning_lineup

