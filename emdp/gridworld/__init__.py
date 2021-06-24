"""
A simple grid world environment
"""
import matplotlib.pyplot as plt
import numpy as np

import emdp.actions
from . import txt_utilities
from . import builder_tools
from .helper_utilities import flatten_state, unflatten_state
from ..common import MDP


class GridWorldMDP(MDP):
    def __init__(self, goal):
        """
        (!) if terminal_states is not empty then there will be an absorbing state. So
            the actual number of states will be size x size + 1
            if there is a terminal state, it should be the last one.
        :param transition: Transition matrix |S| x |A| x |S|
        :param reward: Transition matrix |S| x |A|
        :param discount: discount factor
        :param initial_state: initial starting distribution
        :param terminal_states: Must be a list of (x,y) tuples.  use skip_terminal_state_conversion if giving ints
        :param size: the size of the grid world (i.e there are size x size (+ 1)= |S| states)
        :param seed:
        :param validate_arguments:
        """
        ascii_room = """
        #########
        #   #   #
        #       #
        #   #   #
        ## ### ##
        #   #   #
        #       #
        #   #   #
        #########"""[1:].split('\n')
        ascii_room = [row.strip() for row in ascii_room]
        # a = list(ascii_room[goal[0]])
        # a[goal[1]] = "g"
        # ascii_room[goal[0]] = "".join(a)

        char_matrix = txt_utilities.get_char_matrix(ascii_room)
        reward_spec = {goal: +1}

        grid_size = len(char_matrix[0])
        builder = builder_tools.TransitionMatrixBuilder(grid_size=grid_size, has_terminal_state=False)

        walls, empty_ = txt_utilities.ascii_to_walls(char_matrix)  # hacks
        empty = []
        for e in empty_:
            (e,), = flatten_state(e, grid_size, grid_size * grid_size).nonzero()
            empty.append(e)
        builder.add_grid(p_success=1)
        for (r, c) in walls:
            builder.add_wall_at((r, c))

        R = builder_tools.create_reward_matrix(builder.P.shape[0], builder.grid_size, reward_spec, action_space=builder.P.shape[1])
        # p0 = len(empty)
        p0 = flatten_state((1, 1), builder.grid_size, R.shape[0])
        p0[empty] = 1 / len(empty)

        transition, reward, discount, initial_state, terminal_states, size = builder.P, R, 0.9, p0, (), builder.grid_size
        seed, convert_terminal_states_to_ints = 1337, False

        if not convert_terminal_states_to_ints:
            terminal_states = list(map(lambda tupl: int(size * tupl[0] + tupl[1]), terminal_states))
        self.size = size
        self.human_state = (None, None)
        self.has_absorbing_state = len(terminal_states) > 0
        super().__init__(transition, reward, discount, initial_state, terminal_states, seed=seed)

    def reset(self):
        super().reset()
        self.human_state = self.unflatten_state(self.current_state)
        return self.current_state

    def flatten_state(self, state):
        """Flatten state (x,y) into a one hot vector"""
        return flatten_state(state, self.size, self.num_states)

    def unflatten_state(self, onehot):
        """Unflatten a one hot vector into a (x,y) pair"""
        return unflatten_state(onehot, self.size, self.has_absorbing_state)

    def step(self, action):
        state, reward, done, info = super().step(action)
        self.human_state = self.unflatten_state(self.current_state)
        return state, reward, done, info

    def set_current_state_to(self, tuple_state):
        return super().set_current_state_to(self.flatten_state(tuple_state).argmax())

    def plot_sa(self, title, data, scale_data=True, frame=(0, 0, 0, 0)):
        """ This is going to generate a quiver plot to visualize the policy graphically.
        It is useful to see all the probabilities assigned to the four possible actions in each state """

        if scale_data:
            scale = np.abs(data).max()
            data = data / (scale * 1.1)
        num_cols, num_rows = self.size, self.size
        num_states, num_actions = data.shape
        assert num_actions == 4

        direction = np.zeros((num_actions, 2))
        direction[emdp.actions.LEFT, :] = np.array((-1, 0))  # left
        direction[emdp.actions.RIGHT] = np.array((1, 0))  # right
        direction[emdp.actions.UP] = np.array((0, 1))  # up
        direction[emdp.actions.DOWN] = np.array((0, -1))  # down

        x, y = np.meshgrid(np.arange(num_rows), np.arange(num_cols))
        x, y = x.flatten(), y.flatten()
        figure = plt.figure()
        ax = plt.gca()

        for base, a in zip(direction, range(num_actions)):
            quivers = np.einsum("d,m->md", base, data[:, a])

            pos = data[:, a] > 0
            ax.quiver(x[pos], y[pos], *quivers[pos].T, units='xy', scale=2.0, color='g')

            pos = data[:, a] < 0
            ax.quiver(x[pos], y[pos], *-quivers[pos].T, units='xy', scale=2.0, color='r')

        x0, x1, y0, y1 = frame
        # set axis limits / ticks / etc... so we have a nice grid overlay
        ax.set_xlim((x0 - 0.5, num_cols - x1 - 0.5))
        ax.set_ylim((y0 - 0.5, num_rows - y1 - 0.5)[::-1])

        # ax.set_xticks(xs)
        # ax.set_yticks(ys)

        # major ticks

        ax.set_xticks(np.arange(x0, num_cols - x1, 1))
        ax.xaxis.set_tick_params(labelsize=5)
        ax.set_yticks(np.arange(y0, num_rows - y1, 1))
        ax.yaxis.set_tick_params(labelsize=5)

        # minor ticks
        ax.set_xticks(np.arange(*ax.get_xlim(), 1), minor=True)
        ax.set_yticks(np.arange(*ax.get_ylim()[::-1], 1), minor=True)

        ax.grid(which='minor', color='gray', linestyle='-', linewidth=1)
        ax.set_aspect(1)

        tag = f"plots/{title}"

        if scale_data:
            title += f"_{scale:.4f}"

        ax.set_title(title, fontdict={'fontsize': 8, 'fontweight': 'medium'})
        return tag, figure
