# Things to add
# 
# adversarial nest
# danger pheromones
# play with pheromone decay and whatnot 



from threading import Thread
import time
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from time import sleep
import pandas as pd
import random
import os, shutil
import geopandas as gpd
import concurrent.futures
from shapely.geometry import Point, LineString
import plotly_express as px
import osmnx as ox
# Used for interactive city location
import ipywidgets as widgets
from ipywidgets import interact, interact_manual, IntSlider
from IPython.display import display
from geopy.geocoders import Nominatim




ox.config(use_cache=True, log_console=True)


class city():
    """
    This class creates a graph based off of a city using Open Street Maps.
    
    This is accomplished by sending it coordinates (Latitude,Longitude).
    
    Init
    ----
        Parameters
        ----------
        lat : float
            latitude of city
        lon :
            longitude of city
        size : int
            radius from center you want to include in the map
        network_type : str
            chose which types of edges you want to include
            ‘drive’ – get drivable public streets (but not service roads)
            ‘drive_service’ – get drivable public streets, including service roads
            ‘walk’ – get all streets and paths that pedestrians can use (this network type ignores one-way directionality)
            ‘bike’ – get all streets and paths that cyclists can use
            ‘all’ – download all (non-private) OSM streets and paths
            ‘all_private’ – download all OSM streets and paths, including private-access ones

    """
    def __init__(self, lat,lon,size,network_type,name):
        self.graph = ox.graph_from_point((lat, lon), dist=size, network_type=network_type)
        fig = plt.figure()
        fig, ax = ox.plot_graph(self.graph,node_color='w',node_edgecolor='w',node_size=10, node_zorder=3, edge_color='w', edge_linewidth=2, close=True,bgcolor = 'black')
        fig.savefig('images/'+name+'/'+'aph'+'.jpg', dpi = 100)
    def make_two_way_streets(self):
        """
        For each A-B node in self.graph make sure there is a B-A node
        """
        print("starting len", len(list(self.graph.edges(keys=False))))
        remove_edges = []
        for key,value,n in self.graph.edges(keys=True):
            if n > 0:
                remove_edges.append((key,value))
        self.graph.remove_edges_from(remove_edges)
        counter = 0
        for edge in self.graph.edges(keys=False):
            if (edge[1],edge[0]) not in self.graph.edges:
                edge_to_add = (edge[1],edge[0])
                self.graph.add_edge(*edge_to_add, 
                           length = self.graph.edges[(edge[0],edge[1],0)]['length'], 
#                            highway = self.graph.edges[(edge[0],edge[1],0)]['highway'],
#                            osmid = self.graph.edges[(edge[0],edge[1],0)]['osmid'],
#                            oneway = self.graph.edges[(edge[0],edge[1],0)]['oneway']
                          )
        print("ending len",len(list(self.graph.edges(keys=True))))


