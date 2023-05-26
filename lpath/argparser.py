"""
All argument parsing from commandline is dealt here.
"""
import argparse
import logging

log = logging.getLogger(__name__)

arg_desc = """
lpath: minimal Pathway Analysis Histogram Analysis of Trajectories
=================================================================="""

all_options = ['discretize', 'extract', 'match', 'plot', 'all']


def check_non_neg(value):
    """
    Transform ``value`` into int and make sure it's >= 0.

    Parameters
    ----------
    value : str or float or int
        A value to check to see if it's >= 0.

    Returns
    -------
    value : int
        Only if int is greater or equal to 0. Will transform it to int in the processes.

    Raises
    ------
    argparse.ArgumentTypeError
        If value is < 0.

    ValueError
        If value is not an integer or float.

    """
    try:
        value = int(value)
        if value < 0:
            raise argparse.ArgumentTypeError("{} is not a valid input.".format(value))
    except ValueError:
        raise Exception("{} must be an integer.".format(value))

    return value


def check_positive(value):
    """
    Transform ``value`` into int and make sure it's > 0 (positive number).

    Parameters
    ----------
    value : str or float or int
        A value to check to see if it's > 0.

    Returns
    -------
    value : int
        Only if int is greater than 0. Will transform it to int in the processes.

    Raises
    ------
    argparse.ArgumentTypeError
        If value is <= 0.

    ValueError
        If value is not an integer or float.

    """
    try:
        value = int(value)
        if value <= 0:
            raise argparse.ArgumentTypeError("{} is not a valid positive number.".format(value))
    except ValueError:
        raise Exception("{} must be an integer.".format(value))

    return value


def create_parser():
    """
    Quickly create a parser.

    Returns
    -------
    parser : argparse.ArgumentParser
        Returns an instance of the parser.

    """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=arg_desc)

    return parser


def add_common_args(parser=None):
    """
    This block process all the common arguments for each module.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        A parser passed in from each tool. Separated from each function because the
        catch-all tool to run everything in succession will only have 1 parser.
        This will auto-create a parser if None is passed.

    Returns
    -------
    parser : argparse.ArgumentParser
        Returns an instance of the parser with all the new arguments added in.

    """
    if parser is None:
        parser = create_parser()

    commongroup = parser.add_argument_group('Shared Parameters')

    commongroup.add_argument('-od', '--out-dir', '--output-directory', dest='out_dir', default='succ_traj',
                             type=str, help='Directory to save your output files. Path relative to ``$PWD``.')
    commongroup.add_argument('-st', '--stride', dest='stride', default=1, type=check_positive,
                             help='Dictates how much data to use in analysis. If used in standard MD, this will \
                                   be the step size (at a per file basis during load time). For a WE simulation, \
                                   this will be how many sub-tau frames used from each segment, starting \
                                   from the last frame and then counting backwards.')
    commongroup.add_argument('-s', '--stats', '--statistics', dest='stats', action='store_true',
                             help='Enable results statistics output.')
    commongroup.add_argument('--debug', '-v', action='store_true', help='Enable debug mode.')

    wegroup = parser.add_argument_group('WE-specific Shared Parameters')

    wegroup.add_argument('-we', '-WE', '--weighted-ensemble', '--WEIGHTED-ENSEMBLE', dest='we',
                         action='store_true', help='Run analysis on a weight ensemble simulation.')
    wegroup.add_argument('-W', '--west', '--WEST_H5FILE', '--west-h5file', dest='west_name', default='west.h5',
                         help='The path to your h5 file. If it\'s a ``multi.h5`` file from ``w_multi_west``, make sure \
                               the ``--ibstates`` option successfully merged your initial and basis states. If you\'re \
                               analyzing regular MD trajectories, ignore.')
    wegroup.add_argument('-A', '--assign', '--assign-h5file', '--ASSIGN-H5FILE', dest='assign_name',
                         default='ANALYSIS/TEST/assign.h5',
                         help='Path to your ``assign.h5`` file for WE simulations. \
                               Not used if analyzing an MD trajectory.')
    wegroup.add_argument('-r', '--rcfile', metavar='RCFILE', dest='rcfile', default='west.cfg',
                         help='use RCFILE as the WEST run-time configuration file (default: %(default)s)')

    return parser


