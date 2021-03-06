##############################################################################################################################
# Aim of the Experiment: Continual Learning on CIFAR-100 with Breakup
# Output: All the collected data for individual skill is present in the folder -- Collected_Data
# Task Nets: All the trained CIFAR 100 weights saved in the folder -- task_net_models
# Test & Train Image Samples: All the train,test CIFAR 10 task images sample saved in the folder -- Test_Train_Images
# Plots : If any plots you can save in folder -- Permuated_MNIST_plots (Currently Not Used)
# Conclusion : 
##############################################################################################################################

import argparse
import torch
import torchvision
import torch.nn as nn
import torch.utils.model_zoo as model_zoo
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from torch.autograd import Variable
from sklearn.metrics import mean_squared_error
import helper_functions
import models
import pandas as pd
import os
import numpy as np
import pickle
import matplotlib 
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
from numpy import dot
from numpy.linalg import norm
import visdom
vis = visdom.Visdom()
vis.delete_env('CIFAR100_Cosine_Cutoff') #If you want to clear all the old plots for this python Experiments.Resets the Environment
vis = visdom.Visdom(env='CIFAR100_Cosine_Cutoff')
#from utils import Bar, Logger, AverageMeter, accuracy, mkdir_p, savefig
################################################################################
# EXECUTION FLAGS                                 #                             
################################################################################
Flags = {}
Flags['CIFAR_100'] = False
Flags['CIFAR_10_Incrmental'] = True
Flags['NC_NET'] = False
Flags['NC_NET_CUM'] = False
Flags['CAE_Train'] = True
Flags['SPLIT_INPUT']=True
best_acc = 0  # best test accuracy

parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
parser.add_argument('--batch-size', type=int, default=64, metavar='N',
                    help='input batch size for training (default: 64)')
parser.add_argument('--test-batch-size', type=int, default=100, metavar='N',
                    help='input batch size for testing (default: 1000)')
parser.add_argument('--epochs', type=int, default=10, metavar='N',
                    help='number of epochs to train (default: 10)')
parser.add_argument('--lr', type=float, default=0.1, metavar='LR',
                    help='learning rate (default: 0.1)')
parser.add_argument('--momentum', type=float, default=0.5, metavar='M',
                    help='SGD momentum (default: 0.5)')
parser.add_argument('--schedule', type=int, nargs='+', default=[150, 225],
                        help='Decrease learning rate at these epochs.')
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='disables CUDA training')
parser.add_argument('--seed', type=int, default=1, metavar='S',
                    help='random seed (default: 1)')
parser.add_argument('--gamma', type=float, default=0.1, help='LR is multiplied by gamma on schedule.')
parser.add_argument('--log-interval', type=int, default=10, metavar='N',
                    help='how many batches to wait before logging training status')
args = parser.parse_args()
use_cuda = not args.no_cuda and torch.cuda.is_available()

torch.manual_seed(args.seed)

device = torch.device("cuda" if use_cuda else "cpu")
# Actual_Accuracy=[]
# #model = Resnet.ResNet18()
# net=models.Net()#dense_net2.DenseNet( growthRate=12)#Resnet.ResNet18()Resnet.Net() #
# print(net)
# criterion = nn.CrossEntropyLoss()
# if Flags['CIFAR_100'] :
#     optimizer = optim.SGD(model.parameters(), lr=0.1, momentum=0.9,weight_decay=1e-4)
# else:
#     optimizer = optim.SGD(model.parameters(), lr=0.1, momentum=0.9)

transform_train = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

transform = transforms.Compose(
    [transforms.ToTensor(),
     transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])

trainset = torchvision.datasets.CIFAR100(root='../data', train=True,
                                        download=True, transform=transform)
train_loader = torch.utils.data.DataLoader(trainset, batch_size=4,
                                          shuffle=True, num_workers=4)

testset = torchvision.datasets.CIFAR100(root='../data', train=False,
                                       download=True, transform=transform)
test_loader = torch.utils.data.DataLoader(testset, batch_size=4,
                                         shuffle=False, num_workers=4)