class food_pheromone(object):
    """
    This class stores and manipulates pheromones that ants drop on edges
    
    Parameters
    ----------
        graph : city object
        nest : int
    """
    def __init__(self, graph,nest):
        self.food_in_nest = 0
        self.counter = 1
        self.graph = graph 
        self.pheromone = dict.fromkeys(self.graph.edges(), 0)
        self.discovered_nodes = []
        self.ec = []
        self.nc = []
        self.food_source = []
        self.nest = nest
        
    def add_pheromone(self, edge, release_amount):
        """
        Add given pheromone amount to given edge(A,B) and edge(B,A).
        
        Parameters
        ----------
            edge : tuple
            release_amount : int
        """
        self.pheromone[edge] += release_amount
        self.pheromone[(edge[1],edge[0])] += release_amount
        
    def add_global_pheromone(self, amount):
        """
        Add pheromone to each edge in graph
        
        Parameters
        ----------
            amount : int
        """
        for key,value in self.pheromone.items():
            self.pheromone[key] += (amount)
            
    def decay_pheromone(self,color_start,amount):
        """
        Subtract an amount from each edge that has pheromones until it has reached 0.
        
        Parameters
        ----------
            amount : int
        """
        for key,value in self.pheromone.items():
            if value > color_start: 
                if ((self.pheromone[key] - amount) < color_start):
                    self.pheromone[key] = color_start
                    self.pheromone[(key[0],key[1])] = color_start
                else:
                    self.pheromone[key] -= amount
                    self.pheromone[(key[0],key[1])] -= amount
                
    def edge_weight(self, edge):
        """
        Return edge weight
        
        Parameters
        ----------
            edge : tuple
        """
        return self.pheromone[edge]
    
    def update_graph(self, pheromone_release, name, color_start):
        """
        Update graph with new edge and node colors based off of pheromone concentration on edge. 
        Save each plot as a unique image.
        
        Parameters
        ----------
            pheromone_release : int
        """
        self.ec = []
        current_palette = sns.color_palette("rocket", 100,as_cmap=False)
        for start, end in self.graph.edges(keys=False):
            if(self.pheromone[(start,end)] > color_start): # this value 40 is dependent on other things with the execution code
                if (self.pheromone[(start,end)] >= 99):
                    self.pheromone[(start,end)] = 99
                this_color = current_palette[int(self.pheromone[(start,end)])]
                self.ec.append('#'+str(hex(int(this_color[0]*255))[2:]+hex(int(this_color[1]*255))[2:]+hex(int(this_color[2]*255))[2:]))
            else:
                self.ec.append('midnightblue')
        self.nc = ['midnightblue' if (n in self.discovered_nodes and not self.is_food_source(n) and not self.is_nest(n)) else '' 'lime' if (self.is_food_source(n) and not self.is_nest(n)) else '' 'orange' if (self.is_nest(n)) else 'midnightblue' for n in self.graph.nodes]
        fig = plt.figure()
        fig, ax = ox.plot_graph(self.graph,node_color=self.nc,node_size=25, 
              node_zorder=3, edge_color=self.ec, edge_linewidth=2, close=True,bgcolor = 'midnightblue')
        fig.savefig('images/'+name+'/'+'graph'+str(self.counter)+'.jpg', dpi = 100)
        self.counter += 1
        
    def add_discovered_node(self,node):
        """
        Add given node to list contianing nodes accessed.
        
        Parameters
        ----------
            node : int
        """
        self.discovered_nodes.append(node)
        
    def is_nest(self,node):
        """
        Is given node the nest wehre ants are spawned.
        
        Parameters
        ----------
            node : int
        """
        if (node == self.nest):
            return True
        return False
        
    def make_food_source(self, location):
        """ 
        Make given nodes a food source.
        
        Parameters
        ----------
            location : array
        """
        for i in range(len(location)):
            self.food_source.append(location[i])
    
    def print_food_sources(self):
        """
        Print food sources.
        """
        print("There are food sources here:", self.food_source)
    
    def is_food_source(self,location):
        """
        Check if given node is a food source.
        
        Parameters
        ----------
            location : int
        """
        if location in self.food_source:
            return True
        
    def nest_increment(self):
        """
        Increment food in nest by 1
        """
        self.food_in_nest += 1
        
    def nest_food_amount(self):
        """ 
        Return amount of food in nest
        """
        return self.food_in_nest
        


class ant_agent(object):
    """
    This class creates an agent which traverses the given graph dropping pheromones on each edge looking for food sources.
    Once food source is found the agent returns home and terminates.
    
    Parameters
    ----------
        graph : city object
        nest : int
        food : food_pheromone object
        pheromone_release : int
        name : str
    """
    def __init__(self, graph, nest, food, pheromone_release, name):
        self.location = nest
        self.graph = graph
        self.nest = nest
        self.total_edges_walked = 0
        self.food = food
        self.has_food = False
        self.previous_node = nest
        self.pheromone_release = pheromone_release
        food.add_discovered_node(nest)
        self.name = name
    def move(self):
        """
        This method has two main loops for agent to traverse graph until a food source is reached then head back to where it started.
        Method prints updates on location and current goal of agent.
        """
        print("Looking for food: ", self.name)
        while (not self.has_food):
            if isinstance(self.location,int):
                edge_choice = self.scout_food_from_node()
                self.location = edge_choice
                self.previous_node = edge_choice[0]
                
                node_choice = self.walk_along_edge(edge_choice)
                self.location = node_choice
                food.add_discovered_node(self.location)
                
                if food.is_food_source(self.location):
                    self.has_food = True