def add_discretize_args(parser=None):
    """
    This block process all the necessary arguments for the `discretize.py` module.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        A parser passed in from each tool. Separated from each function because the
        catch-all tool to run everything in succession will only have 1 parser.

    Returns
    -------
    parser : argparse.ArgumentParser
        Returns an instance of the parser with all the new arguments added in.

    """
    if parser is None:
        parser = create_parser()

    discretize_io = parser.add_argument_group('Discretize Specific Parameters')

    discretize_io.add_argument('-i', '-I', '-di', '-DI', '--input', dest='input_name', default='input.dat',
                               help='The path to your input file for discretization. Ideally, this would be a text \
                               file or a NumPy file with the features use to define source and target states. \
                               If the `-WE`` flag is specified, ``w_assign`` will run on ``--west-h5file`` instead \
                               to label your states.')
    discretize_io.add_argument('-o', '-O', '-do', '-DO', '--output', dest='output_name', default='states.npy',
                               help='The path to your output numpy file for after discretization. If ``-WE`` flag is \
                                     specified, ``--assign-h5file`` will be used instead.')
    discretize_io.add_argument('-af', '--assign-function', '--assign-func', dest='assign_func', type=str,
                               default='default_assign',
                               help='User provided function used to discretize MD trajectories.')

    discretize_we = parser.add_argument_group('WE-specific Discretize Parameters')

    discretize_we.add_argument('-ar', '--assign-args', '--assign-arguments', dest='assign_args', type=str, default='',
                               help='A string of arguments to pass onto w_assign as you would input in the command \
                                     line to ``w_assign``. Either use the defaults (leave blank for the ``TEST`` \
                                     scheme in ``west.cfg`` or at a minimum, you need to specify \
                                     ``--config-from-file --scheme NAME_OF_SCHEME`` to read \
                                     the config from your ``west.cfg`` file.')

    return parser


