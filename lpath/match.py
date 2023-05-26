"""
Pattern match your extracted trajectories and cluster pathways classes.
"""
# Code that pattern matches states a trajectory has been through
# and then cluster them into fundamental few pathways.
#
# This is pulled from 'version 6', which expands on reassigning and
# allows for > 9 states.
#

import pickle
from os.path import exists
from shutil import copyfile

import numpy
import pylcs
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import squareform
from sklearn.metrics import pairwise_distances
from tqdm.auto import tqdm, trange

from lpath.extloader import *

log = logging.getLogger(__name__)


def tostr(b):
    """
    Convert a nonstandard string object ``b`` to str with the handling of the
    case where ``b`` is bytes.

    """
    if b is None:
        return None
    elif isinstance(b, bytes):
        return b.decode('utf-8')
    else:
        return str(b)


def calc_dist(seq1, seq2, dictionary, pbar):
    """
    Pattern match and calculate the similarity between two ``state string`` sequences.

    Parameters
    ----------
    seq1 : numpy.ndarray
        First string to be compared.

    seq2 : numpy.ndarray
        Second string to be compared.

    dictionary : dict
        Dictionary mapping ``state_id`` (float/int) to ``state string`` (characters).

    pbar : tqdm.tqdm
        A tqdm.tqdm object for the progress bar.

    Returns
    -------
    1 - similarity : float
        Similarity score.

    """
    # Remove all instances of "unknown" state, which is always the last entry in the dictionary.
    seq1 = seq1[seq1 < len(dictionary) - 1]
    seq1_str = "".join(dictionary[x] for x in seq1)
    seq2 = seq2[seq2 < len(dictionary) - 1]
    seq2_str = "".join(dictionary[x] for x in seq2)

    km = int(pylcs.lcs_sequence_length(seq1_str, seq2_str))
    similarity = (2 * km) / (int(len(seq1_str) + len(seq2_str)))

    pbar.update(1)

    return 1 - similarity


def calc_dist_substr(seq1, seq2, dictionary, pbar):
    """
    Pattern match and calculate the similarity between two ``state string`` substrings.
    Used when you're comparing segment ids.

    Parameters
    ----------
    seq1 : numpy.ndarray
        First string to be compared.

    seq2 : numpy.ndarray
        Second string to be compared.

    dictionary : dict
        Dictionary mapping ``state_id`` (float/int) to ``state string`` (characters).

    pbar : tqdm.tqdm
        A tqdm.tqdm object for the progress bar.

    Returns
    -------
    1 - similarity : float
        Similarity score.

    """
    # Remove all instances of initial/basis states.
    # seq1 = seq1[seq1 > 0]
    seq1_str = "".join(dictionary[x] for x in seq1)
    # seq2 = seq2[seq2 > 0]
    seq2_str = "".join(dictionary[x] for x in seq2)

    km = int(pylcs.lcs_string_length(seq1_str, seq2_str))
    similarity = (2 * km) / (int(len(seq1_str) + len(seq2_str)))

    pbar.update(1)

    return 1 - similarity


def load_data(file_name):
    """
    Load in the pickle data from ``extract``.

    Parameters
    ----------
    file_name: str
        File name of the pickle object from ``extract``

    Returns
    -------
    data : list
        A list with the data necessary to reassign, as extracted from ``output.pickle``.

    pathways : numpy.ndarray
        An empty array with shapes for iter_id/seg_id/state_id/pcoord_or_auxdata/frame#/weight.

    """
    with open(file_name, "rb") as f:
        data = pickle.load(f)

    npathways = len(data)
    assert npathways, "Pickle object is empty. Are you sure there are transitions?"
    lpathways = max([len(i) for i in data])
    n = len(data[0][0])

    pathways = numpy.zeros((npathways, lpathways, n), dtype=object)
    # This "Pathways" array should be Iter/Seg/State/auxdata_or_pcoord/frame#/weight

    log.debug(f'Loaded pickle object.')

    return data, pathways


