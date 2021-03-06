from scipy import sparse
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import utils

#torch.multiprocessing.set_start_method("spawn")

def variable_collate(batch):
    claims = []
    evidences = []
    labels = []
    for item in batch:
        claims.append(item[0])
        evidences.append(item[1])
        labels.append(item[2])
    claims = stack_uneven(claims)
    evidences = stack_uneven(evidences)
    labels = torch.stack(labels)


    print(batch[0]) 
    

class WikiDataset(Dataset):
    """
    Generates data with batch size of 1 sample for the purposes of training our model.
    """
    def __init__(self, data, claims_dict, data_batch_size=10, batch_size=32, split=None):
        """
            Sets the initial arguments and creates
            an indicies array to randomize the dataset
            between epochs
        """
        if split:            
            self.indicies = split
        else:
            self.indicies = list(range(len(data)))
        self.data = data
        use_cuda = True
        self.device = torch.device("cuda:0" if use_cuda else "cpu")
        self.data_batch_size = data_batch_size
        self.encoder = utils.ClaimEncoder()
        self.claims_dict = claims_dict
        self.batch_size = batch_size
        _, _, _, _, self.claim_to_article = utils.extract_fever_jsonl_data("../train.jsonl")
        
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, index):
        return self.get_item(index)
    
    def get_item(self, index):            
        #data_index = index % self.data_batch_size
        item_index = index 
        
        d = self.data[item_index]
        try:
            claim = to_torch_sparse_tensor(self.claims_dict[utils.preprocess_article_name(d['claim']) + " "], device=self.device)
        except KeyError:
            return self.get_item(index+1)

        evidences = []
        labels = []

        processed = self.claim_to_article[d['claim']][0]
        evidence = self.encoder.tokenize_claim(processed)
        evidence = sparse.vstack(evidence)
        evidence = evidence.toarray()
        evidences.append(evidence)
        labels.append(1)

        #evidence = to_torch_sparse_tensor(evidence, device=self.device)
        #dense_arrs = [i.toarray() for i in evidence]
        #stacked_arr = np.vstack(dense_arrs)
        #evidences.append(stacked_arr)
        try:
            for j in range(self.data_batch_size-1):
                e = np.random.choice(d['evidence'])
                processed = utils.preprocess_article_name(e.split("http://wikipedia.org/wiki/")[1])
                #evidence = articles_dict[processed]
                evidence = self.encoder.tokenize_claim(processed)
                evidence = sparse.vstack(evidence).toarray() 
                evidences.append(evidence)
                if processed in self.claim_to_article[d['claim']]:
                    labels.append(1)
                else:
                    labels.append(0)
        except ValueError:
            print(index) 

        #evidences = stack_uneven(evidences)
        #evidences = torch.from_numpy(evidences).float()

        #claim = claim.to(self.device) 
        #evidence = evidence.to(self.device) 
        #claim = claim.cuda()
        #evidences = evidences.cuda()
        #labels = torch.FloatTensor(labels, device=self.device).to(self.device)

        #claim = claim.to_dense()

        #evidences = stack_uneven(evidences)
        #claim = np.broadcast_to(claim, (len(evidences), claim.shape[1], claim.shape[2]))
        #claim = claim.expand(evidences.shape[0], claim.shape[0], claim.shape[1])
        return claim, evidences, labels 

    def on_epoch_end(self):
        #np.random.shuffle(self.indicies)
        pass

def to_torch_sparse_tensor(M, device="cuda:0"):
    M = M.tocoo().astype(np.float32)
    indices = torch.from_numpy(np.vstack((M.row, M.col))).cuda().long()
    values = torch.from_numpy(M.data).cuda()
    shape = torch.Size(M.shape)
    T = torch.cuda.sparse.FloatTensor(indices, values, shape, device=device)
    return T

def stack_uneven(arrays, fill_value=0.):
    '''
    Fits arrays into a single numpy array, even if they are
    different sizes. `fill_value` is the default value.

    Args:
            arrays: list of np arrays of various sizes
                (must be same rank, but not necessarily same size)
            fill_value (float, optional):

    Returns:
            np.ndarray
    '''
    sizes = [a.shape for a in arrays]
    max_sizes = np.max(list(zip(*sizes)), -1)
    # The resultant array has stacked on the first dimension
    result = np.full((len(arrays),) + tuple(max_sizes), fill_value)
    for i, a in enumerate(arrays):
      # The shape of this array `a`, turned into slices
      slices = tuple(slice(0,s) for s in sizes[i])
      # Overwrite a block slice of `result` with this array `a`
      result[i][slices] = a
    return result
