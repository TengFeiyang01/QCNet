from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_scatter import segment_csr

from losses.gaussian_nll_loss import GaussianNLLLoss


class MixtureOfGaussianNLLLoss(nn.Module):

    def __init__(self,
                 full: bool = False,
                 eps: float = 1e-6,
                 reduction: str = 'mean') -> None:
        super(MixtureOfGaussianNLLLoss, self).__init__()
        self.reduction = reduction
        self.nll_loss = GaussianNLLLoss(full=full, eps=eps, reduction='none')

    def forward(self,
                pred: torch.Tensor,
                target: torch.Tensor,
                prob: torch.Tensor,
                mask: torch.Tensor,
                ptr: Optional[torch.Tensor] = None,
                joint: bool = False) -> torch.Tensor:
        nll = self.nll_loss(pred=pred, target=target.unsqueeze(1))
        nll = (nll * mask.view(-1, 1, target.size(-2), 1)).sum(dim=(-2, -1))
        if joint:
            if ptr is None:
                nll = nll.sum(dim=0, keepdim=True)
            else:
                nll = segment_csr(src=nll, indptr=ptr, reduce='sum')
        else:
            pass
        log_pi = F.log_softmax(prob, dim=-1)
        loss = -torch.logsumexp(log_pi - nll, dim=-1)
        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        elif self.reduction == 'none':
            return loss
        else:
            raise ValueError('{} is not a valid value for reduction'.format(self.reduction))
