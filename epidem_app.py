import numpy as np
import pandas as pd

import bokeh.io
import bokeh.plotting
import bokeh.models
import iqplot

import panel as pn
pn.extension()

plot_height = 500
total_width = 1475
plot_width = 925

def infect_more_people(r0, people_array, days_sick, sick_duration, infectious_duration, p_death, p_transmit):
    
    # Count the number of new infections at this time step (a day)
    num_new_infected = 0
    
    # Make drawing lists based on the death and transmission rates. Both are decimals to the hundredth place
    draw_death = list(np.ones(p_death)) + list(np.zeros(100-p_death))
    draw_transmit = list(np.ones(p_transmit)) + list(np.zeros(100-p_transmit))
    
    # Count the number of deaths at this time step
    num_new_dead = 0
        
    # Get indices of all sick people. We only do stuff with people who are infected right now
    infected_indices = [i for i, x in enumerate(people_array) if x == -1]
        
    for num in infected_indices:
            
        # If they are above the duration, then set them to 1, which indicates that the illness is finished
        if days_sick[num] > sick_duration:
            people_array[num] = 1
            
            # For the people who finished the illness, draw a random number to determine whether or not they die
            if np.random.choice(draw_death) == 1:
                num_new_dead += 1

        # If they are still in the infectious period, inclusive
        elif infectious_duration[0] <= days_sick[num] <= infectious_duration[1]:

            # They infect the same number of people on each day of the infectious duration
            num_new_infected += np.round(r0[num] / (infectious_duration[1] - infectious_duration[0]))
            
            days_sick[num] += 1

        # For all sick people who are not infectious, increase the number of days they've been sick
        else:
            days_sick[num] += 1
                
    # Get the indices of the people who came into contact with infectious individuals 
    new_indices = np.random.randint(len(people_array), size=int(num_new_infected))
    
    # If they have never been infected, make them sick according to a coin flip probability
    for i in range(len(new_indices)):
        
        # if they are susceptible (never been infected before)
        if people_array[new_indices[i]] == 0:
            
            # take into account transmission probability
            if np.random.choice(draw_transmit) == 1:
                people_array[new_indices[i]] = -1           
    
    # this includes people who recovered and people who died
    num_immune = list(people_array).count(1)
    
    # number of newly dead people already determined above
    num_recovered = num_immune - num_new_dead
    num_susceptible = list(people_array).count(0)
    num_infected = list(people_array).count(-1)

    return (num_infected, num_recovered, num_new_dead, num_susceptible)


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

# Create throttled widget for the probability of transmission to an exposed contact
transmit_rate_slider = pn.widgets.IntSlider(
    name='Transmit Rate (%)', 
    start=1,
    end=100,
    step=1,
    value=100,
    value_throttled=100)

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
    
button = pn.widgets.Button(name="Update Dashboard", button_type="success")

left_col = pn.Column(R0_input, N_input, death_rate_slider, width=250)
middle_col = pn.Column(pn.Spacer(height=3), init_sick_slider, immune_slider, pn.Spacer(height=3), button, width=250)
right_col = pn.Column(illness_input, infectious_range, transmit_rate_slider, width=250)

widgets = pn.Row(left_col, pn.Spacer(width=20), middle_col, pn.Spacer(width=20), right_col)

# Make the r0 distribution plot
@pn.depends(R0_input.param.value, N_input.param.value)
def plot_r0(R0, N):

    R0 = float(R0)
    N = int(N)
    r0 = np.random.geometric(1/R0, N)

    p = iqplot.histogram(r0,
                         rug=False,
                         height=plot_height,
                         width=(total_width-plot_width),
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
            transmit_rate_slider.param.value_throttled,
            immune_slider.param.value_throttled)
