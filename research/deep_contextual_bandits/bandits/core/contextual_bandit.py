# Copyright 2018 The TensorFlow Authors All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Define a contextual bandit from which we can sample and compute rewards.

We can feed the data, sample a context, its reward for a specific action, and
also the optimal action for a given context.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import pandas as pd
import random
def random_derangement(n):
    while True:
        v = list(range(n))
        for j in range(n - 1, -1, -1):
            p = random.randint(0, j)
            if v[p] == j:
                break
            else:
                v[j], v[p] = v[p], v[j]
        else:
            if v[0] != 0:
                return tuple(v)
def mixup(orig, rewards):
    l = len(orig)
    b = len(orig[0])
    orig = np.concatenate(orig).astype(None).reshape((l, b))
    # rewards = np.concatenate(rewards).astype(None).reshape(l)
    lam = np.random.beta(7, 2, size=len(orig))
    index = random_derangement(len(orig))
#     print(rewards.shape, rewards, rewards.dtype,index)
    shuffled = orig[index, :]
    s_rewards = rewards[[index]]
    mix_contexts =  np.array([ orig[i]*lam[i] + shuffled[i]*(1-lam[i]) if lam[i]> 0.5 else orig[i]*(1-lam[i]) + shuffled[i]*(lam[i]) for i in range(len(orig))])
    mix_rewards = np.array([ rewards [i]*lam[i] + s_rewards[i]*(1-lam[i]) if lam[i]> 0.5 else rewards[i]*(1-lam[i]) + s_rewards[i]*(lam[i]) for i in range(len(orig))])
    maj_rewards = rewards.copy()
    return mix_contexts, mix_rewards
def contrast_mixup(c1, r1, c2, r2):
    l = np.min([len(c1), len(c2)])
#     b = len(orig[0])
#     orig = np.concatenate(orig).astype(None).reshape((l, b))
#     # rewards = np.concatenate(rewards).astype(None).reshape(l)
    lam = np.random.beta(7, 2, size=l)
#     index = random_derangement(len(orig))
# #     print(rewards.shape, rewards, rewards.dtype,index)
#     shuffled = orig[index, :]
#     s_rewards = rewards[[index]]
    mix_contexts =  np.array([ c1[i]*lam[i] + c2[i]*(1-lam[i]) if lam[i]> 0.5 else c1[i]*(1-lam[i]) + c2[i]*(lam[i]) for i in range(l)])
    mix_rewards = np.array([ r1[i]*lam[i] + r2[i]*(1-lam[i]) if lam[i]> 0.5 else r1[i]*(1-lam[i]) + r2[i]*(lam[i]) for i in range(l)])
    # maj_rewards = rewards.copy()
    return mix_contexts, mix_rewards

def run_random_mixup_contextual_bandit(context_dim, num_actions, dataset, algos):
  """Run a contextual bandit problem on a set of algorithms.

  Args:
    context_dim: Dimension of the context.
    num_actions: Number of available actions.
    dataset: Matrix where every row is a context + num_actions rewards.
    algos: List of algorithms to use in the contextual bandit instance.

  Returns:
    h_actions: Matrix with actions: size (num_context, num_algorithms).
    h_rewards: Matrix with rewards: size (num_context, num_algorithms).
  """

  num_contexts = dataset.shape[0]

  # Create contextual bandit
  cmab = ContextualBandit(context_dim, num_actions)
  cmab.feed_data(dataset)

  h_actions = np.empty((0, len(algos)), float)
  h_rewards = np.empty((0, len(algos)), float)
  mixup_every = 30
  df = pd.DataFrame({'context':[], 'reward':[], 'action':[], 'algo':[]})
  # Run the contextual bandit process
  for i in range(num_contexts):
    if i%100==0:
      print(i, " out of ", num_contexts)
    context = cmab.context(i)
    actions = [a.action(context) for a in algos]
    rewards = [cmab.reward(i, action) for action in actions]
    # print(actions, 'actions')
    # print(rewards, 'rewards')
   
    for j, a in enumerate(algos):
      # print("orig_update ", context, actions[j], rewards[j])
      a.update(context, actions[j], rewards[j])
      df = df.append({'context':context, 'reward': rewards[j], 'action':actions[j],'algo':j}, ignore_index=True)

    
    if (i+1)%mixup_every==0:
      for j, a in enumerate(algos):
        df_a = df[df['algo']==j]
        # print(df_a[['action', 'reward']])
        uniq_actions = df_a['action'].unique()