#                     print("Found food: ", self.name)
                    
#                 self.food.update_graph(pheromone_release, self.name)
            else:
                print("Invalid Location")
            self.total_edges_walked += 1

        print("Heading back to the nest: ", self.name)
        self.previous_node = self.location
        
        while (self.has_food):
            if isinstance(self.location,int):
                edge_choice = self.return_home_with_food()
                self.location = edge_choice
                self.previous_node = edge_choice[0]
            
                node_choice = self.walk_along_edge(edge_choice)
                self.location = node_choice
                food.add_discovered_node(self.location)
                
                if (self.location == self.nest):
                    self.has_food = False
#                     print("At nest with food: ", self.name)
                    
#                 self.food.update_graph(self.pheromone_release, self.name)
            else:
                print("Invalid Location")
            self.total_edges_walked += 1
            
        food.nest_increment()
        print("Amount of food in the nest: ",food.nest_food_amount(), ": ", self.name)
        print("Steps taken: ",self.total_edges_walked, ": ", self.name)
        
    def scout_food_from_node(self):
        """
        Chose path to take from node. 
        If there is only way to walk then agent is at a dead end and chose that path.
        If not in a dead end then delete path from where it came from.
        If all paths have no pheromones then chose random path
        Finally chose path with weighted probability with relationship to how many pheromones are on the edge.
        """
        options = [(start, end) for start, end in self.graph.edges(keys=False) if (start==self.location)]
        options = dict.fromkeys(options, 0)
        
        for key,value in options.items():
            options[key] = self.food.edge_weight(key)
        # go back if in dead end
        if (len(options.items()) == 1):
            return list(options.keys())[0]
        # delete path it came from
        try:
            del options[(self.location,self.previous_node)]
            del options[(self.previous_node,self.locatoin)]
        except:
            None          
        # all paths are same pheromone amounts
        all_new = len(list(set(list(options.values())))) == 1
        if all_new:
            key = random.choice(list(options.keys()))
            return key
        # weighted probability choice
        weighted_paths = list(options.keys())
        weighted_values = list(options.values())
        return random.choices(weighted_paths, weights = weighted_values, k = 1)[0]
    
    def return_home_with_food(self):
        """
        After food has been found return home.
        Similar to scout_food_from_node method.
        """
        options = [(start, end) for start, end in self.graph.edges(keys=False) if (start==self.location)]
        options = dict.fromkeys(options, 0)
        for key,value in options.items():
            options[key] = self.food.edge_weight(key)
        # if only way is back the way we came then go that way
        if (len(options.items()) == 1): 
            return list(options.keys())[0] 
        # all new paths
        all_new = len(list(set(list(options.values())))) == 1
        if all_new:
            key = random.choice(list(options.keys()))
            return key
        # delete path it came from
        try: 
            del options[(self.location,self.previous_node)]
            del options[(self.previous_node,self.locatoin)]
        except:
            None
        # weighted random choice
        weighted_paths = list(options.keys())
        weighted_values = list(options.values())
        return random.choices(weighted_paths, weights = weighted_values, k = 1)[0]
    
    def walk_along_edge(self, edge):
        """
        Have agent walk along path for given length, can include sleep(0.001) to model ant taking time to walk
        
        Parameters
        ----------
            edge : tuple
        """
        length = (self.graph.edges[(edge[0],edge[1],0)]['length'])
        self.food.add_pheromone(edge, self.pheromone_release)
        while(length > 0):
            length -= 1
            sleep(0.0001)
        sleep(0.04)
        return edge[1]
    