def add_extract_args(parser=None):
    """
    This block process all the necessary arguments for the "extract.py" module.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        A parser passed in from each tool. Separated from each function because the
        catch-all tool to run everything in succession will only have 1 parser.
        This will auto create a parser if None is passed.

    Returns
    -------
    parser : argparse.ArgumentParser
        Returns an instance of the parser with all the new arguments added in.

    """
    if parser is None:
        parser = create_parser()

    extract_io = parser.add_argument_group('Extract Specific Parameters')

    extract_io.add_argument('-ei', '-EI', '--extract-input', dest='extract_input', default='states.npy',
                            help='The path to your output numpy file from ``discretize`` step. If the ``-WE`` flag is \
                                  specified, this will be ignored as ``--west-h5file`` and ``--assign-h5file`` will be \
                                  used instead.')
    extract_io.add_argument('-eo', '-EO', '--extract-output', dest='extract_output', default='output.pickle',
                            help='Name of the output pickle object file. This will be saved in ``--out-dir``.')
    extract_io.add_argument('-ss', '--source', '--source-state', '--SOURCE-STATE', dest='source_state_num',
                            type=check_non_neg, default=0, help='Index of the source state. If the ``-WE`` flag is \
                                                                specified, this should match the index specified in \
                                                                ``w_assign``.')
    extract_io.add_argument('-ts', '--target', '--target-state', '--TARGET-STATE', dest='target_state_num',
                            type=check_non_neg, default=1, help='Index of the target state. If the ``-WE`` flag is \
                                                                specified, this should match the index specified in \
                                                                ``w_assign``.')
    extract_io.add_argument('--pcoord', '-p', dest='pcoord', action='store_true',
                            help='Output progress coordinate (or featurization) into the pickle file. If the \
                                  ``-WE`` flag is specified, the data will be obtained from the H5 file. Otherwise, \
                                  do specify a file name using the ``--extract-featurization`` flag.')
    extract_io.add_argument('-ef', '-EF', '--extract-pcoord', '--extract-featurization', dest='featurization_name',
                            default=None,
                            help='The path to your feature dataset to be saved in the output pickle file. For most \
                                  people, this would be the input used for the ``discretize`` step. This option \
                                  is only for standard simulations. You MUST manually specify the ``--pcoord`` flag \
                                  for this to work.')
    extract_io.add_argument('-fs', '--feature-stride', dest='feature_stride', default=1, type=check_positive,
                            help='Dictates the step size to which the ``--extract-featurization`` is read in. \
                                   You will want this to match ``--stride`` used in ``discretize``. \
                                   Ignored for a WE simulation.')
    extract_io.add_argument('--trace-basis', '-b', dest='trace_basis', action='store_true',
                            help='Whether to trace all the way back to the "basis state". False by default. For WE \
                                  simulations, this (as it is aptly named) output the trajectory all the way back \
                                  to the basis state. For standard simulations, This will either be the first frame of \
                                  the trajectory or, if it had previously reached the target state, the first time it \
                                  returned to the source state after it has left the target state.')

    raygroup = parser.add_argument_group('Extract Ray options')

    raygroup.add_argument('--use-ray', '-R', '--ray', dest='use_ray', default=True, action='store_true',
                          help='Use Ray work manager. On by default.')
    raygroup.add_argument('--no-ray', '-NR', dest='use_ray', action='store_false',
                          help='Do not use Ray. This overrides ``--use-ray``.')
    raygroup.add_argument('-t', '--threads', type=check_non_neg, default=0, help='Number of threads to use \
                          with Ray. The default of ``0`` uses all available resources detected.')

    extract_we = parser.add_argument_group('WE-specific Extract Parameters')

    extract_we.add_argument('--first', '--first-iter', '--FIRST-ITER', dest='first_iter', type=check_non_neg,
                            default=1, help='First iteration to look for successful trajectories, inclusive.')
    extract_we.add_argument('--last', '--last-iter', '--LAST-ITER', dest='last_iter', type=check_non_neg,
                            default=0, help='Last iteration to look for successful trajectories, inclusive. \
                                            Default is 0, which will use all available iterations.')
    extract_we.add_argument('-hdf5', '--hdf5', dest='hdf5', action='store_true', help='')

    extract_we.add_argument('-a', '--aux', '--AUX', '--auxdata', '--AUXDATA', dest='auxdata', nargs='*',
                            action='extend', help='Names of additional auxiliary datasets to be combined.')
    extract_we.add_argument('-aa', '--auxall', nargs='?', dest='auxdata', const=[],
                            help='Combine all auxiliary datasets.')
    extract_we.add_argument('--rewrite-weights', '-rw', action='store_true',
                            help='Option to zero out the weights of all segments that are not part of the successful \
                                 trajectory ensemble. Note this generates a new H5 file with the ``_succ`` suffix \
                                 added, meaning the default name is ``west_succ.h5``.')

    extract_we.add_argument('-oj', '--out-traj', '--output-trajectory', dest='out_traj',
                            action='store_true', help='Option to output trajectory files into ``out_dir``.')
    extract_we.add_argument('-oe', '--out-traj-ext', '--output-trajectory-extension', dest='out_traj_ext',
                            default='.nc', type=str, help='Extension of the segment files. The name of the file is \
                                                           assumed to be ``seg``, meaning the default name of the file \
                                                           is ``seg.nc``.')
    extract_we.add_argument('-se', '--out-state-ext', '--output-state-extension', dest='out_state_ext',
                            default='.ncrst', type=str, help='Extension of the restart files. The name of the file is \
                                                              assumed to be ``seg``, meaning the default name the file \
                                                              is ``seg.ncrst``.')
    extract_we.add_argument('-ot', '--out-top', '--output-topology', dest='out_top', default='system.prmtop',
                            type=str, help='Name of the topology file. Name is relative to ``$PWD/common_files``.')

    return parser