def reassign_custom(data, pathways, dictionary, assign_file=None):
    """
    Reclassify/assign frames into different states. This is highly
    specific to the system. If w_assign's definition is sufficient,
    you can proceed with what's made in the previous step
    using ``reassign_identity``.

    In this example, the dictionary maps state idx to its corresponding ``state_string``.
    I suggest using alphabets as states.

    Parameters
    ----------
    data : list
        An array with the data necessary to reassign, as extracted from ``output.pickle``.

    pathways : numpy.ndarray
        An empty array with shapes for iter_id/seg_id/state_id/pcoord_or_auxdata/frame#/weight.

    dictionary : dict
        An empty dictionary obj for mapping ``state_id`` with ``state string``.

    assign_file : str, default : None
        A string pointing to the ``assign.h5`` file. Needed as a parameter for all functions,
        but is ignored if it's an MD trajectory.

    Returns
    -------
    dictionary : dict
        A dictionary mapping each ``state_id`` (float/int) with a ``state string`` (character).

    """
    # Other example for grouping multiple states into one.
    for idx, val in enumerate(data):
        # The following shows how you can "merge" multiple states into
        # a single one.
        flipped_val = numpy.asarray(val)[::-1]
        # Further downsizing... to if pcoord is less than 5
        first_contact = numpy.where(flipped_val[:, 3] < 5)[0][0]
        for idx2, val2 in enumerate(flipped_val):
            # First copy all columns over
            pathways[idx, idx2] = val2
            # ortho is assigned to state 0
            if val2[2] in [1, 3, 4, 6, 7, 9]:
                val2[2] = 0
            # para is assigned to state 1
            elif val2[2] in [2, 5, 8]:
                val2[2] = 1
            # Unknown state is assigned 2
            if idx2 < first_contact:
                val2[2] = 2
            pathways[idx, idx2] = val2

    # Generating a dictionary mapping each state
    dictionary = {0: 'A', 1: 'B', 2: '!'}

    return dictionary


def reassign_statelabel(data, pathways, dictionary, assign_file):
    """
    Use ``assign.h5`` states as is with ``statelabels``. Does not reclassify/assign frames
    into new states.

    In this example, the dictionary maps state idx to its ``statelabels``,
    as defined in the assign.h5. I suggest using alphabets as ``statelabels``
    to allow for more than 9 states.

    Parameters
    ----------
    data : list
        An list with the data necessary to reassign, as extracted from ``output.pickle``.

    pathways : numpy.ndarray
        An empty array with shapes for iter_id/seg_id/state_id/pcoord_or_auxdata/frame#/weight.

    dictionary : dict
        An empty dictionary obj for mapping ``state_id`` with "state string".

    assign_file : str
        A string pointing to the ``assign.h5`` file. Needed as a parameter, but ignored if it's an MD trajectory.

    Returns
    -------
    dictionary : dict
        A dictionary mapping each ``state_id`` (float/int) with a state string (character).

    """
    for idx, val in enumerate(data):
        flipped_val = numpy.asarray(val)[::-1]
        for idx2, val2 in enumerate(flipped_val):
            pathways[idx, idx2] = val2

    try:
        import h5py
        with h5py.File(assign_file) as f:
            for idx, val in enumerate(f['state_labels'][:]):
                dictionary[idx] = tostr(val)
        dictionary[len(dictionary)] = '!'  # Unknown state
    except ModuleNotFoundError:
        raise ModuleNotFoundError('Could not import h5py. Exiting out.')

    return dictionary


def reassign_segid(data, pathways, dictionary, assign_file=None):
    """
    Use seg ids as state labels.

    Parameters
    ----------
    data : list
        An list with the data necessary to reassign, as extracted from ``output.pickle``.

    pathways : numpy.ndarray
        An empty array with shapes for iter_id/seg_id/state_id/pcoord_or_auxdata/frame#/weight.

    dictionary : dict
        An empty dictionary obj for mapping ``state_id`` with ``state string``.

    assign_file : str
        A string pointing to the ``assign.h5`` file. Needed as a parameter, but ignored if it's an MD trajectory.

    Returns
    -------
    dictionary : dict
        A dictionary mapping each ``state_id`` (float/int) with a `state string` (character).

    """
    for idx, val in enumerate(data):
        flipped_val = numpy.asarray(val)[::-1]
        for idx2, val2 in enumerate(flipped_val):
            pathways[idx, idx2] = val2  # Copy everything...
            pathways[idx, idx2, 2] = val2[1]  # Replace states with seg_id

    n_states = int(max([seg[2] for traj in pathways for seg in traj])) + 1
    for idx in range(n_states):
        dictionary[idx] = chr(idx + 65)  # Map seg_id to a unique character

    dictionary[n_states] = '!'  # Unknown state

    return dictionary