def run_plot_simulation(N, R0, init_sick, illness_duration, infectious_duration, p_death, p_transmit, p_immune):

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

        results.append(infect_more_people(r0, people_array, days_sick, illness_duration, infectious_duration, p_death, p_transmit))

        num_days += 1

    sick, immune, dead, susceptible = list(zip(*results))
    
    # Get cumulative deaths, rather than deaths on each day
    cumul_dead = [dead[0]] 

    for i in range(len(dead)-1):
        cumul_dead.append(cumul_dead[i] + dead[i+1])
    
    # Get cumulative recoveries and set the first number to the initial immune population
    cumul_recov = N - np.array(sick) - np.array(cumul_dead) - np.array(susceptible)
    cumul_recov[0] = num_immune

    df = pd.DataFrame.from_dict({"day": np.arange(num_days+1),
                                 "sick": sick, 
                                 "recovered": cumul_recov, 
                                 "cumul_dead": cumul_dead, 
                                 "susceptible": susceptible})

    source = bokeh.models.ColumnDataSource(df)
    
    # Width of the lines
    w = 2
    
    TOOLTIPS = [
        ("Infected", "@sick"),
        ("Susceptible", "@susceptible"),
        ("Recovered", "@recovered"),
        ("Cumulative Deaths", "@cumul_dead"),
    ]

    p_results = bokeh.plotting.figure(height=plot_height, width=plot_width,
                                      x_axis_label="Days",
                                      y_axis_label="Number of People",
                                      title="Simulation Results",
                                      toolbar_location="above",
                                      tooltips=TOOLTIPS)

    r1 = p_results.line(x="day", y="sick", source=source, line_width=w)
    r2 = p_results.line(x="day", y="recovered", source=source, color="green", line_width=w)
    r3 = p_results.line(x="day", y="cumul_dead", source=source, color="tomato", line_width=w)
    r4 = p_results.line(x="day", y="susceptible", source=source, color="orange", line_width=w)

    legend = bokeh.models.Legend(items=[
        ("Infected"   , [r1]),
        ("Susceptible" , [r4]),
        ("Recovered" , [r2]),
        ("Cumulative Deaths", [r3]),
    ], location="center")

    # Formatting
    p_results.add_layout(legend, 'right')
    p_results.xgrid.visible = False
    p_results.title.text_font_size = '14pt'
    p_results.legend.click_policy="hide"
    p_results

    return p_results

# Make the plot using the default widget parameters
plot_results = run_plot_simulation(N_input.value, R0_input.value, 
                                   init_sick_slider.value_throttled, illness_input.value, infectious_range.value_throttled, 
                                   death_rate_slider.value_throttled, transmit_rate_slider.value_throttled, immune_slider.value_throttled)

# For horizontal orientation
tab1 = pn.Row(pn.Spacer(width=50),
                pn.Column(
                    pn.Row(pn.layout.HSpacer(), widgets, pn.layout.HSpacer()),
                    pn.Spacer(height=10),
                    pn.Row(plot_r0(R0_input.value, N_input.value), 
                           pn.Spacer(width=30), 
                           plot_results,
                           )
                )
        )

# the next two functions are dependent on the button
def update_r0(event): 
    
    tab1[1][2][0].object = plot_r0(R0_input.value, N_input.value)

def update_results(event): 
    
    plot1 = bokeh.plotting.figure(height=plot_height, width=plot_width,
                                      x_axis_label="Days",
                                      y_axis_label="Number of People",
                                      title="Loading...",
                                      toolbar_location="above")
    
    # make an empty dataframe to plot phantom data
    phantom_source = bokeh.models.ColumnDataSource(data=dict(sick=[], recovered=[], cumul_dead=[], susceptible=[]))
    
    # Width of the lines
    w = 2
    
    r1 = plot1.line(x="day", y="sick", source=phantom_source, line_width=w)
    r2 = plot1.line(x="day", y="recovered", source=phantom_source, color="green", line_width=w)
    r3 = plot1.line(x="day", y="cumul_dead", source=phantom_source, color="tomato", line_width=w)
    r4 = plot1.line(x="day", y="susceptible", source=phantom_source, color="orange", line_width=w)

    legend = bokeh.models.Legend(items=[
        ("Infected"   , [r1]),
        ("Recovered" , [r2]),
        ("Cumulative Deaths", [r3]),
        ("Susceptible" , [r4]),
    ], location="center")

    # Formatting
    plot1.add_layout(legend, 'right')
    plot1.xgrid.visible = False
    
    plot1.title.text_font_size = '14pt'
    
    tab1[1][2][-1].object = plot1
    
    plot2 = run_plot_simulation(N_input.value, R0_input.value, 
                                   init_sick_slider.value_throttled, illness_input.value, infectious_range.value_throttled, 
                                   death_rate_slider.value_throttled, transmit_rate_slider.value_throttled, immune_slider.value_throttled)
    
    plot2.title.text_font_size = '14pt'
    tab1[1][2][-1].object = plot2
    
    
# link the functions to the button
button.on_click(update_r0)
button.on_click(update_results)

# Make the app
layout = pn.Tabs(("Simulation", tab1))
layout.servable()