######################################################################################################
# SAVING ALL THE LABEL DATA FOR RELOADING PURPOSE
######################################################################################################
global_trainset_train_labels=trainset.train_labels
global_trainset_train_data=trainset.train_data
global_testset_test_labels=testset.test_labels
global_testset_test_data=testset.test_data
global_train_loader=train_loader
global_test_loader=test_loader
#####################################################################################################################
# Calculating all the Train and Test Indexes for Each Digit
#####################################################################################################################
train_Indexs=[[] for _ in range(0,100)]
test_Indexs = [[] for _ in range(0,100)]

for num in range(0,len(trainset.train_labels)):
    train_Indexs[trainset.train_labels[num]].append(num)
    
for num in range(0,len(testset.test_labels)):
    test_Indexs[testset.test_labels[num]].append(num)

######################################################################################################
# RELOD THE DATASET WHEN NEEDED
######################################################################################################
def RELOAD_DATASET():
    #print("RELOADING THE DATA")
    global train_loader,test_loader,trainset,testset

    train_loader=global_train_loader
    test_loader=global_test_loader

    trainset.train_data=global_trainset_train_data
    testset.test_data=global_testset_test_data

    trainset.train_labels=global_trainset_train_labels
    testset.test_labels=global_testset_test_labels

######################################################################################################
#MODIFYING DATSET FOR INDIVIDUAL CLASSES
######################################################################################################
def load_individual_class(postive_class,negative_classes):
    RELOAD_DATASET()
    global train_loader,test_loader,train_Indexs,test_Indexs
    index_train_postive=[]
    index_test_postive=[]
    index_train_negative=[]
    index_test_negative=[]
    for i in range(0,len(postive_class)):
        index_train_postive=index_train_postive+train_Indexs[postive_class[i]]
        index_test_postive=index_test_postive+test_Indexs[postive_class[i]]
        
    for i in range(0,len(negative_classes)):
        index_train_negative=index_train_negative+train_Indexs[negative_classes[i]][0:int(0.2*(len(train_Indexs[negative_classes[i]])))]
        index_test_negative=index_test_negative+test_Indexs[negative_classes[i]][0:int(0.2*(len(test_Indexs[negative_classes[i]])))]
    
    index_train=index_train_postive+index_train_negative
    index_test=index_test_postive+index_test_negative
    modified_train_labels = [int(trainset.train_labels[i]%10) for i in index_train] #[1 if (trainset.train_labels[x] in postive_class) else 0 for x in index_train]
    modified_test_labels  = [int(testset.test_labels[i]%10) for i in index_test]#[1 if (testset.test_labels[x] in postive_class) else 0 for x in index_test]
    #print("Modified Test Labels are",modified_train_labels[1:100])
    trainset.train_labels=modified_train_labels#train set labels
    trainset.train_data=trainset.train_data[index_train]#train set data
    testset.test_labels=modified_test_labels#testset labels
    testset.test_data=testset.test_data[index_test]#testset data
    train_loader = torch.utils.data.DataLoader(trainset, batch_size=4,shuffle=True)
    test_loader = torch.utils.data.DataLoader(testset, batch_size=4,shuffle=True) 

    return train_loader,test_loader

######################################################################################################
#                                   RELOD THE WEIGHTS INTO NET                                       #
######################################################################################################
def loadWeights_cifar(weights_to_load, net):
    net.conv1.weight.data = torch.from_numpy(weights_to_load[0])
    net.conv1.bias.data =   torch.from_numpy(weights_to_load[1])
    net.conv2.weight.data = torch.from_numpy(weights_to_load[2])
    net.conv2.bias.data =   torch.from_numpy(weights_to_load[3])
    net.fc1.weight.data =   torch.from_numpy(weights_to_load[4])
    net.fc1.bias.data =     torch.from_numpy(weights_to_load[5])
    net.fc2.weight.data =   torch.from_numpy(weights_to_load[6])
    net.fc2.bias.data =     torch.from_numpy(weights_to_load[7])
    net.fc3.weight.data =   torch.from_numpy(weights_to_load[8])
    net.fc3.bias.data =     torch.from_numpy(weights_to_load[9])
    return net


