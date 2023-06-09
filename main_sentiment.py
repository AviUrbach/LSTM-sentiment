#!/usr/bin/env python
# coding: utf-8
'''fun: sentiment analysis'''


import torch
from torch import nn
import pandas as pd 
import re
import matplotlib.pyplot as plt
import numpy as np
import json
import torch.optim as optim
from torch.utils.data import DataLoader,Dataset,TensorDataset
# import pandas as pd
from DataLoader import MovieDataset
from LSTM import LSTMModel
from GloveEmbed import _get_embedding
import time

import wandb


'''save checkpoint'''
def _save_checkpoint(ckp_path, model, epoches, global_step, optimizer):
    checkpoint = {'epoch': epoches,
                'global_step': global_step,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict()}

    torch.save(checkpoint, ckp_path)


def main():
    gpu_id = 0
    use_cuda = torch.cuda.is_available()
    if use_cuda:
        device = torch.device("cuda", gpu_id)
    else:
        device = torch.device('cpu')
    
    ## alternative method
    # torch.cuda.set_device(device=0) ## choose gpu number
    print('device: ', device)

    ## ---------------------------------------------------------
    ## please change the parameter settings by yourselves
    ## ---------------------------------------------------------
    mode = 'train'
    Batch_size =300
    n_layers = 2 ## choose 1-3 layers

    ## input seq length aligned with data pre-processing
    input_len = 150

    ## word embedding length
    embedding_dim = 100

    # lstm hidden dim
    hidden_dim = 50
    # binary cross entropy
    output_size = 1
    num_epoches = 3
    ## please change the learning rate by youself
    learning_rate = 0.002
    # gradient clipping
    clip = 5
    load_cpt = False #True
    ckp_path = 'cpt/name.pt'
    # embedding_matrix = None
    ## use pre-train Glove embedding or not?
    pretrain = False

    ##-----------------------------------------------------------------------
    ## Bonus (5%): complete code to add GloVe embedding file path below.
    ## Download Glove embedding from https://nlp.stanford.edu/data/glove.6B.zip
    ## "embedding_dim" defined above shoud be aligned with the dimension of GloVe embedddings
    ## if you do not want bonus, you can skip it.
    ##-----------------------------------------------------------------------
    glove_file = 'path/glove.6B.200d.txt' ## change by yourself
    

    ## ---------------------------------------------------------
    ## step 1: create data loader in DataLoader.py
    ## complete code in DataLoader.py (not Below)
    ## ---------------------------------------------------------
    
    
    ## step 2: load training and test data from data loader [it is Done]
    training_set = MovieDataset('training_data.csv')
    training_generator = DataLoader(training_set, batch_size=Batch_size,\
                                    shuffle=True,num_workers=1)
    test_set = MovieDataset('test_data.csv')
    test_generator = DataLoader(test_set, batch_size=Batch_size,\
                                shuffle=False,num_workers=1)


    ## step 3: [Bonus] read tokens and load pre-train embedding [it is Done]
    with open('tokens2index.json', 'r') as f:
        tokens2index = json.load(f)
    vocab_size = len(tokens2index)

    if pretrain:
        print('***** load glove embedding now...****')
        embedding_matrix = _get_embedding(glove_file,tokens2index,embedding_dim)
    else:
        embedding_matrix = None

    ## -----------------------------------------------
    ## step 4: import model from LSTM.py
    ## complete the code in "def forward(self, x)" in LSTM.py file
    ## then import model from LSTM.py below
    ## and also load model to device
    ## -----------------------------------------------
    model = LSTMModel(vocab_size, output_size, embedding_dim, embedding_matrix,\
        hidden_dim, n_layers, input_len, pretrain)
    model.to(device)

    ##-----------------------------------------------------------
    ## step 5: complete code to define optimizer and loss function
    ##-----------------------------------------------------------
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)  # 
    ## define Binary Cross Entropy Loss below
    loss_fun = nn.BCELoss()
    
    ## step 6: load checkpoint
    if load_cpt:
        print("*"*10+'loading checkpoint'+'*'*10)
        ##-----------------------------------------------   
        ## complete code below to load checkpoint
        ##-----------------------------------------------
        checkpoint = torch.load(ckp_path)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        epoches = checkpoint['epoch']


    ## step 7: model training
    print('*'*89)
    print('start model training now')
    print('*'*89)
    if mode == 'train':
        model.train()
        global_step = 0
        for epoches in range(num_epoches):
            for x_batch, y_labels in training_generator:
                global_step += 1
                
                x_batch, y_labels = x_batch.to(device), y_labels.to(device)
                ##-----------------------------------------------
                ## complete code to get predict result from model
                ##-----------------------------------------------
                y_out = model(x_batch)

                ##-----------------------------------------------
                ## complete code to get loss
                ##-----------------------------------------------
                loss = loss_fun(y_out, y_labels)

                ## step 8: back propagation [Done]
                optimizer.zero_grad()
                loss.backward()
                ## **clip_grad_norm helps prevent the exploding gradient problem in LSTMs.
                nn.utils.clip_grad_norm_(model.parameters(), clip)
                optimizer.step()

                if global_step % 3 == 0:
                    wandb.log({'iteration': global_step, 'loss': loss})
                
            ##-----------------------------------------------   
            ## step 9: complete code below to save checkpoint
            ##-----------------------------------------------
            print("**** save checkpoint ****")
            _save_checkpoint('checkpoints/' + 'epoch_{}.pt'.format(epoches+1), model, epoches, global_step, optimizer)
            
    
    ##------------------------------------------------------------------
    ## step 10: complete code below for model testing
    ## predict result is a single value between 0 and 1, such as 0.8, so
    ## we can use y_pred = torch.round(y_out) to predict label 1 or 0
    ##------------------------------------------------------------------
    print("----model testing now----")

    total = 0
    tp = 0
    tn = 0
    fp = 0
    fn = 0

    model.eval()
    with torch.no_grad():
        for x_batch, y_labels in test_generator:
            x_batch, y_labels = x_batch.to(device), y_labels.to(device)
            
            y_out = model(x_batch)
            y_pred = torch.round(y_out)
            
            # count total predictions and correct predictions
            total += len(y_labels)
            tp += (y_labels * y_pred).count_nonzero().item()
            tn += len(y_pred) - (y_labels + y_pred).count_nonzero().item()
            fp += len(y_pred) - (y_labels - y_pred + 1).count_nonzero().item()
            fn += len(y_pred) - (y_labels - y_pred - 1).count_nonzero().item()
        print("Testing Accuracy:", (tp+tn)/total)
        print("Confusion Matrix:")
        print("Actual\t Predict")
        print("\tPos\tNeg")
        print(f'Pos\t{tp}\t{fn}')
        print(f'Neg\t{fp}\t{tn}')
    


if __name__ == '__main__':
    time_start = time.time()
    with wandb.init(project='aviurbach', name='sentiment_LSTM'):
        main()
    time_end = time.time()
    print("running time: ", (time_end - time_start)/60.0, "mins")
    


    

    