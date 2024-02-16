'''
===================================
Author: Stavros Orfanoudakis 2023
===================================
'''
import numpy as np


class Transformer():
    """
    Transformer class for the ev_city environment


    """

    def __init__(self,
                 id,  # unique identifier of the transformer
                 env,
                 max_current=250,  # The maximum capacity of the transformer in A
                 max_power=100,  # The maximum power of the transformer in kW
                 max_power_or_current_mode='current',  # 'current' or 'power'
                 cs_ids=[],  # the charging stations connected to the transformer
                 inflexible_load=np.zeros(96),
                 solar_power=np.zeros(96),
                 simulation_length=96
                 ):
        """
        Initialize the transformer

        :param id: unique identifier of the transformer
        :type id: int
        :param max_current: The maximum capacity of the transformer in A, defaults to 150
        :type max_current: int, optional
        :param min_current: The minimum capacity of the transformer in A, defaults to 0
        :type min_current: int, optional
        :param cs_ids: the charging stations connected to the transformer, defaults to []
        :type cs_ids: list, optional
        :param timescale: the timescale of the simulation, defaults to 5
        :type timescale: int, optional

        """

        self.id = id
        self.max_current = np.ones(simulation_length)*max_current
        self.min_current = np.ones(simulation_length) * -max_current
        self.max_power = np.ones(simulation_length)*max_power
        self.min_power = np.ones(simulation_length) * -max_power

        self.max_power_or_current_mode = max_power_or_current_mode
        self.inflexible_load = inflexible_load        
        self.solar_power = solar_power                

        self.cs_ids = cs_ids
        self.simulation_length = simulation_length

        self.current_amps = 0
        self.current_power = 0

        self.current_step = 0
        
        if env.config['inflexible_loads']['include']:
            self.normalize_inflexible_loads(env)
            self.generate_demand_response_events(env)
        
        if env.config['solar_power']['include']:
            self.normalize_pv_generation(env)    
            self.generate_pv_generation_forecast(env)                            

    def generate_demand_response_events(self, env) -> None:
        '''
        This function is used to generate demand response events using the configuration file
        and by updating the transformer loading
        '''
        events_per_day = env.config['demand_response']['events_per_day']

        event_length_minutes_min = env.config['demand_response']['event_length_minutes_min']
        event_length_minutes_max = env.config['demand_response']['event_length_minutes_max']

        event_start_hour_mean = env.config['demand_response']['event_start_hour_mean']
        event_start_hour_std = env.config['demand_response']['event_start_hour_std']
        event_capacity_percentage_mean = env.config['demand_response']['event_capacity_percentage_mean']
        event_capacity_percentage_std = env.config['demand_response']['event_capacity_percentage_std']

        for i in range(events_per_day):

            event_length_minutes = np.random.randint(
                event_length_minutes_min, event_length_minutes_max)

            event_start_hour = np.random.normal(
                event_start_hour_mean*60, event_start_hour_std*60)

            event_start_hour = np.clip(event_start_hour, 0, 23*60)
            event_start_step = event_start_hour // env.timescale

            sim_start_step = (env.sim_date.hour * 60 +
                              env.sim_date.minute) // env.timescale
            event_start_step = int(event_start_step - sim_start_step)

            event_end_step = int(event_start_step +
                                 event_length_minutes // env.timescale)

            capacity_percentage = np.random.normal(
                event_capacity_percentage_mean, event_capacity_percentage_std)
            capacity_percentage = np.clip(capacity_percentage, 0, 100)

            self.max_power[event_start_step:event_end_step] = self.max_power[event_start_step:event_end_step] - \
                (self.max_power[event_start_step:event_end_step] *
                    capacity_percentage/100)

            self.max_current[event_start_step:event_end_step] = self.max_current[event_start_step:event_end_step] - \
                (self.max_current[event_start_step:event_end_step] *
                    capacity_percentage/100)

            if any(self.inflexible_load[event_start_step:event_end_step] >
                   self.max_power[event_start_step:event_end_step]):
                self.max_power[event_start_step:event_end_step] = self.inflexible_load[event_start_step:event_end_step].max(
                )

    def normalize_pv_generation(self, env) -> None:
        '''
        Normalize the solar_power using the configuration file and teh max_power of the transformer
        '''
        if env.config['solar_power']['include']:            
            mult = env.config['solar_power']['solar_power_capacity_multiplier_mean'] 
            mult = np.random.normal(mult, 0.1)
            self.solar_power = -self.solar_power * \
                mult * max(self.max_power) 
    
    def generate_pv_generation_forecast(self, env) -> None:
        '''
        This function is used to generate pv generation forecast using the configuration file
        '''
        forecast_uncertainty_mean = env.config['solar_power']['forecast_mean'] / 100 * \
            self.solar_power

        forecast_uncertainty_std = env.config['solar_power']['forecast_std'] / 100 * \
            self.solar_power

        self.pv_generation_forecast = np.random.normal(
            forecast_uncertainty_mean,
            abs(forecast_uncertainty_std),
            len(self.solar_power))                                               
    
    def normalize_inflexible_loads(self, env) -> None:
        '''
        Check that infelxible_loads are lower than the max_power, if not, set them to the max_power
        '''

        if env.config['inflexible_loads']['include']:            
            mult = env.config['inflexible_loads']['inflexible_loads_capacity_multiplier_mean']
            mult = np.random.normal(mult, 0.1)

            # scale up the data to match the max_power of the transformers
            self.inflexible_load = self.inflexible_load * \
                mult * (max(self.max_power) /
                        self.inflexible_load.max()+0.00001)
            # for each step
            for j in range(env.simulation_length):
                if self.inflexible_load[j] > self.max_power[j]:
                    self.inflexible_load[j] = self.max_power[j]

                elif self.inflexible_load[j] < self.min_power[j]:
                    self.inflexible_load[j] = self.min_power[j]                

        self.generate_inflexible_loads_forecast(env)
        
    def generate_inflexible_loads_forecast(self, env) -> None:
        '''
        This function is used to generate inflexible loads forecast using the configuration file
        '''
        forecast_uncertainty_mean = env.config['inflexible_loads']['forecast_mean'] / 100 * \
            self.inflexible_load

        forecast_uncertainty_std = env.config['inflexible_loads']['forecast_std'] / 100 * \
            self.inflexible_load

        self.infelxible_load_forecast = np.random.normal(
            forecast_uncertainty_mean,
            forecast_uncertainty_std,
            len(self.inflexible_load))              

    def reset(self, step) -> None:
        '''
        Reset the current power of the transformer
        '''
        self.current_step = step

        self.current_power = self.inflexible_load[step]
        self.current_amps = (self.current_power * 1000) / 400

    def step(self, amps, power) -> None:
        '''
        Update current power of the transformer
        '''
        self.current_amps += amps
        self.current_power += power

    def is_overloaded(self) -> bool:
        '''
        Check if the transformer is overloaded

        Returns:
            - True if the transformer is overloaded
            - False if the transformer is not overloaded
        '''
        e = 0.0001

        if self.max_power_or_current_mode == 'power':
            if self.current_power > self.max_power[self.current_step] + e \
                    or self.current_power < self.min_power[self.current_step] - e:
                return True
        else:
            if self.current_amps > self.max_current[self.current_step] + e \
                    or self.current_amps < self.min_current[self.current_step] - e:

                return True

        return False

    def get_how_overloaded(self) -> float:
        '''
        Check how overloaded the transformer is

        Returns:
            - a amps value if the transformer is overloaded
        '''
        if self.is_overloaded():
            if self.max_power_or_current_mode == 'power':
                return np.abs(self.current_power - self.max_power[self.current_step])
            else:
                return np.abs(self.current_amps - self.max_current[self.current_step])
        else:
            return 0

    def __str__(self) -> str:
        if self.max_power_or_current_mode == 'power':
            return f'  - Transformer {self.id}:  {self.min_power[self.current_step]:.1f} / ' +\
                f'{self.current_power:5.1f} /{self.max_power[self.current_step]:5.1f} kW' +\
                f'\tCSs: {self.cs_ids}'
        else:
            return f'  - Transformer {self.id}:  {self.min_current[self.current_step]:.1f} / ' +\
                f'{self.current_amps:5.1f} /{self.max_current[self.current_step]:5.1f} A' +\
                f'\tCSs: {self.cs_ids}'