######################################################################################################
#                                       PLOTTING                                                     #
######################################################################################################
def plotAccuracies(allAcc):
    for s,acc in enumerate(allAcc):
        x = np.array(acc)
        f = plt.figure()
        for i in range(x.shape[1]):
            plt.plot(x[:,i],'.-', markersize=5, label='Skill: '+str(i))
        plt.xlabel('Iterations')
        plt.ylabel('Accuracy')
        plt.title('Encoded Skills -- Stage ' + str(s))
        plt.legend(loc='lower right')
        plt.show()    
        f.savefig('./CIFAR_plots/acc_'+str(s)+'.pdf', bbox_inches='tight')
        plt.close()


def plotAccuracyDiff(allAcc,Actual_Accuracies):
    for s,acc in enumerate(allAcc):
        x = np.array(acc)
        f = plt.figure()
        for i in range(x.shape[1]):
            plt.plot(Actual_Accuracies[i] - x[:,i],'.-', markersize=5, 
                label='Skill: '+str(i))
        plt.xlabel('Iterations')
        plt.ylabel('True Acc - Reconst. Acc')
        plt.title('Encoded Skills -- Stage ' + str(s))
        plt.legend(loc='upper right')
        plt.show()    
        f.savefig('./CIFAR_plots/acc_diff_'+str(s)+'.pdf', bbox_inches='tight')
        plt.close()


def plotAccuracyDiffPoint(allAcc,Actual_Accuracies,testPoint=25):
    for s,acc in enumerate(allAcc):
        x = np.array(acc)
        f = plt.figure()
        for i in range(x.shape[1]):
            plt.plot(i,Actual_Accuracies[i] - x[testPoint,i],'.-', markersize=10, 
                label='Skill: '+str(i))
        plt.xlabel('Iterations')
        plt.ylabel('True Acc - Reconst. Acc')
        plt.title('Encoded Skills -- Stage ' + str(s) + ', Iter ' + str(testPoint))
        plt.legend(loc='lower right')
        plt.show()    
        f.savefig('./CIFAR_plots/acc_diff_pt_'+str(s)+'_'+str(testPoint)+'.pdf', bbox_inches='tight')
        plt.close()

def plotAccuracyDiffPointAll(allAcc,Actual_Accuracies,testPoint=25):
    f = plt.figure()
    yAll = []
    for i in range(10):
        yAll.append([])
        for s in range(i,10):
            yAll[i].append(Actual_Accuracies[i] - allAcc[s][testPoint][i])
    
    for i,y in enumerate(yAll):
        plt.plot(range(i,10),y,'.-', markersize=5,label='Skill: '+str(i))
    plt.xlabel('Stages')
    plt.ylabel('True Acc - Reconst. Acc')
    plt.title('Encoded Skills -- Iter ' + str(testPoint))
    plt.legend(loc='upper left')
    plt.show()    
    f.savefig('./CIFAR_plots/acc_diff_pt_all_'+str(s)+'_'+str(testPoint)+'.pdf', bbox_inches='tight')
    plt.close()
#####################################################################################################################
#                                             SAVING IMAGES                                                         #
#####################################################################################################################
def imshow(img,cifar_class):
    img = img / 2 + 0.5     # unnormalize
    npimg = img.numpy()
    plt.imshow(np.transpose(npimg, (1, 2, 0)))
    plt.savefig('Test_Train_Images/train_data_image'+str(cifar_class)+'.png')

def imshow_test(img):
    img = img / 2 + 0.5     # unnormalize
    npimg = img.numpy()
    plt.imshow(np.transpose(npimg, (1, 2, 0)))
    plt.savefig('Test_Train_Images/test_data_image'+str(cifar_class)+'.png')

def SHOW_TEST_TRAIN_IMAGES_SAMPLE(cifar_class):
    # get some random training images
    global train_loader
    global test_loader
    dataiter = iter(train_loader)
    dataiter_test = iter(test_loader)
    #print("length of testset loader is",len(test_loader))
    #print("length if train set loader is",len(train_loader))
    images, labels = dataiter.next()
    images_test, labels_test = dataiter_test.next()
    imshow(torchvision.utils.make_grid(images),cifar_class)
    imshow_test(torchvision.utils.make_grid(images_test))
    # img = Image.open('train_data_image'+str(cifar_class)+'.png')
    # img.show()
    # time.sleep(5)
    print(' '.join('%5s' % classes[labels[j]] for j in range(4)))
    # img = Image.open('test_data_image'+str(cifar_class)+'.png')
    print(' '.join('%5s' % classes[labels_test[j]] for j in range(4)))
    # img.show() 
