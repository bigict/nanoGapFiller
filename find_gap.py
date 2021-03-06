import sys
import getopt
import xmap_file
import cmap_file
import gap_info_file


LEN_SITE = 7

def print_help():
    # body = '-r <unmodified_reference_cmap> <_r_cmap> <_q_cmap> <xmap_file> <gap info file>'
    body = '[-k <key transform txt>] [-m 0/1] <_r_cmap> <_q_cmap> <xmap_file> <gap info file>'
    print("python3 {} {}".format(__file__, body))


def get_reversed_name(original_name):
    if original_name.endswith("'"):
        return original_name[:-1]
    else:
        return original_name + "'"

def main():
    mode = 0
    # unmodified_reference_cmap = None
    query_key_txt = None
    interface = 'hm:k:'
    options, args = getopt.getopt(sys.argv[1:], interface)
    for option, value in options:
        if option == '-h':
            print_help()
            sys.exit()
        elif option == '-k':
            query_key_txt = value
        elif option == '-m':
            mode = int(value)
    r_cmap, q_cmap, xmap_file_name, output_file = args

    if query_key_txt:
        query_key_index = {}
        with open(query_key_txt) as fin:
            for line in filter(lambda x: not x.startswith('#'), fin):
                tokens = line.split('\t')
                query_key_index[tokens[0]] = tokens[1]
    
    alignments = xmap_file.read_file_2(xmap_file_name)
    # Transform subject site indexs.
    query_cmap = cmap_file.read_file(q_cmap)
    # unmodified_cmap = cmap_file.read_file(unmodified_reference_cmap)
    second_cmap = cmap_file.read_file(r_cmap)
    # transform_arrays = cmap_file.compare_cmaps(second_cmap,
        # unmodified_cmap)
    index_by_subject_id = {}
    if mode == 0:
        alignments = filter(lambda x: x['oritation'], alignments)
    reversed_alignment = set()
    for alignment in alignments:
        if mode == 1 and alignment['oritation'] == False:
            alignment['subject_start_index'], alignment['subject_end_index'] = \
                alignment['subject_end_index'], alignment['subject_start_index']
            num_site = len(query_cmap[alignment['id_query']].positions)
            alignment['query_start_index'], alignment['query_end_index'] = (
                num_site - alignment[ele] - 1 for ele in ('query_end_index', 'query_start_index'))
            alignment['oritation'] = True
            reversed_alignment.add(alignment['id_query'])
        # alignment['subject_start_index'] = transform_arrays[alignment[
            # 'id_ref']][alignment['subject_start_index']]
        # alignment['subject_end_index'] = transform_arrays[alignment[
            # 'id_ref']][alignment['subject_end_index']]
        try:
            index_by_subject_id[alignment['id_ref']].append(alignment)
        except KeyError:
            index_by_subject_id[alignment['id_ref']] = [alignment]

    if mode == 1:
        for cmap in query_cmap.values():
            if cmap.id in reversed_alignment:
                cmap.reverse(LEN_SITE)

    # Collect gaps.
    fout = open(output_file, 'w')
    for subject_id, alignments in index_by_subject_id.items():
        # Sort alignment by subject index id.
        alignments.sort(key=lambda x: x['subject_start_index'])

        for i in range(len(alignments) - 1):
            start_node_id = alignments[i]['id_query']
            end_node_id = alignments[i + 1]['id_query']
            start_site_index = alignments[i]['query_end_index']
            start_site_position = \
                query_cmap[start_node_id].positions[start_site_index]
            end_site_index = alignments[i + 1]['query_start_index']
            end_site_position = \
                query_cmap[end_node_id].positions[end_site_index]
            positions = second_cmap[subject_id].positions[
                alignments[i]['subject_end_index'] : \
                alignments[i + 1]['subject_start_index'] + 1
            ]
            intervals = []
            for i in range(len(positions) - 1):
                intervals.append(positions[i + 1] - positions[i])
            start_node_id = query_key_index[start_node_id] if start_node_id not in reversed_alignment else get_reversed_name(query_key_index[start_node_id])
            end_node_id = query_key_index[end_node_id] if end_node_id not in reversed_alignment else get_reversed_name(query_key_index[end_node_id])
            new_gap = gap_info_file.Gap(start_node_id, end_node_id, 
                start_site_index, start_site_position,
                end_site_index, end_site_position, intervals)
            new_gap.write_to_file(fout)
    fout.close()


if __name__ == '__main__':
    main()