def reassign_identity(data, pathways, dictionary, assign_file=None):
    """
    Use assign.h5 states as is. Does not attempt to map assignment
    to ``statelabels`` from assign.h5.

    Parameters
    ----------
    data : list
        An list with the data necessary to reassign, as extracted from ``output.pickle``.

    pathways : numpy.ndarray
        An empty array with shapes for iter_id/seg_id/state_id/pcoord_or_auxdata/frame#/weight.

    dictionary : dict
        An empty dictionary obj for mapping ``state_id`` with ``state string``.

    assign_file : str
        A string pointing to the ``assign.h5`` file. Needed as a parameter, but ignored if it's an MD trajectory.

    Returns
    -------
    dictionary : dict
        A dictionary mapping each ``state_id`` (float/int) with a `state string` (character).

    """
    for idx, val in enumerate(data):
        flipped_val = numpy.asarray(val)[::-1]
        for idx2, val2 in enumerate(flipped_val):
            pathways[idx, idx2] = val2

    n_states = int(max([seg[2] for traj in pathways for seg in traj])) + 1
    for idx in range(n_states):
        dictionary[idx] = str(idx)

    dictionary[n_states] = '!'  # Unknown state

    return dictionary


def expand_shorter_traj(pathways, dictionary):
    """
    Assigns a non-state to pathways which are shorter than
    the max length.

    Parameters
    ----------
    pathways : numpy.ndarray or list
        An array with shapes for iter_id/seg_id/state_id/pcoord_or_auxdata/frame#/weight.

    dictionary: dict
        Maps each state_id to a corresponding string.

    """
    for pathway in pathways:
        for step in pathway:
            if step[0] == 0:  # If no iteration number (i.e., a dummy frame)
                step[2] = len(dictionary) - 1  # Mark with the last entry


def gen_dist_matrix(pathways, dictionary, file_name="distmat.npy", out_dir="succ_traj", remake=True, metric=True,
                    n_jobs=None):
    """
    Generate the path_string to path_string similarity distance matrix.

    Parameters
    ----------
    pathways : numpy.ndarray
        An array with all the sequences to be compared.

    dictionary : dict
        A dictionary to map pathways states to characters.

    file_name : str, default : 'distmat.npy'
        The file to output the distance matrix.

    out_dir : str, default : 'succ_traj'
        Directory to output any files.

    remake : bool, default : True
        Indicates whether to remake distance matrix or not.

    metric : bool, default : True
        Indicate which metric to use. If True, the ``longest common subsequence`` metric will be used.
        If False, the ``longest common substring`` metric will be used. The latter should only be used
        when comparing states where ``trace_basis`` set as True, such as with segment IDs.

    n_jobs : int, default : None
        Number of jobs to run for the pairwise_distances() calculation. The default issues one job.

    Returns
    -------

    """
    out_dir = f'{out_dir.rsplit("/", 1)[0]}'
    new_name = f"{out_dir}/{file_name}"

    weights = []
    path_strings = []
    if metric:
        for pathway in pathways:
            # weights for non-existent iters
            nonzero = pathway[pathway[:, 2] < len(dictionary) - 1]
            weights.append(nonzero[-1][-1])
            # Create path_strings
            path_strings.append(pathway[:, 2])
    else:
        for pathway in pathways:
            weights.append(pathway[-1][-1])
            # Create path_strings
            path_strings.append(pathway[:, 2])

    weights = numpy.asarray(weights)

    if not exists(new_name) or remake is True:
        log.debug(f'Proceeding to calculate distance matrix.')
        pbar = tqdm(total=int((len(path_strings) * (len(path_strings) - 1)) / 2))
        if metric:
            distmat = pairwise_distances(
                X=path_strings, metric=lambda x, y: calc_dist(x, y, dictionary, pbar), n_jobs=n_jobs,
            )
        else:
            distmat = pairwise_distances(
                X=path_strings, metric=lambda x, y: calc_dist_substr(x, y, dictionary, pbar), n_jobs=n_jobs,
            )
        numpy.save(file_name, distmat)
    else:
        distmat = numpy.load(file_name)
        log.debug(f'Loaded precalculated distance matrix.')

    return distmat, weights


