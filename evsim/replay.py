'''
===================================
Author: Stavros Orfanoudakis 2023
===================================
'''

import os
import numpy as np
from .utils import get_statistics

class EvCityReplay():
    '''
    This class is used to save the simulation data in a pickle file.
    The pickle file can be used to create a math model of the simulation.    
    '''

    def __init__(self, env):

        # Create replay folder if it does not exist
        if not os.path.exists('replay'):
            os.makedirs('replay')

        self.stats = get_statistics(env)

        self.replay_path = env.replay_path + 'replay_' + env.sim_name + '.pkl'
        self.sim_name = env.sim_name + '_replay'
        self.sim_length = env.simulation_length
        self.n_cs = env.cs
        self.n_transformers = env.number_of_transformers
        self.timescale = env.timescale
        self.score_threshold = env.score_threshold
        self.sim_date = env.sim_starting_date
        self.cs_transformers = env.cs_transformers
        self.power_setpoints = env.power_setpoints

        self.transformers = env.transformers
        self.charging_stations = env.charging_stations
        self.EVs = env.EVs

        # self.transformer_amps  = env.transformer_amps
        # self.cs_power = env.cs_power
        # self.port_power = env.port_power
        
        self.simulate_grid = env.simulate_grid

        self.charge_prices = env.charge_prices
        self.discharge_prices = env.discharge_prices

        self.tra_max_amps = np.ones([self.n_transformers])
        self.tra_min_amps = np.ones([self.n_transformers])

        for i, tra in enumerate(env.transformers):
            self.tra_max_amps[i] = tra.max_current
            self.tra_min_amps[i] = tra.min_current

        self.port_max_charge_current = np.ones([self.n_cs])
        self.port_min_charge_current = np.ones([self.n_cs])
        self.port_max_discharge_current = np.ones([self.n_cs])
        self.port_min_discharge_current = np.ones([self.n_cs])
        self.voltages = np.ones([self.n_cs])

        self.cs_ch_efficiency = np.ones([self.n_cs, self.sim_length])
        self.cs_dis_efficiency = np.ones([self.n_cs, self.sim_length])
        self.cs_transformer = np.ones([self.n_cs])

        self.max_n_ports = 0

        for i, cs in enumerate(env.charging_stations):
            self.port_max_charge_current[i] = cs.max_charge_current
            self.port_min_charge_current[i] = cs.min_charge_current
            self.port_max_discharge_current[i] = cs.max_discharge_current
            self.port_min_discharge_current[i] = cs.min_discharge_current
            self.voltages[i] = cs.voltage

            #consider usecases with variable number of ports per cs
            if cs.n_ports > self.max_n_ports:
                self.max_n_ports = cs.n_ports

            self.cs_transformer[i] = cs.connected_transformer

        self.ev_max_energy = np.zeros([self.max_n_ports,
                                      self.n_cs,
                                      self.sim_length])  # ev max battery capacity, 0 if no ev is there
        self.ev_min_energy = np.zeros([self.max_n_ports,
                                       self.n_cs,
                                       self.sim_length])  # ev min battery capacity, 0 if no ev is there
        self.ev_max_ch_power = np.zeros([self.max_n_ports,
                                         self.n_cs,
                                         self.sim_length])  # ev max charging power, 0 if no ev is there
        self.ev_min_ch_power = np.zeros([self.max_n_ports,
                                         self.n_cs,
                                         self.sim_length])  # ev min charging power, 0 if no ev is there
        self.ev_max_dis_power = np.zeros([self.max_n_ports,
                                          self.n_cs,
                                          self.sim_length])  # ev max discharging power, 0 if no ev is there
        self.ev_min_dis_power = np.zeros([self.max_n_ports,
                                          self.n_cs,
                                          self.sim_length])  # ev min discharging power, 0 if no ev is there
        self.u = np.zeros([self.max_n_ports,
                           self.n_cs,
                           self.sim_length])  # u is 0 if port is empty and 1 if port is occupied
        self.energy_at_arrival = np.zeros([self.max_n_ports,
                                           self.n_cs,
                                           self.sim_length])  # x when ev arrives at the port
        self.ev_arrival = np.zeros([self.max_n_ports,
                                    self.n_cs,
                                    self.sim_length])  # 1 when an ev arrives-> power = 0 and energy = x
        self.t_dep = np.zeros([self.max_n_ports,
                               self.n_cs,
                               self.sim_length])  # time of departure of the ev, 0 if port is empty
        self.ev_des_energy = np.zeros([self.max_n_ports,
                                       self.n_cs,
                                       self.sim_length])  # desired energy of the ev, 0 if port is empty

        for i, ev in enumerate(env.EVs):
            port = ev.id
            cs_id = ev.location
            t_arr = ev.time_of_arrival
            original_t_dep = ev.earlier_time_of_departure
            # print(f'EV {i} is at port {port} of CS {cs_id} from {t_arr} to {original_t_dep}')

            if t_arr >= self.sim_length:
                continue
            if original_t_dep >= self.sim_length:
                t_dep = self.sim_length
            else:
                t_dep = original_t_dep

            self.ev_max_energy[port, cs_id, t_arr:t_dep] = ev.battery_capacity
            # self.ev_min_energy[port, cs_id, t_arr:t_dep] = ev.battery_capacity * ev.min_soc
            self.ev_max_ch_power[port, cs_id,
                                 t_arr:t_dep] = ev.max_ac_charge_power
            # self.ev_min_ch_power[port, cs_id,
            #                      t_arr:t_dep] = 0
            self.ev_max_dis_power[port, cs_id,
                                  t_arr:t_dep] = -ev.max_discharge_power
            # self.ev_min_dis_power[port, cs_id,
            #                       t_arr:t_dep] = 0
            self.u[port, cs_id, t_arr:t_dep] = 1
            self.energy_at_arrival[port, cs_id,
                                   t_arr] = ev.battery_capacity_at_arrival
            self.ev_arrival[port, cs_id, t_arr] = 1
            if original_t_dep < self.sim_length:
                self.t_dep[port, cs_id, t_dep] = 1
                self.ev_des_energy[port, cs_id, t_dep] = ev.desired_capacity

        # print(f'u: {self.u}')
        # print(f'ev_arrival: {self.ev_arrival}')
        # print(f't_dep: {self.t_dep}')
        # print(f'ev_des_energy: {self.ev_des_energy}')
        # print(f'ev_max_energy: {self.ev_max_energy}')
        # print(f'ev_max_ch_power: {self.ev_max_ch_power}')
        # print(f'ev_max_dis_power: {self.ev_max_dis_power}')
