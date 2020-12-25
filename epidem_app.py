# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.8.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# +
import numpy as np
import pandas as pd
import math

import bokeh.io
import bokeh.plotting
import iqplot

import panel as pn
pn.extension()

bokeh.io.output_notebook()


# -

def infect_more_people(r0, people_array, days_sick, sick_duration, infectious_duration, p_death):
    
    # Every new sick person infects their people on the first day
    num_new_infected = 0
    
    # Make drawing list based on the death rate. 
    draw_lst = list(np.ones(p_death)) + list(np.zeros(100-p_death))
    
    # Count the number of deaths at this time step
    num_dead = 0
        
    # Get indices of all sick people. We only do stuff with people who are infected right now
    infected_indices = [i for i, x in enumerate(people_array) if x == -1]
    
    min_infect, max_infect = infectious_duration
    
    for num in infected_indices:
            
        # If they are above the duration, then set them to 1, which indicates that the illness is finished
        if days_sick[num] >= sick_duration:
            people_array[num] = 1
            
            # Randomly draw to determine if they die (given that they've finished the illness)
            if np.random.choice(draw_lst) == 1:
                num_dead += 1

        # If they are still in the infectious period, inclusive
        elif min_infect <= days_sick[num] <= max_infect:

            # They infect the same number of people on each day of the infectious duration
            num_new_infected += math.ceil(r0[num] / (max_infect - min_infect))
            
            days_sick[num] += 1

        # For all sick people who are not infectious, increase the number of days they've been sick
        else:
            days_sick[num] += 1
                
    # Get the indices of the newly infected people
    new_indices = np.random.randint(len(people_array), size=int(num_new_infected))
    
    # If they have never been infected, make them sick
    for i in range(len(new_indices)):
        if people_array[new_indices[i]] == 0:
            people_array[new_indices[i]] = -1
           
    
    num_recovered = list(people_array).count(1)
    
    # num_dead already determined above
    num_immune = num_recovered - num_dead
    num_uninfected = list(people_array).count(0)
    num_sick = list(people_array).count(-1)

    return (num_sick, num_immune, num_dead, num_uninfected)

# +
R0_input = pn.widgets.TextInput(name=u'R\u2080', value='2.5')
N_input = pn.widgets.TextInput(name='Population Size', value='10000')

death_rate_slider = pn.widgets.IntSlider(
    name='Death Rate (%)', 
    start=0,
    end=100,
    step=1,
    value=5,
    value_throttled=5)

immune_slider = pn.widgets.IntSlider(
    name='Initial Immunity (%)', 
    start=0,
    end=100,
    step=1,
    value=0,
    value_throttled=0)

init_sick_input = pn.widgets.TextInput(name='Initial Number of Infected People', value='5')
illness_input = pn.widgets.TextInput(name='Duration of Illness (days)', value='14')

# Create throttled infectious period widget 
infectious_range = pn.widgets.RangeSlider(
    name='Duration of Infectious Period (days)', 
    start=0,
    end=14,
    step=1,
    value=(1, 6),
    value_throttled=(1, 6))

# The infectious period widget depends on the illness duration (the end point is defined by the duration)
@pn.depends(illness_input.param.value, watch=True)
def update_infectious_range(duration):
    infectious_range.end = int(duration)

left_col = pn.Column(R0_input, N_input, death_rate_slider, width=250)
middle_col = pn.Column(init_sick_input, immune_slider, width=250)
right_col = pn.Column(illness_input, infectious_range, width=250)

widgets = pn.Row(left_col, pn.Spacer(width=20), middle_col, pn.Spacer(width=20), right_col)

# Make the r0 distribution plot
@pn.depends(R0_input.param.value, N_input.param.value)
def plot_r0(R0, N):

    R0 = float(R0)
    N = int(N)
    r0 = np.random.geometric(1/R0, N)

    p = iqplot.histogram(r0,
                         rug=False,
                         height=400,
                         title=f"Geometric Distribution in a Population of {N} with R\u2080 = {R0}",
                         x_axis_label="Number of Contacts Infected")
    return p

# Run the simulation and plot
@pn.depends(N_input.param.value, 
            R0_input.param.value, 
            init_sick_input.param.value, 
            illness_input.param.value,
            infectious_range.param.value,
            death_rate_slider.param.value_throttled,
            immune_slider.param.value_throttled)