#####################################################################################################################
#                                              TRAIN CIFAR WITHOUT PROGRESS BAR                                     #
#####################################################################################################################

def train(model,train_loader,test_loader,optimizer, epochs,task_number):
    options = dict(fillarea=True,width=400,height=400,xlabel='Batch_ID(Iterations)',ylabel='Loss',title=str(task_number))
    acc_options = dict(fillarea=True,width=400,height=400,xlabel='Epoch',ylabel='Accuracy',title=str(task_number))
    win = vis.line(X=np.array([0]),Y=np.array([0.7]),win=task_number,name=task_number,opts=options)
    model.to(device)
    model.train()
    total_batchid=0
    task_test_accuracy=[0]
    for epoch in range(0,epochs):
        running_loss = 0.0
        for batch_idx, (data, target) in enumerate(train_loader,0):
            data, target = data.to(device), target.to(device)
            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            #vis.line(X=np.array([total_batchid+batch_idx]),Y=np.array([loss.item()]),win=win,update='append')
            loss.backward()
            optimizer.step()
            #print("loss is ",loss.data[0])
            running_loss += loss.item()
            if batch_idx %  400 == 0:
                print('[%d, %5d] loss: %.3f' %(epoch + 1, batch_idx + 1, running_loss / 400))
                vis.line(X=np.array([total_batchid+batch_idx]),Y=np.array([loss.item()]),win=win,update='append')
                running_loss = 0.0
                # print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                #     epoch, batch_idx * len(data), len(train_loader.dataset),
                #     100. * batch_idx / len(train_loader), loss.item()))
        total_batchid=total_batchid+batch_idx
        accuracy=test(model,test_loader)
        task_test_accuracy.append(accuracy)
        vis.bar(X=np.array(task_test_accuracy),win='ACC'+str(task_number),opts=acc_options)
    return accuracy


#####################################################################################################################
#                                               TRAIN CIFAR WITHOUT PROGRESS BAR                                    #
#####################################################################################################################

def test(model, test_loader):
    model.to(device)
    model.eval()
    test_loss = 0
    correct = 0
    #print("length of testset loader is",len(test_loader))
    #print("length if train set loader is",len(train_loader))
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += criterion(output, target)#.item() # sum up batch loss
            pred = output.max(1, keepdim=True)[1] # get the index of the max log-probability
            correct += pred.eq(target.view_as(pred)).sum().item()

    test_loss /= len(test_loader.dataset)
    print('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({}%)\n'.format(
        test_loss, correct, len(test_loader.dataset),
        100. * correct / len(test_loader.dataset)))
    return 100. * correct / len(test_loader.dataset)

#####################################################################################################################
#                                               Adjusting Learning Rate                                             #
#####################################################################################################################
def adjust_learning_rate(optimizer, epoch):
    global state
    if epoch in args.schedule:
        state['lr'] *= args.gamma
        for param_group in optimizer.param_groups:
            param_group['lr'] = state['lr']


######################################################################################################
#                                   GLOBAL VARIABLES
######################################################################################################
#net=models.Net().to(device)
net_reset=models.Net().to(device)
Actual_Accuracy=[]
criterion = nn.CrossEntropyLoss()
student_model=models.SPLIT_CIFAR_CAE_TWO_SKILLS().to(device)
vae_optimizer =optim.Adam(student_model.parameters(), lr = 0.00001)#, amsgrad=True)
lam = 0.0001
Actual_Accuracy=[]
threshold_batchid=[]
threshold_net_updates=[]
Actual_task_net_weights=[]
#biased training variables
nSamples = 10
nBiased = min(nSamples,10)
trainBias = 0.5
minReps = 1
nReps = 20
stage=2
addRepsTotal = nReps*minReps
#####################################################################################################################
#                                              CAE TRAIN AND CIFAR TEST                                             #
#####################################################################################################################
print("VAE SCHEDULER IS ", vae_optimizer)
Skill_Mu=[[] for _ in range(0,10)]

