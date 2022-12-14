import daisy
import time
import json
import os.path
import networkx as nx
import numpy as np
import argparse
from funlib import evaluate
from evalutils.evalutils import (
    DEFAULT_INPUT_PATH,
    DEFAULT_EVALUATION_OUTPUT_FILE_PATH,
    DEFAULT_GROUND_TRUTH_PATH,
)

def assign_skeleton_indexes(graph):
    '''Assign unique ids to each cluster of connected nodes. This is to
    differentiate between sets of nodes that are discontinuous in the
    ROI but actually belong to the same skeleton ID, which is necessary
    because the network should not be penalized for incorrectly judging
    that these processes belong to different neurons.'''
    skeleton_index_to_id = {}
    skel_clusters = nx.connected_components(graph)
    for i, cluster in enumerate(skel_clusters):
        for node in cluster:
            graph.nodes[node]['skeleton_index'] = i
        skeleton_index_to_id[i] = graph.nodes[cluster.pop()]['skeleton_id']
    return graph


def add_predicted_seg_labels_from_vol(
        graph, segment_array):

    bg_nodes=0

    nodes_outside_roi = []  
    for i, (treenode, attr) in enumerate(graph.nodes(data=True)):
        pos = attr["position"]
        try:    
            attr['zyx_coord'] = (pos[2], pos[1], pos[0])
            attr['seg_label'] = segment_array[daisy.Coordinate(attr['zyx_coord'])]
            if attr['seg_label'] == 0:
                bg_nodes+=1
                raise AssertionError
        except AssertionError as e:
            nodes_outside_roi.append(treenode)

    print(f'Removing {len(nodes_outside_roi)} GT annotations outside of evaluated ROI')
    for node in nodes_outside_roi:
        graph.remove_node(node)

    print('BG_NODES',bg_nodes)
    return assign_skeleton_indexes(graph)


def generate_graphs_with_seg_labels(segment_array, skeleton_path, num_processes):
    unlabeled_skeleton = np.load(skeleton_path, allow_pickle=True)
    return add_predicted_seg_labels_from_vol(unlabeled_skeleton.copy(), segment_array)    


def eval_erl(skeleton_file, segment_array):
    
    node_seg_lut = {}
    graph_list = generate_graphs_with_seg_labels(segment_array, skeleton_file, 1)
    for node, attr in graph_list.nodes(data=True):
        node_seg_lut[node]=attr['seg_label']

    res = evaluate.expected_run_length(skeletons=graph_list,skeleton_id_attribute='skeleton_id',
                        node_segment_lut=node_seg_lut,skeleton_position_attributes=['zyx_coord'],
                        return_merge_split_stats=False,edge_length_attribute='edge_length')

    return res


class XPRESS:
    def __init__(self):
        self.input_file = os.path.join(DEFAULT_INPUT_PATH, "test_pred.h5")
        self.output_file = DEFAULT_EVALUATION_OUTPUT_FILE_PATH
        self.gt_file = os.path.join(DEFAULT_GROUND_TRUTH_PATH, "100nm_Cutout6_Testing_1025.npz")
        self.segmentation_ds = 'submission'

    def evaluate(self):
        # load segmentation
        segment_array = daisy.open_ds(self.input_file, self.segmentation_ds)
        segment_array = segment_array[segment_array.roi]

        # downsample if necessary
        if segment_array.data.shape == (1072, 1072, 1072):
            ndarray = segment_array.data[::3, ::3, ::3]
            ds_voxel_size = segment_array.voxel_size * 3
            # align ROI
            roi_begin = (segment_array.roi.begin // ds_voxel_size) * ds_voxel_size
            roi_shape = daisy.Coordinate(ndarray.shape) * ds_voxel_size
            segment_array = daisy.Array(data=ndarray,
                                        roi=daisy.Roi(roi_begin, roi_shape),
                                        voxel_size=ds_voxel_size
                                        )

        # load to mem
        segment_array.materialize()
        metrics = {"Expected run-length": eval_erl(self.gt_file, segment_array)}

        with open(self.output_file, "w") as f:
            f.write(json.dumps(metrics))


if __name__ == "__main__":
    XPRESS().evaluate()