#         for act in uniq_actions:
#         df_fr = df_a[df_a['action'] == act]
        my_contexts = df_a['context'].values
        my_rewards = df_a['reward'].values
        my_actions = df_a['action'].values
        m_c, m_r = mixup(my_contexts, my_rewards)
        for mix_i in range(len(m_c)):
                # print("my ypodate shape ", my_actions[mix_i])
                a.update(m_c[mix_i], int(my_actions[mix_i]), m_r[mix_i])
      df = pd.DataFrame({'context':[], 'reward':[], 'action':[], 'algo':[]})
    h_actions = np.vstack((h_actions, np.array(actions)))
    h_rewards = np.vstack((h_rewards, np.array(rewards)))

  return h_actions, h_rewards, algos

def run_contrast_mixup_contextual_bandit(context_dim, num_actions, dataset, algos):
  """Run a contextual bandit problem on a set of algorithms.

  Args:
    context_dim: Dimension of the context.
    num_actions: Number of available actions.
    dataset: Matrix where every row is a context + num_actions rewards.
    algos: List of algorithms to use in the contextual bandit instance.

  Returns:
    h_actions: Matrix with actions: size (num_context, num_algorithms).
    h_rewards: Matrix with rewards: size (num_context, num_algorithms).
  """

  num_contexts = dataset.shape[0]

  # Create contextual bandit
  cmab = ContextualBandit(context_dim, num_actions)
  cmab.feed_data(dataset)

  h_actions = np.empty((0, len(algos)), float)
  h_rewards = np.empty((0, len(algos)), float)
  mixup_every = 30
  df = pd.DataFrame({'context':[], 'reward':[], 'action':[], 'algo':[]})
  # Run the contextual bandit process
  for i in range(num_contexts):
    if i%100==0:
      print(i, " out of ", num_contexts)
    context = cmab.context(i)
    actions = [a.action(context) for a in algos]
    rewards = [cmab.reward(i, action) for action in actions]
    
   
    for j, a in enumerate(algos):
      # print("orig_update ", context, actions[j], rewards[j])
      a.update(context, actions[j], rewards[j])
      df = df.append({'context':context, 'reward': rewards[j], 'action':actions[j],'algo':j}, ignore_index=True)

    
    if (i+1)%mixup_every==0:
      for j, a in enumerate(algos):
        df_a = df[df['algo']==j]
        uniq_actions = df_a['action'].unique()
        indices = np.array(random_derangement(len(uniq_actions)))
        # print(indices, uniq_actions)
        other_acts = np.array(uniq_actions)[indices]
        pairs = [(uniq_actions[i], other_acts[i]) for i in range(len(uniq_actions))]
        for a1, a2 in pairs:
          df_fr1 = df_a[df_a['action'] == a1]
          df_fr2 = df_a[df_a['action'] == a2]
          c1 = df_fr1['context'].values
          r1 = df_fr1['reward'].values
          c2 = df_fr2['context'].values
          r2 = df_fr2['reward'].values
          m_c, m_r = contrast_mixup(c1, r1, c2, r2)
          for mix_i in range(len(m_c)):
                # print("my ypodate shape ", act, m_r[mix_i])
                a.update(m_c[mix_i], int(df_fr1['action'].iloc[mix_i]), m_r[mix_i])
      df = pd.DataFrame({'context':[], 'reward':[], 'action':[], 'algo':[]})
    h_actions = np.vstack((h_actions, np.array(actions)))
    h_rewards = np.vstack((h_rewards, np.array(rewards)))

  return h_actions, h_rewards, algos
