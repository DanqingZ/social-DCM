from __future__ import division
import random
import numpy as np
import numpy.linalg as alg
import scipy as spy
import networkx as nx
import time
from itertools import *
import sys
import numpy.linalg as LA
from src.models.GibbsSampler_networkx import GibbsSampler
from src.models.CVX_weighted import CVX_weighted
from scipy.special import expit

class EM_CVX_pre:
	def __init__(self, X, y, temp, Lambda, Rho, num_classes,iterations,burn_In,index_change,X_test,Y_test):
		self.X = X
		self.y = y
		self.num_classes = num_classes
		self.value = 0
		self.dim = X.shape[1]
		self.Lambda = Lambda
		self.Rho = Rho
		self.temp = temp
		self.num_nodes = nx.number_of_nodes(self.temp)
		self.num_edges = self.temp.number_of_edges()
		self.W = np.random.random((self.dim, self.num_classes))
		self.b = np.random.random((self.num_nodes,self.num_classes))
		self.pos_node = []
		self.iterations = iterations
		self.posterior_mat = np.zeros((self.num_nodes,self.num_classes))
		self.burn_In = burn_In
		self.z_0 = np.random.randint(low = 0,high = self.num_classes-1,size = self.num_nodes)
		self.G = GibbsSampler(self.temp,self.b,0,self.burn_In,self.Lambda,self.z_0)
		self.LL = []
		self.X_test = X_test
		self.Y_test = Y_test
		self.index_change = index_change
		self.expected_LL = 0

	def E_step(self,i):
		num_Samples = (i+1)*1000
		self.G = GibbsSampler(self.temp,self.b,num_Samples,self.burn_In,self.Lambda,self.z_0)
		self.G.sampling()
		self.G.cal_node()
		self.G.cal_edge()
		self.G.get_node()
		self.G.get_edge()
		self.temp = self.G.temp
		self.z_0 = self.G.samples[-1,:]
		prior_node = self.G.node_prob
		self.prob_mat = np.zeros((self.num_nodes,self.num_classes))
		posterior_mat = np.zeros((self.num_nodes,self.num_classes))
		for k in range(self.num_classes):
			self.prob_mat[:,k] = 1 / (1+np.exp(np.multiply(self.y.flatten(),-np.dot(self.W[:,k],self.X.T)-self.b[:,k])))
		for k in range(self.num_classes):
			posterior_mat[:,k] = np.multiply(self.prob_mat,prior_node)[:,k]/np.sum(np.multiply(self.prob_mat,prior_node),axis=1)
		num_edges = self.temp.number_of_edges()
		prior_edge = self.G.edge_prob
		prob_mat_edge = np.zeros((self.num_edges,self.num_classes,self.num_classes))
		posterior_mat_edge = np.zeros((self.num_edges,self.num_classes))
		count = 0
		for EI in self.temp.edges_iter():
			for k1 in range(self.num_classes):
				for k2 in range(self.num_classes):
					prob_mat_edge[count,k1,k2] = self.prob_mat[EI[0],k1]*self.prob_mat[EI[1],k2]
			count += 1
		prob_mat_edge = prob_mat_edge.reshape((self.num_edges,self.num_classes**2))
		posterior_mat_edge[:,0] = np.multiply(prob_mat_edge,prior_edge)[:,0]/np.sum(np.multiply(prob_mat_edge,prior_edge),axis=1)
		posterior_mat_edge[:,1] = np.multiply(prob_mat_edge,prior_edge)[:,3]/np.sum(np.multiply(prob_mat_edge,prior_edge),axis=1)
		self.posterior_mat = posterior_mat
		self.posterior_mat_edge = posterior_mat_edge

	def M_step(self):
		self.old_LL = self.expected_LL
		self.expected_LL = 0
		for k in range(self.num_classes):
			pos_node = []
			for NI in self.temp.nodes_iter():
				self.temp.node[NI]['pos_node_prob'] = self.posterior_mat[NI,k]
				pos_node.append(self.posterior_mat[NI,k])
			count = 0
			for EI in self.temp.edges_iter():
				self.temp[EI[0]][EI[1]]['pos_edge_prob'] = self.posterior_mat_edge[count,k]
				count += 1
			A = CVX_weighted(self.X, self.y, self.b,pos_node,self.temp,self.Lambda, self.Rho)
			A.init_P()
			A.solve()
			self.W[:,k] = A.W.flatten()
			self.b[:,k] = A.b.flatten()
			self.expected_LL -= A.value

	def predict(self):
		old_predictions = self.predictions
		old_acc = self.acc
		old_LL = self.old_LL
		prob  = self.G.node_prob[self.index_change,:]
		W = self.W
		b = self.b
		B = b[self.index_change,:]
		num_classes = 2
		predict_prob_mat = np.zeros((self.Y_test.shape[0],2))
		for k in range(num_classes):
			predict_prob_mat[:,0] += np.multiply(expit(np.dot(W[:,k],self.X_test.T)+B[:,k]), prob[:,k] )
		for k in range(num_classes):
			predict_prob_mat[:,1] += np.multiply(1-expit(np.dot(W[:,k],self.X_test.T)+B[:,k]), prob[:,k])
		assignment = predict_prob_mat.argmax(axis=1).astype(int)
		self.predictions = []
		for i in range(len(self.Y_test)):
			if assignment[i] ==0 :
				self.predictions.append(1)
			else:
				self.predictions.append(-1)		
		Y_test = self.Y_test
		count0 = 0
		count1 = 0
		for j in range(Y_test.shape[0]):
			if Y_test[j] ==0:
				count0 += 1
			else:
				if Y_test[j]==self.predictions[j]:
					count1 += 1
		self.acc = count1/(len(self.Y_test)-count0)
		if self.expected_LL < old_LL:
			self.predictions = old_predictions
			self.acc = old_acc


	def run_EM(self):
		self.acc = 0
		self.predictions = np.zeros(self.Y_test.shape[0])
		for i in range(self.iterations):
			print 'iteration: ',i
			W_old = np.copy(self.W)
			b_old = np.copy(self.b)
			self.E_step(i)
			self.M_step()
			if i>3:
				self.predict()
				self.LL.append(self.expected_LL)





