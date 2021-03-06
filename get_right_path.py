import sys
import getopt
import itertools

import fastg_file
import dot_file
from Bio import SeqIO

def parse_node_long_name(long_name):
    short_name, _ = fastg_file.read_long_name(long_name)
    uid, length, _, is_reverse = fastg_file.read_short_name(short_name)
    uid += ('r' if is_reverse else '')
    return uid, length

class Alignment:

    VALID_THRESHOLD = 0.9
    ERROR_MARGIN = 1
    COLOR_PROFILE = ['green', 'yellow', 'yellow', 'orange', 'orange',
        'red']

    def __init__(self, alignment_line):
        self.line = alignment_line
        tokens = alignment_line.rstrip().split('\t')
        self.query_id = tokens[0]
        self.subject_id = tokens[1]
        self.query_node_id, query_node_len = parse_node_long_name(
            self.query_id
        )
        identity = float(tokens[2]) / 100
        alignment_length = int(tokens[3])
        self.alignment_length = alignment_length
        self.num_mismatch = int(tokens[4])
        self.gap_open = int(tokens[5])
        q_start, q_end, s_start, s_end = map(int, tokens[6:10])
        self.start_cut = q_start - 1
        self.end_cut = query_node_len - q_end
        self.num_delete = alignment_length - (abs(q_start - q_end) + 1)
        self.num_insert = alignment_length - (abs(s_start - s_end) + 1)
        self.e_value = float(tokens[10])
        self.bit_score = float(tokens[11])
        self.start = s_start
        self.end = s_end
        self.left = min(s_start, s_end)
        self.right = max(s_start, s_end)
        self.identity = alignment_length * identity / query_node_len
        self.is_valid = True if\
            self.identity > Alignment.VALID_THRESHOLD else False
        self.is_forward = s_end > s_start
        self.children = []
        self.num_mistake = self.num_mismatch + self.gap_open
        self.color = self.COLOR_PROFILE[min(len(self.COLOR_PROFILE) - 1,
            self.num_mismatch)]

    def __str__(self):
        return ','.join((self.query_node_id,
            '-'.join(map(str, (self.start, self.end))),
            str(self.end - self.start + 1)
            ))

    def add_child(self, alignment):
        self.children.append(alignment)

    def adjacent_before(self, alignment, overlap):
        """This mean self is adjacent to `alignment` and 
        `self` is on the upper stream of `alignment`."""
        min_insert = min(self.num_insert, alignment.num_insert)
        min_delete = min(self.num_delete, alignment.num_delete)
        # To be True, two alignment must be in the same ref and have
        # the same direction.
        is_same_dir = (self.is_forward == alignment.is_forward and
            self.subject_id == alignment.subject_id)
        shift = overlap - 1
        if not is_same_dir:
            return False
        if self.is_forward:
            real_self_end = self.end + self.end_cut
            result_other_start = alignment.start - alignment.start_cut
            valid_l = result_other_start  - min_insert - \
                Alignment.ERROR_MARGIN
            valid_h = result_other_start + min_delete + \
                Alignment.ERROR_MARGIN
            return valid_l <= real_self_end - shift <= valid_h
        else:
            real_self_end = self.end - self.end_cut
            real_other_start = alignment.start + alignment.start_cut
            valid_l = real_other_start - min_delete - \
                Alignment.ERROR_MARGIN
            valid_h = real_other_start + min_insert + \
                Alignment.ERROR_MARGIN
            return valid_l <= real_self_end + shift <= valid_h

    @classmethod
    def index(cls, alignments, key):
        if key == 'node id':
            key_attr = 'query_node_id'
        elif key == 'start position':
            key_attr = 'start'
        else:
            raise ValueError('Key not supported.')
        index = {}
        for alignment in alignments:
            if getattr(alignment, key_attr) in index:
                index[getattr(alignment, key_attr)].append(alignment)
            else:
                index[getattr(alignment, key_attr)] = [alignment]
        return index

    @classmethod
    def add_connection(cls, alignments, nodes):
        """Only for those forward alignments"""
        alignments = list(filter(lambda x: x.is_forward, alignments))
        # Sort method.
        alignments.sort(key=lambda x: x.start)
        for i in range(len(alignments)):
            for child_node, overlap in\
                    nodes[alignments[i].query_node_id].children:
                safe_margin = 50
                stop_position = alignments[i].end - (overlap - 1) + \
                    safe_margin
                j = i + 1
                while j < len(alignments) and \
                        alignments[j].start < stop_position:
                    if alignments[j].query_node_id == \
                            child_node.uid and \
                            alignments[i].adjacent_before(alignments[j],
                                overlap):
                        alignments[i].add_child(alignments[j])
                    j += 1

    @classmethod
    def write_alignments_to_dot_file(cls, alignments, file_name,
            actions=None, values=None):
        with dot_file.DotFile(file_name) as fout:
            for alignment in alignments:
                attribute = {"color": alignment.color}
                if values:
                    attribute["label"] = str(alignment) + ',' + \
                        str(values[alignment])
                fout.add_node(str(alignment), attribute)
                if alignment.children:
                    for child in alignment.children:
                        attribute = {}
                        if actions and actions[alignment] == child:
                            attribute['color'] = 'green'
                        fout.add_edge(*map(str, (alignment, child)),
                            attribute)

    @classmethod
    def write_path_to_dot_file(cls, actions, values, file_name):
        # matched_node_ids = ['252510', '252526', '252226', '252410r', '252216r', '252312', '253626r', '252316', '252486', '252292', '252290', '252244', '252042r', '252228', '252546', '252466', '251900r', '252386r', '252206r', '252434', '252180', '252148', '252482', '252310r', '252382r', '252424r', '252458r', '252036', '251936r', '252408r', '252538r', '253628r', '252448r', '252300', '252208', '252238', '252252', '252288', '252132', '251622r', '252506', '252268r']
        matched_node_ids = ['252514', '253626r', '252292', '252510', '252196', '252226', '252216r', '252526', '252486', '252312']
        special_id = set(matched_node_ids)
        with dot_file.DotFile(file_name) as fout:
            alignment_values = list(values.items())
            alignments, values_ = zip(*alignment_values)
            max_index = values_.index(max(values_))
            alignment = alignments[max_index]
            next_alignment = actions[alignment]
            while next_alignment:
                attribute = {"color": alignment.color}
                if alignment.query_node_id in special_id:
                    attribute["style"] = "filled"
                    attribute["fillcolor"] = 'red'
                    special_id.remove(alignment.query_node_id)
                fout.add_node(str(alignment), attribute)
                fout.add_edge(*map(str, (alignment, next_alignment)))
                alignment = next_alignment
                next_alignment = actions[alignment]
        print('remain special nodes:', special_id)
    
    @classmethod
    def get_path(cls, alignments):
        values = {a: (a.alignment_length - a.num_mistake) \
            for a in alignments}
        actions = {a: (a.children[0] if a.children else None) \
            for a in alignments}
        n_count = 0
        to_update = True
        alignments.sort(key=lambda a: a.start, reverse=True)
        while to_update:
            to_update = False
            for alignment in alignments:
                if actions[alignment]:
                    next_alignemnt = actions[alignment]
                    # Update values of alignments.
                    overlap_size = alignment.end - \
                        next_alignemnt.start + 1
                    old_value = values[alignment]
                    new_value = values[next_alignemnt] + \
                        (alignment.alignment_length - \
                        alignment.num_mistake) - overlap_size
                    if new_value != old_value:
                        to_update = True
                        values[alignment] = new_value

                    children_values = [values[child] for \
                        child in alignment.children]
                    # Update action of alignments. 
                    actions[alignment] = alignment.children[
                        children_values.index(max(children_values))
                    ]
            n_count += 1
        print(len(alignments), n_count)
        return values, actions