def add_match_args(parser=None):
    """
    This block process all the necessary arguments for the "match.py" module.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        A parser passed in from each tool. Separated from each function because the
        catch-all tool to run everything in succession will only have 1 parser.
        This will auto create a parser if None is passed.

    Returns
    -------
    parser : argparse.ArgumentParser
        Returns an instance of the parser with all the new arguments added in.

    """
    if parser is None:
        parser = create_parser()

    match_io = parser.add_argument_group('Match Specific Parameters')

    match_io.add_argument('-ip', '--IP', '--pickle', '--input-pickle', dest='input_pickle',
                          default='succ_traj/output.pickle', type=str, help='Path to pickle object from the `extract` \
                          step.')
    match_io.add_argument('-op', '--OP', '--output-pickle', dest='output_pickle',
                          default='succ_traj/pathways.pickle', type=str, help='Path to reassigned object to be \
                          outputted from the `match` step.')
    match_io.add_argument('-co', '--cl-output', '--cluster-label-output', dest='cl_output',
                          default='succ_traj/cluster_labels.npy', type=str,
                          help='Output file location for cluster labels.')
    match_io.add_argument('--reassign', '-ra', '--reassign-method', dest='reassign_method',
                          default='reassign_identity', type=str,
                          help='Reassign Method to use. Could be one of the defaults or a module to load. Defaults are \
                                ``reassign_identity``, ``reassign_statelabel``, ``reassign_segid`` , \
                                and ``reassign_custom``.')
    match_io.add_argument('--subsequence', '-seq', '--longest-common-subsequence', dest='longest_subsequence',
                          action='store_true', default=True,
                          help='Use the longest common subsequence metric. The final answer is a total of common \
                                discontinuous characters. This is the default.')
    match_io.add_argument('--substring', '-str', '--longest-common-substring', dest='longest_subsequence',
                          action='store_false',
                          help='Use the longest common substring metric. The final answer is a length of common \
                                continuous characters. This is not the default and (probably) should only be used when \
                                comparing segment ids with ``trace_basis`` turned on in ``extract``. Overrides \
                                ``--longest-common-subsequence``.')

    match_io.add_argument('--remake', '-dR', dest='dmatrix_remake', default=True, action='store_true',
                          help=argparse.SUPPRESS)
    match_io.add_argument('--no-remake', '-dN', '-nd', dest='dmatrix_remake', action='store_false',
                          help='Do not remake distance matrix. This overrides `--remake.`')
    match_io.add_argument('--remake-file', '--remade-file', '-dF', dest='dmatrix_save', type=str, default='distmat.npy',
                          help='Path to pre-calculated distance matrix. Make sure the ``--no-remake`` flag is \
                                specified. Assumed to be in ``out-dir``.')
    match_io.add_argument('--remake-parallel', '-dP', dest='dmatrix_parallel', type=int,
                          help='Number of jobs to run with the pairwise distance calculations. The default=None issues \
                                one job. A value of -1 uses all available resources. This is directly passed to the \
                                n_jobs parameter for ``sklearn.metrics.pairwise_distances()``.')

    match_io.add_argument('-dt', '--dendro-threshold', '--dendrogram-threshold', dest='dendrogram_threshold',
                          type=check_non_neg, default=0.5, help='Horizontal threshold line for the dendrogram.')
    match_io.add_argument('-ds', '--dendro-show', '--dendrogram-show', dest='dendrogram_show', default=True,
                          action='store_true', help=argparse.SUPPRESS)
    match_io.add_argument('-dh', '--dendro-hide', '--dendrogram-hide', dest='dendrogram_show', action='store_false',
                          help='Do not show dendrogram. Overrides ``--dendrogram-show``.')
    match_io.add_argument('-c', '--clusters', dest='clusters', default=None, nargs='*',
                          help='Clusters to export. 0-indexed. The default ``None`` will output all clusters.')

    match_we = parser.add_argument_group('WE-specific Match Parameters')

    match_we.add_argument('-ex', '--ex-h5', '--export-h5', dest='export_h5',
                          action='store_true', help='Export each cluster as an independent H5 file.')
    match_we.add_argument('-fp', '--fp', '--file-pattern', dest='file_pattern',
                          default="west_succ_c{}.h5", type=str, help='Pattern to name per-cluster HDF5 files.')

    return parser


def add_plot_args(parser=None):
    """
    This block process all the necessary arguments for the "plot.py" module.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        A parser passed in from each tool. Separated from each function because the
        catch-all tool to run everything in succession will only have 1 parser.
        This will auto create a parser if None is passed.

    Returns
    -------
    parser : argparse.ArgumentParser
        Returns an instance of the parser with all the new arguments added in.

    """
    if parser is None:
        parser = create_parser()

    plot_io = parser.add_argument_group('Plot Specific Parameters')

    plot_io.add_argument('-im', '--IM', '--match-plot', '--input-match', dest='output_pickle',
                         default='succ_traj/pathways.pickle', type=str, help='Path to pickle object from the `extract` \
                         step.')

    return parser