def visualize(distmat, threshold, out_dir="succ_traj", show=True):
    """
    Visualize the Dendrogram to determine hyper-parameters (n-clusters).
    Theoretically done only once to check.

    """
    out_dir = f'{out_dir.rsplit("/", 1)[0]}'

    distmat_condensed = squareform(distmat, checks=False)

    z = sch.linkage(distmat_condensed, method="ward")

    try:
        import matplotlib.pyplot as plt
    except (ModuleNotFoundError, ImportError) as e:
        log.debug(e)
        log.debug(f'Can not import matplotlib.')
        return

    # Clean slate.
    plt.cla()

    # Plot dendrogram
    try:
        sch.dendrogram(z, no_labels=True, color_threshold=threshold)
    except RecursionError as e:
        # Catch cases where are too many branches in the dendrogram for default recursion to work.
        import sys
        sys.setrecursionlimit(100000)
        log.warning(e)
        log.warning(f'WARNING: Dendrogram too complex to plot with default settings. Upping the recursion limit.')
        sch.dendrogram(z, no_labels=True, color_threshold=threshold)

    plt.axhline(y=threshold, c="k")
    plt.ylabel("distance")
    plt.xlabel("pathways")
    plt.savefig(f"{out_dir}/dendrogram.pdf")
    if show:
        plt.show()


def hcluster(distmat, n_clusters):
    """
    Scikit-learn Hierarchical Clustering of the different pathways.

    """
    distmat_condensed = squareform(distmat, checks=False)

    z = sch.linkage(distmat_condensed, method="ward")

    # (Hyper Parameter t=number of cluster)
    cluster_labels = sch.fcluster(z, t=n_clusters, criterion="maxclust")

    return cluster_labels


def determine_clusters(cluster_labels, clusters=None):
    """
    Determine how many clusters to output.

    Parameters
    ----------
    cluster_labels : numpy.ndarray
        An array with cluster assignments for each pathway.

    clusters : list or None
        Straight from the argparser.

    Returns
    -------
    clusters : list
        A list of clusters to output.

    """
    if clusters is None:
        clusters = list(range(0, max(cluster_labels) + 1))
    elif not isinstance(clusters, list):
        try:
            list(clusters)
        except TypeError:
            raise TypeError(
                "Provided cluster numbers don't work. Provide a list desired of cluster numbers or 'None' to output \
                all clusters."
            )

    return clusters


def export_pickle(pathways, output_path):
    """
    Option to output the reassigned pickle object.

    Parameters
    ----------
    pathways : numpy.ndarray
        A reassigned pathway object

    output_path : str
        Path to output pickle object.

    """
    with open(output_path, 'wb') as f:
        pickle.dump(pathways, f)


def select_rep(data_arr, weights, cluster_labels, icluster):
    """
    Small function to determine representative array/weight

    Parameters
    ----------
    data_arr : numpy.ndarray
        The array with all the pathways.

    weights : numpy.ndarray
        Weight information of the pathways.

    cluster_labels : numpy.ndarray
        An array with cluster assignments for each pathway.

    icluster : int
        Index of cluster to look at.

    Returns
    -------
    data_cl : list
        A list of pathways from icluster.

    rep_weight : float
        The weight of the representative structure of icluster.

    """
    selected_cluster = cluster_labels == icluster
    cluster_arr = numpy.array(data_arr, dtype=object)[selected_cluster]
    data_cl = list(cluster_arr)
    weights_cl = weights[selected_cluster]
    rep_weight = data_cl[numpy.argmax(weights_cl)][0]

    return data_cl, rep_weight