def CAE_AE_TRAIN(shapes,task_samples,iterations):
    global stage
    global Skill_Mu
    options = dict(fillarea=True,width=400,height=400,xlabel='Iterations',ylabel='Loss',title='CAE_skills'+str(len(task_samples)))
    options_2 = dict(fillarea=True,width=400,height=400,xlabel='Iterations',ylabel='Accuracy',title='Acc_skills_'+str(len(task_samples)))
    options_mse = dict(fillarea=True,width=400,height=400,xlabel='Iterations',ylabel='MSE',title='MSE_skills_'+str(len(task_samples)))
    options_mse_org = dict(fillarea=True,width=400,height=400,xlabel='Iterations',ylabel='Cosine_Similarity',title='Cosine_Similarity_'+str(len(task_samples)))
    win = vis.line(X=np.array([0]),Y=np.array([0.005]),win='Loss_skills_'+str(len(task_samples)),name='Loss_skills'+str(len(task_samples)),opts=options)
    win_2 = vis.line(X=np.array([0]),Y=np.array([0]),win='Acc_skills_'+str(len(task_samples)),name='Acc_skills_'+str(len(task_samples)),opts=options_2)
    win_mse = vis.line(X=np.array([0]),Y=np.array([0]),win='MSE_skills_'+str(len(task_samples)),name='MSE_skills_'+str(len(task_samples)),opts=options_mse)
    win_mse_org = vis.line(X=np.array([0]),Y=np.array([0]),win='Cosine_Sim '+str(len(task_samples)),name='Cosine_similarity_'+str(len(task_samples)),opts=options_mse_org)
    splitted_input=[]
    skills=[]
    total_resend=0
    task_samples_copy=task_samples
    total=len(task_samples)
    final_dataframe_1=pd.DataFrame()
    accuracies = np.zeros((iterations,len(task_samples)))
    for t_input in range(0,len(task_samples)):
        #print("split is",len(task_samples[t_input]))
        splitted_input=np.array_split(task_samples[t_input],3)
        for i in range(0,len(splitted_input)):
            #print("split is",len(splitted_input[i]))
            if(len(splitted_input[i])==20668):
                splitted_input[i]=np.concatenate((splitted_input[i], [0]))
            skills.append(splitted_input[i])
    task_samples=skills
    Skill_Mu=[[] for _ in range(0,len(task_samples))]
    global student_model
    global vae_optimizer
    student_model.train()
    iterations=iterations
    for batch_idx in range(1,iterations):
        randPerm=np.random.permutation(len(task_samples))
        #randPerm,nReps = helper_functions.biased_permutation(stage+1,nBiased,trainBias,total*3,minReps)
        print(randPerm,nReps)
        resend=[]
        for s in randPerm:
            skill=s
            vae_optimizer.zero_grad()
            data=Variable(torch.FloatTensor(task_samples[skill])).to(device)
            hidden_representation, recons_x = student_model(data)
            W = student_model.state_dict()['fc2.weight']
            loss,con_mse,con_loss,closs_mul_lam = helper_functions.Contractive_loss_function(W, 
                data.view(-1, 20669), recons_x,hidden_representation, lam)
            Skill_Mu[skill]=hidden_representation
            vis.line(X=np.array([batch_idx]),Y=np.array([loss.item()]),win=win,name='Loss_Skill_'+str(skill),update='append')
            loss.backward()
            vae_optimizer.step()
            print('Train Iteration: {},tLoss: {:.6f},picked skill {}'.format(batch_idx,loss.data[0],skill ))
            #print(float(loss.data[0] * 1000))
            if float(loss.data[0] * 1000000)>=1.00:
                resend.append(s)
        print("RESEND List",resend)
        total_resend=total_resend+len(resend)
        for s in resend:
            skill=s
            #print("resending skills",resend)
            vae_optimizer.zero_grad()
            data=Variable(torch.FloatTensor(task_samples[skill])).to(device)
            hidden_representation, recons_x = student_model(data)
            W = student_model.state_dict()['fc2.weight']
            loss,con_mse,con_loss,closs_mul_lam = helper_functions.Contractive_loss_function(W, 
                data.view(-1, 20669), recons_x,hidden_representation, lam)
            Skill_Mu[skill]=hidden_representation
            vis.line(X=np.array([batch_idx]),Y=np.array([loss.item()]),win=win,name='Loss_Skill_'+str(skill),update='append')
            loss.backward()
            vae_optimizer.step()

            print('Train Iteration: {},tLoss: {:.6f},picked skill {}'.format(batch_idx,loss.data[0],skill ))
        if batch_idx %1==0:
            m=0
            n=3
            values=0
            for i in range(0,int(len(task_samples)/3)):
                collect_data_1=[]
                RELOAD_DATASET()
                Avg_Accuracy=0
                Train_loader,Test_loader=load_individual_class(list(range(i*10, (i+1)*10)),[])
                sample=[]
                for k in range(m,n):
                    mu1=Skill_Mu[k][0]
                    mini_task_sample = student_model.decoder(mu1).cpu()
                    task_sample=mini_task_sample.data.numpy().reshape(20669)
                    sample=np.concatenate([sample,task_sample])
                m=m+3
                n=n+3
                final_weights=helper_functions.unFlattenNetwork(torch.from_numpy(sample).float(), shapes)
                model_x=loadWeights_cifar(final_weights,model)
                Avg_Accuracy=test(model_x, Test_loader)
                mse=mean_squared_error(sample[0:62006],Variable(torch.FloatTensor(task_samples_copy[i][0:62006])).data.numpy())
                mse_orginal=mean_squared_error(sample[0:62006],Actual_task_net_weights[i])
                b=torch.FloatTensor(task_samples_copy[i]).data.numpy()
                b1=torch.FloatTensor(Actual_task_net_weights[i]).data.numpy()
                COSINE_SIMILARITY=dot(sample[0:62006], b[0:62006])/(norm(sample[0:62006])*norm(b[0:62006]))
                COSINE_SIMILARITY_wrt_orginal=dot(sample[0:62006], b1[0:62006])/(norm(sample[0:62006])*norm(b1[0:62006]))
                collect_data_1.extend([total,batch_idx,i,mse,mse_orginal,Avg_Accuracy,Actual_Accuracy[i],len(resend),COSINE_SIMILARITY,COSINE_SIMILARITY_wrt_orginal])
                final_dataframe_1=pd.concat([final_dataframe_1, pd.DataFrame(collect_data_1).transpose()])
                final_dataframe_1=pd.concat([final_dataframe_1, pd.DataFrame(collect_data_1).transpose()])
                vis.line(X=np.array([batch_idx]),Y=np.array([Avg_Accuracy]),win=win_2,name='Acc_Skill_'+str(i),update='append')
                vis.line(X=np.array([batch_idx]),Y=np.array([mse]),win=win_mse,name='MSE_Skill_'+str(i),update='append')
                vis.line(X=np.array([batch_idx]),Y=np.array([COSINE_SIMILARITY]),win=win_mse_org,name='Cos_Sim_Skill_'+str(i),update='append')#,opts=options_lgnd)
                if (COSINE_SIMILARITY)>=(0.996):
                    values=values+1
                # if total<=7:
                #     if (Avg_Accuracy)>=(Actual_Accuracy[i]):
                #         values=values+1
                # else:
                #     if (Avg_Accuracy)>=(Actual_Accuracy[i]):
                #         print("verifying the degrading threshold")
                #         values=values+1
            if values==total:
                print("########## \n Batch id is",batch_idx,"\n#########")
                threshold_batchid.append(batch_idx)
                threshold_net_updates.append((batch_idx*total)+total_resend)
                break
    final_dataframe_1.columns=['no_of_skills','batch_idx','skill','caluclated_mse','mse_wrt_orginal','Accuracy','Actual_Accuracy','Resend_len','COSINE_SIMILARITY','COSINE_SIMILARITY_wrt_orginal']
    final_dataframe_1.to_hdf('Collected_Data/'+str(len(task_samples_copy))+'_test_data.hdf','key1')
    stage=stage+3
    return accuracies

