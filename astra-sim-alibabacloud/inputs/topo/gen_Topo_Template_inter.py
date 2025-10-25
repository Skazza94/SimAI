"""
This file can generate topology of AlibabaHPN, Spectrum-X, DCN+.
Users can freely customize the topology according to their needs。
"""

import argparse
import warnings
import json
import os
from pathlib import Path


def Rail_Opti_SingleToR(parameters):
    print("num dcs: " + str(parameters["n_dcs"]))

    nodes_per_asw = parameters['nics_per_aswitch']
    asw_switch_num_per_segment = parameters['gpu_per_server']
    if(parameters['gpu'] % (nodes_per_asw * asw_switch_num_per_segment) == 0):
        segment_num = (int)(parameters['gpu']/ (nodes_per_asw * asw_switch_num_per_segment))
    else:
        segment_num = (int)(parameters['gpu']/ (nodes_per_asw * asw_switch_num_per_segment))+1
    
    if(segment_num != parameters['asw_switch_num'] / asw_switch_num_per_segment):
        warnings.warn("Error relations between total GPU Nums and total aws_switch_num.\n \
                         The correct asw_switch_num is set to "+str(segment_num * asw_switch_num_per_segment))
        parameters['asw_switch_num'] = segment_num * asw_switch_num_per_segment
    print("asw_switch_num: " + str(parameters['asw_switch_num']))
    if segment_num > int(parameters['asw_per_psw'] /  asw_switch_num_per_segment):
        raise ValueError("Number of GPU exceeds the capacity of Rail_Optimized_SingleToR(One Pod)")
    pod_num = 1
    print("psw_switch_num: " + str(parameters['psw_switch_num']))
    print("Creating single DC of totally " + str(segment_num) + " segment(s), totally "+ str(pod_num) + " pod(s)." )  

    nv_switch_num = ((int)(parameters['gpu'] / parameters['gpu_per_server']) * parameters['nv_switch_per_server'])
    nodes = ((int) (parameters['gpu'] + parameters['asw_switch_num'] + parameters['psw_switch_num']+ nv_switch_num + (1 if parameters['n_dcs'] > 1 else 0))) * parameters["n_dcs"] 
    switch_nodes = ((int)(parameters['psw_switch_num'] + parameters['asw_switch_num'] + nv_switch_num + (1 if parameters['n_dcs'] > 1 else 0))) * parameters["n_dcs"] 
    
    nv_switch = []
    asw_switch = []
    psw_switch = []
    dsw_switch = []

    nnodes = nodes - switch_nodes
    for i in range(nnodes, nodes):
        if len(nv_switch) < nv_switch_num * parameters["n_dcs"]:
            nv_switch.append(i)
        elif len(asw_switch) < parameters['asw_switch_num'] * parameters["n_dcs"]:
            asw_switch.append(i)
        elif len(psw_switch) < parameters['psw_switch_num'] * parameters["n_dcs"]:
            psw_switch.append(i)
        else:
            dsw_switch.append(i)

    lines = []
    ind_asw = 0
    curr_node = 0
    group_num = 0
    group_account = 0
    ind_nv = 0
    curr_dc = 0
    for i in range(parameters['gpu'] * parameters['n_dcs']):
        curr_node = curr_node + 1
        if curr_node > parameters['gpu_per_server']:
            curr_node = 1
            ind_nv = ind_nv + parameters['nv_switch_per_server']
        if i > 0 and i % parameters['gpu'] == 0:
            curr_dc += 1
            ind_asw = (asw_switch_num_per_segment * segment_num) * curr_dc
            group_num = 0
            group_account = 0
        
        for j in range(0, parameters['nv_switch_per_server']):
            lines.append(str(i)+" "+str(nv_switch[ind_nv+j])+" "+str(parameters['nvlink_bw'])+" "+str(parameters['nv_latency'])+" "+str(parameters['error_rate']))
        lines.append(str(i)+" "+str(asw_switch[group_num*asw_switch_num_per_segment+ind_asw])+" "+str(parameters['bandwidth'])+" "+str(parameters['latency'])+" "+str(parameters['error_rate']))
                
        ind_asw = ind_asw + 1
        group_account = group_account + 1
        if ind_asw == asw_switch_num_per_segment + ((asw_switch_num_per_segment * segment_num) * curr_dc):
            ind_asw = (asw_switch_num_per_segment * segment_num) * curr_dc
        if group_account == (parameters['gpu_per_server'] * parameters['nics_per_aswitch']):
            group_num = group_num + 1
            group_account = 0

    for dc in range(parameters['n_dcs']):
        asw_dc_offset = parameters['asw_switch_num'] * dc
        psw_dc_offset = parameters['psw_switch_num'] * dc
        for i in asw_switch[asw_dc_offset:asw_dc_offset+parameters['asw_switch_num']]:
            for j in psw_switch[psw_dc_offset:psw_dc_offset+parameters['psw_switch_num']]:
                lines.append(str(i) + " " + str(j) +" "+ str(parameters['ap_bandwidth'])+" " +str(parameters['latency'])+" "+str(parameters['error_rate']))

    for dc, i in enumerate(dsw_switch):
        psw_dc_offset = parameters['psw_switch_num'] * dc
        for j in psw_switch[psw_dc_offset:psw_dc_offset+parameters['psw_switch_num']]:
            lines.appendbin(str(j) + " " + str(i) +" "+ str(parameters['ap_bandwidth'])+" " +str(parameters['latency'])+" "+str(parameters['error_rate']))

    dsw_pairs = set()
    for dc1, i in enumerate(dsw_switch):
        for dc2, j in enumerate(dsw_switch):
            if dc1 == dc2:
                continue
            if (i, j) not in dsw_pairs and (j, i) not in dsw_pairs:
                dsw_pairs.add((i, j))
    for i, j in dsw_pairs:
        lines.append(str(i) + " " + str(j) +" "+ str(parameters['ap_bandwidth'])+" " +str(parameters['interdc_lat'])+" "+str(parameters['error_rate']))

    file_name = "Spectrum-X_"+str(parameters['gpu'])+"g_"+str(parameters['gpu_per_server'])+"gps_"+parameters['bandwidth']+"_"+parameters['gpu_type']+"_"+str(parameters['n_dcs'])+"_"+str(parameters['interdc_lat'])
    with open(file_name, 'w') as f:
        first_line = str(nodes)+" "+str(parameters['gpu_per_server'])+" "+str(len(nv_switch))+" "+str(switch_nodes-len(nv_switch))+" "+str(len(lines))+" "+str(parameters['gpu_type'])+" "+str(parameters['n_dcs'])
        f.write(first_line)
        f.write('\n')

        f.write(" ".join(map(lambda x: str(x), nv_switch + asw_switch + psw_switch + dsw_switch)))
        f.write('\n')

        f.write("\n".join(lines))

    current_path = os.path.dirname(Path(__file__).absolute())
    with open(os.path.join(current_path, "topology.tpl.html"), "r") as topology_tpl_file:
        topology_tpl = topology_tpl_file.read()

    id2name = {}
    id2server = {}
    curr_dc = 1
    server_count = 0
    segment_count = -1
    dc = {"nodes": set(), "links": []}
    for line in lines:
        src, dst, bw, lat, _ = line.split(" ")
        src = int(src)
        dst = int(dst)

        if src < parameters['gpu'] * parameters['n_dcs']:
            if dst in nv_switch:
                continue

            if src > 0 and src % parameters['gpu'] == 0:
                curr_dc += 1

            if dst not in id2name:
                asw_idx = asw_switch.index(dst)
                asw_count = asw_idx % asw_switch_num_per_segment
                if asw_count == 0:
                    if (segment_count+1) < segment_num:
                        segment_count += 1
                    else:
                        segment_count = 0

                id2name[dst] = f"dc{curr_dc}_asw_{segment_count}_{asw_count}"

            if src not in id2name:
                if src > 0 and src % parameters['gpu_per_server'] == 0:
                    if src not in id2server:
                        server_count += 1
                        id2server[src] = server_count
                    else:
                        server_count = id2server[src]

                id2name[src] = f"dc{curr_dc}_server_{segment_count}_{server_count}"
        elif src in asw_switch:
            dc_str, _, seg, _ = id2name[src].split('_')

            if dst not in id2name:
                psw_idx = psw_switch.index(dst)
                psw_count = psw_idx % parameters['psw_switch_num']
                id2name[dst] = f"{dc_str}_psw_{seg}_{psw_count}"
        elif src in psw_switch:
            dc_str, _, _, _ = id2name[src].split('_')

            if dst not in id2name:
                id2name[dst] = f"{dc_str}_dsw_0_0"
                
        dc["nodes"].add(id2name[src])
        dc["nodes"].add(id2name[dst])
        dc["links"].append({"source": id2name[src], "target": id2name[dst], "value": f"bw:{bw}|lat:{lat}", "label": f"bw:{bw}|lat:{lat}"})

    dc["nodes"] = [{"id": x, "label": x} for x in dc["nodes"]]

    topology_tpl = topology_tpl.replace('"%GRAPH%"', json.dumps(dc))
    with open(f"{file_name}_topology.html", "w") as topo_file:
        topo_file.write(topology_tpl)

    with open(f"{file_name}_meta.txt", "w") as f:
        f.write(json.dumps({
            "n_dcs": parameters["n_dcs"],
            "gpus_per_dc": parameters['gpu'],
            "gpus_per_server": parameters['gpu_per_server'],
            "segment_num": segment_num,
            "total_nodes": nodes,
            "nv_switch": nv_switch,
            "asw_switch": asw_switch,
            "psw_switch": psw_switch,
            "dsw_switch": dsw_switch,
            "id2name": id2name
        }, indent=4))