def add_all_args(parser=None):
    """
    This block process all the necessary arguments for all steps.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        A parser passed in from each tool. Separated from each function because the
        catch-all tool to run everything in succession will only have 1 parser.
        This will auto create a parser if None is passed.

    Returns
    -------
    parser : argparse.ArgumentParser
        Returns an instance of the parser with all the new arguments added in.

    """
    if parser is None:
        parser = create_parser()

    parser = add_common_args(parser)
    parser = add_discretize_args(parser)
    parser = add_extract_args(parser)
    parser = add_match_args(parser)
    parser = add_plot_args(parser)

    return parser


def create_subparsers(parser, subparser_list):
    # Generate all subparsers
    subparser = parser.add_subparsers(dest='step_name', required=True,
                                      help='Specify step(s) to execute')
    discretize = subparser.add_parser('discretize', description='=== Discretize Step ===',
                                      help='The discretization step')
    extract = subparser.add_parser('extract', description='=== Extract Step ===', help='The extract step')
    match = subparser.add_parser('match', description='=== Match Step ===', help='The pattern matching step')
    plot = subparser.add_parser('plot', description='=== Plot Step ===', help='The plotting step')
    all_steps = subparser.add_parser('all', description='=== All Steps ===', help='Run all steps')

    # Discretize
    discretize = add_common_args(discretize)
    subparser_list.append(add_discretize_args(discretize))

    # Extract
    extract = add_common_args(extract)
    subparser_list.append(add_extract_args(extract))

    # Match
    match = add_common_args(match)
    subparser_list.append(add_match_args(match))

    # Plot
    plot = add_common_args(plot)
    subparser_list.append(add_plot_args(plot))

    # All steps
    subparser_list.append(add_all_args(all_steps))

    return parser, subparser_list


def process_assign_args(arguments):
    """
    Process arguments for w_assign.

    Parameters
    ----------
    arguments : argparse.Namespace
        Parsed arguments by parser.

    """
    # Check if any extra w_assign arguments are specified in command line.
    if arguments.we and (arguments.step_name in ['discretize', 'all']):
        # If using we and doing discretize step
        if arguments.assign_args != '':
            # Try to import and process ``w_assign`` arguments
            try:
                import westpa
                from westpa.cli.tools import w_assign
            except ModuleNotFoundError as e:
                print(e)
                raise ModuleNotFoundError("Trying to discretize an HDF5 file but can't import w_assign")

            tool = w_assign.WAssign()
            final_ns = tool.make_parser_and_process(args=arguments.assign_args.split())
            setattr(arguments, 'assign_args', final_ns)
        else:
            # Use default arguments instead
            default_args = argparse.Namespace(  # These are arguments for w_assign
                verbosity='verbose',  # Verbose or debug
                rcfile='west.cfg',  # west.cfg
                max_queue_length=None,
                we_h5filename='west.h5',  # west.h5 path
                construct_dataset=None,  # If you need some custom auxiliary dataset
                dsspecs=None,
                output='assign.h5',  # Output file
                subsample=None,
                config_from_file=True,  # Read config from rcfile
                scheme='TEST',  # Scheme name
            )
            setattr(arguments, 'assign_args', default_args)

    else:
        log.debug('Not using w_assign.')

    return arguments


def process_args(parser):
    """
    Actually process whatever passed to the parser.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        An instance of argument parser.

    Returns
    -------
    args : argparse.Namespace
        A Namespace object with all the argument parsed.

    """
    args = parser.parse_args()
    # Automatically parse arguments for w_assign
    args = process_assign_args(args)

    # Process extract arguments
    if args.step_name in ['extract', 'all']:
        # Automatically turn on Ray unless no_ray is specified. A
        if args.use_ray:
            try:
                import ray
                setattr(args, 'use_ray', True)
            except (ModuleNotFoundError, ImportError, AttributeError) as e:
                setattr(args, 'use_ray', False)
                log.debug(e)
                log.info(f'INFO: Unable to load Ray. Will proceed without using Ray.')

    # Turn Debugging on!
    if args.debug is True:
        logging.basicConfig(level=logging.DEBUG)

    return args


def check_argv():
    """
    Check to see if argv > 2 is empty. Print warning if so.

    """
    import sys
    if len(sys.argv) < 3 and sys.argv[1] in all_options:
        log.warning(f'WARNING: Running {sys.argv[1]} with all default values. Make sure you\'re sure of this!')