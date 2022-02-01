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

def infect_more_people(r0, people_array, days_sick, sick_duration, infectious_duration, p_death, birth_rate, death_rate):
    
    # Count the number of new infections at this time step (a day)
    num_new_infected = 0
    
    # Make drawing list based on the death rate, which is a decimal to the hundredth place
    draw_death = list(np.ones(p_death)) + list(np.zeros(100-p_death))
    
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
    
    # If they have never been infected, make them sick. No probability here because we're already using R for each person to determine how many contacts they infect
    for i in range(len(new_indices)):
        
        # if they are susceptible (never been infected before). Leave immune people alone at this step
        if people_array[new_indices[i]] == 0:
            people_array[new_indices[i]] = -1           
    
    # this includes people who recovered and people who died
    num_immune = list(people_array).count(1)
    
    # number of newly dead people already determined above
    num_recovered = num_immune - num_new_dead
    
    num_susceptible = list(people_array).count(0)
    num_infected = list(people_array).count(-1)
    
    total_people = num_infected + num_recovered + num_new_dead + num_susceptible
        
    # birth and death rates are per year, and the time steps for this simulation are days
    # add births to susceptible population, add deaths to dead population
    # keep it simple, assume people in all 4 groups are equally likely to die
    new_births = int(birth_rate / 1000 * total_people)
    num_susceptible += new_births
    
    # babies born are all susceptible, so update the arrays that are keeping track
    new_people_array = np.concatenate((people_array, np.zeros(new_births)))
    r0_new_array = np.concatenate((r0, np.random.geometric(1/np.mean(r0), new_births)))
    days_sick_new = np.concatenate((days_sick, np.zeros(new_births)))

    other_deaths = int(death_rate / 1000 * total_people)
    
    # death rate is for other causes, not including this infectious disease because it was the baseline death rate before the epidemic
    # so the deaths should be removed from the susceptible and recovered populations, making them smaller
    return (num_infected, num_recovered-int(other_deaths/2), num_new_dead, num_susceptible-int(other_deaths/2), new_people_array, r0_new_array, days_sick_new)


R0_input = pn.widgets.TextInput(name=u'R\u2080', value='2.5')
N_input = pn.widgets.TextInput(name='Population Size', value='1000')

illness_input = pn.widgets.TextInput(name='Duration of Illness (days)', value='14')

# Create throttled widget for the death rate
fatality_rate_slider = pn.widgets.IntSlider(
    name='Fatality Rate (%)', 
    start=0,
    end=100,
    step=1,
    value=5,
    value_throttled=5)

birth_rate_slider = pn.widgets.IntSlider(
    name='Birth Rate (per 1,000)', 
    start=0,
    end=100,
    step=1,
    value=11,
    value_throttled=11)

death_rate_slider = pn.widgets.IntSlider(
    name='Death Rate (per 1,000)', 
    start=0,
    end=100,
    step=1,
    value=10,
    value_throttled=10)

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

left_col = pn.Column(R0_input, N_input, fatality_rate_slider, width=250)
middle_col = pn.Column(pn.Spacer(height=3), init_sick_slider, immune_slider, pn.Spacer(height=3), button, width=250)
right_col = pn.Column(illness_input, infectious_range, birth_rate_slider, death_rate_slider, width=250)

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
            fatality_rate_slider.param.value_throttled,
            immune_slider.param.value_throttled,
            birth_rate_slider.param.value_throttled,
            death_rate_slider.param.value_throttled)