def export_std_files(data_arr, weights, cluster_labels, clusters=None, out_dir="succ_traj"):
    """
    Export data for standard simulations.

    Parameters
    ----------
    data_arr : numpy.ndarray
        The array with all the pathways.

    weights : numpy.ndarray
        Weight information of the pathways.

    cluster_labels : numpy.ndarray
        An array with cluster assignments for each pathway.

    clusters : list or None
        A list of clusters to output, straight from the argparser.

    out_dir : str
        Directory to output files.

    """
    clusters = determine_clusters(cluster_labels, clusters)

    representative_file = f'{out_dir.rsplit("/", 1)[0]}' + '/representative_segments.txt'
    representative_list = []

    for icluster in clusters:
        trace_out_list = []
        data_cl, rep_weight = select_rep(data_arr, weights, cluster_labels, icluster)
        log.debug(f'cluster {icluster} representative weight: {rep_weight}')
        representative_list.append(f'{rep_weight}\n')

        for idx, item in enumerate(data_cl):
            trace_out_list.append(list(numpy.array(item)[:, :2]))

    with open(representative_file, 'w') as f:
        f.writelines(representative_list)


def export_we_files(data_arr, weights, cluster_labels, clusters, file_pattern="west_succ_c{}.h5",
                    out_dir="succ_traj", west_name='west.h5'):
    """
    Export each group of successful trajectories into independent west.h5 file.

    Parameters
    ----------
    data_arr : numpy.ndarray
        The array with all the pathways.

    weights : numpy.ndarray
        Weight information of the pathways.

    cluster_labels : numpy.ndarray
        An array with cluster assignments for each pathway.

    clusters : list or None
        A list of clusters to output.

    file_pattern : str
        String pattern of how files should be outputted.

    out_dir : str
        Directory to output files.

    west_name : str
        Name of west.h5 file to use as base.

    """
    try:
        import h5py
    except ModuleNotFoundError:
        raise ModuleNotFoundError('Could not import h5py. Exiting out.')

    clusters = determine_clusters(cluster_labels, clusters)
    out_dir = out_dir.rsplit("/", 1)[0]

    representative_file = f'{out_dir}' + '/representative_segments.txt'
    representative_list = []
    for icluster in clusters:
        new_file = f'{out_dir}/' + file_pattern.format(str(icluster))

        if not exists(new_file):
            copyfile(west_name, new_file)

        first_iter = 1
        with h5py.File(west_name, "r") as h5_file:
            last_iter = len(h5_file['summary'])

        # tqdm load bar, working backwards
        tqdm_iter = trange(last_iter, first_iter - 1, -1, desc="iter")

        # Identify constituents of a cluster to output.
        trace_out_list = []
        data_cl, rep_weight = select_rep(data_arr, weights, cluster_labels, icluster)

        log.debug(f'cluster {icluster} representative weight: {rep_weight}')
        representative_list.append(f'{rep_weight}\n')

        for idx, item in enumerate(data_cl):
            trace_out_list.append(list(numpy.array(item)[:, :2]))

        exclusive_set = {tuple(pair) for ilist in trace_out_list for pair in ilist}
        with h5py.File(new_file, "r+") as h5file:
            for n_iter in tqdm_iter:
                for n_seg in trange(len(h5file[f'iteration/{n_iter:>08}/seg_index']), leave=False):
                    if (n_iter, n_seg) not in exclusive_set:
                        h5file[f"iterations/iter_{n_iter:>08}/seg_index"]["weight", n_seg] = 0

    with open(representative_file, 'w') as f:
        f.writelines(representative_list)


def determine_rerun(dist_matrix):
    """
    Asks if you want to regenerate the dendrogram.

    Parameters
    ----------
    dist_matrix : numpy.ndarray
        A Numpy array of the distance matrix.
    """
    while True:
        try:
            ans = input('Do you want to regenerate the graph with a new threshold (y/[n])?\n')
            if ans == 'y' or ans == 'Y':
                ans2 = input('What new threshold would you like?\n')
                visualize(dist_matrix, threshold=float(ans2), show=True)
            elif ans == 'n' or ans == 'N' or ans == '':
                break
            else:
                input("Invalid input.\n")
        except KeyboardInterrupt:
            sys.exit(0)


def ask_number_cluster():
    """
    Asks how many clusters you want to separate the trajectories into.

    """
    while True:
        try:
            ans = input('How many clusters would you like to separate the pathways into?\n')
            try:
                ans = int(ans)
                return ans
            except ValueError:
                print("Invalid input.\n")
        except KeyboardInterrupt:
            sys.exit(0)


