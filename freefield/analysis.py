import numpy as np
from scipy import stats
import pandas as pd
from slab import Trialsequence


def get_loctest_data(sequence):
    """
    Extract the data from a trialsequence and return them in a data frame. The trialsequence must be in the same format
    that is returned by the localization test functions in the main module. This means that every element in the
    conditions attribute must be an entry of the speaker table (pandas series) and every element of the data attribute
    must be a tuple with (azimuth, elevation) of the subjects response in that trial.
    Args:
        sequence (instance of slab.Trialsequence): the sequence containing the targets and response data
    Returns:
        pandas DataFrame: target and response coordinates
    """
    if not isinstance(sequence, Trialsequence):
        raise ValueError("Input must be slab trialsequence!")
    data = pd.DataFrame(columns=["azi_target", "ele_target", "azi_response", "ele_response"])
    for trial, response in zip(sequence.trials, sequence.data):
        target = sequence.conditions[trial-1]
        row = {"azi_target": target.azi, "ele_target": target.ele,
               "azi_response": response[0], "ele_response": response[1]}
        data = data.append(row, ignore_index=True)
    return data


def mean_dir(data, speaker):
    # use vector addition with uncorrected angles:
    # sines, cosines = _sines_cosines(data, speaker)
    # return numpy.rad2deg(sines.sum(axis=1) / cosines.sum(axis=1)).flatten()
    # use regular addition with corrected angles:
    idx = np.where(data[:,1] == speaker)
    return data[idx,2:4].mean(axis=1)


def mad(data, speaker, ref_dir=None):
    'Mean absolute difference between reference directions and pointed directions'
    if ref_dir is None:
        ref_dir = mean_dir(data, speaker)
    idx = np.where(data[:,1] == speaker)
    diffs = data[idx,2:4] - ref_dir
    return np.sqrt((diffs**2).sum(axis=2)).mean()


def rmse(data, speaker, ref_dir=None):
    'Vertical and horizontal localization accuracies were quantified by computing the root mean square of the discrep- ancies between perceived and physical locations (RMSE, Hartmann, 1983; Savel, 2009).'
    if ref_dir is None:
        ref_dir = mean_dir(data, speaker)
    idx = np.where(data[:,1] == speaker)
    diffs = data[idx,2:4] - ref_dir
    dist = np.sqrt((diffs**2).sum(axis=2))
    return np.sqrt((dist**2).mean())


def eg(data, speaker_positions=None):
    '''
    Vertical localization performance was also quantified by the EG, defined as the slope of the linear regression of perceived versus physical elevations (Hofman et al., 1998). Perfect localization corresponds to an EG of 1, while random elevation responses result in an EG of 0.'''
    eles = data[:,3]
    if speaker_positions is None:
        return np.percentile(eles, 75) - np.percentile(eles, 25)
    speaker_seq = data[:,1].astype(int) # presented sequence of speaker numbers
    elevation_seq = speaker_positions[speaker_seq,1] # get the elevations for the speakers in the presented sequence
    regression = stats.linregress(eles, elevation_seq)
    return regression.slope