def run_plot_simulation(N, R0, init_sick, illness_duration, infectious_duration, p_death, p_immune):

    R0 = float(R0)
    N = int(N)

    illness_duration = int(illness_duration)
    init_sick = int(init_sick)

    # r0 is how many people they infect
    r0 = np.random.geometric(1/R0, N)

    # Sick status. 1 = immune, start with some number of immune people
    num_immune = int(p_immune / 100.0 * N)
    people_array = np.concatenate((np.ones(num_immune), np.zeros(N - num_immune)))
    np.random.shuffle(people_array)
    
    # Get the indices of the susceptible people
    indices_susceptible = [i for i, x in enumerate(people_array) if x == 0]
    
    # Number of days sick
    days_sick = np.zeros(N)

    # Pick random people to be sick
    index_infected = np.random.choice(indices_susceptible, size=init_sick)
    people_array[index_infected] = -1
    days_sick[index_infected] += 1

    num_days = 0
    results = [(init_sick, num_immune, 0, len(indices_susceptible)-init_sick)]

    # Call the infect_more_people function
    while list(people_array).count(-1) != 0:

        results.append(infect_more_people(r0, people_array, days_sick, illness_duration, infectious_duration, p_death))

        num_days += 1

    sick, immune, dead, susceptible = list(zip(*results))
    
    # Get cumulative deaths, rather than deaths on each day
    cumul_dead = np.zeros(len(dead))
    
    for i in range(1, len(dead)):
        cumul_dead[i] = cumul_dead[i-1] + dead[i]
    
    cumul_recov = N - np.array(sick) - np.array(cumul_dead) - np.array(susceptible)
    cumul_recov[0] = num_immune

    df = pd.DataFrame.from_dict({"day": np.arange(num_days+1),
                                 "sick": sick, 
                                 "recovered": cumul_recov, 
                                 "cumul_dead": cumul_dead, 
                                 "susceptible": susceptible})

    # Width of the lines
    w = 2

    p_results = bokeh.plotting.figure(height=400, width=700,
                                      x_axis_label="Days",
                                      y_axis_label="Number of People",
                                      title="Simulation Results",
                                      toolbar_location="above",)

    r1 = p_results.line(x="day", y="sick", source=df, line_width=w)
    r2 = p_results.line(x="day", y="recovered", source=df, color="green", line_width=w)
    r3 = p_results.line(x="day", y="cumul_dead", source=df, color="tomato", line_width=w)
    r4 = p_results.line(x="day", y="susceptible", source=df, color="orange", line_width=w)

    legend = bokeh.models.Legend(items=[
        ("Infected"   , [r1]),
        ("Recovered" , [r2]),
        ("Cumulative Deaths", [r3]),
        ("Susceptible" , [r4]),
    ], location="center")

    # Formatting
    p_results.add_layout(legend, 'right')
    p_results.xgrid.visible = False

    return p_results

plot_results = run_plot_simulation(N_input.value, R0_input.value, 
                                   init_sick_input.value, illness_input.value, infectious_range.value_throttled, 
                                   death_rate_slider.value_throttled, immune_slider.value_throttled)

# For horizontal orientation
layout = pn.Column(
        widgets,
        pn.Spacer(height=10),
        pn.Row(plot_r0(R0_input.value, N_input.value), pn.Spacer(width=20), 
               plot_results)
    )


# +
def update_r0(event): 
    layout[2][0].object = plot_r0(R0_input.value, N_input.value)

def update_results(event): 
    layout[2][2].object = run_plot_simulation(N_input.value, R0_input.value, 
                                   init_sick_input.value, illness_input.value, infectious_range.value_throttled, 
                                   death_rate_slider.value_throttled, immune_slider.value_throttled)
    
R0_input.param.watch(update_r0, 'value')
N_input.param.watch(update_r0, 'value')

R0_input.param.watch(update_results, 'value')
N_input.param.watch(update_results, 'value')
init_sick_input.param.watch(update_results, 'value')
illness_input.param.watch(update_results, 'value')
infectious_range.param.watch(update_results, 'value_throttled')
death_rate_slider.param.watch(update_results, 'value_throttled')
immune_slider.param.watch(update_results, 'value_throttled')
# -

layout.servable()