def run_plot_simulation(N, R0, init_sick, illness_duration, infectious_duration, p_death, p_immune, birth_rate, death_rate):

    ### Parameters and initial conditions ###
    
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

    ### Run the simulation ####
    
    num_days = 0
    results = [(init_sick, num_immune, 0, len(indices_susceptible)-init_sick)]
    
    # need to keep track of the population size as a function of time
    Nt = [N]

    # Call the infect_more_people function until there are no more sick people (epidemic stops)
    while list(people_array).count(-1) != 0:
        
        step = infect_more_people(r0, people_array, days_sick, illness_duration, infectious_duration, p_death, birth_rate, death_rate)
        
        # update the people array after the step
        people_array, r0, days_sick = step[-3:]
        results.append(step[:-3])
        Nt.append(len(people_array))
        
        num_days += 1

    sick, immune, dead, susceptible = list(zip(*results))
    
    # Get cumulative deaths, rather than deaths on each day
    cumul_dead = [dead[0]] 

    for i in range(len(dead)-1):
        cumul_dead.append(cumul_dead[i] + dead[i+1])
    
    # Get cumulative recoveries and set the first number to the initial immune population
    cumul_recov = Nt - np.array(sick) - np.array(cumul_dead) - np.array(susceptible)
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
        ("Deaths", "@cumul_dead"),
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
        ("Deaths", [r3]),
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
                                   fatality_rate_slider.value_throttled, immune_slider.value_throttled, 
                                   birth_rate_slider.value_throttled, death_rate_slider.value_throttled)

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
                                   fatality_rate_slider.value_throttled, immune_slider.value_throttled,
                                birth_rate_slider.value_throttled, death_rate_slider.value_throttled)
    
    plot2.title.text_font_size = '14pt'
    tab1[1][2][-1].object = plot2
    
    
# link the functions to the button
button.on_click(update_r0)
button.on_click(update_results)

# Create an HTML page for the first tab

html_pane = pn.pane.HTML("""
<center><h1><b>Epidemiological Simulation and the SEIRD Model</b></h1></center><br>
<center>
<div style='width:80%; text-align: justify; font-size:16pt;'>
Mathematical models are very useful in epidemiology to forecast the spread of a disease and predict how interventions like vaccination and isolation will affect the course of an epidemic. In this interactive web tool, you can observe the spread of a simulated disease in a closed population under different sets of parameters and compare the results to a mathematical model based on ordinary differential equations. 
</div>
</center>
<center><h1><b>Simulation</b></h1></center><br>
<center>
<div style='width:80%; text-align: justify; font-size:16pt;'>
The interactive tool simulates a simple outbreak spreading through a closed population. It is a <b>stochastic model</b>, meaning that there is an element of randomness. Initializing the simulation with the same parameters can lead to different solutions because of the randomness.
The simulation makes the following assumptions:
<ul>
    <li>This is a semi-closed population: people are born and die of causes other than the spreading infectious disease, but no people immigrate into the population and no one emigrates out of it.</li>
    <li>The population is well-mixed: the probability of a person getting infected is based only on the number of contacts they have, but the simulation doesn't take geography into account.</li>
    <li>When people recover from the infection, they are immune for life and will not be infected or able to transmit the disease again.</li>
</ul>
<br>
The epidemic ends when the number of infected cases drops to 0. Based on the size of the population and how the infection transmitted, some susceptible people may remain in the population.
</div>
</center>
<center>
<h1><b>SEIRD Model</b></h1><br>
<div style='width:80%; text-align: justify; font-size:16pt;'>
The SEIRD model is a type of <b>compartmental model</b> that considers only the overall behavior of a group of people. It is different from an <b>individual model</b>, which takes into account the actions of individual people. The simulation described above does treat people as individuals, but the model only considers the following large groups: 
<ul>
    <li><b>Susceptible</b>: Can be infected.</li>
    <li><b>Exposed</b>: Have been in contact with an infected person, but can not yet spread the infection to others.</li>
    <li><b>Infectious</b>: Currently infectious (able to spread the infection to others).</li>
    <li><b>Recovered</b>: Recovered from the infection and are now totally immune (unable to get infected again).</li>
    <li><b>Dead</b>: Died of the infection.</li>
</ul>
</div>
</center>
""",
#                         style={'background-color': '#F6F6F6', 'border': '2px solid black',
#             'border-radius': '5px', 'padding': '10px'}
                        )

# Make the app
layout = pn.Tabs(("About", html_pane), ("Simulation", tab1))
layout.servable()