######################################################################################################
#                           FLATTEN THE CIFAR WEIGHTS AND FEED IT TO CAE                             #
######################################################################################################
def FLATTEN_WEIGHTS_TRAIN_VAE(task_samples,model):
    final_skill_sample=[]
    Flat_input,net_shapes=helper_functions.flattenNetwork(model.cpu())
    final_skill_sample.append(Flat_input)
    Actual_task_net_weights.append(Flat_input)
    if len(task_samples)==0:
        accuracies = CAE_AE_TRAIN(net_shapes,task_samples+final_skill_sample,100)
    else:
        accuracies = CAE_AE_TRAIN(net_shapes,task_samples+final_skill_sample,300)
    return accuracies

#####################################################################################################################
#                                  CIFAR AND CAE TRAIN START HERE ALL START HERE                                    #
#####################################################################################################################
#if Flags['CIFAR_10_Incrmental']:

for cifar_class in range(0,10):
    allAcc = []
    model=models.Net()
    #model.load_state_dict(torch.load('../cifar_10_pretrain.pt'))
    optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9)
    task_samples=[]
    Train_loader,Test_loader=load_individual_class(list(range(cifar_class*10, (cifar_class+1)*10)),[])
    accuracy=train(model,Train_loader,Test_loader,optimizer,3,'CIFAR Skill '+str(cifar_class+1))
    torch.save(model.state_dict(),'task_net_models/cifar_classes_'+str(cifar_class)+'.pt')
    Actual_Accuracy.append(int(accuracy))
    print("Actual ACCCC",Actual_Accuracy,cifar_class)
    print("Threshold of Different SKills are",threshold_batchid)
    if cifar_class==0:
        accuracies=FLATTEN_WEIGHTS_TRAIN_VAE([],model)
    else:
        m=0
        n=3
        #print(Skill_Mu)
        #print(len(Skill_Mu))
        for i in range(0,cifar_class):
            generated_sample=[]
            for j in range(m,n):  
                recall_memory_sample=Skill_Mu[j][0]
                sample=student_model.decoder(recall_memory_sample).cpu()
                sample=sample.data.numpy()#.reshape(20442)
                generated_sample=np.concatenate([generated_sample,sample])
            task_samples.append(generated_sample)
            m=m+3
            n=n+3
        accuracies=FLATTEN_WEIGHTS_TRAIN_VAE(task_samples[0:62006],model) 
    allAcc.append(accuracies)

    with open('Collected_Data/allAcc_'+str(cifar_class), 'wb') as fp:
        pickle.dump(allAcc, fp)

    with open('Collected_Data/Actual_Accuracy_'+str(cifar_class), 'wb') as fp:
        pickle.dump(Actual_Accuracy, fp)

    if cifar_class>=1:
        options = dict(fillarea=True,width=400,height=400,xlabel='Skill',ylabel='Actual_Accuracy',title='Actual_Accuracy')
        options_threshold = dict(fillarea=True,width=400,height=400,xlabel='Skill',ylabel='Threshold_Cutoff',title='Cutoff_Threshold')
        options_threshold_net_updates = dict(fillarea=True,width=400,height=400,xlabel='Skill',ylabel='Threshold_Cutoff',title='Cutoff_Threshold_Net_Updates')
        vis.bar(X=Actual_Accuracy,opts=options,win='acc_viz')
        vis.bar(X=threshold_batchid,opts=options_threshold,win='threshold_viz')
        vis.bar(X=threshold_net_updates,opts=options_threshold_net_updates,win='threshold_viz_net_updates')

# plotAccuracies(allAcc)
# plotAccuracyDiff(allAcc,Actual_Accuracy)
# plotAccuracyDiffPoint(allAcc,Actual_Accuracy,testPoint=25)
# plotAccuracyDiffPointAll(allAcc,Actual_Accuracy,testPoint=25)

# if Flags['CIFAR_10_Incrmental']:
#     for classess in range(0,10):
#         load_individual_class(list(range(classess*10, (classess+1)*10)),[])
#         for epoch in range(0,5):
#             train_cifar10(epoch)
#             test_cifar10(epoch)
#         torch.save(net.state_dict(),'cifar_individual_weights/cifar_classes_'+str(classess*10)+'to'+str((classess+1)*10)+'.pt')
#         # criterion = nn.CrossEntropyLoss()


#--------------------------------------------