output_text = widgets.Text()
input_text = widgets.Text()
def get_city_name_from_user(text):
    output_text.value = input_text.value
    
input_text.on_submit(get_city_name_from_user)
print("Please enter city name, hit enter, then run cells below:")
print("Examples include: \nSan Francisco, CA\nRome\nParis\nMoscow, Russia\nBarcelona, Spain\nDubai")
display(input_text)

num_agents = widgets.IntText(
    value=7,
    description='',
    disabled=False
)
num_food_sources = widgets.IntText(
    value=7,
    description='',
    disabled=False
)
map_size = widgets.IntText(
    value=300,
    description='',
    disabled=False
)
print("Please enter the number of agents: ")
display(num_agents)
print("Please enter the number of food sources: ")
display(num_food_sources)
print("Please enter the radius of the map (km) (Small = 300, Medium = 700, Large = 1000): ")
display(map_size)


city_name = output_text.value.lower()
geolocator = Nominatim(user_agent='myapplication')
location = geolocator.geocode(city_name)
print("This is the city chosen:", location.address)
print("This is the number of ants chosen,food sources, and map size:", (num_agents.value),', ',num_food_sources.value, ', ',map_size.value,'km')
input_city_lat = location.latitude
input_city_lon = location.longitude
print(location.latitude,location.longitude)


# Initialize city class
chosen_city_obj = city(lat = input_city_lat, lon = input_city_lon, size=map_size.value, network_type='drive', name = 'chosen_city')  
chosen_city_obj.make_two_way_streets()

# Initialize food class
pheromone_release = 5 # free var
pheromone_decay = 2 # free var
color_start = 40 # free var
init_release = 0.1
amount_of_food_sources = num_food_sources.value
num_ants = (num_agents.value)

# Initialize nest, food sources, and set color pheromone variable 
nest = random.choice(list(chosen_city_obj.graph.nodes())) # random nest
food_sources = random.choices(list(chosen_city_obj.graph.nodes()),k=amount_of_food_sources) # chose k food sources
food = food_pheromone(chosen_city_obj.graph,nest) 
food.make_food_source(food_sources)
food.add_global_pheromone(color_start)

# make list of ant agent objects names 'abc'
ants = list()
for i in range(num_ants):
    ants.append(ant_agent(chosen_city_obj.graph, nest, food, pheromone_release, name = 'abc'))

# make list of ant agent objects that are threads
t_ants = []
for i in range(num_ants):
    t_ants.append(Thread(target=ants[i].move))

# at start release 10% of ants
for i in range(int(num_ants*init_release)):
    t_ants[i].start()
    
# release the other 90% of ants one every 0.5 seconds 
for i in range(int(num_ants*init_release),num_ants):
    food.decay_pheromone(color_start,pheromone_decay)
    food.update_graph(pheromone_release, 'chosen_city', color_start)
    time.sleep(0.5)
    t_ants[i].start()

# save graph every 0.01 seconds and decay pheromones 
for i in range(num_ants):
    while(t_ants[i].is_alive()):
        food.decay_pheromone(color_start,pheromone_decay)
        sleep(0.01)
        food.update_graph(pheromone_release, 'chosen_city', color_start)

# wait for all ants to stop
for i in range(num_ants):
    t_ants[i].join()


# delete all photos
folder = 'images/chosen_city'
for filename in os.listdir(folder):
    file_path = os.path.join(folder, filename)
    try:
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
    except Exception as e:
        print('Failed to delete get_ipython().run_line_magic("s.", " Reason: %s' % (file_path, e))")



# sns.set(rc={'figure.figsize': (1,1)})
# current_palette = sns.color_palette("rocket", 100,as_cmap=False)
# sns.palplot(current_palette)
# this_color = current_palette[99]

# print(this_color)
# my_color = str(hex(int(this_color[0]*255))+hex(int(this_color[1]*255))[2:]+hex(int(this_color[2]*255))[2:])

# print((my_color))

