import numpy as np
import pandas as pd
import itertools

import bokeh.io
import bokeh.plotting
import iqplot

import panel as pn
pn.extension()


def infect_more_people(r0, people_array, days_sick, sick_duration, infectious_duration, p_death):
    
    # Count the number of new infections at this time step (a day)
    num_new_infected = 0
    
    # Make drawing list based on the death rate. 
    draw_lst = list(np.ones(p_death)) + list(np.zeros(100-p_death))
    
    # Count the number of deaths at this time step
    num_dead = 0
        
    # Get indices of all sick people. We only do stuff with people who are infected right now
    infected_indices = [i for i, x in enumerate(people_array) if x == -1]
        
    for num in infected_indices:
            
        # If they are above the duration, then set them to 1, which indicates that the illness is finished
        if days_sick[num] > sick_duration:
            people_array[num] = 1
            
            # For the people who finished the illness, draw a random number to determine whether or not they die
            if np.random.choice(draw_lst) == 1:
                num_dead += 1

        # If they are still in the infectious period, inclusive
        elif infectious_duration[0] <= days_sick[num] <= infectious_duration[1]:

            # They infect the same number of people on each day of the infectious duration
            num_new_infected += np.round(r0[num] / (infectious_duration[1] - infectious_duration[0]))
            
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


R0_input = pn.widgets.TextInput(name=u'R\u2080', value='2.5')
N_input = pn.widgets.TextInput(name='Population Size', value='1000')

illness_input = pn.widgets.TextInput(name='Duration of Illness (days)', value='14')

# Create throttled widget for the death rate
death_rate_slider = pn.widgets.IntSlider(
    name='Death Rate (%)', 
    start=0,
    end=100,
    step=1,
    value=5,
    value_throttled=5)

# Create throttled widget for the number of immune people initially
immune_slider = pn.widgets.IntSlider(
    name='Initial Immunity (%)', 
    start=0,
    end=100,
    step=1,
    value=0,
    value_throttled=0)

# Create throttled widget for the number of people infected initially
init_sick_slider = pn.widgets.IntSlider(
    name='Number of Infected People Initially', 
    start=0,
    end=100,
    step=1,
    value=5,
    value_throttled=5)

# Create throttled infectious period widget 
infectious_range = pn.widgets.RangeSlider(
    name='Duration of Infectious Period (days)', 
    start=1,
    end=14,
    step=1,
    value=(1, 6),
    value_throttled=(1, 6))

# The infectious period widget depends on the illness duration (the end point is defined by the duration)
@pn.depends(illness_input.param.value, watch=True)
def update_infectious_range(duration):
    infectious_range.end = int(duration)
    
# The widget for the number of sick people initially depends on the population. The number of sick people must be <= 1% of the population
@pn.depends(N_input.param.value, watch=True)
def update_init_sick(population):
    init_sick_slider.end = int(0.01*int(population))

left_col = pn.Column(R0_input, N_input, death_rate_slider, width=250)
middle_col = pn.Column(init_sick_slider, immune_slider, width=250)
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
                         width=500,
                         x_axis_label="Number of Contacts Infected")
    
    p.add_layout(bokeh.models.Title(text=f"Population = {N},  R\u2080 = {R0}", text_font_size="12pt"), 'above')
    p.add_layout(bokeh.models.Title(text="Geometric Distribution", text_font_size="12pt"), 'above')
    
    return p

# Run the simulation and plot
@pn.depends(N_input.param.value, 
            R0_input.param.value, 
            init_sick_slider.param.value_throttled, 
            illness_input.param.value,
            infectious_range.param.value_throttled,
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
    
    # Shuffle the group to increased randomization
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

    # Call the infect_more_people function until there are no more sick people (epidemic stops)
    while list(people_array).count(-1) != 0:

        results.append(infect_more_people(r0, people_array, days_sick, illness_duration, infectious_duration, p_death))

        num_days += 1

    sick, immune, dead, susceptible = list(zip(*results))
    
    # Get cumulative deaths, rather than deaths on each day
    cumul_dead = list(itertools.accumulate(dead))
    
    # Get cumulative recoveries and set the first number to the initial immune population
    cumul_recov = N - np.array(sick) - np.array(cumul_dead) - np.array(susceptible)
    cumul_recov[0] = num_immune

    df = pd.DataFrame.from_dict({"day": np.arange(num_days+1),
                                 "sick": sick, 
                                 "recovered": cumul_recov, 
                                 "cumul_dead": cumul_dead, 
                                 "susceptible": susceptible})

    # Width of the lines
    w = 2

    p_results = bokeh.plotting.figure(height=400, width=775,
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
    p_results.title.text_font_size = '14pt'
    p_results.legend.click_policy="hide"

    return p_results

# Make the plot using the default widget parameters
plot_results = run_plot_simulation(N_input.value, R0_input.value, 
                                   init_sick_slider.value_throttled, illness_input.value, infectious_range.value_throttled, 
                                   death_rate_slider.value_throttled, immune_slider.value_throttled)

# For horizontal orientation
layout = pn.Column(
        widgets,
        pn.Spacer(height=10),
        pn.Row(plot_r0(R0_input.value, N_input.value), pn.Spacer(width=30), 
               plot_results)
    )



def update_r0(event): 
    
    layout[2][0].object = plot_r0(R0_input.value, N_input.value)

def update_results(event): 
    
    plot1 = bokeh.plotting.figure(height=400, width=600,
                                      x_axis_label="Days",
                                      y_axis_label="Number of People",
                                      title="Loading...",
                                      toolbar_location="above")
    
    plot1.title.text_font_size = '14pt'
    layout[2][2].object = plot1
    
    plot2 = run_plot_simulation(N_input.value, R0_input.value, 
                                   init_sick_slider.value_throttled, illness_input.value, infectious_range.value_throttled, 
                                   death_rate_slider.value_throttled, immune_slider.value_throttled)
    
    plot2.title.text_font_size = '14pt'
    layout[2][2].object = plot2
    
# Set up watches to monitor the states of all the parameters
R0_input.param.watch(update_r0, 'value')
N_input.param.watch(update_r0, 'value')

R0_input.param.watch(update_results, 'value')
N_input.param.watch(update_results, 'value')
init_sick_slider.param.watch(update_results, 'value_throttled')
illness_input.param.watch(update_results, 'value')
infectious_range.param.watch(update_results, 'value_throttled')
death_rate_slider.param.watch(update_results, 'value_throttled')
immune_slider.param.watch(update_results, 'value_throttled')

# Make the app
layout.servable()