def run_mixup_contextual_bandit(context_dim, num_actions, dataset, algos):
  """Run a contextual bandit problem on a set of algorithms.

  Args:
    context_dim: Dimension of the context.
    num_actions: Number of available actions.
    dataset: Matrix where every row is a context + num_actions rewards.
    algos: List of algorithms to use in the contextual bandit instance.

  Returns:
    h_actions: Matrix with actions: size (num_context, num_algorithms).
    h_rewards: Matrix with rewards: size (num_context, num_algorithms).
  """

  num_contexts = dataset.shape[0]

  # Create contextual bandit
  cmab = ContextualBandit(context_dim, num_actions)
  cmab.feed_data(dataset)

  h_actions = np.empty((0, len(algos)), float)
  h_rewards = np.empty((0, len(algos)), float)
  mixup_every = 30
  df = pd.DataFrame({'context':[], 'reward':[], 'action':[], 'algo':[]})
  # Run the contextual bandit process
  for i in range(num_contexts):
    if i%100==0:
      print(i, " out of ", num_contexts)
    context = cmab.context(i)
    actions = [a.action(context) for a in algos]
    rewards = [cmab.reward(i, action) for action in actions]
    
   
    for j, a in enumerate(algos):
      # print("orig_update ", context, actions[j], rewards[j])
      a.update(context, actions[j], rewards[j])
      df = df.append({'context':context, 'reward': rewards[j], 'action':actions[j],'algo':j}, ignore_index=True)

    
    if (i+1)%mixup_every==0:
      for j, a in enumerate(algos):
        df_a = df[df['algo']==j]
        uniq_actions = df_a['action'].unique()
        for act in uniq_actions:
          df_fr = df_a[df_a['action'] == act]
          my_contexts = df_fr['context'].values
          my_rewards = df_fr['reward'].values
          m_c, m_r = mixup(my_contexts, my_rewards)
          for mix_i in range(len(m_c)):
                # print("my ypodate shape ", act, m_r[mix_i])
                a.update(m_c[mix_i], int(act), m_r[mix_i])
      df = pd.DataFrame({'context':[], 'reward':[], 'action':[], 'algo':[]})
    h_actions = np.vstack((h_actions, np.array(actions)))
    h_rewards = np.vstack((h_rewards, np.array(rewards)))

  return h_actions, h_rewards, algos
def run_contextual_bandit(context_dim, num_actions, dataset, algos):
  """Run a contextual bandit problem on a set of algorithms.

  Args:
    context_dim: Dimension of the context.
    num_actions: Number of available actions.
    dataset: Matrix where every row is a context + num_actions rewards.
    algos: List of algorithms to use in the contextual bandit instance.

  Returns:
    h_actions: Matrix with actions: size (num_context, num_algorithms).
    h_rewards: Matrix with rewards: size (num_context, num_algorithms).
  """

  num_contexts = dataset.shape[0]

  # Create contextual bandit
  cmab = ContextualBandit(context_dim, num_actions)
  cmab.feed_data(dataset)
  h_actions = np.empty((0, len(algos)), float)
  h_rewards = np.empty((0, len(algos)), float)
  mixup_every = 30
  df = pd.DataFrame({'conext':[], 'reward':[], 'action':[], 'algo':[]})
  # Run the contextual bandit process
  for i in range(num_contexts):
    if i%100==0:
      print(i, " out of ", num_contexts)
    context = cmab.context(i)
    actions = [a.action(context) for a in algos]
    rewards = [cmab.reward(i, action) for action in actions]

    for j, a in enumerate(algos):
      a.update(context, actions[j], rewards[j])
      df.loc[i*len(algos)+j] = [context, actions[j], rewards[j], j]
 
    df = pd.DataFrame({'conext':[], 'reward':[], 'action':[], 'algo':[]})
    h_actions = np.vstack((h_actions, np.array(actions)))
    h_rewards = np.vstack((h_rewards, np.array(rewards)))

  return h_actions, h_rewards, algos

class ContextualBandit(object):
  """Implements a Contextual Bandit with d-dimensional contexts and k arms."""

  def __init__(self, context_dim, num_actions):
    """Creates a contextual bandit object.

    Args:
      context_dim: Dimension of the contexts.
      num_actions: Number of arms for the multi-armed bandit.
    """

    self._context_dim = context_dim
    self._num_actions = num_actions

  def feed_data(self, data):
    """Feeds the data (contexts + rewards) to the bandit object.

    Args:
      data: Numpy array with shape [n, d+k], where n is the number of contexts,
        d is the dimension of each context, and k the number of arms (rewards).

    Raises:
      ValueError: when data dimensions do not correspond to the object values.
    """

    if data.shape[1] != self.context_dim + self.num_actions:
      raise ValueError('Data dimensions do not match.')

    self._number_contexts = data.shape[0]
    self.data = data
    self.order = range(self.number_contexts)

  def reset(self):
    """Randomly shuffle the order of the contexts to deliver."""
    self.order = np.random.permutation(self.number_contexts)

  def context(self, number):
    """Returns the number-th context."""
    return self.data[self.order[number]][:self.context_dim]

  def reward(self, number, action):
    """Returns the reward for the number-th context and action."""
    return self.data[self.order[number]][self.context_dim + action]

  def optimal(self, number):
    """Returns the optimal action (in hindsight) for the number-th context."""
    return np.argmax(self.data[self.order[number]][self.context_dim:])

  @property
  def context_dim(self):
    return self._context_dim

  @property
  def num_actions(self):
    return self._num_actions

  @property
  def number_contexts(self):
    return self._number_contexts