def main():
    parser = argparse.ArgumentParser(description='Python script for generating a topology for SimAI')

    #Whole Structure Parameters:
    parser.add_argument('-g','--gpu',type=int,default=None,help='gpus num, default 32')
    parser.add_argument('-er','--error_rate',type=str,default=None,help='error_rate, default 0')
    #Intra-Host Parameters:
    parser.add_argument('-gps','--gpu_per_server',type=int,default=None,help='gpu_per_server, default 8')
    parser.add_argument('-gt','--gpu_type',type=str,default=None,help='gpu_type, default H100')
    parser.add_argument('-nsps','--nv_switch_per_server',type=int,default=None,help='nv_switch_per_server, default 1')
    parser.add_argument('-nvbw','--nvlink_bw',type=str,default=None,help='nvlink_bw, default 2880Gbps')
    parser.add_argument('-nl','--nv_latency',type=str,default=None,help='nv switch latency, default 0.000025ms')
    parser.add_argument('-l','--latency',type=str,default=None,help='nic latency, default 0.0005ms')
    #Intra-Segment Parameters:
    parser.add_argument('-bw','--bandwidth',type=str,default=None,help='nic to asw bandwidth, default 400Gbps')
    parser.add_argument('-asn','--asw_switch_num',type=int,default=None,help='asw_switch_num, default 8')
    parser.add_argument('-npa','--nics_per_aswitch',type=int,default=None,help='nnics per asw, default 64')
    #Intra-Pod Parameters:
    parser.add_argument('-psn','--psw_switch_num',type=int,default=None,help='psw_switch_num, default 64')
    parser.add_argument('-apbw','--ap_bandwidth',type=str,default=None,help='asw to psw bandwidth,default 400Gbps')   
    parser.add_argument('-app','--asw_per_psw',type=int,default=None,help='asw for psw')

    parser.add_argument('-dcs','--n_dcs',type=int,default=None,help='Number of DCs to create, default 1')
    parser.add_argument('-il','--interdc_lat',type=str,default=None,help='interdc latency, default 0.0005ms')

    args = parser.parse_args()

    default_parameters = []
    parameters = analysis_template(args, default_parameters)
    Rail_Opti_SingleToR(parameters)