def report_statistics(nclusters, cluster_labels, weights):
    """
    Report statistics about the final clusters.

    Parameters
    ----------
    nclusters : int
        Number of clusters.

    cluster_labels : numpy.ndarray
        An array mapping pathways to cluster

    weights : numpy.ndarray
        Weight information

    Returns
    -------

    """
    # Initialize the dictionary with 0 weight. 1-based for cl.
    final_dictionary = dict()
    counts = dict()
    for j in range(1, nclusters + 1):
        final_dictionary[j] = 0
        counts[j] = 0

    for (cl, weight) in zip(cluster_labels, weights):
        final_dictionary[cl] += weight
        counts[cl] += 1

    report = f'===lpath Pattern Matching Statistics===\n'
    report += f'Total Number of clusters: {nclusters}\n'
    for (key, val) in final_dictionary.items():
        report += f'Weight/count of cluster {key}: {val} / {counts[key]}\n'
    log.info(report)


def main(arguments):
    """
    Main function that executes the whole `match` step.

    Parameters
    ----------
    arguments : argparse.Namespace
        A Namespace object will all the necessary parameters.

    """
    # Dealing with the preset assign_method
    preset_reassign = {
        'reassign_identity': reassign_identity,
        'reassign_statelabel': reassign_statelabel,
        'reassign_custom': reassign_custom,
        'reassign_segid': reassign_segid,
    }

    if arguments.reassign_method in preset_reassign.keys():
        reassign = preset_reassign[arguments.reassign_method]
    else:
        import sys
        import os
        sys.path.append(os.getcwd())

        reassign = get_object(arguments.reassign_method)
        log.info(f'INFO: Replaced reassign() with {arguments.reassign_method}')

    # Prepping the data + Calculating the distance matrix
    data, pathways = load_data(arguments.input_pickle)

    dictionary = {}
    # Reassignment... (or not) Make sure `dictionary` is declared globally since calc_distances() requires it.
    dictionary = reassign(data, pathways, dictionary, arguments.assign_name)  # system-specific reassignment of states

    if len(dictionary) < 3:
        log.warning(f'WARNING: Only {len(dictionary)} states defined, including the "unknown" state. \
                      This will likely produce bad clustering results and you should considering reassigning to more \
                      intermediate states using a modified ``--reassign-method``.')

    log.debug(f'Completed reassignment.')

    # Cleanup
    expand_shorter_traj(pathways, dictionary)  # Necessary if pathways are of variable length
    log.debug(f'Cleaned up trajectories.')
    dist_matrix, weights = gen_dist_matrix(pathways, dictionary, file_name=arguments.dmatrix_save,
                                           out_dir=arguments.out_dir,
                                           remake=arguments.dmatrix_remake,  # Calculate distance matrix
                                           metric=arguments.longest_subsequence,  # Which metric to use
                                           n_jobs=arguments.dmatrix_parallel)  # Number of jobs for pairwise_distance

    log.debug(f'Generated distance matrix.')
    # Visualize the Dendrogram and determine how clusters used to group successful trajectories
    visualize(dist_matrix, threshold=arguments.dendrogram_threshold, out_dir=arguments.out_dir,
              show=arguments.dendrogram_show)  # Visualize
    determine_rerun(dist_matrix)
    ncluster = ask_number_cluster()
    cluster_labels = hcluster(dist_matrix, ncluster)

    # Report statistics
    if arguments.stats:
        log.debug('Reporting statistics')
        report_statistics(ncluster, cluster_labels, weights)

    # Output cluster labels and reassigned pickle object
    log.debug('Outputting files')
    export_pickle(pathways, arguments.output_pickle)
    numpy.save(arguments.cl_output, cluster_labels)

    # Following exports each cluster to its own h5 file, all weights of segments not in that group = 0.
    if arguments.we and arguments.export_h5:
        export_we_files(
            pathways,
            weights,
            cluster_labels,
            clusters=arguments.clusters,
            out_dir=arguments.out_dir,
            file_pattern=arguments.file_pattern,
            west_name=arguments.west_name,
        )