def read_file(file_name):
    alignments = []
    with open(file_name) as fin:
        for line in filter(lambda x: not x.startswith('#'), fin):
            # Parse a line.
            alignment = Alignment(line)
            alignments.append(alignment)
    return alignments

def is_adjacent(node_a, node_b, node_id2alignments, overlap):
    for alignment_a, alignment_b in itertools.product(
            node_id2alignments[node_a], node_id2alignments[node_b]):
        if alignment_a.adjacent_before(alignment_b, overlap):
            return True
    return False

def write_file(output_file, alignments):
    fout = open(output_file, 'w')
    for alignment in alignments:
        fout.write(alignment.line)
        for child in alignment.children:
            fout.write('\t')
            fout.write(child.line)
        fout.write('\n')
    fout.close()

def print_help_message():
    body = '[-h] <-l overlap len> <fastg file> <blast result> <output>'
    print('python3 {} {}'.format(__file__, body))

def main():
    fastg_file_name = ''
    blast_result_file = ''
    output_file = ''
    overlap_len = None
    options, args = getopt.getopt(sys.argv[1:], 'hl:')
    for option, value in options:
        if option == '-l':
            overlap_len = int(value)
        elif option == '-h':
            print_help_message()
            sys.exit()
        else:
            print_help_message()
            sys.exit()
    fastg_file_name, blast_result_file, output_file = args

    nodes = fastg_file.build_assembly_graph(fastg_file_name,
        overlap_len)
    alignments = list(filter(lambda x: x.is_valid and x.is_forward,
        read_file(blast_result_file)))
    Alignment.add_connection(alignments, nodes)
    alignments.sort(key=lambda x: x.start)
    # write_file(output_file, alignments)
    values, actions = Alignment.get_path(alignments)
    # Alignment.write_alignments_to_dot_file(alignments, output_file,
        # actions, values)
    Alignment.write_path_to_dot_file(actions, values, output_file)

if __name__ == '__main__':
    main()