def analysis_template(args, default_parameters):
    # Basic default parameters
    default_parameters = {'rail_optimized': True, 'dual_ToR': False, 'dual_plane': False, 'gpu': 32, 'error_rate':0,
                          'gpu_per_server': 8, 'gpu_type': 'H100', 'nv_switch_per_server': 1, 
                          'nvlink_bw': '2880Gbps','nv_latency': '0.000025ms', 'latency': '1us',
                          'bandwidth': '400Gbps', 'asw_switch_num': 8,  'nics_per_aswitch': 64,
                          'psw_switch_num': 64, 'ap_bandwidth': "400Gbps", 'asw_per_psw' : 64, 'n_dcs': 1, 'interdc_lat': '0.0005ms'}
    parameters = {}

    default_parameters.update({
        'gpu': 4096
    })
    parameters.update({
        'rail_optimized': True, 
        'dual_ToR': False, 
        'dual_plane': False,
    })
    
    parameter_keys = [
        'gpu', 'error_rate', 'gpu_per_server', 'gpu_type', 'nv_switch_per_server',
        'nvlink_bw', 'nv_latency', 'latency', 'bandwidth', 'asw_switch_num',
        'nics_per_aswitch', 'psw_switch_num', 'ap_bandwidth','asw_per_psw', 'n_dcs', 'interdc_lat'
    ]
    for key in parameter_keys:
        parameters[key] = getattr(args, key, None) if getattr(args, key, None) is not None else default_parameters[key]
    # for key, value in parameters.items():
    #     print(f'{key}: {value}')
    # print("==================================")
    return parameters


if __name__ =='__main__':
    main()