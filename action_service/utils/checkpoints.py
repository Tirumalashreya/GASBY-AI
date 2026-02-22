import os
import torch

def load_weights(model, args):
    pretrained_dict = torch.load('{}/{}_{}_{}.pt'.format(args.model_path, args.base_model_name, args.start_epoch, args.lr),  map_location=torch.device('cpu'))['state_dict']
    model_dict = model.state_dict()
    pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict}
    model_dict.update(pretrained_dict)
    model.load_state_dict(model_dict)

    return model
