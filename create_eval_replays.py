from evsim import ev_city
from evsim_math_model import ev_city_model

import numpy as np
import os
import pickle
from utils.arg_parser import arg_parser

""""
This file is used to create replay files with optimal profits for evaluation purposes.
The replay files are saved in the replay folder and can be used to evaluate the performance of the RL agent."""


def evalreplay(number_of_charging_stations,
               n_transformers,
               steps,
               timescale,
               static_prices,
               save_opt_trajectories,
               save_replay):
    
    verbose = False

    env = ev_city.EVCity(cs=number_of_charging_stations,
                         number_of_ports_per_cs=2,
                         number_of_transformers=n_transformers,
                         static_ev_spawn_rate=True,
                         load_ev_from_replay=True,
                         load_prices_from_replay=False,
                         static_prices=static_prices,
                         load_from_replay_path=None,
                         empty_ports_at_end_of_simulation=True,
                         generate_rnd_game=True,
                         simulation_length=steps,
                         timescale=timescale,
                         score_threshold=1,
                         save_plots=False,
                         save_replay=True,
                         verbose=verbose,)

    new_replay_path = f"replay/replay_{env.sim_name}.pkl"
    # new_replay_path = replay_path

    _ = env.reset()
    rewards = []

    for i in range(steps):
        # all ports are charging instantly
        actions = np.ones(env.number_of_ports)
        if verbose:
            print(f'Actions: {actions}')

        new_state, reward, done, _ = env.step(
            actions, visualize=False)  # takes action
        rewards.append(reward)

        if verbose:
            print(f'Reward: {reward} \t Done: {done}')

        if done and i < steps - 1:
            # print(f'End of simulation at step {i}')
            exit()

    # Solve optimally
    math_model = ev_city_model.EV_City_Math_Model(
        sim_file_path=new_replay_path)
    opt_actions = math_model.get_actions()

    if static_prices:
        prices = "static"
    else:
        prices = "dynamic"

    group_name = f'{number_of_charging_stations}cs_{n_transformers}tr_{prices}_prices'

    # Simulate in the gym environment and get the rewards
    env = ev_city.EVCity(cs=number_of_charging_stations,
                         number_of_transformers=n_transformers,
                         load_ev_from_replay=True,
                         load_prices_from_replay=True,
                         load_from_replay_path=new_replay_path,
                         empty_ports_at_end_of_simulation=True,
                         replay_path="./replay/"+group_name+"/",
                         generate_rnd_game=False,
                         simulation_length=steps,
                         timescale=timescale,
                         save_plots=False,
                         save_replay=save_replay,
                         verbose=verbose,)
    _ = env.reset()
    rewards_opt = []

    trajectory_i = {"observations": [],
                    "actions": [],
                    "rewards": [],
                    "dones": []}

    for i in range(steps):
        # all ports are charging instantly
        # print(f'Optimal actions: {opt_actions[:,:,i]}')
        # print(f'Optimal actions: {opt_actions[:,:,i].T.reshape(-1)}')
        actions = opt_actions[:, :, i].T.reshape(-1)
        if verbose:
            print(f' OptimalActions: {actions}')

        new_state, reward, done, _ = env.step(
            actions, visualize=False)  # takes action
        rewards_opt.append(reward)

        if save_opt_trajectories:
            trajectory_i["observations"].append(new_state)
            trajectory_i["actions"].append(actions)
            trajectory_i["rewards"].append(reward)
            trajectory_i["dones"].append(done)

        if verbose:
            print(f'Reward: {reward} \t Done: {done}')

        if done:
            break

    if save_opt_trajectories:
        trajectory_i["observations"] = np.array(trajectory_i["observations"])
        trajectory_i["actions"] = np.array(trajectory_i["actions"])
        trajectory_i["rewards"] = np.array(trajectory_i["rewards"])
        trajectory_i["dones"] = np.array(trajectory_i["dones"])

    # delete the replay file
    os.remove(new_replay_path)

    return trajectory_i


if __name__ == "__main__":

    args = arg_parser()

    trajectories = []

    number_of_charging_stations = args.cs
    n_transformers = args.transformers
    prices = args.static_prices
    ev_spawn_rate = args.static_ev_spawn_rate
    steps = args.steps
    timescale = args.timescale
    score_threshold = args.score_threshold
    n_trajectories = args.n_trajectories

    prices = "static" if prices else "dynamic"
    ev_spawn_rate = "static" if ev_spawn_rate else "dynamic"

    file_name = f"optimal_{number_of_charging_stations}_cs_{n_transformers}_tr_{prices}_prices_{ev_spawn_rate}_ev_spawn_rate_{steps}_steps_{timescale}_timescale_{score_threshold}_score_threshold_{n_trajectories}_trajectories.pkl"

    save_folder_path = f"./trajectories/"
    if not os.path.exists(save_folder_path):
        os.makedirs(save_folder_path)

    for i in range(n_trajectories):
        print(f'Trajectory: {i}')
        trajectory = evalreplay(number_of_charging_stations=number_of_charging_stations,
                                n_transformers=n_transformers,
                                steps=steps,
                                timescale=timescale,
                                static_prices=prices,
                                save_opt_trajectories=True,
                                save_replay=False)
        trajectories.append(trajectory)

        if i % 1000 == 0:
            print(f'Saving trajectories to {save_folder_path+file_name}')
            f = open(save_folder_path+file_name, 'wb')
            # source, destination
            pickle.dump(trajectories, f)
            f.close()
